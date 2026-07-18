"""
Provider-agnostic model register

The single entry point for all LLM calls.
Switch providers by changing DEFAULT_PROVIDER in .env.

TODO: Fallback logic also goes here - downstream code doesn't need to know which provider is actually handling a request.
"""

from app.core.config import settings
from app.core.providers.base import BaseProvider
from app.core.providers.definitions import ProviderName
from app.core.providers.groq_provider import GroqProvider
from app.core.providers.ollama_provider import OllamaProvider

_provider: BaseProvider | None = None


def get_provider() -> BaseProvider:
    """
    Return the configured provider. The provider is initialized the first time it is called.

    Switch providers by setting DEFAULT_PROVIDER in .env:
    - groq: Groq --> (fast, free-tier friendly)
    - openrouter: OpenRouter --> (fallback when Groq throttles or has issues)
    - ollama: Local models
    - vllm: Self-hosted vLLM (Phase 7)
    """

    global _provider

    if _provider is not None:
        return _provider

    configured_provider_name = settings.default_provider.lower()

    match configured_provider_name:
        case ProviderName.GROQ:
            _provider = GroqProvider()
        # case ProviderName.OPENROUTER:
        #     _provider = OpenRouterProvider()
        case ProviderName.OLLAMA:
            _provider = OllamaProvider()
        # case ProviderName.VLLM:
        #     _provider = VLLMProvider()
        case "":
            raise ValueError("No provider configured, or configured with an empty value. Please set DEFAULT_PROVIDER in .env.")
        case _:
            raise ValueError(f"The configured provider '{configured_provider_name}' is not supported.")

    return _provider


def reset_provider() -> None:
    """
    Reset the current provider to None.
    """

    global _provider
    _provider = None
