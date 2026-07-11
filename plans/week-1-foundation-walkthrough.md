# Week 1 — Foundation Walkthrough

> **Role:** Mentor-led tutorial for a system/tool programmer pivoting into AI deployment engineering.
> **Estimated total time:** ~6 hours (six 1-hour sessions)
> **Prerequisite reading:** `DESIGN.md` (the NexusDoc architecture doc)
> **Outcome:** A working RAG pipeline with provider-agnostic model calls, self-hosted observability, and end-to-end tracing — all running on free tiers.

---

## Before We Start — What You're Actually Building

By the end of this week, you will have:

```
┌─────────────────────────────────────────────────┐
│              Your Code (app/core/)              │
│  ┌───────────────────────────────────────────┐  │
│  │         Model Registry                    │  │
│  │  Groq ── OpenRouter ── Ollama (local)    │  │
│  │  env-switchable, one interface            │  │
│  └───────────────┬───────────────────────────┘  │
│                  │                               │
│  ┌───────────────▼───────────────────────────┐  │
│  │         Hello-World RAG                   │  │
│  │  Embed doc → Vector store → Query → Answer│  │
│  └───────────────┬───────────────────────────┘  │
│                  │                               │
│  ┌───────────────▼───────────────────────────┐  │
│  │         LangFuse (Docker)                 │  │
│  │  Every call traced: latency, tokens, cost │  │
│  └───────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
```

**This is not a toy.** Every line you write this week becomes the foundation of the entire 12-week project. The model registry you build in Step 2 will route every LLM call for the next 11 weeks. The LangFuse instrumentation you add in Step 6 will trace every agent decision you build in Week 5. Take your time here — weeks 2-12 are dramatically easier if Week 1 is solid.

---

## Concepts — What You Need to Know Before Coding

*If you already understand LLMs, RAG, and observability, skip to Step 1. Otherwise, read this once — it grounds every decision in the plan.*

### What is an LLM (and why does a "provider" matter)?

An **LLM (Large Language Model)** is a neural network trained on vast amounts of text. You send it a prompt (text), it returns a completion (more text). That's it. The magic is that the completion can be an answer, code, JSON, a translation — whatever the prompt asks for.

A **provider** is the company or service that runs the model and exposes an API. Think of it like a database driver: PostgreSQL is the thing that stores data, but you talk to it through `psycopg2`, `pg`, or `sqlx`. Same idea here:

| Provider | What it is | Why we use it |
| ---------- | ----------- | --------------- |
| **Groq** | LPU-based inference (not GPU — custom chips). Extremely fast, generous free tier. | Primary provider. Free, fast. |
| **OpenRouter** | Aggregator. Routes your request to whichever backend has capacity. | Fallback when Groq rate-limits us. |
| **Ollama** | Runs models locally on your machine. No network, no API key, no cost. | Offline dev, privacy-sensitive data, zero cost. |
| **vLLM (Week 7)** | Production-grade self-hosted model server. You deploy and own the model. | The "deployment engineer" story. |

The key insight: **all of these speak the same API format** (OpenAI-compatible chat completions). Your job this week is to build a thin adapter layer so you can switch providers by changing one environment variable. This is not over-engineering — it's the difference between "I built an app that calls Groq" and "I built an app that routes to any OpenAI-compatible provider." The latter is what AI deployment engineers do.

### What is RAG?

**RAG = Retrieval Augmented Generation.** It solves the fundamental problem that LLMs don't know about *your* data.

Without RAG:

```
User: "What was Apple's revenue in Q3 2025?"
LLM: "I don't have access to that information. My training data cuts off at..."
```

With RAG:

```
User: "What was Apple's revenue in Q3 2025?"
      ↓
1. RETRIEVE: Search your vector database for relevant document chunks
      ↓  (finds: "Apple Q3 2025 10-Q: Revenue was $94.9 billion...")
2. AUGMENT: Glue the retrieved text into the prompt
      ↓  (prompt: "Based on the following document, answer the question...")
3. GENERATE: LLM reads the context and answers
      ↓
LLM: "Apple's Q3 2025 revenue was $94.9 billion, up 5% year-over-year. [Source: page 32]"
```

The "retrieve" step uses a **vector database** — it stores chunks of text as mathematical vectors (arrays of floats). When you ask a question, it finds chunks whose vectors are "close" to your question's vector. "Close" means semantically similar, not keyword-similar. This is why it can find "revenue" when you ask about "top line income."

For Week 1, you'll do a minimal version: one document, in-memory vectors (no pgvector yet), just to prove the pipeline works end-to-end.

### What is observability (and why LangFuse)?

Observability = knowing what your system is doing without `print()` statements.

In traditional programming, you debug with a debugger. In AI systems, your "code" includes probabilistic model calls, vector searches, and multi-step agent chains. A single user request might trigger 8-15 LLM calls. You cannot `print()` your way through that.

LangFuse gives you a **trace** — a tree of spans showing every step:

```
User Query: "What was Apple's revenue?"
├── [span] retrieve (237ms) — found 5 chunks from pgvector
├── [span] rerank (89ms) — cross-encoder scored 5 chunks, kept top 3
├── [span] llm-call (1.2s) — Groq/llama-3.3-70b, 1,247 tokens in, 89 out
│   └── cost: $0.00012
└── [span] guardrail-check (12ms) — PII scan passed
```

This is a **non-negotiable** skill for AI engineering roles. Every job listing that mentions "LLMOps" or "production AI" expects you to instrument your pipelines. We set up LangFuse in Week 1 so that every single thing you build for the next 11 weeks is automatically traced.

---

## Prerequisites

Before you start coding, create these accounts and install these tools. All are free.

### Accounts to create (free tiers)

| Service | Sign-up URL | What you need |
| --------- | ------------ | --------------- |
| **Groq** | <https://console.groq.com> | Create account → API Keys → copy key |
| **OpenRouter** | <https://openrouter.ai> | Create account → API Keys → copy key |
| **Supabase** | <https://supabase.com> | Create account → new project → copy connection string (you won't use it until Week 2, but create it now) |

### Tools to install

| Tool | Install command | Why |
| ------ | ---------------- | ----- |
| **uv** | `powershell -c "irm https://astral.sh/uv/install.ps1 \| iex"` (Windows) or `curl -LsSf https://astral.sh/uv/install.sh \| sh` (macOS/Linux) | Python package manager. 10-100x faster than pip. Replaces pip, venv, poetry, pyenv. |
| **Docker Desktop** | <https://www.docker.com/products/docker-desktop/> | Runs LangFuse locally |
| **Ollama** | <https://ollama.com/download> | Runs LLMs locally |
| **Git** | Already installed if you're a dev | Version control |
| **VS Code** (or your editor) | <https://code.visualstudio.com> | Python extension, ruff extension recommended |

### Verify installations

Run these and confirm they all work before moving on:

```bash
uv --version          # should print uv 0.x.x
docker --version      # should print Docker version 27.x.x or later
ollama --version      # should print ollama version is 0.x.x
git --version         # should print git version 2.x.x

# Pull a small model for local testing (takes ~5 min, ~4.7 GB):
ollama pull llama3.2:3b
```

---

## Step 1 — Project Scaffold (~1 hour)

**Goal:** A clean Python project with dependency management, linting, and a working `.env` system.

### What you'll learn

- Modern Python project structure with `uv`
- `pyproject.toml` as the single source of truth
- Environment variable management for secrets
- Pre-commit hooks for code quality

### 1.1 Create the project

```bash
# Create and enter the project directory
mkdir nexusdoc && cd nexusdoc

# Initialize git
git init
git checkout -b main

# Initialize Python project with uv
uv init --app .

# This creates a minimal pyproject.toml. Now let's flesh it out.
```

### 1.2 Write pyproject.toml

Open `pyproject.toml` and replace the content with this:

```toml
[project]
name = "nexusdoc"
version = "0.1.0"
description = "Multi-Agent Document Intelligence Platform"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "groq>=0.20.0",
    "openai>=1.0.0",           # OpenRouter uses OpenAI-compatible API
    "ollama>=0.4.0",
    "langfuse>=3.0.0",
    "python-dotenv>=1.0.0",
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
    "numpy>=1.26.0",
    "sentence-transformers>=3.0.0",  # local embeddings
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.24.0",
    "ruff>=0.9.0",
    "mypy>=1.13.0",
    "pre-commit>=4.0.0",
    "vcrpy>=7.0.0",
]

[tool.ruff]
target-version = "py312"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP", "B", "SIM"]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"

[tool.mypy]
python_version = "3.12"
strict = true
warn_return_any = true
warn_unused_configs = true

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

> **Why these choices:** `ruff` is a single Rust-based tool that replaces flake8 + isort + black. It runs in milliseconds. `mypy` with `strict = true` catches type errors that would be runtime crashes. Both are table stakes for production Python in 2026 — any AI engineering team expects them.

### 1.3 Create virtual environment and install

```bash
# uv creates and manages the venv for you
uv venv

# Activate it (Windows PowerShell):
.venv\Scripts\Activate.ps1
# OR (macOS/Linux):
source .venv/bin/activate

# Install the project and dev dependencies
uv pip install -e ".[dev]"
```

### 1.4 Create .env.example and .env

Create `.env.example` (this goes into git — it's the template):

```bash
# LLM Providers
GROQ_API_KEY=           # from https://console.groq.com/keys
OPENROUTER_API_KEY=     # from https://openrouter.ai/keys

# Database (Week 2)
SUPABASE_URL=           # from https://supabase.com dashboard
SUPABASE_SERVICE_KEY=   # from Supabase project settings

# Observability
LANGFUSE_SECRET_KEY=    # generate: openssl rand -hex 32
LANGFUSE_PUBLIC_KEY=    # generate: openssl rand -hex 32
LANGFUSE_HOST=http://localhost:3000

# Local models
OLLAMA_HOST=http://localhost:11434

# App config
DEFAULT_PROVIDER=groq   # groq | openrouter | ollama
LOG_LEVEL=INFO
```

Create `.env` (this does NOT go into git):

```bash
cp .env.example .env
# Now fill in your actual API keys
```

> **Critical habit:** `.env` contains secrets. Add it to `.gitignore` immediately:
>
> ```bash
> echo ".env" >> .gitignore
> ```

### 1.5 Set up pre-commit hooks

Create `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.9.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.13.0
    hooks:
      - id: mypy
        additional_dependencies: [pydantic>=2.0.0]
```

Install the hooks:

```bash
pre-commit install
```

### 1.6 Create the directory structure

```bash
mkdir -p app/core app/rag tests data/sample_docs
touch app/__init__.py app/core/__init__.py app/rag/__init__.py tests/__init__.py
```

### 1.7 Verify everything works

```bash
# Lint check (should pass with no files to check)
ruff check .

# Type check (should pass)
mypy app/

# Run pre-commit on all files (should pass)
pre-commit run --all-files

# Verify you can import your package
python -c "import app; print('app package works')"
```

### Step 1 checkpoint

- [ ] `uv run python -c "import groq; print('groq ok')"` works
- [ ] `uv run python -c "import langfuse; print('langfuse ok')"` works
- [ ] `.env` exists with your Groq and OpenRouter keys filled in
- [ ] `.env` is in `.gitignore`
- [ ] `ruff check .` passes
- [ ] `mypy app/` passes
- [ ] Git is initialized

**If anything fails here, stop and fix it.** Every later step depends on this foundation.

---

## Step 2 — Model Registry: Design + Groq Provider (~1 hour)

**Goal:** A provider-agnostic interface. Call `registry.get_provider()` and get back an object that handles chat completions, regardless of whether the backend is Groq, OpenRouter, or Ollama.

### What you'll learn

- Abstract base classes for provider abstraction (the Strategy pattern)
- Why you want this before you write any agent code
- How to use Pydantic Settings for configuration from environment variables

### 2.1 Why a registry?

Imagine building 12 weeks of code that all calls `groq_client.chat.completions.create(...)` directly. Then Week 7 you need to benchmark against a self-hosted vLLM endpoint. You'd have to find-and-replace every `groq_client` reference. Now imagine you add a fallback: "if Groq returns a rate-limit error, try OpenRouter." Without a registry, you're adding `try/except` blocks everywhere.

With a registry, you change one environment variable (`DEFAULT_PROVIDER=groq` → `DEFAULT_PROVIDER=vllm`) and every call in the entire codebase automatically routes to the new provider. The fallback logic lives in one place.

**This is not architecture astronautics.** It's maybe 80 lines of code and it pays off in every single week after this one.

### 2.2 The design

```
app/core/
├── __init__.py
├── config.py          # Pydantic Settings — reads from .env
├── model_registry.py   # Provider factory + fallback logic
└── providers/
    ├── __init__.py
    ├── base.py         # Abstract base class
    └── groq_provider.py # Groq implementation
```

### 2.3 Write the config (`app/core/config.py`)

```python
"""Application configuration via Pydantic Settings.

Reads from .env file automatically. Every setting has a default
that works for local development with free-tier providers.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # ignore unknown env vars, don't crash
    )

    # -- LLM Providers --
    groq_api_key: str = ""
    openrouter_api_key: str = ""
    ollama_host: str = "http://localhost:11434"

    # -- Default provider (groq | openrouter | ollama) --
    default_provider: str = "groq"

    # -- Observability --
    langfuse_secret_key: str = ""
    langfuse_public_key: str = ""
    langfuse_host: str = "http://localhost:3000"

    # -- Database (Week 2+) --
    supabase_url: str = ""
    supabase_service_key: str = ""

    # -- App --
    log_level: str = "INFO"


# Singleton — import this everywhere
settings = Settings()
```

> **Why Pydantic Settings?** It automatically reads from `.env`, validates types, and crashes early if required values are missing. No more `os.getenv("GROQ_API_KEY")` scattered across 20 files. One import, one source of truth.

### 2.4 Write the abstract base provider (`app/core/providers/base.py`)

```python
"""Abstract base class for all LLM providers.

Every provider (Groq, OpenRouter, Ollama, vLLM) implements this interface.
The rest of the codebase only ever imports BaseProvider — it never knows
which concrete provider is behind it.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ChatMessage:
    """A single message in a conversation."""
    role: str        # "system" | "user" | "assistant"
    content: str


@dataclass
class CompletionResult:
    """What every provider returns from a chat completion."""
    content: str
    model: str
    usage: dict = field(default_factory=dict)  # {prompt_tokens, completion_tokens, total_tokens}


class BaseProvider(ABC):
    """Interface that every provider must implement."""

    @abstractmethod
    def chat(
        self,
        messages: list[ChatMessage],
        model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 1024,
    ) -> CompletionResult:
        """Send a chat completion request and return the result."""
        ...

    @abstractmethod
    def list_models(self) -> list[str]:
        """Return the list of available model IDs for this provider."""
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable provider name for logging/tracing."""
        ...
```

> **Parallel to system programming:** This is exactly the same pattern as a graphics API abstraction (Direct3D vs Vulkan vs Metal). You define `draw_triangle()`, and each backend implements it. The game engine doesn't care which backend is active.

### 2.5 Write the Groq provider (`app/core/providers/groq_provider.py`)

```python
"""Groq provider — LPU-based ultra-fast inference.

Uses the official Groq Python SDK. Groq's API is OpenAI-compatible
but we use the native SDK for proper error types and streaming support.
"""

from groq import Groq

from app.core.config import settings
from app.core.providers.base import BaseProvider, ChatMessage, CompletionResult


class GroqProvider(BaseProvider):
    """Groq chat completion provider.

    Free tier limits (as of July 2026):
    - 30 requests per minute
    - ~1,000 requests per day
    - Model list: llama-3.3-70b, llama-3.1-8b, mixtral-8x7b, gemma2-9b, qwen-2.5-32b
    """

    def __init__(self) -> None:
        if not settings.groq_api_key:
            raise ValueError(
                "GROQ_API_KEY is not set. Get a free key at https://console.groq.com/keys"
            )
        self._client = Groq(api_key=settings.groq_api_key)

    @property
    def provider_name(self) -> str:
        return "groq"

    def chat(
        self,
        messages: list[ChatMessage],
        model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 1024,
    ) -> CompletionResult:
        model = model or "llama-3.3-70b-versatile"

        response = self._client.chat.completions.create(
            model=model,
            messages=[{"role": m.role, "content": m.content} for m in messages],
            temperature=temperature,
            max_tokens=max_tokens,
        )

        choice = response.choices[0]
        return CompletionResult(
            content=choice.message.content or "",
            model=response.model,
            usage={
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                "total_tokens": response.usage.total_tokens if response.usage else 0,
            },
        )

    def list_models(self) -> list[str]:
        """Return models available on Groq free tier."""
        return [
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "mixtral-8x7b-32768",
            "gemma2-9b-it",
            "qwen-2.5-32b",
        ]
```

### 2.6 Write the model registry (`app/core/model_registry.py`)

```python
"""Provider-agnostic model registry.

The single entry point for all LLM calls. Switch providers by changing
DEFAULT_PROVIDER in .env. Add fallback logic here — downstream code
never knows which provider is actually handling the request.
"""

from app.core.config import settings
from app.core.providers.base import BaseProvider
from app.core.providers.groq_provider import GroqProvider


# Lazy-initialized singleton
_provider: BaseProvider | None = None


def get_provider() -> BaseProvider:
    """Return the configured provider, initializing on first call.

    Switch providers by setting DEFAULT_PROVIDER in .env:
      groq       → Groq (fast, free-tier-friendly)
      openrouter → OpenRouter (fallback when Groq rate-limits)
      ollama     → Local models (offline, zero cost)
      vllm       → Self-hosted vLLM (Week 7)
    """
    global _provider
    if _provider is not None:
        return _provider

    name = settings.default_provider.lower()
    if name == "groq":
        _provider = GroqProvider()
    # elif name == "openrouter":
    #     _provider = OpenRouterProvider()   # Step 3
    # elif name == "ollama":
    #     _provider = OllamaProvider()       # Step 3
    else:
        raise ValueError(
            f"Unknown provider '{name}'. "
            f"Set DEFAULT_PROVIDER to one of: groq, openrouter, ollama"
        )

    return _provider


def reset_provider() -> None:
    """Reset the cached provider (useful for testing)."""
    global _provider
    _provider = None
```

### 2.7 Test it

Create `tests/test_model_registry.py`:

```python
"""Tests for model registry and Groq provider.

These tests require a valid GROQ_API_KEY in .env.
They will make real API calls — we'll add VCR cassettes in Week 6
to make them fully offline.
"""

import pytest
from app.core.config import settings
from app.core.model_registry import get_provider, reset_provider
from app.core.providers.base import ChatMessage


@pytest.fixture(autouse=True)
def reset():
    """Reset the provider singleton between tests."""
    reset_provider()


@pytest.mark.skipif(not settings.groq_api_key, reason="GROQ_API_KEY not set")
def test_groq_provider_chat():
    """Test that the Groq provider returns a valid completion."""
    provider = get_provider()
    assert provider.provider_name == "groq"

    result = provider.chat(
        messages=[
            ChatMessage(role="system", content="Reply with exactly: pong"),
            ChatMessage(role="user", content="ping"),
        ],
        max_tokens=10,
    )

    assert "pong" in result.content.lower()
    assert result.usage["total_tokens"] > 0
    print(f"  Tokens: {result.usage['total_tokens']}")


@pytest.mark.skipif(not settings.groq_api_key, reason="GROQ_API_KEY not set")
def test_groq_list_models():
    """Test that the provider lists available models."""
    provider = get_provider()
    models = provider.list_models()
    assert len(models) > 0
    assert any("llama" in m for m in models)
```

Run the tests:

```bash
uv run pytest tests/test_model_registry.py -v -s
```

If you see `ping → pong` in the output, your model registry is working.

### Step 2 checkpoint

- [ ] `uv run pytest tests/test_model_registry.py -v` passes
- [ ] You can change `DEFAULT_PROVIDER` in `.env` from `groq` to `foo` and get a clear error
- [ ] You understand the Strategy pattern: `BaseProvider` → `GroqProvider` → `get_provider()`

---

## Step 3 — OpenRouter + Ollama Providers (~1 hour)

**Goal:** Two more providers, same interface. Switch between them by changing one env var.

### What you'll learn

- How different providers expose the same OpenAI-compatible API
- OpenRouter's free-tier model router
- Running models locally with Ollama (no network, no API key, no cost)

### 3.1 Write the OpenRouter provider

Create `app/core/providers/openrouter_provider.py`:

```python
"""OpenRouter provider — model aggregator with a free tier.

OpenRouter routes requests to the cheapest available backend.
The free tier limits you to specific free models but requires
no payment method.

API docs: https://openrouter.ai/docs
"""

from openai import OpenAI

from app.core.config import settings
from app.core.providers.base import BaseProvider, ChatMessage, CompletionResult


class OpenRouterProvider(BaseProvider):
    """OpenRouter chat completion provider.

    Uses the OpenAI-compatible endpoint. The OpenAI Python SDK
    works with any OpenAI-compatible server by setting base_url.
    """

    def __init__(self) -> None:
        if not settings.openrouter_api_key:
            raise ValueError(
                "OPENROUTER_API_KEY is not set. Get a free key at https://openrouter.ai/keys"
            )
        self._client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=settings.openrouter_api_key,
        )

    @property
    def provider_name(self) -> str:
        return "openrouter"

    def chat(
        self,
        messages: list[ChatMessage],
        model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 1024,
    ) -> CompletionResult:
        model = model or "meta-llama/llama-3.3-70b-instruct"

        response = self._client.chat.completions.create(
            model=model,
            messages=[{"role": m.role, "content": m.content} for m in messages],
            temperature=temperature,
            max_tokens=max_tokens,
        )

        choice = response.choices[0]
        return CompletionResult(
            content=choice.message.content or "",
            model=response.model,
            usage={
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                "total_tokens": response.usage.total_tokens if response.usage else 0,
            },
        )

    def list_models(self) -> list[str]:
        """Free-tier models on OpenRouter (subject to change)."""
        return [
            "meta-llama/llama-3.3-70b-instruct",
            "google/gemma-2-9b-it",
            "mistralai/mistral-7b-instruct",
            "qwen/qwen-2.5-7b-instruct",
        ]
```

> **Teaching point:** Notice that `OpenRouterProvider` uses the `openai` Python package, not a special OpenRouter SDK. This is because OpenRouter exposes an OpenAI-compatible endpoint. The same `openai` package will also work with vLLM in Week 7. This is why the OpenAI API format became the industry standard — one client library talks to everything.

### 3.2 Write the Ollama provider

Create `app/core/providers/ollama_provider.py`:

```python
"""Ollama provider — local model inference.

Ollama runs models on your machine. No API key, no network,
no rate limits, no cost. Great for development and offline work.

Requires: ollama installed and a model pulled (e.g., ollama pull llama3.2:3b)
"""

from ollama import Client

from app.core.config import settings
from app.core.providers.base import BaseProvider, ChatMessage, CompletionResult


class OllamaProvider(BaseProvider):
    """Ollama local chat completion provider."""

    def __init__(self) -> None:
        self._client = Client(host=settings.ollama_host)

    @property
    def provider_name(self) -> str:
        return "ollama"

    def chat(
        self,
        messages: list[ChatMessage],
        model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 1024,
    ) -> CompletionResult:
        model = model or "llama3.2:3b"

        response = self._client.chat(
            model=model,
            messages=[{"role": m.role, "content": m.content} for m in messages],
            options={
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        )

        return CompletionResult(
            content=response["message"]["content"],
            model=response["model"],
            usage={
                "prompt_tokens": response.get("prompt_eval_count", 0),
                "completion_tokens": response.get("eval_count", 0),
                "total_tokens": response.get("prompt_eval_count", 0)
                + response.get("eval_count", 0),
            },
        )

    def list_models(self) -> list[str]:
        """List locally pulled models."""
        try:
            models = self._client.list()
            return [m["name"] for m in models.get("models", [])]
        except Exception:
            return []
```

### 3.3 Update the registry

Edit `app/core/model_registry.py` — uncomment the new providers in `get_provider()`:

```python
from app.core.providers.openrouter_provider import OpenRouterProvider
from app.core.providers.ollama_provider import OllamaProvider

# In get_provider():
    elif name == "openrouter":
        _provider = OpenRouterProvider()
    elif name == "ollama":
        _provider = OllamaProvider()
```

### 3.4 Test all three

```bash
# Test Groq (set DEFAULT_PROVIDER=groq in .env)
uv run pytest tests/test_model_registry.py -v -s

# Test OpenRouter (change DEFAULT_PROVIDER=openrouter, run again)
uv run pytest tests/test_model_registry.py -v -s

# Test Ollama (change DEFAULT_PROVIDER=ollama, run again)
uv run pytest tests/test_model_registry.py -v -s
```

### Step 3 checkpoint

- [ ] All three providers pass the same test
- [ ] You can switch providers with one env var change
- [ ] `ollama list` shows at least one pulled model
- [ ] You ran the test with Ollama and it completed successfully (no network needed)

---

## Step 4 — LangFuse Self-Hosted with Docker (~1 hour)

**Goal:** LangFuse running locally in Docker. Every future API call traced automatically.

### What you'll learn

- What LLM observability looks like in practice
- Docker Compose for local infrastructure
- LangFuse's trace → span → generation hierarchy

### 4.1 What is a trace?

A **trace** is a tree representing one user interaction:

```
Trace: "What was Apple's Q3 2025 revenue?"
├── Span: retrieve
│   ├── Generation: embedding (fastembed/bge-small-en)
│   └── Span: vector_search (pgvector HNSW)
├── Span: rerank
│   └── Generation: cross-encoder (bge-reranker-v2-m3)
└── Span: generate_answer
    └── Generation: chat_completion (Groq/llama-3.3-70b)
        ├── prompt_tokens: 1247
        ├── completion_tokens: 89
        └── cost: $0.00012
```

- **Trace** = one end-to-end user request
- **Span** = a unit of work (retrieval, reranking, guardrail check)
- **Generation** = a specific LLM call (model, tokens, cost)

This is the mental model. LangFuse instruments it automatically when you wrap your functions.

### 4.2 Create docker-compose for LangFuse

Create `docker-compose.yml` in the project root:

```yaml
# LangFuse self-hosted — single-container setup for local development.
# For production, see: https://langfuse.com/docs/deployment/self-host
#
# This uses the pre-built LangFuse image with embedded ClickHouse
# (since Jan 2026). Much simpler than the old multi-container setup.

services:
  langfuse:
    image: ghcr.io/langfuse/langfuse:latest
    ports:
      - "3000:3000"
    environment:
      # Generate these with: openssl rand -hex 32
      NEXTAUTH_SECRET: "${LANGFUSE_SECRET_KEY}"
      SALT: "${LANGFUSE_SECRET_KEY}"
      ENCRYPTION_KEY: "${LANGFUSE_SECRET_KEY}"
      # Database — embedded ClickHouse+Postgres in the image
      DATABASE_URL: "postgresql://postgres:postgres@localhost:5432/postgres"
      # Allow local connections without HTTPS
      NEXTAUTH_URL: "http://localhost:3000"
      TELEMETRY_ENABLED: "false"
      # Initial admin user (create on first launch)
      LANGFUSE_INIT_USER_EMAIL: "admin@nexusdoc.local"
      LANGFUSE_INIT_USER_PASSWORD: "nexusdoc-dev"
      LANGFUSE_INIT_USER_NAME: "NexusDoc Admin"
      LANGFUSE_INIT_ORG_ID: "nexusdoc"
      LANGFUSE_INIT_ORG_NAME: "NexusDoc"
      LANGFUSE_INIT_PROJECT_ID: "nexusdoc-dev"
      LANGFUSE_INIT_PROJECT_NAME: "nexusdoc-dev"
    volumes:
      - langfuse_data:/var/lib/langfuse
    restart: unless-stopped

volumes:
  langfuse_data:
```

> **Note:** The exact LangFuse self-hosted setup may change. If the above doesn't work, check <https://langfuse.com/docs/deployment/self-host> for the latest `docker-compose.yml`. The important thing is getting a running instance — the exact YAML is secondary.

### 4.3 Start LangFuse

```bash
docker compose up -d

# Check it's running
docker compose ps
# Should show langfuse service as "Up"

# Check logs if it fails to start
docker compose logs langfuse
```

Once running, open <http://localhost:3000>. You should see the LangFuse UI.

### 4.4 Get your API keys

1. Go to <http://localhost:3000>
2. Sign in with `admin@nexusdoc.local` / `nexusdoc-dev`
3. Go to Settings → API Keys
4. Click "Create API Key"
5. Copy the secret key and public key

Update your `.env`:

```bash
LANGFUSE_SECRET_KEY=sk-lf-...   # the secret key you copied
LANGFUSE_PUBLIC_KEY=pk-lf-...   # the public key you copied
LANGFUSE_HOST=http://localhost:3000
```

### 4.5 Verify LangFuse receives data

Create a quick test script `scripts/test_langfuse.py`:

```python
"""Quick smoke test: send a trace to LangFuse and verify it appears."""
from langfuse import Langfuse

from app.core.config import settings

langfuse = Langfuse(
    secret_key=settings.langfuse_secret_key,
    public_key=settings.langfuse_public_key,
    host=settings.langfuse_host,
)

# Create a trace
trace = langfuse.trace(name="smoke-test")

# Add a span (unit of work)
span = trace.span(name="test-operation")
span.end()

# Add a generation (LLM call)
generation = trace.generation(
    name="test-llm-call",
    model="llama-3.3-70b",
    input="What is the capital of France?",
    output="Paris",
    usage={
        "prompt_tokens": 10,
        "completion_tokens": 5,
        "total_tokens": 15,
    },
)
generation.end()

langfuse.flush()
print("✅ Trace sent. Check http://localhost:3000")
```

Run it:

```bash
uv run python scripts/test_langfuse.py
```

Refresh LangFuse at <http://localhost:3000>. You should see a "smoke-test" trace with a span and a generation.

### Step 4 checkpoint

- [ ] `docker compose ps` shows LangFuse running
- [ ] <http://localhost:3000> loads the LangFuse UI
- [ ] You created API keys and saved them in `.env`
- [ ] The smoke-test trace appears in LangFuse

---

## Step 5 — Hello-World RAG Pipeline (~1 hour)

**Goal:** Embed a document, store its vectors, query it, and get a cited answer — all traced in LangFuse.

### What you'll learn

- What embeddings are and how they enable semantic search
- Minimal RAG pipeline: chunk → embed → retrieve → generate
- How to use sentence-transformers for local embeddings

### 5.1 What are embeddings?

An **embedding** converts text into a vector (a list of 768 or 1024 floats). Think of it as a coordinate in "meaning space":

```
"cat"        → [0.12, -0.34, 0.87, ...]
"kitten"     → [0.11, -0.32, 0.85, ...]  ← close to "cat"
"dog"        → [0.45, 0.21, -0.12, ...]   ← somewhat close
"democracy"  → [-0.89, 0.56, 0.03, ...]   ← far from "cat"
```

The distance between two vectors represents semantic similarity. "Cat" and "kitten" are close; "cat" and "democracy" are far apart.

For RAG, we embed every chunk of a document and store the vectors. When a user asks a question, we embed the question and find chunks whose vectors are closest. This is **semantic search** — it finds meaning, not keywords.

We use `sentence-transformers` with the `all-MiniLM-L6-v2` model (80 MB, runs on CPU, good enough for Week 1). We'll upgrade to `bge-m3` in Week 3.

### 5.2 Create a sample document

Create `data/sample_docs/nexus_brief.txt`:

```
NexusDoc: Multi-Agent Document Intelligence Platform

OVERVIEW
NexusDoc is an AI-powered platform that ingests complex financial and
regulatory documents, runs a multi-agent pipeline, and produces structured
intelligence reports.

KEY FEATURES
- Document understanding: Single VLM pass extracts tables, figures, and
  layout from PDF documents.
- Hybrid retrieval: Combines dense vector search with sparse keyword
  search, then reranks with a cross-encoder for accuracy.
- Multi-agent orchestration: A LangGraph supervisor routes queries to
  specialized agents for retrieval, summarization, and risk classification.
- Self-hosted serving: vLLM serves quantized models behind an
  OpenAI-compatible endpoint, with benchmarked throughput and latency.
- Observability: Every agent step, LLM call, and retrieval is traced
  in LangFuse with cost attribution per request.

TECHNICAL ARCHITECTURE
The system uses a provider-agnostic model registry so that any component
can use Groq, OpenRouter, Ollama, or a self-hosted vLLM endpoint by
changing one environment variable. Embeddings and reranking run locally
(bge-m3 + bge-reranker-v2-m3) for zero per-call cost. The vector store
(pgvector on Supabase) supports hybrid search with HNSW indexing.

PROBLEM STATEMENT
Analysts and compliance teams spend significant time manually extracting
data from documents that mix prose, tables, and figures. NexusDoc automates
this end-to-end: document → intelligence, with citations.

TARGET METRICS
- RAG faithfulness >90%
- End-to-end latency <30s for a 50-page document
- 40-50 curated eval cases with a CI eval gate
```

### 5.3 Write the minimal RAG pipeline

Create `app/rag/pipeline.py`:

```python
"""Minimal RAG pipeline for Week 1.

This is intentionally simple — in-memory, no pgvector, no reranker.
We'll add those in Weeks 2-3. The goal here is to prove the full
pipeline works end-to-end with tracing.
"""

import re

import numpy as np
from sentence_transformers import SentenceTransformer

from app.core.model_registry import get_provider
from app.core.providers.base import ChatMessage


# ---- Chunking ----

def chunk_text(text: str, chunk_size: int = 300, overlap: int = 50) -> list[str]:
    """Split text into overlapping chunks by sentence boundaries.

    Simple approach for Week 1. Week 2 adds proper semantic chunking.
    """
    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for sentence in sentences:
        words = len(sentence.split())
        if current_len + words > chunk_size and current:
            chunks.append(" ".join(current))
            # Keep last `overlap` words for context continuity
            overlap_text = " ".join(current[-max(1, overlap // 10) :])
            current = [overlap_text, sentence] if overlap_text else [sentence]
            current_len = len(overlap_text.split()) + words if overlap_text else words
        else:
            current.append(sentence)
            current_len += words

    if current:
        chunks.append(" ".join(current))

    return chunks


# ---- Embedding ----

class Embedder:
    """Lightweight local embedding model.

    all-MiniLM-L6-v2: 80 MB, 384 dimensions, runs on CPU.
    Good enough for Week 1. Upgrade to bge-m3 in Week 3.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        print(f"Loading embedding model: {model_name}...")
        self._model = SentenceTransformer(model_name)

    def embed(self, texts: list[str]) -> np.ndarray:
        """Convert a list of texts to a numpy array of vectors."""
        return self._model.encode(texts, show_progress_bar=False)


# ---- In-memory vector store ----

class InMemoryVectorStore:
    """Minimal vector store for Week 1. Week 2 replaces with pgvector."""

    def __init__(self, embedder: Embedder) -> None:
        self._embedder = embedder
        self._chunks: list[str] = []
        self._vectors: np.ndarray | None = None

    def add_document(self, text: str) -> None:
        """Chunk a document, embed all chunks, store in memory."""
        self._chunks = chunk_text(text)
        print(f"  Chunked into {len(self._chunks)} chunks")
        self._vectors = self._embedder.embed(self._chunks)
        print(f"  Embedded {len(self._chunks)} chunks ({self._vectors.shape[1]}-dim)")

    def search(self, query: str, top_k: int = 3) -> list[tuple[str, float]]:
        """Find the top-k most similar chunks to the query."""
        if self._vectors is None:
            return []

        query_vec = self._embedder.embed([query])[0]

        # Cosine similarity: dot product of normalized vectors
        similarities = np.dot(self._vectors, query_vec) / (
            np.linalg.norm(self._vectors, axis=1) * np.linalg.norm(query_vec)
        )

        top_indices = np.argsort(similarities)[::-1][:top_k]

        return [(self._chunks[i], float(similarities[i])) for i in top_indices]


# ---- RAG query ----

def rag_query(
    query: str,
    vector_store: InMemoryVectorStore,
    top_k: int = 3,
) -> dict:
    """Run a single RAG query: retrieve → augment → generate.

    Returns a dict with the answer, sources, and metadata.
    """
    # 1. Retrieve
    results = vector_store.search(query, top_k=top_k)
    if not results:
        return {"answer": "No relevant documents found.", "sources": [], "usage": {}}

    # 2. Augment: build a prompt with retrieved context
    context_text = "\n\n---\n\n".join(
        f"[Source {i + 1}]:\n{chunk}" for i, (chunk, _) in enumerate(results)
    )

    system_prompt = (
        "You are a helpful assistant that answers questions based on the "
        "provided document context. If the answer is not in the context, "
        "say so. Always cite which source(s) you used."
    )

    user_prompt = (
        f"Document context:\n\n{context_text}\n\n"
        f"Question: {query}\n\n"
        f"Answer the question based on the context above. Cite sources by number."
    )

    # 3. Generate
    provider = get_provider()
    result = provider.chat(
        messages=[
            ChatMessage(role="system", content=system_prompt),
            ChatMessage(role="user", content=user_prompt),
        ],
        temperature=0.0,
        max_tokens=512,
    )

    return {
        "answer": result.content,
        "sources": [
            {"chunk": chunk[:200] + "...", "score": round(score, 4)}
            for chunk, score in results
        ],
        "usage": result.usage,
        "model": result.model,
        "provider": provider.provider_name,
    }
```

### 5.4 Create a run script

Create `scripts/hello_rag.py`:

```python
"""Hello-world RAG: embed one doc, ask questions, see it work."""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.rag.pipeline import Embedder, InMemoryVectorStore, rag_query

# Load the sample document
doc_path = Path("data/sample_docs/nexus_brief.txt")
text = doc_path.read_text()

# Build the vector store
print("=" * 60)
print("Building vector store...")
embedder = Embedder()
store = InMemoryVectorStore(embedder)
store.add_document(text)
print("=" * 60)

# Ask questions
questions = [
    "What is NexusDoc?",
    "How does the retrieval system work?",
    "What model is used for serving?",
    "What are the target metrics?",
]

for q in questions:
    print(f"\n❓ {q}")
    result = rag_query(q, store)
    print(f"🤖 {result['answer'][:300]}")
    print(f"   Provider: {result['provider']} | Model: {result['model']}")
    print(f"   Tokens: {result['usage'].get('total_tokens', '?')}")
```

Run it:

```bash
uv run python scripts/hello_rag.py
```

You should see:

1. The embedding model loads (~80 MB download, one-time)
2. The document is chunked and embedded
3. Each question retrieves relevant context and generates an answer

### Step 5 checkpoint

- [ ] `uv run python scripts/hello_rag.py` runs without errors
- [ ] The answers are relevant to the questions (they cite the NexusDoc document)
- [ ] You understand: chunk → embed → search → prompt → generate
- [ ] You can change `DEFAULT_PROVIDER` and re-run to see different models answer

---

## Step 6 — Wire Tracing + End-to-End Verification (~1 hour)

**Goal:** Every RAG step traced in LangFuse. Full observability from day one.

### What you'll learn

- Instrumenting Python code with LangFuse decorators
- Trace hierarchy: trace → span → generation
- Verifying traces in the LangFuse UI

### 6.1 Instrument the RAG pipeline

Update `app/rag/pipeline.py` — add LangFuse tracing:

```python
"""Minimal RAG pipeline for Week 1 — with LangFuse tracing."""
import re
import uuid

import numpy as np
from langfuse import Langfuse
from langfuse.decorators import langfuse_context, observe
from sentence_transformers import SentenceTransformer

from app.core.config import settings
from app.core.model_registry import get_provider
from app.core.providers.base import ChatMessage

# ---- LangFuse client ----

_langfuse: Langfuse | None = None


def get_langfuse() -> Langfuse:
    """Lazy-initialize LangFuse client."""
    global _langfuse
    if _langfuse is None:
        _langfuse = Langfuse(
            secret_key=settings.langfuse_secret_key,
            public_key=settings.langfuse_public_key,
            host=settings.langfuse_host,
        )
    return _langfuse


# ---- Chunking (same as Step 5) ----

def chunk_text(text: str, chunk_size: int = 300, overlap: int = 50) -> list[str]:
    """Split text into overlapping chunks."""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for sentence in sentences:
        words = len(sentence.split())
        if current_len + words > chunk_size and current:
            chunks.append(" ".join(current))
            overlap_text = " ".join(current[-max(1, overlap // 10):])
            current = [overlap_text, sentence] if overlap_text else [sentence]
            current_len = len(overlap_text.split()) + words if overlap_text else words
        else:
            current.append(sentence)
            current_len += words

    if current:
        chunks.append(" ".join(current))
    return chunks


# ---- Embedding (same as Step 5) ----

class Embedder:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        print(f"Loading embedding model: {model_name}...")
        self._model = SentenceTransformer(model_name)

    def embed(self, texts: list[str]) -> np.ndarray:
        return self._model.encode(texts, show_progress_bar=False)


# ---- In-memory vector store ----

class InMemoryVectorStore:
    def __init__(self, embedder: Embedder) -> None:
        self._embedder = embedder
        self._chunks: list[str] = []
        self._vectors: np.ndarray | None = None

    @property
    def chunk_count(self) -> int:
        return len(self._chunks)

    def add_document(self, text: str) -> None:
        self._chunks = chunk_text(text)
        self._vectors = self._embedder.embed(self._chunks)

    @observe(name="vector_search")
    def search(self, query: str, top_k: int = 3) -> list[tuple[str, float]]:
        """Find the top-k most similar chunks."""
        if self._vectors is None:
            return []

        query_vec = self._embedder.embed([query])[0]
        similarities = np.dot(self._vectors, query_vec) / (
            np.linalg.norm(self._vectors, axis=1) * np.linalg.norm(query_vec)
        )
        top_indices = np.argsort(similarities)[::-1][:top_k]

        # Log to LangFuse
        langfuse_context.update_current_observation(
            input=query,
            output={"top_chunks": [(self._chunks[i][:100], float(similarities[i])) for i in top_indices]},
            metadata={"total_chunks": len(self._chunks), "top_k": top_k},
        )

        return [(self._chunks[i], float(similarities[i])) for i in top_indices]


# ---- RAG query with tracing ----

@observe(name="rag_query")
def rag_query(query: str, vector_store: InMemoryVectorStore, top_k: int = 3) -> dict:
    """Run a RAG query with full tracing.

    Each step (search, generate) appears as a child span in LangFuse.
    """
    trace_id = str(uuid.uuid4())
    langfuse_context.update_current_trace(
        name="rag-query",
        user_id="week1-tutorial",
        session_id="hello-world",
        input=query,
    )

    # 1. Retrieve (child span)
    results = vector_store.search(query, top_k=top_k)
    if not results:
        langfuse_context.update_current_observation(output="No results found")
        return {"answer": "No relevant documents found.", "sources": [], "usage": {}}

    # 2. Augment
    context_text = "\n\n---\n\n".join(
        f"[Source {i + 1}]:\n{chunk}" for i, (chunk, _) in enumerate(results)
    )
    system_prompt = (
        "You are a helpful assistant that answers questions based on the "
        "provided document context. If the answer is not in the context, "
        "say so. Always cite which source(s) you used."
    )
    user_prompt = (
        f"Document context:\n\n{context_text}\n\n"
        f"Question: {query}\n\n"
        f"Answer the question based on the context above. Cite sources by number."
    )

    # 3. Generate (child generation — automatically traced by @observe)
    provider = get_provider()
    result = provider.chat(
        messages=[
            ChatMessage(role="system", content=system_prompt),
            ChatMessage(role="user", content=user_prompt),
        ],
        temperature=0.0,
        max_tokens=512,
    )

    # Log the LLM generation
    generation = get_langfuse().generation(
        trace_context={"trace_id": langfuse_context.get_current_trace_id()},
        name="llm_generation",
        model=result.model,
        input=[{"role": "system", "content": system_prompt[:500]},
               {"role": "user", "content": user_prompt[:500]}],
        output=result.content[:1000],
        usage={
            "prompt_tokens": result.usage.get("prompt_tokens", 0),
            "completion_tokens": result.usage.get("completion_tokens", 0),
            "total_tokens": result.usage.get("total_tokens", 0),
        },
        metadata={"provider": provider.provider_name},
    )
    generation.end()

    # Finalize the trace
    langfuse_context.update_current_observation(
        output={"answer": result.content[:200], "sources_count": len(results)},
        metadata={"provider": provider.provider_name, "model": result.model},
    )

    # Flush to LangFuse
    get_langfuse().flush()

    return {
        "answer": result.content,
        "sources": [
            {"chunk": chunk[:200] + "...", "score": round(score, 4)}
            for chunk, score in results
        ],
        "usage": result.usage,
        "model": result.model,
        "provider": provider.provider_name,
        "trace_id": trace_id,
    }
```

> **Wait — what is `@observe`?** It's a LangFuse decorator that automatically creates a span. When you call `rag_query()`, it creates a trace. When `rag_query` calls `vector_store.search()`, that creates a child span. You can also manually create traces with `get_langfuse().trace()` — we use both approaches so you see the full range of the API.

### 6.2 Update the run script

Create `scripts/hello_rag_traced.py`:

```python
"""Hello-world RAG with LangFuse tracing."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.rag.pipeline import Embedder, InMemoryVectorStore, rag_query

# Load document
doc_path = Path("data/sample_docs/nexus_brief.txt")
text = doc_path.read_text()

# Build vector store
print("Building vector store...")
embedder = Embedder()
store = InMemoryVectorStore(embedder)
store.add_document(text)
print(f"Vector store ready: {store.chunk_count} chunks\n")

# Ask questions
questions = [
    "What is NexusDoc?",
    "How does the retrieval system work?",
    "What model is used for model serving?",
    "What are the target metrics?",
]

for q in questions:
    print(f"\n{'=' * 60}")
    print(f"❓ {q}")
    result = rag_query(q, store)
    print(f"\n🤖 {result['answer'][:400]}")
    print(f"\n   Provider: {result['provider']} | Model: {result['model']}")
    print(f"   Tokens: {result['usage'].get('total_tokens', '?')}")
    print(f"   Trace:  {result.get('trace_id', 'N/A')}")

print(f"\n{'=' * 60}")
print("✅ All queries traced. Check http://localhost:3000")
```

### 6.3 Run and verify

```bash
# Make sure LangFuse is running
docker compose up -d

# Run the traced RAG
uv run python scripts/hello_rag_traced.py
```

Now go to <http://localhost:3000>. You should see:

1. A project called "nexusdoc-dev"
2. Inside it, traces for each question
3. Each trace contains:
   - A `rag_query` span
   - A `vector_search` child span
   - An `llm_generation` with token counts and cost

### Step 6 checkpoint

- [ ] `uv run python scripts/hello_rag_traced.py` runs without errors
- [ ] Traces appear in LangFuse at <http://localhost:3000>
- [ ] Each trace shows: search span → generation → token counts
- [ ] You can click into a trace and see the full input/output of each step

---

## Week 1 — Final Verification

Run this checklist before moving on to Week 2. If anything fails, fix it now — these are the foundations for the entire project.

### Sanity check script

Create `scripts/week1_verify.py`:

```python
"""Week 1 verification: test everything end-to-end."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def check(step: str, condition: bool) -> None:
    status = "✅" if condition else "❌"
    print(f"  {status} {step}")
    if not condition:
        sys.exit(1)


def main() -> None:
    print("=" * 60)
    print("NexusDoc Week 1 — Verification")
    print("=" * 60)

    # 1. Config
    from app.core.config import settings
    check("Settings loaded from .env", settings.default_provider != "")

    # 2. Model registry
    from app.core.model_registry import get_provider
    provider = get_provider()
    check(f"Provider '{provider.provider_name}' initialized", True)
    models = provider.list_models()
    check(f"Provider lists {len(models)} models", len(models) > 0)

    # 3. Groq API call
    from app.core.providers.base import ChatMessage
    result = provider.chat(
        messages=[ChatMessage(role="user", content="Say exactly: nexusdoc-ok")],
        max_tokens=10,
    )
    check("Provider returns valid completion", "nexusdoc" in result.content.lower())

    # 4. RAG pipeline
    from app.rag.pipeline import Embedder, InMemoryVectorStore, rag_query
    embedder = Embedder()
    store = InMemoryVectorStore(embedder)
    doc_path = Path("data/sample_docs/nexus_brief.txt")
    store.add_document(doc_path.read_text())
    check(f"Document chunked: {store.chunk_count} chunks", store.chunk_count > 0)

    rag_result = rag_query("What is NexusDoc?", store)
    check("RAG returns answer", len(rag_result["answer"]) > 10)
    check("RAG returns sources", len(rag_result["sources"]) > 0)
    check("RAG returns token usage", rag_result["usage"]["total_tokens"] > 0)

    # 5. LangFuse tracing
    trace_id = rag_result.get("trace_id")
    check(f"Trace created: {trace_id}", trace_id is not None)

    print("\n" + "=" * 60)
    print("✅ ALL CHECKS PASSED — Week 1 complete!")
    print(f"   Provider:  {rag_result['provider']}")
    print(f"   Model:     {rag_result['model']}")
    print(f"   Tokens:    {rag_result['usage']['total_tokens']}")
    print(f"   Trace:     http://localhost:3000")
    print("=" * 60)


if __name__ == "__main__":
    main()
```

Run it:

```bash
uv run python scripts/week1_verify.py
```

### Final checklist

- [ ] `week1_verify.py` passes all checks
- [ ] Traces visible in LangFuse with search spans and token counts
- [ ] Switching `DEFAULT_PROVIDER` in `.env` changes which model answers
- [ ] `ruff check .` passes
- [ ] `mypy app/` passes
- [ ] All three providers (Groq, OpenRouter, Ollama) work when configured
- [ ] Git commit made: `git add -A && git commit -m "Week 1: Foundation — model registry, LangFuse, hello-world RAG"`

---

## What You Actually Learned This Week

This isn't just a checklist — these are the skills you now have:

| Skill | Where you used it | Why it matters for AI jobs |
| ------- | ------------------- | --------------------------- |
| **Provider abstraction** | `BaseProvider` → 3 implementations | Production AI systems switch providers based on cost/latency/availability. You built the pattern. |
| **Pydantic Settings** | `app/core/config.py` | Every AI codebase uses typed config. You know the standard approach. |
| **Docker Compose for AI infra** | LangFuse container | AI systems run databases, vector stores, and observability — all containerized. |
| **LLM observability** | `@observe` decorator, traces, spans | LLMOps jobs list LangFuse/MLflow/W&B as requirements. You instrumented from day one. |
| **Embeddings & semantic search** | `InMemoryVectorStore` with cosine similarity | RAG is the #1 AI pattern in production. You built it from scratch. |
| **Prompt engineering** | System/user prompt construction in `rag_query` | Knowing how to structure prompts for retrieval + generation is table stakes. |
| **Free-tier-first design** | Groq + OpenRouter + Ollama | Real AI engineering means cost-conscious architecture. Your pipeline runs at $0. |

---

## What's Next (Week 2 Preview)

In Week 2 you'll replace the in-memory store with a real database:

- SEC EDGAR API: fetch real 10-K/10-Q filings
- PyMuPDF: parse PDFs into text and metadata
- pgvector: store vectors in Postgres (Supabase free tier)
- Proper chunking with page citations

The model registry you built this week will route every call. The LangFuse tracing will show every embedding and retrieval. Nothing this week gets thrown away — it all scales forward.

---

## If You Get Stuck

1. **Groq API key not working?** Check <https://console.groq.com/keys> — free tier keys expire after inactivity. Generate a new one.
2. **LangFuse won't start?** Run `docker compose logs langfuse` and check for port conflicts. If port 3000 is busy, change the port mapping.
3. **Ollama model not found?** Run `ollama list` — if empty, `ollama pull llama3.2:3b`.
4. **Embedding model download fails?** sentence-transformers pulls from HuggingFace. If blocked (corporate VPN, China), set `HF_ENDPOINT=https://hf-mirror.com`.
5. **Type errors from mypy?** Run `mypy app/ --follow-imports=skip` if third-party stubs are missing. This is common with newer packages.

---

*Week 1 complete. Take a breath. You just built the foundation of a production AI system.*
