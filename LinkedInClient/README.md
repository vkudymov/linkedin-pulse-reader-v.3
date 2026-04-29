# LinkedInClient (Python)

Production-grade Python library to interact with LinkedIn using **Playwright (Chromium)** browser automation.

## Scope and constraints

- **No LinkedIn API usage**
- **Chromium only** (via Playwright)
- **Stateless by design**: the library does not store cookies or user credentials
- **Browser lifecycle managed inside the library**
- Public entrypoint: **`LinkedInClient`**

## Installation (dev)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
playwright install chromium
```

## Usage

With cookies:

```python
from linkedin_client import LinkedInClient

with LinkedInClient(cookies=cookies) as client:
    posts = client.fetch_posts(limit=10)
```

Without cookies (manual login):

```python
from linkedin_client import LinkedInClient

with LinkedInClient() as client:
    cookies = client.login_and_get_cookies()
```

## Configuration

```python
from linkedin_client import LinkedInClient, LinkedInClientConfig
from linkedin_client.browser import BrowserConfig
from linkedin_client.loading import ScrollConfig

cfg = LinkedInClientConfig(
    browser=BrowserConfig(headless=False, timeout_ms=600_000),
    scroll=ScrollConfig(max_scrolls=80),
)

with LinkedInClient(cookies=cookies, config=cfg) as client:
    posts = client.fetch_posts(limit=10)
```

## Tests

Unit tests:

```bash
pytest -q
```

E2E tests (disabled by default; requires logged-in cookies or manual login and Playwright browsers installed):

```bash
LINKEDIN_E2E=1 pytest -q
```
