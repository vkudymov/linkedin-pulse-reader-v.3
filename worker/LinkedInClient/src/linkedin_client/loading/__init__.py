"""
RU: Loading layer (waiting + scrolling).
    Компоненты, которые обеспечивают “контент присутствует и стабилен” перед парсингом.

EN: Loading layer (waiting + scrolling).
    Components that ensure “content is present and stable” before parsing.
"""

from .scroller import HumanScroller, ScrollConfig
from .waiter import FeedWaiter

__all__ = ["FeedWaiter", "HumanScroller", "ScrollConfig"]

