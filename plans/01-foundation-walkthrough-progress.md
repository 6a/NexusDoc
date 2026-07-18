# Phase 1 — Progress Tracker

> Updated as steps are completed. Check this file before resuming a session.
>
> **2026-07-12:** `DESIGN.md` rewritten (Japan FDE, appliance manuals, Hetzner, Ollama-on-5080).
> Walkthrough Step 4.1 Langfuse YAML is replaced by **official compose** instructions.
> Sample doc path is now `data/sample_docs/appliance_manual_excerpt.txt`.

**Started:** 2026-07-11
**Last session:** 2026-07-18 (Step 3 complete — ready for commit or Step 4)
**Last commit:** `37665a8` — Implements config, providers base class, and groq provider

---

## Step 1 — Project Scaffold (~30 min)

| # | Task | Status | Notes |
| --- | ------ | -------- | ------- |
| 1.1 | `uv init --app .` | ✅ Done | Created `main.py`, `pyproject.toml` skeleton |
| 1.2 | `pyproject.toml` (full) | ✅ Done | Walked through all 6 sections line-by-line |
| 1.2.1 | `.python-version` | ✅ Done | Pinned to `3.13` (best mix of speed + wheel support) |
| 1.3 | `uv venv` + deps | ✅ Done | Python 3.13.6, all deps installed |
| 1.4a | `.env.example` | ✅ Done | Standard names (`GROQ_API_KEY`, etc.) |
| 1.4b | `.env` | ✅ Done | Project-local only (`DEFAULT_PROVIDER`, `OLLAMA_HOST`, `LOG_LEVEL`); API keys in **OS env** |
| 1.5 | `.pre-commit-config.yaml` | ✅ Done | Created, `pre-commit install` ran |
| 1.6 | Directory structure | ✅ Done | `app/core/providers/`, `tests/`, `scripts/`, `data/sample_docs/` |
| — | `ruff check .` | ✅ Passes | |
| — | `mypy app/` | ✅ Passes | |
| — | `pyright .` | ✅ Passes | Via `cmd /c pyright .` (shazam hook fixed) |
| — | Committed | ✅ Done | `d5770fa` — 20 files, all hooks green |

**Step 1 complete.**

---

## Step 2 — Model Registry (~75 min)

| # | Task | Status | Notes |
| --- | ------ | -------- | ------- |
| 2.1 | Concept explained | ✅ Done | Strategy pattern, provider abstraction; `@dataclass`, `ABC`, decorators |
| 2.2 | Design reviewed | ✅ Done | Groq + Ollama first; OpenRouter deferred; OS env for API keys OK |
| 2.3 | `app/core/config.py` | ✅ Done | Pydantic Settings + `Field(repr=False)` on secrets/hosts; `uv sync --extra dev` for mypy |
| 2.4 | `app/core/providers/base.py` | ✅ Done | `Role = Literal[...]`, `ChatMessage`, `CompletionResult`, `BaseProvider`; `dict[str, int]` for usage |
| 2.5 | `app/core/providers/groq_provider.py` | ✅ Done | mypy passes; manual smoke test (`pong`) OK |
| — | `app/core/providers/messages.py` | ✅ Done | Shared `to_chat_message_params()`; vendor-neutral `ChatMessageParam` |
| 2.6 | `app/core/model_registry.py` | ✅ Done | Lazy singleton; `match` on `ProviderName`; Ollama/OpenRouter commented |
| 2.7 | Tests | ✅ Done | Contract/shape asserts; `ProviderName`/`Role` enums; indirect fixture; unknown/empty cases |

**Step 2 complete.**

### Session notes (2026-07-12)

- Groq SDK `usage` is `Optional` — assign `usage = response.usage` for mypy narrowing.
- Cast `to_chat_message_params()` → `list[ChatCompletionMessageParam]` at provider boundary.
- PowerShell `python -c`: use double-outer / single-inner quotes; prefer `scripts/*.py` for multi-line.
- Provider smoke tests: worth adding in 2.7; skip in CI without key; model regressions → Phase 5 evals.

### Session notes (2026-07-18)

- Added `ProviderName` (`definitions.py`) and `Role` (`StrEnum` in `base.py`); Settings types `default_provider` as `ProviderName`.
- Tests: assert contract not `pong`; parametrize via indirect `set_default_provider` fixture.
- `list_models`: shape only (list of non-empty str) — no specific model IDs; catalog churn ≠ adapter failure.
- Handoff absorbed; deleted `plans/01-foundation-HANDOFF.md`.

---

## Step 3 — Ollama (+ optional OpenRouter) (~20 min)

| # | Task | Status | Notes |
| --- | ------ | -------- | ------- |
| 3.1 | `ollama_provider.py` | ✅ Done | `DEFAULT_MODEL`, `num_predict`, `is_available()`; SDK `model` not `name` |
| 3.2 | `openrouter_provider.py` | ⬜ Deferred | Only after POC + optional $10 credits |
| 3.3 | Update registry | ✅ Done | `ProviderName.OLLAMA` wired; retry/fallback deferred |
| 3.4 | Test Groq + Ollama | ✅ Done | Shared `_PROVIDER_PARAMS`; 6 passed |

**Step 3 complete** (OpenRouter + retry/fallback still deferred).

---

## Step 4 — Langfuse + RAG (~75–90 min)

| # | Task | Status | Notes |
| --- | ------ | -------- | ------- |
| 4.1 | Official Langfuse compose | ⬜ Not started | **Not** the old single-container YAML |
| 4.2 | Langfuse API keys | ⬜ Not started | |
| 4.3 | Smoke test | ⬜ Not started | |
| 4.4 | Sample appliance excerpt | ⬜ Not started | `appliance_manual_excerpt.txt` (+ JP stub) |
| 4.5 | RAG pipeline | ⬜ Not started | |
| 4.6 | Run script | ⬜ Not started | E12 / drain filter questions |
| — | Verification | ⬜ Not started | |

---

## Pending Actions for Next Session

1. Commit Step 2 + 3 work when ready (registry, Ollama, tests, enums)
2. **Step 4** — Langfuse **official** compose (not obsolete single-service YAML)
3. Optional later: Groq→Ollama retry/fallback; OpenRouter after POC
4. Re-read `DESIGN.md` cut list before adding features
