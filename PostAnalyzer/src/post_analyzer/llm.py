from __future__ import annotations

from typing import Protocol


class LLMClient(Protocol):
    def complete(self, *, system: str | None, user: str) -> str:
        """Return the model completion as plain text.

        Implementations are provided by library consumers and can wrap any
        provider (OpenAI, Anthropic, local models, etc.).
        """

