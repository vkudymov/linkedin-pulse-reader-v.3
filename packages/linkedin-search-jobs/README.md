# linkedin-search-jobs

LinkedIn job search. Depends on `linkedin-search-core` and does not import the posts library.

Requires Python 3.11+.

## Install

```bash
pip install linkedin-search-jobs
```

That also installs `linkedin-search-core`.

Local editable install (core first):

```bash
pip install -e packages/linkedin-search-core
pip install -e packages/linkedin-search-jobs
```

## Dependencies

- `linkedin-search-core>=0.1.0`
- `playwright>=1.49.0`

## Example

```python
from linkedin_search_core import LinkedInSession
from linkedin_search_jobs import JobSearch

with LinkedInSession(cookies=cookies) as session:
    jobs = JobSearch(session).fetch(keywords="ABAP", location="Berlin", limit=10)
```

## API

- `JobSearch.fetch(keywords, location=None, limit=25, filters=None)` and `JobSearch.search(...)` (same operation)
- `Job`
