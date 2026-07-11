# Phase 1 — Progress Tracker

> Updated as steps are completed. Check this file before resuming a session.

**Started:** 2026-07-11
**Last session:** 2026-07-11
**Last commit:** `d5770fa` — "Sets up basic project layout and development environment"

---

## Step 1 — Project Scaffold (~30 min)

| # | Task | Status | Notes |
| --- | ------ | -------- | ------- |
| 1.1 | `uv init --app .` | ✅ Done | Created `main.py`, `pyproject.toml` skeleton |
| 1.2 | `pyproject.toml` (full) | ✅ Done | Walked through all 6 sections line-by-line |
| 1.2.1 | `.python-version` | ✅ Done | Pinned to `3.13` (best mix of speed + wheel support) |
| 1.3 | `uv venv` + deps | ✅ Done | Python 3.13.6, all deps installed |
| 1.4a | `.env.example` | ✅ Done | Created, committed |
| 1.4b | `.env` | ✅ Done | Groq API key filled in during session |
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
| 2.1 | Concept explained | ✅ Done | Strategy pattern, provider abstraction |
| 2.2 | Design reviewed | ⬜ Not started | |
| 2.3 | `app/core/config.py` | ⬜ Not started | |
| 2.4 | `app/core/providers/base.py` | ⬜ Not started | |
| 2.5 | `app/core/providers/groq_provider.py` | ⬜ Not started | |
| 2.6 | `app/core/model_registry.py` | ⬜ Not started | |
| 2.7 | Tests | ⬜ Not started | |

---

## Step 3 — OpenRouter + Ollama (~20 min)

| # | Task | Status | Notes |
| --- | ------ | -------- | ------- |
| 3.1 | `openrouter_provider.py` | ⬜ Not started | |
| 3.2 | `ollama_provider.py` | ⬜ Not started | |
| 3.3 | Update registry | ⬜ Not started | |
| 3.4 | Test all three | ⬜ Not started | |

---

## Step 4 — LangFuse + RAG (~75 min)

| # | Task | Status | Notes |
| --- | ------ | -------- | ------- |
| 4.1 | Docker Compose | ⬜ Not started | |
| 4.2 | LangFuse API keys | ⬜ Not started | |
| 4.3 | Smoke test | ⬜ Not started | |
| 4.4 | Sample document | ⬜ Not started | |
| 4.5 | RAG pipeline | ⬜ Not started | |
| 4.6 | Run script | ⬜ Not started | |
| — | Verification | ⬜ Not started | |

---

## Pending Actions for Next Session

1. Fill in `GROQ_API_KEY` in `.env`
2. (Optional) Pull Ollama model: `ollama pull llama3.2:3b`
3. Start Step 2.3 — write `app/core/config.py`
