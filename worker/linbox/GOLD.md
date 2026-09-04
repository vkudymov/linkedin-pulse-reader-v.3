# session_snapshot GOLD

Source: Linbox converters. Copy these functions verbatim into Pulse `session_snapshot`,
then type them. Do not simplify cookie conversion.

Consumer: LinkedIn Pulse Reader worker. LinkedIn-only. Do not port Linbox product
(accounts, MCP, tasks, limits).

Linbox paths:
- `api/tools/session_capture_html.py`
- `api/tools/session_export.py`
- `api/services/linkedin_browser_session.py` (restore / save-back order)
- `linbox-extension/service-worker.js` (optional MV3 capture)
- `linbox-extension/content-script.js` (optional page env)

## Pulse LinkedIn config (fixed)

- `TARGET_HOST_SUFFIX` = `linkedin.com`
- `AUTH_COOKIE_NAME` = `li_at`
- `DEFAULT_ORIGIN` = `https://www.linkedin.com`
- `LOGOUT_URL_HINTS` = `["/login", "/checkpoint", "/authwall", "/uas/"]`

Match Pulse `FeedNavigator` login-wall. `li_at` is the auth cookie gate.

## Invariants

1. Persist **Chrome cookie objects**. Convert only at the Playwright boundary.
2. If a cookie has `domain`, pass `domain` + `path`. Never convert those to host-only via `url` only.
3. Chrome sameSite: `no_restriction` → Playwright `None`; `lax` → `Lax`; `strict` → `Strict`; `unspecified` → omit.
4. Chrome `expirationDate` → Playwright `expires` (int). Reverse on export.
5. Restore order: `add_cookies` → `page.goto(origin, wait_until="commit")` → `apply_storage_snapshot` → caller `goto(https://www.linkedin.com/feed/)`.
6. If `is_logged_out(page.url)`: **do not save-back**.
7. Never log cookie values. Counts / domains are OK.
8. Old Pulse rows store a Playwright cookie **list** in `linkedin_accounts.cookies_json`. Read them through an adapter into a minimal snapshot. Do not pass that list into `add_cookies` without going through `to_playwright_cookies` after the adapter (adapter output cookies are already Playwright-shaped or Chrome-shaped — see PROMPT).

## Payload shape (source of truth on disk)

```json
{
  "createdAt": "ISO-8601",
  "cookies": ["raw chrome.cookies.getAll objects OR Chrome-shaped exports"],
  "storage": {
    "origin": "https://www.linkedin.com",
    "localStorage": {},
    "sessionStorage": {}
  },
  "browser": {
    "userAgent": "",
    "language": "",
    "languages": [],
    "platform": "",
    "timeZone": null,
    "headersProfile": { "accept-language": "" }
  },
  "viewport": {
    "innerWidth": 0,
    "innerHeight": 0,
    "devicePixelRatio": 1,
    "colorDepth": 24
  },
  "tab": { "url": "", "title": "" },
  "diagnostics": { "cookieCount": 0, "captured_at": "", "source": "server_browser" }
}
```

Pulse today has no storage/UA. After Playwright UI login, `export_session` fills storage from the live page. Until then, adapter snapshots may have empty `storage` / `browser` / `viewport`.

---

## Python: Chrome → Playwright

From `api/tools/session_capture_html.py`.

```python
def chrome_cookie_to_playwright(cookie: dict[str, Any]) -> dict[str, Any]:
    domain = cookie.get("domain")
    domain_without_dot = (domain or "").lstrip(".")
    path = cookie.get("path") or "/"
    scheme = "https" if cookie.get("secure", False) else "http"
    cookie_url = f"{scheme}://{domain_without_dot}{path}" if domain_without_dot else None

    same_site_map = {
        "no_restriction": "None",
        "lax": "Lax",
        "strict": "Strict",
        "unspecified": None,
        "None": "None",
        "Lax": "Lax",
        "Strict": "Strict",
    }
    normalized_same_site = same_site_map.get(cookie.get("sameSite") or "")

    playwright_cookie: dict[str, Any] = {
        "name": cookie["name"],
        "value": cookie["value"],
        "secure": bool(cookie.get("secure", False)),
        "httpOnly": bool(cookie.get("httpOnly", False)),
    }
    if normalized_same_site:
        playwright_cookie["sameSite"] = normalized_same_site
    expires = cookie.get("expirationDate")
    if isinstance(expires, (int, float)) and expires > 0:
        playwright_cookie["expires"] = int(expires)

    if domain:
        playwright_cookie["domain"] = domain
        playwright_cookie["path"] = path
    elif cookie_url:
        playwright_cookie["url"] = cookie_url
    return playwright_cookie


def apply_storage_snapshot(page: Any, storage_snapshot: dict[str, Any]) -> None:
    local_items = storage_snapshot.get("localStorage", {})
    session_items = storage_snapshot.get("sessionStorage", {})
    page.evaluate(
        """({ localItems, sessionItems }) => {
            localStorage.clear();
            sessionStorage.clear();
            for (const [k, v] of Object.entries(localItems || {})) {
                localStorage.setItem(k, v ?? "");
            }
            for (const [k, v] of Object.entries(sessionItems || {})) {
                sessionStorage.setItem(k, v ?? "");
            }
        }""",
        {"localItems": local_items, "sessionItems": session_items},
    )
```

---

## Python: Playwright → Chrome + merge

From `api/tools/session_export.py`.

Public API rename: `account_timezone` → optional `browser_timezone`.
Keep merge behavior: only overwrite `browser.timeZone` when a non-empty value is passed.

```python
def playwright_cookies_to_extension(cookies: list[dict[str, Any]]) -> list[dict[str, Any]]:
    exported: list[dict[str, Any]] = []
    for cookie in cookies:
        if not isinstance(cookie, dict):
            continue
        name = str(cookie.get("name") or "").strip()
        value = str(cookie.get("value") or "")
        if not name:
            continue
        exported_cookie: dict[str, Any] = {
            "name": name,
            "value": value,
            "domain": cookie.get("domain"),
            "path": cookie.get("path") or "/",
            "secure": bool(cookie.get("secure", False)),
            "httpOnly": bool(cookie.get("httpOnly", False)),
            "sameSite": cookie.get("sameSite"),
        }
        expires = cookie.get("expires")
        if isinstance(expires, (int, float)) and expires > 0:
            exported_cookie["expirationDate"] = float(expires)
        exported.append(exported_cookie)
    return exported


def capture_storage_from_page(page: Any) -> dict[str, Any]:
    snapshot = page.evaluate(
        """() => ({
            origin: window.location.origin,
            localStorage: Object.fromEntries(
                Object.keys(localStorage).map((key) => [key, localStorage.getItem(key)])
            ),
            sessionStorage: Object.fromEntries(
                Object.keys(sessionStorage).map((key) => [key, sessionStorage.getItem(key)])
            ),
        })"""
    )
    if not isinstance(snapshot, dict):
        return {"origin": "", "localStorage": {}, "sessionStorage": {}}
    return {
        "origin": snapshot.get("origin") or "",
        "localStorage": snapshot.get("localStorage") or {},
        "sessionStorage": snapshot.get("sessionStorage") or {},
    }


def _is_valid_storage_snapshot(storage: dict[str, Any]) -> bool:
    if not isinstance(storage, dict):
        return False
    origin = storage.get("origin")
    if not isinstance(origin, str) or not origin.strip():
        return False
    parsed = urlparse(origin.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return False
    return isinstance(storage.get("localStorage", {}), dict) and isinstance(
        storage.get("sessionStorage", {}),
        dict,
    )


def _is_persistable_tab_url(tab_url: str | None) -> bool:
    if not isinstance(tab_url, str) or not tab_url.strip():
        return False
    parsed = urlparse(tab_url.strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def merge_session_payload(
    base_payload: dict[str, Any],
    *,
    cookies: list[dict[str, Any]],
    storage: dict[str, Any],
    tab_url: str | None,
    account_timezone: str | None,
) -> dict[str, Any]:
    payload: dict[str, Any] = deepcopy(base_payload if isinstance(base_payload, dict) else {})
    if cookies:
        payload["cookies"] = cookies
    if _is_valid_storage_snapshot(storage):
        payload["storage"] = storage

    tab = payload.get("tab") if isinstance(payload.get("tab"), dict) else {}
    if _is_persistable_tab_url(tab_url):
        tab["url"] = tab_url
    payload["tab"] = tab

    browser = payload.get("browser") if isinstance(payload.get("browser"), dict) else {}
    fingerprint_timezone = str(account_timezone or "").strip()
    if fingerprint_timezone:
        browser["timeZone"] = fingerprint_timezone
    payload["browser"] = browser

    diagnostics = payload.get("diagnostics") if isinstance(payload.get("diagnostics"), dict) else {}
    diagnostics["captured_at"] = datetime.now(timezone.utc).isoformat()
    diagnostics["source"] = "server_browser"
    payload["diagnostics"] = diagnostics
    return payload
```

---

## Python: restore + save-back order

From `api/services/linkedin_browser_session.py`. Port the order, not Linbox types.

```python
# RESTORE
cookies = [
    chrome_cookie_to_playwright(cookie)
    for cookie in raw_cookies
    if isinstance(cookie, dict) and "name" in cookie and "value" in cookie
]
if cookies:
    context.add_cookies(cookies)
if storage_snapshot:
    origin = storage_snapshot.get("origin") or "https://www.linkedin.com"
    page.goto(origin, wait_until="commit")  # not domcontentloaded, not /feed
    apply_storage_snapshot(page, storage_snapshot)

# Caller then: page.goto("https://www.linkedin.com/feed/")

# SAVE-BACK (skip if is_logged_out(page.url) using LOGOUT_URL_HINTS)
refreshed_payload = merge_session_payload(
    base_payload=session_payload,
    cookies=playwright_cookies_to_extension(context.cookies()),
    storage=capture_storage_from_page(page),
    tab_url=page.url,
    account_timezone=None,
)
```

If `storage` is empty (legacy adapter snapshot), still `add_cookies`. Skip origin seed when there is nothing to write (no origin or empty local+session dicts).

---

## JS (optional MV3) — cookie collect

Pulse v1 capture is Playwright UI login, not the extension. Keep these for a later capture path.

From `linbox-extension/service-worker.js`. `ALLOWED_HOST_SUFFIX = "linkedin.com"`. Gate: cookie name `li_at`.

```javascript
function dedupeCookies(cookies) {
  const unique = new Map();
  for (const cookie of cookies) {
    const key = [
      cookie.name || "",
      cookie.domain || "",
      cookie.path || "/",
      cookie.storeId || "",
      cookie.partitionKey?.topLevelSite || "",
    ].join("|");
    if (!unique.has(key)) {
      unique.set(key, cookie);
    }
  }
  return Array.from(unique.values());
}

function getParentDomains(hostname) {
  const parts = hostname.split(".");
  const parents = [];
  for (let i = 1; i < parts.length - 1; i++) {
    parents.push(parts.slice(i).join("."));
  }
  return parents;
}

async function collectCookiesForUrl(tabUrl) {
  const targetUrl = new URL(tabUrl);
  const hostname = targetUrl.hostname;
  const domains = new Set([hostname, ALLOWED_HOST_SUFFIX]);
  for (const parent of getParentDomains(hostname)) {
    domains.add(parent);
  }
  const queries = [chrome.cookies.getAll({ url: tabUrl })];
  for (const domain of domains) {
    queries.push(chrome.cookies.getAll({ domain }));
  }
  const results = await Promise.all(queries);
  return dedupeCookies(results.flat());
}
```

`collectPageEnv` (localStorage, sessionStorage, UA, viewport) lives in Linbox `linbox-extension/content-script.js`. Copy that function if you ship the extension.
