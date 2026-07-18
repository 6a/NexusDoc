"""
Ollama provider implementation.
"""

from ollama import Client

from app.core.config import settings
from app.core.providers.base import BaseProvider, ChatMessage, CompletionResult
from app.core.providers.definitions import ProviderName
from app.core.providers.messages import to_chat_message_params

DEFAULT_MODEL: str = "qwen2.5:7b"


class OllamaProvider(BaseProvider):
    """
    Ollama provider implementation.
    """

    def __init__(self) -> None:
        self._client = Client(host=settings.ollama_host)

    @property
    def provider_name(self) -> str:
        return ProviderName.OLLAMA

    def chat(self, messages: list[ChatMessage], model: str | None = None, temperature: float = 0.0, max_tokens: int = 1024) -> CompletionResult:
        model = model or DEFAULT_MODEL

        response = self._client.chat(
            model=model,
            messages=to_chat_message_params(messages),
            options={
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        )

        response_text: str = response["message"]["content"] or ""

        model_name: str = response["model"] or ""

        prompt_tokens: int = response["prompt_eval_count"] or 0
        completion_tokens: int = response["eval_count"] or 0

        usage_dict: dict[str, int] = {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": completion_tokens + prompt_tokens,
        }

        return CompletionResult(content=response_text, model=model_name, usage=usage_dict)

    def list_models(self) -> list[str]:
        """
        Returns the ID's of the models that are available for this provider.

        Returns models currently available on the local Ollama daemon, or an empty list if the daemon is unreachable.
        """

        try:
            model_list = self._client.list()
            return [m["model"] for m in model_list.get("models", []) if m.get("model")]
        except Exception:
            return []

    def is_available(self) -> bool:
        """
        Returns true if the local Ollama daemon is available and the default model is available.
        """

        return DEFAULT_MODEL in self.list_models()
