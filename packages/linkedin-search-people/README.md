# linkedin-search-people

## Description

LinkedIn people search. Depends on `linkedin-search-core` and does not import the jobs or posts libraries.

Requires Python 3.11+.

## Installation

```bash
pip install linkedin-search-people
```

That also installs `linkedin-search-core`.

Local editable install (core first):

```bash
pip install -e packages/linkedin-search-core
pip install -e packages/linkedin-search-people
```

## Usage

```python
from linkedin_search_core import LinkedInSession
from linkedin_search_people import PeopleSearch

with LinkedInSession(cookies=cookies) as session:
    people = PeopleSearch(session).fetch(
        keywords='ABAP AND "S/4HANA"',
        limit=10,
        filters={"network": ["F", "S"], "profile_language": "en"},
    )
    person = PeopleSearch(session).enrich(people[0].profile_url)
```

## API

- `PeopleSearch.fetch(keywords, limit=25, filters=None)` and `PeopleSearch.search(...)` (same operation)
- `PeopleSearch.enrich(profile_url)` — open a profile and fill about, skills, experience, education
- `Person`
- `normalize_boolean_query` / `validate_boolean_query`

## Filters

`filters` keys (All filters):

- `network`: `["F"]` (1st), `["S"]` (2nd), `["O"]` (3rd+); combinations allowed
- `locations`: list of region names or geo IDs
- `current_company`, `past_company`, `school`: names or numeric organization IDs
- `industry`: industry id or name
- `profile_language`: `en`, `ru`, `de`, …
- `keywords`: extra keywords merged into the query
