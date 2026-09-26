"""LinkedIn post search on top of linkedin-search-core."""

from .models.post import Author, Post
from .search import PostSearch

__all__ = ["Author", "Post", "PostSearch"]
