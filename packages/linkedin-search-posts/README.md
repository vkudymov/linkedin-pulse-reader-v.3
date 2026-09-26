# linkedin-search-posts

LinkedIn feed post search. Depends on `linkedin-search-core` and does not import the jobs library.

Requires Python 3.11+.

## Install

```bash
pip install linkedin-search-posts
```

That also installs `linkedin-search-core`.

Local editable install (core first):

```bash
pip install -e packages/linkedin-search-core
pip install -e packages/linkedin-search-posts
```

## Dependencies

- `linkedin-search-core>=0.1.0`
- `playwright>=1.49.0`

## Example

```python
from linkedin_search_core import LinkedInSession
from linkedin_search_posts import PostSearch

with LinkedInSession(cookies=cookies) as session:
    posts = PostSearch(session).fetch(limit=10)
```

## API

- `PostSearch.fetch(limit=10)` — open the feed, scroll, and parse posts
- `PostSearch.read(limit=10)` — parse posts already on the current page
- `PostSearch.search(limit=10)` — alias of `fetch`
- `Author`, `Post`
