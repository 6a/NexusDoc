"""
Application configuration, implemented using Pydantic.

Reads from the .env file automatically. Every setting has a default that works for local development with free tier providers.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # LLM Providers
    groq_api_key: str = Field(default="", repr=False)
    openrouter_api_key: str = Field(default="", repr=False)
    ollama_host: str = Field(default="http://localhost:11434", repr=False)
    
    # Default provider: groq | ollama | openrouter
    default_provider: str = Field(default="groq")

    # Observability
    langfuse_secret_key: str = Field(default="", repr=False)
    langfuse_public_key: str = Field(default="", repr=False)
    langfuse_host: str = Field(default="http://localhost:3000", repr=False)

    # Database
    supabase_url: str = Field(default="", repr=False)
    supabase_service_key: str = Field(default="", repr=False)

    # Application
    log_level: str = Field(default="INFO")

settings = Settings()