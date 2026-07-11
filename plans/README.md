# NexusDoc — Plan Index

> **Source:** `DESIGN.md` — 12-week part-time roadmap (~12–15 hrs/week)
> **Role:** AI deployment engineer / AI solutions architect portfolio project
> **Last updated:** 2026-07-07

---

## Status Dashboard

| Week | Topic | Walkthrough | Status |
| ------ | ------- | ------------- | -------- |
| 1 | Foundation — registry, LangFuse, hello-world RAG | [week-1-foundation-walkthrough.md](week-1-foundation-walkthrough.md) | ✅ Walkthrough written |
| 2 | Ingestion — SEC EDGAR, PyMuPDF, pgvector | `week-2-ingestion-walkthrough.md` | ⬜ Not started |
| 3 | Retrieval — bge-m3 + hybrid search + reranker | `week-3-retrieval-walkthrough.md` | ⬜ Not started |
| 4 | Document understanding — Qwen3-VL | `week-4-vlm-walkthrough.md` | ⬜ Not started |
| 5 | Multi-agent — LangGraph supervisor + agents | `week-5-agents-walkthrough.md` | ⬜ Not started |
| 6 | Eval harness — RAGAS + LLM-as-judge + CI gate | `week-6-eval-walkthrough.md` | ⬜ Not started |
| 7 | Model serving — vLLM spike + quantization benchmark | `week-7-serving-walkthrough.md` | ⬜ Not started |
| 8 | Guardrails + observability polish | `week-8-guardrails-walkthrough.md` | ⬜ Not started |
| 9 | Streamlit UI — chat, citations, report viewer | `week-9-ui-walkthrough.md` | ⬜ Not started |
| 10 | Docker Compose + CI/CD + deploy | `week-10-deploy-walkthrough.md` | ⬜ Not started |
| 11 | Eval hardening + ADRs | `week-11-eval-hardening-walkthrough.md` | ⬜ Not started |
| 12 | Demo video + portfolio writeup | `week-12-portfolio-walkthrough.md` | ⬜ Not started |

## Quick Reference

### Architecture (from DESIGN.md)

```
User → Streamlit UI → FastAPI → Model Registry → Groq/OpenRouter/Ollama/vLLM
                                  ↓
                            LangGraph Agents
                            ├─ Retriever/QA
                            └─ Summarizer/Risk
                                  ↓
                            pgvector (Supabase)
                            bge-m3 embeddings
                            bge-reranker-v2-m3
                                  ↓
                            Guardrails AI → LangFuse tracing
```

### Key Decisions (ADRs to write by Week 11)

| ADR | Topic | Week |
| ----- | ------- | ------ |
| ADR-001 | Provider-agnostic model registry | 1 (draft), 11 (final) |
| ADR-002 | vLLM serving + AWQ quantization | 7 (draft), 11 (final) |
| ADR-003 | Hybrid retrieval + cross-encoder reranking | 3 (draft), 11 (final) |
| ADR-004 | RAGAS + CI eval gate | 6 (draft), 11 (final) |

### Prerequisites Tracker

| Service | Account Created? | Key in .env? |
| --------- | ----------------- | -------------- |
| Groq | ⬜ | ⬜ |
| OpenRouter | ⬜ | ⬜ |
| Supabase | ⬜ | ⬜ |
| LangFuse (self-hosted) | N/A (local Docker) | ⬜ |

### Tools Installed?

| Tool | Installed? |
| ------ | ----------- |
| uv | ⬜ |
| Docker Desktop | ⬜ |
| Ollama | ⬜ |
| VS Code | ⬜ |

---

## Walkthrough Format (template for Weeks 2-12)

Each walkthrough follows the same structure:

1. **Overview** — what you'll build this week and why it matters
2. **Concepts** — AI-specific knowledge needed (explained from scratch)
3. **Prerequisites** — accounts, tools, prior weeks completed
4. **Step-by-step** — 5-6 sessions, ~1 hour each, copy-pasteable code
5. **Verification** — `weekN_verify.py` script that proves everything works
6. **What's next** — preview of next week
