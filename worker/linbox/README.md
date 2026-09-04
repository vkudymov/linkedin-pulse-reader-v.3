# session_snapshot handoff (Pulse)

Prompt pack for the LinkedIn Pulse Reader worker: a `session_snapshot` module
that replaces Playwright-list inject/extract with Chrome-shaped restore/export.

| File | Role |
|---|---|
| `GOLD.md` | Verbatim converters + restore order + LinkedIn constants |
| `PROMPT.md` | Agent prompt: build the package in the Pulse repo |

## Placeholders (already filled)

These were decided from Pulse + Linbox LinkedIn session logic:

- `TARGET_HOST_SUFFIX` = `linkedin.com`
- `AUTH_COOKIE_NAME` = `li_at`
- `LOGOUT_URL_HINTS` = `/login`, `/checkpoint`, `/authwall`, `/uas/`
- `DEFAULT_ORIGIN` = `https://www.linkedin.com`

Pulse captures login via Playwright UI, not the Linbox Chrome extension. The
prompt treats MV3 as optional follow-up.

## How to use in Pulse

1. Copy this folder to `worker/linbox/` in the Pulse repo (or keep `GOLD.md` + `PROMPT.md` at repo root).
2. Also copy `PULSE_WORKER_COOKIES.md` if the Pulse agent does not have it — it maps `[COOKIE]` / `[INTEGRATE]` call sites.
3. Agent mode: *Read `PROMPT.md` and `GOLD.md`. Implement Phase 1 only.*
4. After pytest is green, a second prompt: *Wire Phase 2 INTEGRATE-1..10. Do not touch fetch_posts / LLM.*
