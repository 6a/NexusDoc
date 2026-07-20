# Phase 1 — Progress Tracker

> Updated as steps are completed. Check this file before resuming a session.
>
> **2026-07-12:** `DESIGN.md` rewritten (Japan FDE, appliance manuals, Hetzner, Ollama-on-5080).
> Walkthrough Step 4.1 Langfuse YAML is replaced by **official compose** instructions.
> Sample doc path is now `data/sample_docs/appliance_manual_excerpt.txt`.

**Started:** 2026-07-11
**Last session:** 2026-07-20 (Phase 1 Final Verification script green)
**Last commit:** (pending) Phase 1 e2e verify + script utils
**Handoff:** absorbed and deleted

---

## Step 1 — Project Scaffold (~30 min)

| # | Task | Status | Notes |
| --- | ------ | -------- | ------- |
| 1.1 | `uv init --app .` | ✅ Done | Created `main.py`, `pyproject.toml` skeleton |
| 1.2 | `pyproject.toml` (full) | ✅ Done | Walked through all 6 sections line-by-line |
| 1.2.1 | `.python-version` | ✅ Done | Pinned to `3.13` (best mix of speed + wheel support) |
| 1.3 | `uv venv` + deps | ✅ Done | Python 3.13.6, all deps installed |
| 1.4a | `.env.example` | ✅ Done | Updated 2026-07-18 for Langfuse compose + HF_TOKEN |
| 1.4b | `.env` | ✅ Done | Langfuse compose secrets + SDK keys + HF_TOKEN; Groq often OS env |
| 1.5 | `.pre-commit-config.yaml` | ✅ Done | Created, `pre-commit install` ran |
| 1.6 | Directory structure | ✅ Done | `app/core/providers/`, `app/rag/`, `tests/`, `scripts/`, `data/sample_docs/` |
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
| 2.3 | `app/core/config.py` | ✅ Done | Pydantic Settings + `Field(repr=False)` on secrets/hosts; `load_dotenv()` at top |
| 2.4 | `app/core/providers/base.py` | ✅ Done | `Role` StrEnum, `ChatMessage`, `CompletionResult`, `BaseProvider` |
| 2.5 | `app/core/providers/groq_provider.py` | ✅ Done | usage keys: `prompt_tokens` / `completion_tokens` / `total_tokens` |
| — | `app/core/providers/messages.py` | ✅ Done | Shared `to_chat_message_params()` |
| 2.6 | `app/core/model_registry.py` | ✅ Done | Lazy singleton; `match` on `ProviderName` |
| 2.7 | Tests | ✅ Done | Contract/shape asserts; 6 passed (Groq + Ollama) |

**Step 2 complete.**

### Session notes (2026-07-12)

- Groq SDK `usage` is `Optional` — assign `usage = response.usage` for mypy narrowing.
- Cast `to_chat_message_params()` → `list[ChatCompletionMessageParam]` at provider boundary.
- PowerShell `python -c`: use double-outer / single-inner quotes; prefer `scripts/*.py` for multi-line.

### Session notes (2026-07-18)

- Added `ProviderName` (`definitions.py`) and `Role` (`StrEnum` in `base.py`).
- Tests: contract not `pong`; `list_models` shape only.
- Step 3 completed; Step 4 Langfuse + RAG completed same day (evening).

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
| 4.1 | Official Langfuse compose | ✅ Done | Official multi-service compose; UI :3000; headless NexusDoc |
| 4.2 | Langfuse API keys | ✅ Done | `LANGFUSE_SECRET_KEY` / `PUBLIC_KEY` / `BASE_URL` or `HOST` |
| 4.3 | Smoke test | ✅ Done | `scripts/test_langfuse.py`; SDK v4 APIs |
| 4.4 | Sample appliance excerpt | ✅ Done | EN + JP in `data/sample_docs/` |
| 4.5 | RAG pipeline | ✅ Done | `app/rag/pipeline.py` — chunk → embed → cosine search → traced generate |
| 4.6 | Run script | ✅ Done | `scripts/test_rag.py` (E12 / drain / E27); traces in Langfuse UI |
| 4.7 | Phase 1 verify script | ✅ Done | `scripts/verify_e2e_phase1.py` + `scripts/utils.py`; SDK v4 / dataclass-aware |

**Step 4 complete.** Phase 1 e2e verify script passes (Groq). Optional checklist: Ollama switch, ruff/mypy, commit.

---

## Pending Actions for Next Session

1. Optional: confirm Langfuse UI + Ollama provider switch; `ruff check .` / `mypy app/`.
2. Mark Phase 1 complete; start Phase 2 per `DESIGN.md`.
3. Deferred: OpenRouter; Groq→Ollama retry/fallback; Varlock; Graph RAG (after Phase 3 only).
4. Re-read `DESIGN.md` cut list before adding features.

### Session notes (2026-07-18 evening) — carry forward

- **Langfuse compose:** official only; `DATABASE_URL` no literal `<>`; S3 secrets == `MINIO_ROOT_PASSWORD`.
- **langfuse 4.x:** `observe` / `propagate_attributes` from `langfuse`; `start_as_current_observation(as_type="generation")`; I/O on root span via `update_current_span` — not deprecated `set_current_trace_io`.
- **Client init:** eager `get_langfuse()` at end of `pipeline.py` so `@observe` hits keyed singleton (Settings ≠ `os.environ` alone).
- **`load_dotenv()`** in `app/core/config.py` before `Settings()` — publishes `.env` to process for HF Hub / libs that read env.
- **Editable install:** hatchling + `packages = ["app"]` in `pyproject.toml`.
- **Usage keys:** provider dict uses `prompt_tokens` / `completion_tokens`; Langfuse `usage_details` uses `input_tokens` / `output_tokens`.
- **Torch:** CPU-only (`+cpu`); GPU embed deferred. HF: optional `HF_TOKEN` (Read).
- **Varlock / Graph RAG:** deferred (see DESIGN).
- **Do not invent** alternate Langfuse compose or leave `...` stubs for user to copy.
