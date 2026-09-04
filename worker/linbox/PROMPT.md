# Build `session_snapshot` for LinkedIn Pulse Reader worker

Read `GOLD.md` in the same folder first. GOLD converters are the source of truth:
copy them verbatim, then add types. Do not reinvent cookie conversion.

This prompt is for the **Pulse worker repo** (or a package Pulse will import).
It is not a generic any-site library and not a Linbox port.

Paste this file + `GOLD.md` into the Pulse project (expected path there:
`worker/linbox/PROMPT.md` + `worker/linbox/GOLD.md`) and implement.

---

## Context (Pulse today)

Pulse worker already logs into LinkedIn with Playwright and stores cookies.

| Fact | Value |
|---|---|
| Search / LLM | Do **not** change `fetch_posts`, PostAnalyzer, `feed_posts`, UI |
| Cookie store now | `public.linkedin_accounts.cookies_json` = **Playwright cookie list** |
| Inject now | `LinkedInClient` → `inject_cookies` → `context.add_cookies(list)` |
| Extract now | `extract_cookies` → `context.cookies()` → `update_cookies` |
| Login now | Playwright UI (`POST /v1/linkedin/login` + CLI fallback), not Chrome extension |
| Logout now | `FeedNavigator` raises `LoginRequiredError` on `/login` `/checkpoint` `/authwall` |
| User | `auth.users.id`; one LinkedIn session = one `linkedin_accounts` row |

The new module replaces **only the session boundary**: convert, restore, export,
logout detect, legacy-list adapter. It does not replace feed parsing.

---

## LinkedIn / Pulse constants (already decided)

```python
TARGET_HOST_SUFFIX = "linkedin.com"
AUTH_COOKIE_NAME = "li_at"
DEFAULT_ORIGIN = "https://www.linkedin.com"
LOGOUT_URL_HINTS = ["/login", "/checkpoint", "/authwall", "/uas/"]
```

Use these as module defaults. Callers may pass overrides; defaults must be LinkedIn.

---

## Goal

Python package `session_snapshot` that Pulse can call like this:

```python
from session_snapshot import (
    load_snapshot,          # row cookies_json | session_snapshot → snapshot dict
    restore_session,        # Playwright context+page
    export_session,         # after feed work or after UI login
    is_logged_out,
    has_auth_cookie,
    should_save_back,       # False on login-wall
    playwright_cookies_for_context,  # snapshot["cookies"] → add_cookies list
)

snapshot = load_snapshot(account_row)
# LinkedInClient.__enter__: build context from snapshot UA/viewport/locale if present
restore_session(context, page, snapshot)
# existing client: goto feed, fetch_posts  — unchanged
if is_logged_out(page.url):
    # LoginRequiredError; do not persist
    ...
else:
    new_snapshot = export_session(context, page, snapshot)
    # persist new_snapshot (Chrome-shaped cookies + storage)
```

---

## Non-goals

- Linbox FastAPI / Supabase RPC / MCP / tasks / limits / campaigns / plugin tokens
- Pulse `fetch_posts`, DOM parsers, PostAnalyzer, admin posts API, frontend
- `LinkedInClient/run/cookies.json` demo CLI (leave alone)
- Persistent `.playwright-profile/` for Google/Apple login (leave alone)
- Chrome MV3 extension in **v1** (Playwright UI login is the capture path). Extension may be a follow-up using GOLD JS snippets.
- Stealth / proxy fingerprinting

---

## Public Python API (implement all)

```python
# convert
to_playwright_cookies(raw: list[dict]) -> list[dict]
from_playwright_cookies(pw: list[dict]) -> list[dict]

# storage
apply_storage_snapshot(page, storage: dict) -> None
seed_origin_storage(page, storage: dict) -> None
capture_storage_from_page(page) -> dict

# merge
merge_snapshot(base: dict, *, cookies, storage, tab_url, browser_timezone=None) -> dict

# linkedin / pulse
has_auth_cookie(cookies: list[dict], name: str = AUTH_COOKIE_NAME) -> bool
is_logged_out(url: str, hints: list[str] | None = None) -> bool
should_save_back(url: str) -> bool  # not is_logged_out

# restore / export
restore_session(context, page, snapshot: dict) -> None
export_session(context, page, base_snapshot: dict, *, browser_timezone=None) -> dict

# pulse storage adapter
is_snapshot_payload(value: Any) -> bool
playwright_list_to_snapshot(cookies: list[dict]) -> dict
load_snapshot(account_row: dict) -> dict
```

`load_snapshot` rules:

1. If `account_row` has `session_snapshot` dict with a `cookies` list → use it.
2. Else if `cookies_json` is a dict with `cookies` list → treat as snapshot (schema option A).
3. Else if `cookies_json` is a list of cookie dicts → `playwright_list_to_snapshot`.
4. Else → empty snapshot (`cookies=[]`, empty storage, `storage.origin=DEFAULT_ORIGIN`).

`playwright_list_to_snapshot`: wrap the list as Chrome-shaped cookies via
`from_playwright_cookies` (Playwright `expires`/`sameSite` already look like
export output). Set `diagnostics.source = "legacy_playwright_list"`. Empty
browser/viewport. Storage `{origin: DEFAULT_ORIGIN, localStorage: {}, sessionStorage: {}}`.

`restore_session` MUST:

1. Take `snapshot["cookies"]`, run GOLD `chrome_cookie_to_playwright` for entries
   with name+value (`to_playwright_cookies`).
2. `context.add_cookies(...)`.
3. `seed_origin_storage`: if storage has a valid origin AND (localStorage or
   sessionStorage has keys), `page.goto(origin, wait_until="commit")` then GOLD
   `apply_storage_snapshot`. If storage is empty, skip goto (legacy Pulse rows).
4. Return. Caller navigates to `/feed/` (existing `FeedNavigator`).

`export_session` MUST:

- If `is_logged_out(page.url)`: do not merge login-page cookies. Raise a small
  typed error (e.g. `SessionLoggedOutError`) or return a result object with
  `saved=False`. Pick one and document it; Pulse will map it to `LoginRequiredError`.
- Else GOLD merge using `from_playwright_cookies(context.cookies())` and
  `capture_storage_from_page(page)`.
- Public arg name `browser_timezone` (GOLD internal `account_timezone`).

`is_logged_out(url)`: lowercase URL; true if path or query contains any of
`LOGOUT_URL_HINTS` (default list). Same idea as Pulse FeedNavigator + `/uas/`.

Context options helper (optional but useful for INTEGRATE-2):

```python
def playwright_context_options(snapshot: dict) -> dict:
    # user_agent, viewport {width,height} from innerWidth/innerHeight, locale from browser.language
    # omit keys that are missing so LinkedInClient can keep its current defaults
```

Never log cookie values.

---

## Layout in Pulse repo

Prefer:

```
worker/session_snapshot/
  __init__.py          # export public API
  convert.py           # GOLD to/from playwright
  storage.py           # apply, capture, seed
  merge.py             # GOLD merge
  restore.py           # restore_session, export_session
  linkedin.py          # constants, has_auth_cookie, is_logged_out, should_save_back
  adapter.py           # load_snapshot, playwright_list_to_snapshot, is_snapshot_payload
  models.py            # optional pydantic, extra="allow"
worker/linbox/GOLD.md  # this gold file (already provided)
worker/linbox/PROMPT.md
worker/tests/session_snapshot/   # or worker/session_snapshot/tests/
README.md              # 15-line Pulse usage: load → restore → feed → export if should_save_back
```

Do not put the package inside `LinkedInClient` (that library must stay a thin
Playwright client). Pulse orchestration imports `session_snapshot`.

---

## Tests (required)

- sameSite map + `expirationDate` ↔ `expires` round-trip
- cookie with `domain` keeps `domain`+`path`, not url-only
- cookie without `domain` uses `url`
- `unspecified` sameSite omitted
- `seed_origin_storage` calls `goto(..., wait_until="commit")` only when storage has keys (mock page)
- empty legacy storage → restore add_cookies, no origin goto
- merge replaces cookies, keeps base browser/viewport, updates tab.url when persistable
- merge does not overwrite `browser.timeZone` when `browser_timezone` is None
- `is_logged_out` true for `/login`, `/checkpoint`, `/authwall`, `/uas/login`; false for `/feed/`
- `should_save_back` false on those logout URLs
- `has_auth_cookie` looks up `li_at`
- `load_snapshot` from Playwright list; from full snapshot dict; from empty
- `playwright_list_to_snapshot` cookies round-trip through `to_playwright_cookies` without losing name/value/domain
- no test prints cookie values

No live LinkedIn tests.

---

## Phase 1 vs Phase 2

**Phase 1 (this prompt): ship the package + tests.** Pulse search must still
run on the old inject/extract path until Phase 2.

**Phase 2 (separate, only after Phase 1 pytest is green).** Wire Pulse
`[COOKIE]` / `[INTEGRATE]` points from `PULSE_WORKER_COOKIES.md`. Do not do
Phase 2 in the same turn unless the user explicitly asks.

Phase 2 map (for the next agent, not for Phase 1 code):

| Id | File | Change |
|---|---|---|
| INTEGRATE-1 | `LinkedInClient/.../auth/cookies.py` | wrap/replace inject+extract with restore/export |
| INTEGRATE-2 | `LinkedInClient/.../client.py` `__enter__` | snapshot in → `restore_session`; context options from snapshot |
| INTEGRATE-3 | `get_cookies` / login end | `export_session` snapshot, not raw list |
| INTEGRATE-4..6 | `run_post_search.py` | `load_snapshot`; pass snapshot; save-back only if `should_save_back` |
| INTEGRATE-7 | auth check | `has_auth_cookie` + `is_logged_out` |
| INTEGRATE-8 | `pulse_api/linkedin/sessions.py` + `persist.py` | after UI login, `export_session`, persist snapshot |
| INTEGRATE-9 | Storage | **B**: new column `session_snapshot jsonb`; keep `cookies_json` for old rows; `load_snapshot` reads either |
| INTEGRATE-10 | `navigation/feed.py` | use `is_logged_out`; no save-back on `LoginRequiredError` |

Schema B is the Pulse recommendation: do not overwrite `cookies_json` meaning
until rows are migrated. The package must not require the new column — that is
Pulse Storage work in Phase 2.

---

## Done when (Phase 1)

- `pytest` for `session_snapshot` passes
- Public API matches the list above
- GOLD sameSite map and domain-vs-url branch are recognizable in `convert.py`
- Defaults are LinkedIn/Pulse constants
- README shows Pulse load → restore → (existing fetch) → export with logout guard
- No Linbox imports, no changes to post search / LLM
