"""
Groq provider implementation.
"""

from typing import cast

from groq import Groq
from groq.types.chat import ChatCompletionMessageParam

from app.core.config import settings
from app.core.providers.base import BaseProvider, ChatMessage, CompletionResult
from app.core.providers.definitions import ProviderName
from app.core.providers.messages import to_chat_message_params


class GroqProvider(BaseProvider):
    """
    Groq provider implementation.
    """

    def __init__(self) -> None:
        if not settings.groq_api_key:
            raise ValueError("Groq API key is not set.")

        self._client = Groq(api_key=settings.groq_api_key)

    @property
    def provider_name(self) -> str:
        return ProviderName.GROQ

    def chat(self, messages: list[ChatMessage], model: str | None = None, temperature: float = 0.0, max_tokens: int = 1024) -> CompletionResult:
        model = model or "llama-3.3-70b-versatile"

        response = self._client.chat.completions.create(
            model=model, messages=cast(list[ChatCompletionMessageParam], to_chat_message_params(messages)), temperature=temperature, max_tokens=max_tokens
        )

        response_text: str = response.choices[0].message.content or ""
        usage = response.usage
        usage_dict: dict[str, int] = {
            "prompt_tokens": usage.prompt_tokens if usage else 0,
            "completion_tokens": usage.completion_tokens if usage else 0,
            "total_tokens": usage.total_tokens if usage else 0,
        }

        return CompletionResult(content=response_text, model=response.model, usage=usage_dict)

    def list_models(self) -> list[str]:
        """
        Returns the ID's of the models that are available for this provider.

        Currently limited to free tier models.
        """

        return [
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "qwen-2.5-32b",
            "gemma2-9b-it",
        ]
