"""
RU: Feature navigation layer.
    Минимальные роутеры к ключевым страницам + сигнализация auth-редиректов.

EN: Feature navigation layer.
    Minimal routers to key pages + explicit auth-redirect signaling.
"""

from .feed import FeedNavigator

__all__ = ["FeedNavigator"]

