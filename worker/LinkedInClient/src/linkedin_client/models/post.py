"""Compatibility re-export. Implementation lives in the linkedin-search packages."""

from linkedin_search_posts.models.post import (
    Author,
    merge_authors,
    Post,
)

__all__ = ['Author', 'merge_authors', 'Post']
