"""Compatibility re-export. Implementation lives in the linkedin-search packages."""

from linkedin_search_posts.parsing.author_extract import (
    pick_post_container,
    extract_author_headline,
    extract_author_profile_url,
    extract_author_avatar_url,
    extract_author_fields,
)

__all__ = ['pick_post_container', 'extract_author_headline', 'extract_author_profile_url', 'extract_author_avatar_url', 'extract_author_fields']
