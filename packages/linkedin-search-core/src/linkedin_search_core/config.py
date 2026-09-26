from __future__ import annotations

"""
RU: Конфигурация boundary-слоя.
    Здесь собираются “policies” клиента (browser runtime + поведение фич), чтобы публичный API оставался
    стабильным, а расширение опций не приводило к росту аргументов в методах.

EN: Boundary configuration.
    This module aggregates client policies (browser runtime + feature behavior) to keep the public API
    stable and avoid argument proliferation as options evolve.
"""

from dataclasses import dataclass

from .browser import BrowserConfig
from .loading.scroller import ScrollConfig


@dataclass(frozen=True, slots=True)
class LinkedInClientConfig:
    """
    RU: Краткое описание
        `LinkedInClientConfig` — централизованный объект конфигурации для `LinkedInClient`.
        Он фиксирует контракт “как мы запускаем браузер и как ведём себя на страницах LinkedIn”,
        позволяя настраивать поведение без изменения прикладного кода, который использует клиент.

    RU: Архитектурная роль
        Объект конфигурации уровня boundary (Configuration/Options Object), который отделяет
        политику выполнения (таймауты, параметры браузера, стратегия скроллинга, режимы парсинга)
        от механики исполнения. Это делает библиотеку расширяемой и безопасной для эволюции:
        добавление новых опций не ломает публичный API и не требует новых параметров в каждом методе.

    RU: Ответственность в системе
        - Хранить согласованный набор настроек для browser lifecycle (через `BrowserConfig`).
        - Определять настройки поведения “фич” (например, URL ленты, параметры скроллинга,
          флаги для устойчивого извлечения контента).
        - Обеспечивать предсказуемые defaults для production-использования и возможность
          переопределения для разных сред (локальный дебаг, CI, разные таймзоны/локали).

    RU: Взаимодействие с другими компонентами
        `LinkedInClient` читает этот объект при построении внутренних компонентов (browser manager,
        navigator, waiter/scroller, parser) и использует его как источник единого “policy”.
        Пользователь библиотеки передаёт `LinkedInClientConfig` в конструктор `LinkedInClient`,
        чтобы управлять поведением клиента целиком (а не настраивать каждый слой вручную).

    EN: Short description
        `LinkedInClientConfig` is the centralized configuration object for `LinkedInClient`.
        It captures the contract of “how the browser is started and how LinkedIn pages are handled”,
        enabling behavior changes without modifying the calling application’s control flow.

    EN: Architectural role
        A boundary-level Options/Configuration object that separates execution policy (timeouts,
        browser parameters, scrolling strategy, parsing behavior flags) from execution mechanics.
        This keeps the public API stable and makes the library extensible: new options can be added
        without proliferating parameters across methods.

    EN: System responsibilities
        - Provide a coherent set of settings for browser lifecycle (via `BrowserConfig`).
        - Define feature-level behavior (e.g., feed URL, scrolling parameters, extraction toggles).
        - Offer production-safe defaults while allowing overrides for different environments
          (local debugging, CI, locale/timezone variations).

    EN: Collaboration with other components
        `LinkedInClient` consumes this object when composing internal components (browser manager,
        navigator, waiter/scroller, parser) and treats it as the single source of policy.
        Library users pass `LinkedInClientConfig` to `LinkedInClient` to control the client end-to-end
        without wiring internal layers manually.
    """
    browser: BrowserConfig = BrowserConfig()

    feed_url: str = "https://www.linkedin.com/feed/"

    scroll: ScrollConfig = ScrollConfig()
    expand_truncated_text: bool = True

