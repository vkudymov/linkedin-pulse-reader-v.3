# Architecture

This package is a **standalone, stateless** Python library that automates LinkedIn through
**Playwright (Chromium)**. It does not use any LinkedIn APIs, and it does not store cookies.

## Key goals

- **Stateless**: cookies are only injected/extracted and returned to the caller
- **Encapsulated lifecycle**: Playwright + Chromium startup/teardown is owned by the library
- **Resilient extraction**: selectors are best-effort and designed to degrade gracefully

## Module map

- `linkedin_client.client.LinkedInClient`
  - Public facade and context manager (`with LinkedInClient(...) as client:`)
  - Orchestrates navigation → waiting → scrolling → parsing

- `linkedin_client.browser`
  - `BrowserConfig`: browser + context configuration
  - `BrowserManager`: starts/stops Playwright, launches Chromium, creates context + page

- `linkedin_client.auth`
  - `cookies`: validate/inject/extract cookies (no persistence)
  - `login`: manual login flow (opens LinkedIn login page and waits for redirect)

- `linkedin_client.navigation`
  - `FeedNavigator`: navigates to the feed URL and detects auth redirects

- `linkedin_client.loading`
  - `FeedWaiter`: waits for feed container + post containers and stabilizes list
  - `HumanScroller`: human-like scrolling to load more posts

- `linkedin_client.parsing`
  - `PostParser`: best-effort extraction of post data into `Post` objects

- `linkedin_client.models`
  - `Post`, `Author` (immutable/slots dataclasses)

## Operational flow (fetch_posts)

1. Start Playwright
2. Launch Chromium
3. Create browser context
4. Inject cookies (if provided)
5. Navigate to feed URL
6. Wait until feed is ready and stable
7. Scroll to load additional posts
8. Parse and return `Post` objects

