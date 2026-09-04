# session_snapshot (Pulse)

Chrome-shaped LinkedIn session restore/export. Does not fetch posts or run LLM.

Install from `worker/`: `python3 -m pip install -e session_snapshot`

```python
from session_snapshot import load_snapshot, restore_session, export_session
from session_snapshot import is_logged_out, should_save_back, SessionLoggedOutError

snapshot = load_snapshot(account_row)  # cookies_json list or session_snapshot dict
# LinkedInClient: open Playwright context (optional playwright_context_options(snapshot))
restore_session(context, page, snapshot)
# existing Pulse: FeedNavigator.goto_feed + fetch_posts — unchanged
if is_logged_out(page.url) or not should_save_back(page.url):
    raise LoginRequiredError(...)  # Pulse mapping; do not persist
new_snapshot = export_session(context, page, snapshot)
# Phase 2: persist new_snapshot (Chrome cookies + storage)
```

Logout URLs (`/login`, `/checkpoint`, `/authwall`, `/uas/`): `export_session` raises `SessionLoggedOutError`. Never log cookie values.
