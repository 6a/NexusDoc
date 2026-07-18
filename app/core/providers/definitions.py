"""
Definitions for all supported provider names.
"""

from enum import StrEnum


class ProviderName(StrEnum):
    """
    Enum for all supported provider names.
    """

    GROQ = "groq"
    OPENROUTER = "openrouter"
    OLLAMA = "ollama"
    VLLM = "vllm"
