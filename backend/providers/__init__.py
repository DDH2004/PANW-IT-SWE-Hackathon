"""Model provider scaffold.

Currently only an Ollama provider implementation is wired. Additional providers
can register by adding a module and updating the PROVIDERS map in factory.py.
"""

from .factory import get_coach_provider, ModelProviderError  # noqa: F401
