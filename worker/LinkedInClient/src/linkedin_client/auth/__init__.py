"""
RU: Auth boundary.
    В этом пакете собраны механизмы восстановления сессии через session_snapshot и manual login.
    Хранение сессии — ответственность внешнего приложения.

EN: Auth boundary.
    This package contains session restoration via session_snapshot and manual login.
    Persistence belongs to the calling application.
"""

from .methods import LoginMethod

__all__ = ["LoginMethod"]
