from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class Author:
    """
    RU: Доменная модель автора поста (boundary-объект).
        Возвращается наружу как стабильный контракт, независимо от того, как меняется DOM LinkedIn.

    EN: Post author domain model (boundary object).
        Returned as a stable contract, independent of LinkedIn DOM changes.
    """
    name: str
    headline: str | None = None
    profile_url: str | None = None
    urn: str | None = None

    extra: Mapping[str, Any] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "extra", MappingProxyType(dict(self.extra)))


@dataclass(frozen=True, slots=True)
class Post:
    """
    RU: Доменная модель поста из ленты (публичный контракт).
        Поля optional по дизайну: LinkedIn UI/типы постов различаются, а парсер работает best-effort.

    EN: Feed post domain model (public contract).
        Optional fields are intentional: LinkedIn UI/post types vary and parsing is best-effort.
    """

    id: str | None = None
    urn: str | None = None
    post_url: str | None = None

    author: Author | None = None
    content: str | None = None
    published_at_text: str | None = None

    reactions_count: int | None = None
    comments_count: int | None = None

    media_urls: tuple[str, ...] = ()

    extra: Mapping[str, Any] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "extra", MappingProxyType(dict(self.extra)))

