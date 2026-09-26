# linkedin-search-core

Shared LinkedIn browser session for search libraries. This package opens Chromium through Playwright, restores a session, and runs interactive login. It does not search jobs or posts.

Requires Python 3.11+.

## Install

```bash
pip install linkedin-search-core
```

Local editable install from this monorepo:

```bash
pip install -e packages/linkedin-search-core
```

## Dependencies

- `playwright>=1.49.0`
- `session-snapshot` is optional. Import it in the same environment when you restore or export a full Chrome session snapshot. Without it, cookie-only login still works.

## Example

```python
from linkedin_search_core import LinkedInSession

with LinkedInSession(cookies=cookies, headless=True) as session:
    print(session.is_logged_in())
```

## API

- `LinkedInSession` — context manager for the browser session (`login_and_get_cookies`, `get_cookies`, `export_session_snapshot`, `is_logged_in`)
- `LinkedInClientConfig`, `BrowserConfig`, `LoginMethod`
- `UserIdentity`
- Errors: `LinkedInClientError`, `BrowserLifecycleError`, `CookieFormatError`, `LoginRequiredError`, `LoginTimeoutError`, `LoginCheckpointError`, `LoginCancelledError`, `FeedLoadError`, `PostParseError`
