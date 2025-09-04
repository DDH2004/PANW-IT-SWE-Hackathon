import os
from functools import lru_cache
from .base import CoachModelProvider, ModelProviderError
from .ollama_provider import OllamaCoachProvider


PROVIDERS: dict[str, type[CoachModelProvider]] = {
    'ollama': OllamaCoachProvider,
    # future: 'openai': OpenAICoachProvider,
    # future: 'anthropic': AnthropicCoachProvider,
}


@lru_cache(maxsize=1)
def get_coach_provider() -> CoachModelProvider:
    name = os.getenv('MODEL_PROVIDER', 'ollama').lower()
    cls = PROVIDERS.get(name)
    if not cls:
        raise ModelProviderError(f"Unknown provider '{name}'")
    return cls()

__all__ = [
    'get_coach_provider',
    'ModelProviderError',
]
