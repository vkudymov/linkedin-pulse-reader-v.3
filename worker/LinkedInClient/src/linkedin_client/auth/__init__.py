"""
RU: Auth boundary.
    В этом пакете собраны механизмы восстановления/поддержания сессии через cookies и manual login.
    Хранение cookies/учётных данных — ответственность внешнего приложения.

EN: Auth boundary.
    This package contains session restoration mechanisms via cookies and manual login.
    Persistence of cookies/credentials belongs to the calling application.
"""

from .cookies import Cookie, Cookies, extract_cookies, inject_cookies
from .methods import LoginMethod

__all__ = ["Cookie", "Cookies", "LoginMethod", "extract_cookies", "inject_cookies"]

