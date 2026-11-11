# LinkedIn search libraries

Installable packages extracted from the worker LinkedIn client:

```text
linkedin-search-core
        ↑
   ┌────┼────┐
   │    │    │
jobs  posts people
```

- `linkedin-search-core` — Playwright session, login, browser config, shared errors, scrolling
- `linkedin-search-jobs` — job search, job filters, job models (`linkedin-search-core`)
- `linkedin-pulse-search-posts` — post search, post models (`linkedin-search-core`; source dir `packages/linkedin-search-posts`)
- `linkedin-search-people` — people search, boolean query, profile enrich (`linkedin-search-core`)

`linkedin-search-core` does not import jobs, posts, or people. Jobs, posts, and people do not import each other.

The worker package `linkedin-client` remains the facade used by `run_job_search.py`, `run_post_search.py`, `run_people_search.py`, and the API. It delegates to these libraries.

## Installation

From PyPI (after publication):

```bash
pip install linkedin-search-core
pip install linkedin-search-jobs
pip install linkedin-pulse-search-posts
pip install linkedin-search-people
```

`linkedin-search-jobs`, `linkedin-pulse-search-posts`, and `linkedin-search-people` install `linkedin-search-core` automatically.

## Local install

From the repository root:

```bash
pip install -e packages/linkedin-search-core
pip install -e packages/linkedin-search-jobs
pip install -e packages/linkedin-search-posts
pip install -e packages/linkedin-search-people
```

Install core before jobs, posts, or people so the package-name dependency resolves from the local checkout.
