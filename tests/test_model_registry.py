"""
Tests for the model registry module.

Notes:
- Only groq/ollama tests are implemented for now.
- These tests use real API calls - in the future we'll add VCR cassettes (Phase 5) to make them fully offline.
"""

import pytest

from app.core.config import settings
from app.core.model_registry import get_provider, reset_provider
from app.core.providers.base import ChatMessage, Role
from app.core.providers.definitions import ProviderName
from app.core.providers.ollama_provider import OllamaProvider

_PROVIDER_PARAMS = [
    # Groq
    pytest.param(ProviderName.GROQ, marks=pytest.mark.skipif(not settings.groq_api_key, reason="GROQ_API_KEY not set")),
    # Ollama
    pytest.param(ProviderName.OLLAMA, marks=pytest.mark.skipif(not OllamaProvider().is_available(), reason="Ollama daemon, or default model not available")),
]


@pytest.fixture(autouse=True)
def reset() -> None:
    """
    Reset the provider singleton before each test.
    """

    reset_provider()


@pytest.fixture()
def set_default_provider(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> str | ProviderName:
    provider: str | ProviderName = request.param
    monkeypatch.setattr(settings, "default_provider", provider)
    return provider


@pytest.mark.parametrize("set_default_provider", _PROVIDER_PARAMS, indirect=True)
def test_provider_chat(set_default_provider: ProviderName) -> None:
    """
    Test that the specified provider returns a valid response.
    """

    provider = get_provider()

    assert provider.provider_name == set_default_provider

    result = provider.chat(
        messages=[
            ChatMessage(role=Role.SYSTEM, content="Reply with exactly: pong"),
            ChatMessage(role=Role.USER, content="ping"),
        ],
        max_tokens=10,
    )

    assert isinstance(result.content, str)
    assert len(result.content) > 0
    assert result.model
    assert result.usage["total_tokens"] > 0
    assert "prompt_tokens" in result.usage
    assert "completion_tokens" in result.usage


@pytest.mark.parametrize("set_default_provider", _PROVIDER_PARAMS, indirect=True)
def test_provider_list_models(set_default_provider: ProviderName) -> None:
    """
    Test that the specified provider lists available models.
    """

    provider = get_provider()

    assert provider.provider_name == set_default_provider

    models = provider.list_models()

    assert isinstance(models, list)
    assert all(isinstance(m, str) and m.strip() for m in models)


@pytest.mark.parametrize("set_default_provider", ["foo"], indirect=True)
def test_unknown_provider(set_default_provider: str) -> None:
    """
    Test that an unknown provider raises an error.
    """

    with pytest.raises(ValueError, match=f"The configured provider '{set_default_provider}' is not supported."):
        get_provider()


@pytest.mark.parametrize("set_default_provider", [""], indirect=True)
def test_missing_provider(set_default_provider: str) -> None:
    """
    Test that a missing provider raises an error.
    """

    with pytest.raises(ValueError, match="No provider configured, or configured with an empty value. Please set DEFAULT_PROVIDER in .env."):
        get_provider()
