"""
Application configuration, implemented using Pydantic.

Reads from the .env file automatically. Every setting has a default that works for local development with free tier providers.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.providers.definitions import ProviderName


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # LLM Providers
    groq_api_key: str = Field(default="", repr=False)
    openrouter_api_key: str = Field(default="", repr=False)
    ollama_host: str = Field(default="http://localhost:11434", repr=False)

    # Default provider: groq | ollama | openrouter
    default_provider: ProviderName = ProviderName.GROQ

    # Observability
    langfuse_secret_key: str = Field(default="", repr=False)
    langfuse_public_key: str = Field(default="", repr=False)
    langfuse_host: str = Field(default="http://localhost:3000", repr=False)

    # Database
    supabase_url: str = Field(default="", repr=False)
    supabase_service_key: str = Field(default="", repr=False)
    supabase_db_url: str = Field(default="", repr=False)

    # Ingestion / embeddings
    embedding_model: str = Field(default="BAAI/bge-m3")
    embedding_dim: int = Field(default=1024)
    empty_page_min_chars: int = Field(default=40)
    chunk_size: int = Field(default=480)
    chunk_overlap: int = Field(default=48)

    # Application
    log_level: str = Field(default="INFO")


settings = Settings()
