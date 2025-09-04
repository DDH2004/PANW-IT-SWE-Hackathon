from __future__ import annotations
from abc import ABC, abstractmethod


class ModelProviderError(RuntimeError):
    """Standard error raised by model providers to allow uniform handling."""
    pass


class CoachModelProvider(ABC):
    name: str = "base"

    @abstractmethod
    async def generate(self, *, prompt: str, model: str, fast: bool) -> str:
        """Generate a completion for the given prompt.

        Implementations should raise ModelProviderError on retriable/provider issues
        so the API layer can translate to HTTP error responses.
        """
        raise NotImplementedError


class CategorizerModelProvider(ABC):
    name: str = "base"

    @abstractmethod
    async def categorize(self, description: str, merchant: str | None) -> dict:
        """Return {category: str, confidence: float}."""
        raise NotImplementedError
