"""
Abstract base class for all LLM providers.

Every provider implements this interface.
Downstream code only imports BaseProvider - never a concrete provider implementation.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Literal

Role = Literal["system", "user", "assistant"]

@dataclass
class ChatMessage:
    """
    A single message in a conversation.
    """

    role: Role
    content: str


@dataclass
class CompletionResult:
    """
    What the provider returns from a chat completion request.
    """

    content: str
    model: str
    usage: dict[str, int] = field(default_factory=dict) # prompt_tokens, completion_tokens, total_tokens


class BaseProvider(ABC):
    """
    Interface that every provider must implement.
    """

    @abstractmethod
    def chat(self, messages: list[ChatMessage], model: str | None = None, temperature: float = 0.0, max_tokens: int = 1024) -> CompletionResult:
        """
        Send a chat completion request and return the result
        """
        ...

    @abstractmethod
    def list_models(self) -> list[str]:
        """
        Returns available model ID's for this provider.
        """
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """
        Human-readable provider name for logging etc.
        """
        ...
