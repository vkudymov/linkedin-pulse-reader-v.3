"""
RU: Scroll utilities.
    Небольшие утилиты, которые имитируют пользовательские действия (например, прокрутку) и
    могут переиспользоваться разными фичами (feed, search, profiles) без зависимости от парсинга.

EN: Scroll utilities.
    Small utilities that simulate user actions (e.g., scrolling) and can be reused by multiple features
    (feed, search, profiles) without coupling to parsing logic.
"""

from .human_scroll import human_scroll

__all__ = ["human_scroll"]

