"""
Convert between our internal message format and the provider's message format.
"""

from typing import TypedDict

from app.core.providers.base import ChatMessage, Role


class ChatMessageParam(TypedDict):
    """
    OpenAI format
    """

    role: Role
    content: str


def to_chat_message_param(message: ChatMessage) -> ChatMessageParam:
    return {"role": message.role, "content": message.content}


def to_chat_message_params(messages: list[ChatMessage]) -> list[ChatMessageParam]:
    return [to_chat_message_param(m) for m in messages]
