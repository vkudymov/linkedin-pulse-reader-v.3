"""LinkedIn people search on top of linkedin-search-core."""

from .models.person import Person
from .navigation.boolean_query import BooleanQueryResult, normalize_boolean_query, validate_boolean_query
from .search import PeopleSearch

__all__ = [
    "BooleanQueryResult",
    "PeopleSearch",
    "Person",
    "normalize_boolean_query",
    "validate_boolean_query",
]
