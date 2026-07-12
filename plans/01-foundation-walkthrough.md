# Phase 1 — Foundation Walkthrough

> **⚠️ SUPERSEDED SCOPE (2026-07-12):** `DESIGN.md` was rewritten for a **Japan FDE / ~45h** plan.
> - **Domain:** appliance support manuals (EN+JP), not arXiv/RFC.
> - **Providers:** Groq + **Ollama on RTX 5080**; OpenRouter only after $10 credits if needed.
> - **Langfuse:** use the **official** multi-service compose (ClickHouse + Redis + MinIO + worker) — the single-container YAML in Step 4.1 below is **obsolete and will fail**.
> - **Later phases:** no multi-agent risk supervisor, no RedisVL, no Colab vLLM before Sept.
> Follow this walkthrough for **registry + traced hello-RAG** mechanics only; treat sample-doc / Langfuse / roadmap text as stale where it conflicts with `DESIGN.md`.
>
> **Role:** Senior-dev-led tutorial for a system/tool programmer pivoting into Japan AI FDE / applied AI integration.
> **Estimated total time:** ~5 hours (DESIGN Phase 1)
> **Prerequisite reading:** `DESIGN.md` (Architecture, Cost, Phase 1)
> **Outcome:** Provider registry (Groq + Ollama), Langfuse tracing, hello-world RAG on a sample manual excerpt.
>
> **📋 Progress tracking:** [`01-foundation-walkthrough-progress.md`](01-foundation-walkthrough-progress.md)

---


## Before We Start — What You're Actually Building

By the end of Phase 1 you will have:

```
┌─────────────────────────────────────────────────┐
│              Your Code (app/core/)              │
│  ┌───────────────────────────────────────────┐  │
│  │  Groq ── Ollama (RTX 5080) ── (OpenRouter optional) │
│  │  env-switchable, one interface            │
│  └───────────────┬───────────────────────────┘  │
│                  │                              │
│  ┌───────────────▼───────────────────────────┐  │
│  │   Hello-World RAG (appliance excerpt)     │  │
│  │  Embed doc → Vector store → Query → Answer│  │
│  └───────────────┬───────────────────────────┘  │
│                  │                              │
│  ┌───────────────▼───────────────────────────┐  │
│  │   Langfuse (official Docker compose)      │  │
│  │  Every call traced: latency, tokens, cost │  │
│  └───────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
```

**This is not a toy.** The model registry routes every LLM call for later phases. Langfuse instrumentation traces retrieval and generation. Take your time — later phases are easier if Phase 1 is solid.

**Where your existing knowledge helps:** You've integrated OpenAI-style APIs before, so Groq will feel familiar. New: **registry pattern**, **RAG**, **observability**.

---

## Concepts — What You Need to Know Before Coding

*Read this once — it grounds every decision in Phase 1. If a concept is already familiar, skim it; the parts about RAG and observability are the ones that are likely new to you.*

### 1. The provider-agnostic model registry (the architectural centerpiece)

A **provider** is the service that runs the model and exposes an API. Think of it like a database driver: PostgreSQL is the thing that stores data, but you talk to it through `psycopg2` or `sqlx`. Same idea here:

| Provider | What it is | Why we use it |
| ---------- | ----------- | --------------- |
| **Groq** | LPU-based inference (custom chips, not GPUs). Extremely fast, generous free tier. | Primary provider. Free, fast. |
| **OpenRouter** | Aggregator. Routes your request to whichever backend has capacity. | Fallback when Groq rate-limits us. |
| **Ollama** | Runs models locally (use RTX 5080). No API key, no cloud cost. | Self-host / offline path — **primary local provider** |
| **vLLM** | Deferred past Sept (Blackwell wheel/source friction). | Optional later; not Phase 1–7 critical path |
| **OpenRouter** | Aggregator; free tier is **50 RPD** until $10 lifetime credits. | Optional overflow after POC — not required for Phase 1 |

The key insight: **all of these speak the same API format** (OpenAI-compatible chat completions). Your job in Step 2 is to build a thin adapter layer so you can switch providers by changing one environment variable. This is not over-engineering — it's the difference between "I built an app that calls Groq" and "I built an app that routes to any OpenAI-compatible provider." The latter is what AI deployment engineers do, and it's what lets you drop in a self-hosted vLLM endpoint in Phase 7 without rewriting your codebase.

**The pattern:** an abstract `BaseProvider` class defines `chat()` and `list_models()`. Each concrete provider (`GroqProvider`, `OpenRouterProvider`, `OllamaProvider`) implements it. A `get_provider()` factory reads the `DEFAULT_PROVIDER` env var and returns the right one. Downstream code only ever imports `BaseProvider` — it never knows which concrete provider is behind it.

If you've done graphics programming, this is exactly the Direct3D/Vulkan/Metal abstraction: you define `draw_triangle()`, each backend implements it, the engine doesn't care which is active. Same mental model.

### 2. What is RAG? (you haven't built one before)

**RAG = Retrieval Augmented Generation.** It solves the fundamental problem that LLMs don't know about *your* data.

Without RAG:

```
User: "What does RFC 9110 say about the 308 status code?"
LLM: "I don't have access to that document. My training data cuts off at..."
```

With RAG:

```
User: "What does RFC 9110 say about the 308 status code?"
      ↓
1. RETRIEVE: Search your vector database for relevant document chunks
      ↓  (finds: "308 Permanent Redirect: The target resource has been
      ↓   assigned a new permanent URI...")
2. AUGMENT: Glue the retrieved text into the prompt
      ↓  (prompt: "Based on the following document, answer the question...")
3. GENERATE: LLM reads the context and answers
      ↓
LLM: "RFC 9110 defines 308 Permanent Redirect. The target resource has
     been assigned a new permanent URI... [Source: §15.4.4, page 47]"
```

The "retrieve" step uses a **vector database** — it stores chunks of text as mathematical vectors (arrays of floats). When you ask a question, it finds chunks whose vectors are "close" to your question's vector. "Close" means semantically similar, not keyword-similar. This is why it can find "revenue" when you ask about "top line income."

**An embedding** converts text into a vector. Think of it as a coordinate in "meaning space":

```
"cat"        → [0.12, -0.34, 0.87, ...]
"kitten"     → [0.11, -0.32, 0.85, ...]  ← close to "cat"
"dog"        → [0.45, 0.21, -0.12, ...]   ← somewhat close
"democracy"  → [-0.89, 0.56, 0.03, ...]   ← far from "cat"
```

For Phase 1, you'll do a minimal version: one document, **in-memory** vectors (no pgvector yet — that's Phase 2), just to prove the pipeline works end-to-end. You'll use `all-MiniLM-L6-v2` (80 MB, runs on CPU) in Phase 1 and upgrade to `bge-m3` (the production model in the design) in Phase 3.

### 3. What is observability, and why LangFuse? (entirely new to you)

Observability = knowing what your system is doing without `print()` statements.

In traditional programming, you debug with a debugger. In AI systems, your "code" includes probabilistic model calls, vector searches, and multi-step agent chains. A single user request might trigger 8-15 LLM calls (you'll see this in Phase 4). You cannot `print()` your way through that.

LangFuse gives you a **trace** — a tree of spans showing every step:

```
Trace: "What does RFC 9110 say about 308?"
├── Span: retrieve (237ms) — found 5 chunks from vector store
├── Span: rerank (89ms) — cross-encoder scored 5 chunks, kept top 3
├── Generation: llm-call (1.2s) — Groq/llama-3.3-70b, 1247 tokens in, 89 out
│   └── cost: $0.00012
└── Span: guardrail-check (12ms) — PII scan passed
```

- **Trace** = one end-to-end user request
- **Span** = a unit of work (retrieval, reranking, guardrail check)
- **Generation** = a specific LLM call (model, tokens, cost)

This is a **non-negotiable** skill for AI engineering roles. Every job listing that mentions "LLMOps" or "production AI" expects you to instrument your pipelines. We set up LangFuse in Phase 1 so that every single thing you build for the next 11 phases is automatically traced. By the time you reach the eval harness in Phase 5, observability will already be wired into your muscle memory.

LangFuse is self-hosted (free, open-source, MIT-licensed). We run it in a Docker container — which gives you a chance to warm up your container skills before the heavier `docker-compose` work in Phase 10.

---

## Prerequisites

Before you start coding, create these accounts and install these tools. All are free.

### Accounts to create (free tiers)

| Service | Sign-up URL | What you need |
| --------- | ------------ | --------------- |
| **Groq** | <https://console.groq.com> | API key — primary for cloud/demo |
| **Ollama** | local install | Pull a 7B-class model for the RTX 5080 |
| **Supabase** | <https://supabase.com> | Project + connection string (Phase 2+); create now |
| **OpenRouter** | optional | Only after E2E POC; add **$10** credits once if you need 1000 RPD |

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
ollama --version      # should print ollama version 0.x.x
git --version         # should print git version 2.x.x

# Pull a model that fits the RTX 5080 (preferred for Phase 1+):
ollama pull qwen2.5:7b
# Smaller CPU-friendly option if needed for a quick smoke test:
# ollama pull llama3.2:3b
```

> **Why `qwen2.5:7b`?** Fits 16GB VRAM comfortably and is strong enough for EN+JP support Q&A. Use `llama3.2:3b` only if you need a tiny offline smoke test without loading a 7B.

---

## Step 1 — Project Scaffold (~30 min)

**Goal:** A clean Python project with dependency management, typed config, linting, and a working `.env` system.

### What you'll learn

- Modern Python project structure with `uv`
- `pyproject.toml` as the single source of truth for deps, lint, and type config
- Environment-variable management for secrets (Pydantic Settings)
- Pre-commit hooks for code quality

You have some exposure to Python backend tooling, so this step is intentionally brisk. If any of the tools (uv, ruff, mypy) are new to you, that's the part worth slowing down on — the rest is standard.

### 1.1 Create the project

```bash
mkdir nexusdoc && cd nexusdoc
git init
git checkout -b main
uv init --app .
```

`uv init --app .` creates a minimal `pyproject.toml`. We'll flesh it out next.

### 1.2 Write `pyproject.toml`

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
    "openai>=1.0.0",           # OpenRouter uses the OpenAI-compatible API
    "ollama>=0.4.0",
    "langfuse>=3.0.0",
    "python-dotenv>=1.0.0",
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
    "numpy>=1.26.0",
    "sentence-transformers>=3.0.0",  # local embeddings (Phase 1: all-MiniLM-L6-v2)
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

> **Why these choices:** `ruff` is a single Rust-based tool that replaces flake8 + isort + black. It runs in milliseconds. `mypy` with `strict = true` catches type errors that would be runtime crashes. Both are table stakes for production Python in 2026 — any AI engineering team expects them. `vcrpy` records HTTP cassettes so your tests run offline (you'll use it from Phase 2 onward).

> **Pitfall — `openai` for OpenRouter?** Yes. The `openai` Python SDK talks to *any* OpenAI-compatible endpoint when you set `base_url`. OpenRouter, vLLM (Phase 7), and many others expose this format. This is why the OpenAI API format became the industry standard — one client library talks to everything. You'll reuse this exact trick for vLLM later.

### 1.3 Create virtual environment and install

```bash
uv venv
# Activate it (Windows PowerShell):
.venv\Scripts\Activate.ps1
# OR (macOS/Linux):
source .venv/bin/activate

uv pip install -e ".[dev]"
```

### 1.4 Create `.env.example` and `.env`

Create `.env.example` (this goes into git — it's the template):

```bash
# LLM Providers
GROQ_API_KEY=           # from https://console.groq.com/keys
OPENROUTER_API_KEY=     # from https://openrouter.ai/keys

# Database (Phase 2+)
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

Create `.env` (this does **NOT** go into git):

```bash
cp .env.example .env
# Now fill in your real Groq and OpenRouter keys. LangFuse keys come in Step 3.
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

## Step 2 — Model Registry: The Provider-Agnostic Abstraction (~75 min, DEEP)

**Goal:** A provider-agnostic interface. Call `registry.get_provider()` and get back an object that handles chat completions, regardless of whether the backend is Groq, OpenRouter, or Ollama.

### What you'll learn

- Abstract base classes for provider abstraction (the Strategy pattern)
- Why you want this *before* you write any agent code
- Why this exact abstraction is what makes the vLLM spike (Phase 7) a 1-hour change instead of a refactor

### 2.1 Why a registry? (the reasoning that matters)

Imagine building 11 phases of code that all call `groq_client.chat.completions.create(...)` directly. Then Phase 7 you need to benchmark against a self-hosted vLLM endpoint. You'd have to find-and-replace every `groq_client` reference. Now imagine you add a fallback: "if Groq returns a rate-limit error, try OpenRouter." Without a registry, you're adding `try/except` blocks everywhere.

With a registry, you change one environment variable (`DEFAULT_PROVIDER=groq` → `DEFAULT_PROVIDER=vllm`) and every call in the entire codebase automatically routes to the new provider. The fallback logic lives in one place.

**This is maybe 80 lines of code and it pays off in every single phase after this one.** It is also the single most asked-about pattern in AI deployment interviews: "How do you handle provider switching, rate-limit fallback, and cost optimization?" — this is the answer.

### 2.2 The design

```
app/core/
├── __init__.py
├── config.py            # Pydantic Settings — reads from .env
├── model_registry.py    # Provider factory + fallback logic
└── providers/
    ├── __init__.py
    ├── base.py          # Abstract base class
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

    # -- Database (Phase 2+) --
    supabase_url: str = ""
    supabase_service_key: str = ""

    # -- App --
    log_level: str = "INFO"


# Singleton — import this everywhere
settings = Settings()
```

> **Why Pydantic Settings?** It automatically reads from `.env`, validates types, and crashes early if required values are missing. No more `os.getenv("GROQ_API_KEY")` scattered across 20 files. One import, one source of truth. This is the 2026 standard for typed Python config.

### 2.4 Write the abstract base provider (`app/core/providers/base.py`)

First create `app/core/providers/__init__.py` (empty).

```python
"""Abstract base class for all LLM providers.

Every provider (Groq, OpenRouter, Ollama, vLLM) implements this interface.
The rest of the codebase only ever imports BaseProvider — it never knows
which concrete provider is behind it.

This is the Strategy pattern: define the interface once, swap implementations
freely. Downstream code depends on the abstraction, not the concretion.
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

> **Parallel to system programming:** This is exactly the same pattern as a graphics API abstraction (Direct3D vs Vulkan vs Metal). You define `draw_triangle()`, and each backend implements it. The game engine doesn't care which backend is active. Here, `chat()` is your `draw_triangle()`, and Groq/OpenRouter/Ollama/vLLM are your backends.

> **Why dataclasses for the message/result types?** They give you frozen-by-default-ish value semantics, type safety, and zero boilerplate. You'll convert these to Pydantic models in Phase 3 when you need structured output — for now dataclasses keep the surface area small.

### 2.5 Write the Groq provider (`app/core/providers/groq_provider.py`)

```python
"""Groq provider — LPU-based ultra-fast inference.

Uses the official Groq Python SDK. Groq's API is OpenAI-compatible
but we use the native SDK for proper error types and streaming support.

Free tier limits (as of July 2026):
- 30 requests per minute
- ~1,000 requests per day
- Models: llama-3.3-70b, llama-3.1-8b, qwen-2.5-32b, gemma2-9b
"""

from groq import Groq

from app.core.config import settings
from app.core.providers.base import BaseProvider, ChatMessage, CompletionResult


class GroqProvider(BaseProvider):
    """Groq chat completion provider."""

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
            "qwen-2.5-32b",
            "gemma2-9b-it",
        ]
```

> **Pitfall — rate limits are per-request, not per-token.** Groq's free tier is ~30 RPM / ~1,000 RPD. A multi-agent run (Phase 4) is 8-15 LLM calls per document. So the *requests* ceiling bites before tokens do. This is why the caching layer (Phase 6) and the fallback provider matter so much. Keep this in mind when you build your agents later.

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
      vllm       → Self-hosted vLLM (Phase 7)
    """
    global _provider
    if _provider is not None:
        return _provider

    name = settings.default_provider.lower()
    if name == "groq":
        _provider = GroqProvider()
    # elif name == "openrouter":
    #     _provider = OpenRouterProvider()   # Step 2.7
    # elif name == "ollama":
    #     _provider = OllamaProvider()       # Step 2.7
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

### 2.7 Test Groq

Create `tests/test_model_registry.py`:

```python
"""Tests for model registry and Groq provider.

These tests require a valid GROQ_API_KEY in .env.
They make real API calls — we'll add VCR cassettes in Phase 5
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

If you see `ping → pong` in the output, your model registry works. This is the moment you stop writing "an app that calls Groq" and start writing "an app that routes to any provider."

### Step 2 checkpoint

- [ ] `uv run pytest tests/test_model_registry.py -v` passes
- [ ] You can change `DEFAULT_PROVIDER` in `.env` from `groq` to `foo` and get a clear error
- [ ] You understand the Strategy pattern: `BaseProvider` → `GroqProvider` → `get_provider()`

---

## Step 3 — Add Ollama Provider (~20 min; OpenRouter optional/deferred)

**Goal:** Local provider on the RTX 5080. Switch with one env var.

OpenRouter is **deferred** per `DESIGN.md` (50 RPD until $10 credits). Skip `openrouter_provider.py` until after E2E POC unless you already paid the $10.

### 3.1 Write the Ollama provider

Create `app/core/providers/ollama_provider.py`:

```python
"""Ollama provider — local inference on the workstation GPU (RTX 5080)."""

from ollama import Client

from app.core.config import settings
from app.core.providers.base import BaseProvider, ChatMessage, CompletionResult


class OllamaProvider(BaseProvider):
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
        model = model or "qwen2.5:7b"
        response = self._client.chat(
            model=model,
            messages=[{"role": m.role, "content": m.content} for m in messages],
            options={"temperature": temperature, "num_predict": max_tokens},
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
        try:
            models = self._client.list()
            return [m["name"] for m in models.get("models", [])]
        except Exception:
            return []
```

```bash
ollama pull qwen2.5:7b
```

### 3.2 Update the registry

Wire `ollama` into `get_provider()`. Prefer **retry + fallback** (e.g. Groq 429 → Ollama) in one place in the registry.

### 3.3 Test Groq + Ollama

```bash
# DEFAULT_PROVIDER=groq
uv run pytest tests/test_model_registry.py -v -s

# DEFAULT_PROVIDER=ollama
uv run pytest tests/test_model_registry.py -v -s
```

### Step 3 checkpoint

- [ ] Groq and Ollama pass the same chat test
- [ ] `ollama list` shows a pulled model
- [ ] Switching `DEFAULT_PROVIDER` changes the backend

---

## Step 3b — OpenRouter (deferred)

Only after POC. Remember: free models are **50 RPD** without $10 lifetime credits.

Use the `openai` SDK with `base_url=https://openrouter.ai/api/v1` and prefer `:free` model IDs when on free quota. Do not rely on OpenRouter for CI until unlocked.

---

## Step 4 — Langfuse Self-Hosted + Hello-World Traced RAG (~75–90 min, DEEP)

**Goal:** LangFuse running in Docker. Then a minimal RAG pipeline (chunk → embed → retrieve → generate) with every step automatically traced.

This combines the two concepts that are newest to you — observability and RAG — into one step. We'll set up LangFuse first (you need API keys for the tracing code), then build the pipeline, then instrument it.

### 4.1 Langfuse via official Docker Compose (**do not use a single-container hack**)

Modern Langfuse **requires** Postgres + ClickHouse + Redis + MinIO + `langfuse-web` + `langfuse-worker`. A lone `langfuse` service with `DATABASE_URL=...@localhost` will fail.

**Do this:**

1. Copy the official compose from Langfuse:  
   <https://github.com/langfuse/langfuse/blob/main/docker-compose.yml>  
   into this repo as `docker-compose.yml` (or `docker-compose.langfuse.yml`).
2. Pin ClickHouse to a supported tag if `latest` breaks (see Langfuse issues — avoid untested 26.x until docs say otherwise). Prefer the versions in Langfuse’s own file / docs.
3. Set secrets via `.env` (`NEXTAUTH_SECRET`, `SALT`, `ENCRYPTION_KEY`, DB passwords) — generate with `openssl rand -hex 32`.
4. Set init user/project env vars if you want a deterministic local admin (see official compose comments).

```bash
docker compose up -d
docker compose ps    # web, worker, postgres, clickhouse, redis, minio should be healthy
```

> **Docs:** <https://langfuse.com/self-hosting>  
> **If port 3000 is busy:** change the web port mapping and set `LANGFUSE_HOST` / `NEXTAUTH_URL` accordingly.  
> **Windows:** ensure Docker Desktop has enough RAM (ClickHouse stack is heavier than a toy single container).

### 4.2 Get your LangFuse API keys

1. Open <http://localhost:3000>
2. Sign in with `admin@nexusdoc.local` / `nexusdoc-dev`
3. Go to Settings → API Keys → Create API Key
4. Copy the **secret key** and **public key**

Update your `.env`:

```bash
LANGFUSE_SECRET_KEY=sk-lf-...   # the secret key you copied
LANGFUSE_PUBLIC_KEY=pk-lf-...   # the public key you copied
LANGFUSE_HOST=http://localhost:3000
```

### 4.3 Smoke-test LangFuse

Create `scripts/test_langfuse.py`:

```python
"""Quick smoke test: send a trace to LangFuse and verify it appears."""
from langfuse import Langfuse

from app.core.config import settings

langfuse = Langfuse(
    secret_key=settings.langfuse_secret_key,
    public_key=settings.langfuse_public_key,
    host=settings.langfuse_host,
)

trace = langfuse.trace(name="smoke-test")
span = trace.span(name="test-operation")
span.end()

generation = trace.generation(
    name="test-llm-call",
    model="llama-3.3-70b",
    input="What is the capital of France?",
    output="Paris",
    usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
)
generation.end()

langfuse.flush()
print("Sent trace. Check http://localhost:3000")
```

Run it:

```bash
uv run python scripts/test_langfuse.py
```

Refresh LangFuse at <http://localhost:3000>. You should see a "smoke-test" trace with a span and a generation.

### Step 4a checkpoint

- [ ] `docker compose ps` shows LangFuse running
- [ ] <http://localhost:3000> loads
- [ ] API keys saved in `.env`
- [ ] The smoke-test trace appears in LangFuse

### 4.4 Create a sample document

Create `data/sample_docs/appliance_manual_excerpt.txt` (stand-in until Phase 2 PDFs):

```
NexusWash NW-8000 — User Manual (excerpt, EN)
Model: NW-8000  |  Language: English  |  Pages: 1–3 (sample)

ERROR CODES
E12 — Drain fault. Water was not drained within the expected time.
Procedure:
1. Pause the cycle and switch the unit off at the wall.
2. Check that the drain hose is not kinked and the sink outlet is clear.
3. Clean the drain filter (see Maintenance §3.2).
4. Restart. If E12 returns within one cycle, contact authorized service.

E27 — Unbalanced load. The drum could not spin up safely.
Procedure:
1. Open the door when unlocked.
2. Redistribute garments evenly around the drum.
3. Do not mix heavy items (bath mats) with light synthetics in one spin.
4. Close the door and press Start.

MAINTENANCE §3.2 — Drain filter
1. Place a shallow tray under the filter cover at the front bottom.
2. Turn the filter cap counter-clockwise; expect residual water.
3. Remove lint and debris; rinse the filter under tap water.
4. Refit the cap firmly clockwise until hand-tight. Do not over-tighten.

SAFETY
Do not put hands in the drum while it is moving.
Disconnect mains power before removing the drain filter.
```

Also add a tiny JP stub `data/sample_docs/appliance_manual_excerpt_ja.txt` for bilingual smoke tests later:

```
NexusWash NW-8000 — 取扱説明書（抜粋）
エラーコード E12 — 排水異常。規定時間内に排水できませんでした。
対処: 電源を切る → 排水ホースの折れを確認 → 排水フィルター清掃（§3.2）→ 再起動。
```

> **Why this document?** Matches the locked DESIGN domain (support manuals, cited troubleshooting). Phase 2 replaces this with real manufacturer EN+JP PDFs.

### 4.5 Write the minimal RAG pipeline with tracing

Create `app/rag/pipeline.py`:

```python
"""Minimal RAG pipeline for Phase 1 — with LangFuse tracing.

Intentionally simple: in-memory, no pgvector, no reranker.
We add those in Phases 2-3. The goal here is to prove the full
pipeline works end-to-end with tracing, so every later phase inherits
working observability.
"""

import re
import uuid

import numpy as np
from langfuse import Langfuse
from langfuse.decorators import langfuse_context, observe
from sentence_transformers import SentenceTransformer

from app.core.config import settings
from app.core.model_registry import get_provider
from app.core.providers.base import ChatMessage


# ---- LangFuse client (lazy singleton) ----

_langfuse: Langfuse | None = None


def get_langfuse() -> Langfuse:
    global _langfuse
    if _langfuse is None:
        _langfuse = Langfuse(
            secret_key=settings.langfuse_secret_key,
            public_key=settings.langfuse_public_key,
            host=settings.langfuse_host,
        )
    return _langfuse


# ---- Chunking ----

def chunk_text(text: str, chunk_size: int = 300, overlap: int = 50) -> list[str]:
    """Split text into overlapping chunks by sentence boundaries.

    Simple approach for Phase 1. Phase 2 adds proper semantic chunking
    with page/section metadata.
    """
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


# ---- Embedding ----

class Embedder:
    """Lightweight local embedding model.

    all-MiniLM-L6-v2: 80 MB, 384 dimensions, runs on CPU.
    Good enough for Phase 1. Upgrade to bge-m3 (1024-dim) in Phase 3.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        print(f"Loading embedding model: {model_name}...")
        self._model = SentenceTransformer(model_name)

    def embed(self, texts: list[str]) -> np.ndarray:
        return self._model.encode(texts, show_progress_bar=False)


# ---- In-memory vector store ----

class InMemoryVectorStore:
    """Minimal vector store for Phase 1. Phase 2 replaces with pgvector."""

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
        """Find the top-k most similar chunks to the query."""
        if self._vectors is None:
            return []

        query_vec = self._embedder.embed([query])[0]
        similarities = np.dot(self._vectors, query_vec) / (
            np.linalg.norm(self._vectors, axis=1) * np.linalg.norm(query_vec)
        )
        top_indices = np.argsort(similarities)[::-1][:top_k]

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
        user_id="phase1-tutorial",
        session_id="hello-world",
        input=query,
    )

    # 1. Retrieve (child span — automatically traced by @observe)
    results = vector_store.search(query, top_k=top_k)
    if not results:
        langfuse_context.update_current_observation(output="No results found")
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

    # Log the LLM generation as a LangFuse generation (model + tokens + cost)
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

    langfuse_context.update_current_observation(
        output={"answer": result.content[:200], "sources_count": len(results)},
        metadata={"provider": provider.provider_name, "model": result.model},
    )
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

> **What is `@observe`?** It's a LangFuse decorator that automatically creates a span when the function is called. When `rag_query()` runs, it creates a trace. When `rag_query` calls `vector_store.search()` (also decorated), that becomes a *child* span. You get the trace tree for free — no manual span arithmetic. The manual `get_langfuse().generation(...)` call logs the LLM call with its tokens/cost as a *generation* node (richer than a span). Both approaches are valid; you'll see both in LangFuse dashboards in production codebases.

> **Pitfall — `langfuse_context` only works inside an observed call.** If you call `langfuse_context.update_current_trace(...)` from a function that *isn't* decorated with `@observe`, you'll get an error or a no-op. The decorator establishes the trace context; everything called beneath it inherits it.

### 4.6 Create a run script

Create `scripts/hello_rag_traced.py`:

```python
"""Hello-world RAG with LangFuse tracing."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.rag.pipeline import Embedder, InMemoryVectorStore, rag_query

# Load document
doc_path = Path("data/sample_docs/appliance_manual_excerpt.txt")
text = doc_path.read_text(encoding="utf-8")

# Build vector store
print("Building vector store...")
embedder = Embedder()
store = InMemoryVectorStore(embedder)
store.add_document(text)
print(f"Vector store ready: {store.chunk_count} chunks\n")

# Ask questions
questions = [
    "What does error code E12 mean?",
    "How do I clean the drain filter?",
    "What should I do for an unbalanced load E27?",
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

Run it:

```bash
# Make sure LangFuse is running
docker compose up -d

uv run python scripts/hello_rag_traced.py
```

Now go to <http://localhost:3000>. You should see:

1. A project called "nexusdoc-dev"
2. Inside it, traces for each question
3. Each trace contains:
   - A `rag_query` span (the whole query)
   - A `vector_search` child span (the retrieval)
   - An `llm_generation` with token counts, model name, and provider

Click into a trace and walk the span tree: you can see the exact input, output, latency, and token cost of every step. **This is observability.** From now on, every component you build gets the same treatment — just slap `@observe` on it.

### Step 4 checkpoint

- [ ] `uv run python scripts/hello_rag_traced.py` runs without errors
- [ ] Answers are relevant to the questions (they cite the NexusDoc brief)
- [ ] Traces appear in LangFuse at <http://localhost:3000>
- [ ] Each trace shows: `rag_query` span → `vector_search` child span → `llm_generation` with tokens
- [ ] You can change `DEFAULT_PROVIDER` and re-run to see a different model answer (and the trace reflects the new provider)

---

## Phase 1 — Final Verification

### Sanity check script

Create `scripts/phase1_verify.py`:

```python
"""Phase 1 verification: test everything end-to-end."""
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
    print("NexusDoc Phase 1 — Verification")
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

    # 3. LLM call
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
    doc_path = Path("data/sample_docs/appliance_manual_excerpt.txt")
    store.add_document(doc_path.read_text(encoding="utf-8"))
    check(f"Document chunked: {store.chunk_count} chunks", store.chunk_count > 0)

    rag_result = rag_query("What does error code E12 mean?", store)
    check("RAG returns answer", len(rag_result["answer"]) > 10)
    check("RAG returns sources", len(rag_result["sources"]) > 0)
    check("RAG returns token usage", rag_result["usage"]["total_tokens"] > 0)

    # 5. LangFuse tracing
    trace_id = rag_result.get("trace_id")
    check(f"Trace created: {trace_id}", trace_id is not None)

    print("\n" + "=" * 60)
    print("✅ ALL CHECKS PASSED — Phase 1 complete!")
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
uv run python scripts/phase1_verify.py
```

### Final checklist

- [ ] `phase1_verify.py` passes all checks
- [ ] Traces visible in LangFuse with search spans and token counts
- [ ] Switching `DEFAULT_PROVIDER` in `.env` changes which model answers (and the trace reflects it)
- [ ] `ruff check .` passes
- [ ] `mypy app/` passes
- [ ] Groq and Ollama work when configured
- [ ] Git commit: Phase 1 foundation (registry, Langfuse, hello-world RAG on appliance excerpt)

---

## What You Actually Learned

This isn't just a checklist — these are the skills you now have, all directly relevant to target job roles:

| Skill | Where you used it | Why it matters for AI jobs |
| ------- | ------------------- | --------------------------- |
| **Provider abstraction** | `BaseProvider` → 3 implementations | Production AI systems switch providers based on cost/latency/availability. You built the pattern. |
| **Pydantic Settings** | `app/core/config.py` | Every AI codebase uses typed config. You know the standard approach. |
| **Docker Compose for AI infra** | LangFuse container | AI systems run databases, vector stores, and observability — all containerized. |
| **LLM observability** | `@observe` decorator, traces, spans, generations | LLMOps jobs list LangFuse/MLflow/W&B. You instrumented from day one. |
| **Embeddings & semantic search** | `InMemoryVectorStore` with cosine similarity | RAG is the #1 AI pattern in production. You built it from scratch. |
| **Prompt engineering** | System/user prompt construction in `rag_query` | Knowing how to structure prompts for retrieval + generation is table stakes. |
| **Free-tier-first design** | Groq + OpenRouter + Ollama | Real AI engineering means cost-conscious architecture. Your pipeline runs at $0. |

---

## What's Next (Phase 2 Preview)

In Phase 2 you'll ingest **real EN+JP appliance manuals** (see `DESIGN.md`):

- Curate 15–30 official manufacturer PDFs
- **PyMuPDF** parse → page metadata; flag empty OCR pages
- **pgvector on Supabase** with HNSW indexing

The model registry and Langfuse tracing from this phase carry forward. **Nothing here is thrown away** — only the domain and later-phase cuts in `DESIGN.md` changed.

---

## If You Get Stuck

1. **Groq API key not working?** Check <https://console.groq.com/keys> — free tier keys can be deactivated after inactivity. Generate a new one. It's instant and free.
2. **LangFuse won't start?** Run `docker compose logs langfuse` and check for port conflicts. If port 3000 is busy, change the port mapping in `docker-compose.yml` and update `LANGFUSE_HOST` in `.env`.
3. **Ollama model not found?** Run `ollama list` — if empty, `ollama pull llama3.2:3b`. The first pull is ~4.7 GB.
4. **Embedding model download fails?** `sentence-transformers` pulls from HuggingFace. If blocked (corporate VPN, region), set `HF_ENDPOINT=https://hf-mirror.com` in your `.env`.
5. **mypy errors from third-party stubs?** Run `mypy app/ --follow-imports=skip` if third-party stubs are missing. Common with newer packages — fixable in Phase 2 by adding `mypy` stubs or per-package overrides.
6. **`langfuse_context` errors?** It only works inside a function decorated with `@observe`. Make sure every manual `langfuse_context.*` call happens beneath an `@observe`-decorated function in the call stack.
7. **Cosine similarity returns `NaN`?** Check that `_vectors` isn't `None` and that no chunk is empty (zero-vector → divide-by-zero). Add a guard in `add_document` to skip empty chunks.

---

*Phase 1 complete. You just built the foundation of a production AI system — and the three concepts that were new to you (provider abstraction, RAG, observability) are now in your toolkit. The next 11 phases build on this.*
