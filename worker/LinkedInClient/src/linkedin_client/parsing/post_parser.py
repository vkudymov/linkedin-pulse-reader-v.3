"""Compatibility re-export. Implementation lives in the linkedin-search packages."""

from linkedin_search_posts.parsing.post_parser import (
    parse_compact_number,
    PostParser,
)

__all__ = ['parse_compact_number', 'PostParser']
