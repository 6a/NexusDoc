# NexusDoc — Multi-Agent Document Intelligence Platform

**A production-style AI system that ingests complex financial/regulatory documents, runs a multi-agent LangGraph pipeline over them (VLM document understanding → hybrid retrieval + reranking → risk classification → multi-level summarization → structured report), with a real LLM-as-judge eval harness, guardrails, self-hosted observability, and self-served model inference via vLLM.**

> **Goal of this project (meta):** A portfolio piece to transition the author from game-systems / tool programming into an **AI deployment engineer / AI solutions architect** role within ~3 months, built part-time (~12–15 hrs/week) alongside a full-time job. Scope is deliberately bounded: one focused, *finished* system beats two half-built ones.

---

## 🧭 What It Does

NexusDoc turns dense, multi-format business documents into structured intelligence.

**Input:** SEC 10-K/10-Q filings (PDF, via EDGAR), contracts, research papers.

**Output:**
- Structured JSON report (extracted financials, risk tags, key dates, source citations)
- Multi-level summary (paragraph → bullets → one-liner)
- Interactive chat UI with cited, streamed answers over the document

**Problem:** Analysts and compliance teams spend significant time manually extracting data from documents that mix prose, tables, and figures. NexusDoc fuses **document understanding + hybrid retrieval + multi-agent reasoning + evaluation + self-hosted serving** into one observable pipeline.

---

## 🧠 Core Capabilities (what the system actually does)

The earlier version of this doc framed the project around "9 HuggingFace task categories." That framing has been removed — it read like a checklist optimized for a model zoo rather than for solving the problem well. In 2026 the right tool for document QA, table extraction, classification, and summarization is a **strong general LLM + VLM with structured output**, not a chain of specialized HF models. Task coverage is a *consequence* of good design, not a goal.

| Capability | Implementation (2026-appropriate) |
|---|---|
| Document & table understanding | Single **VLM pass** (Qwen3-VL / Qwen2.5-VL) for layout, table extraction, and figure reasoning — replaces LayoutLMv3 + TAPAS + Table Transformer |
| Hybrid retrieval | pgvector dense (bge-m3 / nomic-embed-text-v2) + sparse, with a **cross-encoder reranker** (bge-reranker-v2-m3) |
| Multi-agent orchestration | **LangGraph** StateGraph: supervisor routes to a retriever/QA agent and a summarizer/risk agent |
| Risk classification | LLM structured output + zero-shot fallback |
| Summarization | LLM with controlled prompts (paragraph → bullet → one-liner) |
| Evaluation | **RAGAS** (faithfulness, context recall, answer relevancy) + LLM-as-judge, 40–50 curated cases |
| Guardrails | **Guardrails AI** (PII, topic, toxicity validators) — lighter than NeMo, fits portfolio scope |
| Observability | **LangFuse** self-hosted (tracing, token/cost attribution, eval dashboards) |
| Model serving | **vLLM** serving a quantized 7–8B model behind an OpenAI-compatible endpoint — the real "deployment" story |

---

## 🏗️ Architecture

### High-Level System Flow

```
┌───────────────────────────────────────────────────────────────┐
│                       User Input Layer                        │
│  ┌─────────────────┐ ┌─────────────────┐                      │
│  │   Upload PDF    │ │   SEC Ticker    │                       │
│  └────────┬────────┘ └────────┬────────┘                      │
│           ▼                   ▼                               │
│                 Ingestion (simple script/cron)                │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐  │
│  │ SEC EDGAR fetch │ │ PyMuPDF parse   │ │  Text Chunking  │  │
│  └────────┬────────┘ └────────┬────────┘ └────────┬────────┘  │
│           ▼                   ▼                   ▼           │
│  ┌─────────────────────────────────────────────────────────┐  │
│        VLM Document Pass (Qwen3-VL) — tables + layout      │  │
│  └────────┬───────────────────────────────────────────────┘  │
│           ▼                                                 │
│  ┌─────────────────────────────────────────────────────────┐  │
│            Vector Store (pgvector on Supabase)              │  │
│    ┌───────────────┐  ┌───────────────┐                     │  │
│    │  Text Chunks  │  │  Table Cells  │                     │  │
│    └───────┬───────┘  └───────┬───────┘                     │  │
│  └────────┬───────────────────────────────────────────────┘  │
│           ▼                                                 │
│   Hybrid Retrieve (dense+sparse) → Rerank (bge-reranker)     │
│           ▼                                                 │
│  ┌─────────────────────────────────────────────────────────┐  │
│              LangGraph Multi-Agent Orchestrator             │  │
│  │  Supervisor (classify doc type + query intent)          │  │
│  │     ├─ Retriever/QA Agent   (cited answers)             │  │
│  │     └─ Summarizer/Risk Agent (summary + risk tags)      │  │
│  │  collect → validate (faithfulness) → format             │  │
│  └────────┬───────────────────────────────────────────────┘  │
│           ▼                                                 │
│  ┌─────────────────┐ ┌─────────────────┐                     │
│  │ Structured JSON │ │   Chat UI (str) │                     │
│  └─────────────────┘ └─────────────────┘                     │
│                                                             │
│  Observability: LangFuse (self-hosted) — every span traced   │
│  Guardrails:   Guardrails AI — PII/topic on input & output   │
└───────────────────────────────────────────────────────────────┘
```

### Model Serving Layer (the "deployment engineer" story)

Every model call goes through a **provider-agnostic registry**. Crucially, one of those providers is a **self-hosted vLLM endpoint** — not just third-party APIs. This is the differentiator between "app that calls APIs" and "engineer who can deploy models."

```
┌───────────────────────────────────────────────────────────────┐
│                 Model Registry (provider-agnostic)            │
│                                                               │
│  DEFAULT_PROVIDER   = groq          # free-tier primary       │
│  FALLBACK_PROVIDER  = openrouter    # rate-limit overflow     │
│  SELF_HOST_PROVIDER = vllm          # ← the deployment story  │
│  OFFLINE_PROVIDER   = ollama        # local dev, no internet  │
│  EVAL_PROVIDER      = openrouter    # separate model for judge│
│                                                               │
│  Embeddings: bge-m3 / nomic-embed-text-v2 (local, always free)│
│  Reranker:   bge-reranker-v2-m3    (local, always free)       │
│  VLM:        Qwen3-VL via Groq or self-hosted vLLM            │
└───────────────────────────────────────────────────────────────┘
```

**vLLM serving spike (Week 7):** deploy a quantized (AWQ) 7–8B instruct model (e.g. Qwen2.5-7B-Instruct-AWQ or Llama-3.1-8B-Instruct-AWQ) on a RunPod RTX 4090 (~$0.34/hr) or HuggingFace Inference Endpoint (NVIDIA L4, ~$0.80/hr, scale-to-zero). Benchmark **TTFT, throughput (tok/s), concurrent requests, and quantization quality-loss** vs. the full-precision baseline. Wire it into the registry as a first-class OpenAI-compatible provider. Document the latency/throughput/cost tradeoffs in an ADR (see Decisions section).

### State Management (LangGraph)

```python
class DocumentState(TypedDict):
    doc_id: str
    file_path: str
    chunks: list[DocumentChunk]
    tables: list[ExtractedTable]

class AgentState(TypedDict):
    doc: DocumentState
    query: str
    retrieval_result: dict | None
    qa_result: dict | None        # {answer, citations, confidence}
    summary_result: dict | None   # {short, medium, long}
    risk_result: dict | None      # {risks: [{category, severity, text}]}
    errors: list[str]
    validation: ValidationReport | None
```

---

## 💸 Cost Strategy (verified 2026 limits)

Designed to run on free tiers for development and demo. **Paid spend is intentionally tiny and reserved for the serving spike + eval runs.**

### Free tier (development & demo)

| Component | Solution | Real 2026 limits |
|---|---|---|
| **LLM inference (primary)** | Groq free tier | **30 RPM, ~1,000 RPD** per model — *requests* are the binding constraint, not tokens |
| **LLM fallback** | OpenRouter free router (`openrouter/free`) | 20 RPM, 1,000 RPD; model set shifts over time |
| **LLM local** | Ollama (Llama 3.1 8B, Qwen2.5 7B, Gemma 3) | Free; needs 8GB+ VRAM for 7B quantized |
| **VLM (doc/table)** | Qwen3-VL via Groq free tier | Same Groq limits; falls back to self-hosted vLLM |
| **Embeddings** | bge-m3 / nomic-embed-text-v2 (local) | Free, local, no API calls |
| **Reranker** | bge-reranker-v2-m3 (local) | Free, local |
| **Vector store** | pgvector on Supabase free | 500 MB Postgres + pgvector + auth |
| **Observability** | LangFuse self-hosted (Docker) | MIT-licensed, ClickHouse-backed since Jan 2026 |
| **Doc parsing** | PyMuPDF + Unstructured.io (local) | Free, local |

### Intentional paid spend (< ~$10/mo, only when needed)

| Component | When | Approx cost |
|---|---|---|
| **vLLM serving spike** | Week 7 benchmarking (a few hours) | RunPod 4090 $0.34/hr → ~$2–5 total |
| Eval runs (when free RPD is too low) | 40–50 cases × multi-step pipeline | $2–5/mo on a paid Groq tier or OpenRouter paid models |
| HF Inference Endpoint (optional alt) | If not using RunPod | L4 $0.80/hr, scale-to-zero |

> ⚠️ **GitHub Models free tier is intentionally *not* used as a production provider** — its terms restrict use to prototyping/experimentation only. Fine for ad-hoc testing, not for the served registry.

### Why this strategy works (and where the earlier doc was wrong)

- The earlier plan claimed "Groq = 500K tokens/day → 50 documents/day." That's **misleading**: a multi-agent run is 8–15 LLM calls per document, so the **~1,000 RPD** ceiling (not tokens) is what bites — realistically **~60–120 documents/day**, and the 30 RPM cap adds wall-clock time. Planning around requests, not tokens, is what makes the eval week actually finishable.
- Embeddings + reranker stay local and free — no per-vector API costs that silently grow.
- Self-hosted LangFuse gives production-grade observability without a per-seat subscription.
- The vLLM spike is the only "real spend" and it's a few hours of GPU time — cheap, and it's the single most marketable artifact in the project.

---

## 🛠️ Tech Stack

| Category | Choice | Why (2026-grounded) |
|---|---|---|
| **Agent orchestration** | **LangGraph** | Dominant for graph-shaped, stateful, branching agent workflows with human-in-the-loop |
| **Framework glue** | LangChain | Tool binding, loaders, retrievers, LCEL |
| **Vector store** | pgvector on Supabase | Hybrid search + transactional queries; generous free tier |
| **Embeddings** | **bge-m3** or **nomic-embed-text-v2** (local) | Modern open-weight leaders; `all-MiniLM-L6-v2` is dated and dropped |
| **Reranker** | **bge-reranker-v2-m3** (local) | Lightweight open-weight cross-encoder; cheap RAG quality win |
| **Doc / table understanding** | **Qwen3-VL** (or Qwen2.5-VL) | One VLM pass replaces LayoutLMv3 + TAPAS + Table Transformer — better results, far less glue code |
| **LLM inference** | Groq / OpenRouter / **vLLM (self-hosted)** / Ollama | Configurable; the vLLM provider is the deployment story |
| **Model serving** | **vLLM** (AWQ quantized) | Production standard; OpenAI-compatible server; quantization (AWQ/GPTQ/FP8) supported |
| **Summarization / risk** | Groq/OpenRouter LLMs w/ structured output | Pydantic-validated outputs |
| **Eval** | **RAGAS** + LLM-as-judge | RAG-specific metrics (faithfulness, context recall, answer relevancy) |
| **Guardrails** | **Guardrails AI** | Lighter than NeMo; community validators for PII/topic/toxicity. NeMo optional (complementary) |
| **Observability** | LangFuse self-hosted | Open-source tracing + cost attribution; framework-agnostic via OpenTelemetry |
| **Backend** | FastAPI (thin) | Async, type-safe, auto-docs for the app's REST surface |
| **Frontend** | **Streamlit** (only) | Rapid chat UI + report viewer; no dual-frontend scope |
| **CI/CD** | GitHub Actions + pytest | Eval-gated merges |
| **Containers** | Docker + docker-compose | Reproducible: app + LangFuse + DB in one stack |
| **Testing** | pytest + VCR.py (cassettes) | Deterministic unit tests without network |

### Deliberately cut from the earlier plan (and why)

| Cut | Reason |
|---|---|
| **TTS / audio briefings (Coqui)** | Coqui shut down Jan 2024; only an unmaintained `idiap` fork remains. TTS is off-goal for an AI *deployment* role — nobody hires you for narration. |
| **Prefect** | Overkill for a demo ingestion pipeline; a script + cron is enough. Another system to learn/run. |
| **TAPAS, LayoutLMv3, Table Transformer** | Dated/specialized; a single VLM pass is better and faster to build. |
| **NeMo Guardrails (primary)** | Heavyweight; Guardrails AI covers PII/topic/toxicity with less setup. NeMo kept as optional only. |
| **FastAPI + Streamlit both as first-class** | Picked Streamlit for UI; FastAPI kept thin for the REST/serving surface only. |
| **200 eval cases → 40–50** | 200 padded cases are worse than 40 curated ones. Part-time reality. |
| **"9 HuggingFace tasks" framing** | Reads as a model-zoo checklist, not engineering. Removed. |

---

## 📋 Resume-Ready Impact (honest language)

### Measured targets (stated as targets until reproduced)

| Metric | Target | How measured |
|---|---|---|
| Document types handled | 3 (SEC filings, contracts, research papers) | Integration tests |
| RAG faithfulness / context recall | >90% recall, low hallucination | RAGAS on 40–50 curated cases |
| End-to-end latency | <30s for a 50-page doc | LangFuse traces |
| Eval cases | 40–50 curated Q/A pairs | Dedicated eval set |
| Guardrail recall | High PII detection, zero toxic output | Directed test suite |
| vLLM serving | Quantized 7–8B at target TTFT + throughput | Benchmark script |

> **Honesty rule:** no metric goes on the resume until a clean, reproducible run produces it. Targets below are written as *"targeted and measured via…"*, not as achieved facts.

### Portfolio statement (resume-ready, defensible)

> *"Built NexusDoc — a multi-agent document-intelligence platform: hybrid RAG (pgvector + bge-m3 + cross-encoder reranking), a LangGraph supervisor/worker graph, RAGAS-evaluated pipelines (40+ curated cases with a CI eval gate), Guardrails-AI input/output safety, and self-hosted LangFuse tracing. Processes real SEC EDGAR filings end-to-end with citations and structured risk/summary output."*

> *"Designed the LLMOps stack: provider-agnostic model registry (Groq / OpenRouter / Ollama / self-hosted vLLM), RAGAS eval harness wired into GitHub Actions to block merges on regression, and LangFuse cost/latency attribution per agent step."*

> *"Self-served a quantized 7–8B model via vLLM behind an OpenAI-compatible endpoint (AWQ on RunPod RTX 4090 / HF Inference Endpoint), benchmarked TTFT, throughput, and quantization quality-loss vs. full-precision, and documented latency/throughput/cost tradeoffs in architecture decision records."*

### How it maps to real AI engineering jobs (2026)

| JD requirement | NexusDoc evidence |
|---|---|
| **Production RAG with hybrid search + reranking** | pgvector + bge-m3 + bge-reranker-v2-m3 (dense+sparse → cross-encoder rerank) |
| **Multi-agent orchestration** | LangGraph supervisor/worker StateGraph with typed state |
| **Model serving / deployment** ⬅ key gap-filler | vLLM serving quantized model, OpenAI-compatible, benchmarked |
| **Quantization & inference tradeoffs** ⬅ key gap-filler | AWQ vs full-precision benchmark + ADR |
| **LLMOps & evaluation** | RAGAS + LangFuse + CI eval gate |
| **Guardrails & safety** | Guardrails AI for PII/topic/toxicity |
| **Document understanding (multi-modal)** | Qwen3-VL single-pass doc/table/layout |
| **Vector databases & indexing** | pgvector + HNSW indexing |
| **Structured output** | Pydantic → JSON reports |
| **Observability** | LangFuse self-hosted (spans, token tracking, cost) |
| **Cost-optimized inference** | Provider registry, free-tier-first, measured spend |
| **Containerization & deployment** | Docker / docker-compose → deploy + CI/CD |

> 67% of 2026 AI engineering postings mention deployment. The vLLM spike + quantization ADR exist specifically to answer that requirement — without them the project is "app engineering," not "deployment engineering."

---

## 🗺️ 12-Week Part-Time Roadmap (~12–15 hrs/week)

```
Week 1 : Foundation — repo, config, model registry (Groq+OpenRouter+Ollama), LangFuse up, hello-world RAG
Week 2 : Ingestion — SEC EDGAR fetch, PyMuPDF parse, chunking, pgvector schema
Week 3 : Retrieval — bge-m3 embeddings + hybrid search + bge-reranker-v2-m3
Week 4 : Document understanding — Qwen3-VL pass for tables/layout (replaces 3 specialized models)
Week 5 : LangGraph multi-agent — supervisor + Retriever/QA + Summarizer/Risk agents
Week 6 : Eval harness — RAGAS + 40–50 curated cases + LLM-as-judge + CI gate
Week 7 : Model serving spike — vLLM (AWQ) on RunPod/HF, benchmark, wire into registry
Week 8 : Guardrails (Guardrails AI) + observability polish + cost dashboard
Week 9 : Streamlit UI — streaming chat, citations, report viewer
Week 10: Docker compose + CI/CD + deploy
Week 11: Eval hardening — reproduce all metrics, write ADRs, honest numbers
Week 12: Demo video + portfolio writeup + resume bullets
```

**Outside this build (reserve ~2 weeks):** resume finalization, a 3-min demo video, and interview prep / applications. Do **not** spend all 12 weeks coding — the wrap-up is what makes you marketable.

### Week 1 — Foundation
- Repo scaffold, `pyproject.toml`, pre-commit, `.env.example`
- Model registry: Groq + OpenRouter + Ollama providers, env-switchable
- LangFuse self-hosted via docker-compose (single container)
- End-to-end "hello world": embed one doc, answer one RAG query, see it traced in LangFuse
- **Deliverable:** a traced RAG query works against a single doc.

### Week 2 — Ingestion
- SEC EDGAR API (CIK lookup, 10-K/10-Q retrieval)
- PyMuPDF → text chunks + page metadata
- pgvector schema (HNSW index) + upsert pipeline
- **Deliverable:** CLI ingests an SEC filing into pgvector.

### Week 3 — Hybrid Retrieval + Reranking
- bge-m3 (or nomic-embed-text-v2) local embeddings
- Dense + sparse hybrid retrieval
- bge-reranker-v2-m3 cross-encoder rerank (top-K)
- Citation plumbing (chunk → page)
- **Deliverable:** cited hybrid-RAG answers with reranking.

### Week 4 — Document Understanding (VLM)
- Qwen3-VL (via Groq or self-hosted vLLM) for table extraction + layout/figure reasoning
- Store extracted tables alongside text chunks
- Structured-output schemas for table cells
- **Deliverable:** tables from a real 10-K parsed and queryable.

### Week 5 — Multi-Agent Orchestration
- LangGraph StateGraph: supervisor classifies doc type + query intent
- Retriever/QA agent (cited answers) + Summarizer/Risk agent (summary + risk tags)
- Typed agent state, error handling, retry/timeout
- Human-in-the-loop checkpoint for low-confidence results
- **Deliverable:** end-to-end multi-agent run on a real filing.

### Week 6 — Eval Harness
- RAGAS pipeline (faithfulness, context recall, answer relevancy)
- 40–50 curated Q/A pairs across 3 doc types (quality > quantity)
- LLM-as-judge using a *separate* eval provider
- GitHub Actions gate: PR blocks on eval regression
- **Deliverable:** reproducible eval suite; CI gates merges.

### Week 7 — Model Serving Spike (the deployment story)
- Deploy quantized (AWQ) Qwen2.5-7B-Instruct or Llama-3.1-8B-Instruct on RunPod RTX 4090 (or HF Inference Endpoint L4, scale-to-zero)
- vLLM OpenAI-compatible server
- Benchmark: TTFT, throughput (tok/s), concurrency, quantization quality-loss vs full-precision
- Add as `SELF_HOST_PROVIDER` in the registry
- Write ADR documenting latency/throughput/cost tradeoffs
- **Deliverable:** self-hosted model answers real queries; benchmark + ADR on the repo.

### Week 8 — Guardrails + Observability Polish
- Guardrails AI: PII masking, topic enforcement, toxicity on input + output
- LangFuse: span traces for every agent/tool call, cost + latency dashboards
- Guardrail test cases in the suite
- **Deliverable:** traced, guarded end-to-end run.

### Week 9 — Streamlit UI
- Chat UI with streaming responses + inline citations
- PDF upload + SEC ticker input
- Structured report viewer (JSON + markdown)
- **Deliverable:** usable web UI.

### Week 10 — Docker + CI/CD + Deploy
- docker-compose: app + LangFuse + Postgres
- GitHub Actions: lint → unit → eval gate → build
- Deploy (Railway/Fly.io free tier, or self-host)
- **Deliverable:** reproducible `docker compose up` demo.

### Week 11 — Eval Hardening + ADRs
- Reproduce every resume metric from a clean checkout
- Write 3–4 ADRs (serving/quantization, retrieval, eval strategy, provider abstraction)
- Fix anything that doesn't reproduce
- **Deliverable:** honest, defensible numbers + decision writeups.

### Week 12 — Demo + Portfolio
- 3-min demo video (real SEC filing, end-to-end)
- README finalization + architecture diagrams
- Resume bullet drafts
- **Deliverable:** portfolio-ready repo + demo.

---

## 📁 Planned File Structure

```
nexusdoc/
├── README.md                       # this file (source of truth)
├── docs/adr/                       # architecture decision records
│   ├── ADR-001-provider-registry.md
│   ├── ADR-002-vllm-serving-quantization.md
│   ├── ADR-003-retrieval-reranking.md
│   └── ADR-004-eval-strategy.md
├── plans/                          # per-week plans (optional, derived)
├── app/
│   ├── ingestion/                  # sec_edgar, pdf_parser, chunking
│   ├── vlm/                        # qwen3_vl document/table pass
│   ├── rag/                        # embeddings, vector_store, hybrid_retriever, reranker
│   ├── agents/                     # supervisor, retriever_qa, summarizer_risk
│   ├── core/                       # config, model_registry, state, schemas
│   ├── guardrails/                 # Guardrails AI validators
│   ├── eval/                       # ragas_pipeline, test_cases, ci_gate
│   ├── serving/                    # vllm benchmark scripts + deploy notes
│   ├── ui/                         # streamlit app + components
│   └── main.py
├── tests/
│   ├── ingestion/  rag/  agents/  guardrails/  eval/  serving/
├── data/
│   ├── sample_docs/                # seed SEC filings, contracts
│   └── test_cases/                 # curated eval Q/A pairs
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
└── .env.example
```

---

## 📐 Architecture Decision Records (solutions-architect angle)

A short ADR per major decision. Each records **context → options considered → decision → tradeoffs/consequences.** This is the artifact that signals "solutions architect," not just "implementer."

- **ADR-001 — Provider-agnostic model registry:** why every call is provider-switchable; cost of the abstraction (a thin adapter layer) vs. benefit (free-tier-first, no lock-in).
- **ADR-002 — vLLM serving + AWQ quantization:** why self-host (deployment skill + cost control); why AWQ over GPTQ/FP8/GGUF for this hardware (4090/Ada); measured quality-loss; when to switch to FP8 on Hopper.
- **ADR-003 — Hybrid retrieval + cross-encoder reranking:** why bge-m3 + bge-reranker-v2-m3; latency cost of the rerank stage vs. recall gain; when a reranker is *not* worth it.
- **ADR-004 — RAGAS + CI eval gate:** why RAGAS over DeepEval/Promptfoo for this RAG-centric scope; why a CI gate (eval regression as a merge blocker).

---

## 🔮 Future Enhancements (post-MVP)

- **Earnings-call ingest** — Whisper ASR to pair transcript with filings
- **Multi-document comparison** — metrics across quarters/companies
- **Fine-tuned classifier** — replace zero-shot risk tagging once eval data accumulates
- **Real-time SEC watch** — poll EDGAR for new filings matching saved queries
- **Human-in-the-loop annotations** — analyst corrections feed an eval/fine-tune dataset

---

## 🧬 Transferable Skills (game-systems / tool programming → AI deployment)

This isn't called out in most learning plans, but it's a real marketability lever:

- **Performance & profiling** (frame budgets → TTFT/throughput budgets)
- **Systems/tooling** (build pipelines, asset pipelines → data/eval/serving pipelines)
- **Determinism & reproducibility** (deterministic builds → reproducible evals, VCR cassettes)
- **Resource budgets** (memory/CPU on consoles → VRAM/latency/cost on GPUs)
- **C++/low-level comfort** → comfortable reading vLLM/kernel internals when needed

Frame these explicitly in interviews and the resume — they directly map to the "deployment" half of the target title.

---

## 📝 Development Principles

1. **Provider abstraction first** — every model call through the registry; never hardcode a provider.
2. **Eval-driven development** — write test cases before/alongside agents; a PR that degrades eval scores does not merge.
3. **Deterministic by default** — unit tests use VCR.py cassettes; they pass without network.
4. **Observability from day one** — every agent step, LLM call, and retriever query traced in LangFuse.
5. **Self-host at least one model** — the vLLM spike is non-negotiable; it's the deployment story.
6. **Honest metrics** — nothing on the resume that hasn't been reproduced from a clean checkout.
7. **Free-tier-first, measured spend** — default to $0; spend only on the serving spike and eval overflow.
8. **Documentation as code** — this README + ADRs are the source of truth; update them first.

---

## 🚀 Getting Started (Week 1 scaffold)

```bash
git clone https://github.com/yourusername/nexusdoc.git
cd nexusdoc
cp .env.example .env          # add free-tier keys (Groq, OpenRouter, Supabase)
docker compose up -d          # app + LangFuse + Postgres
python -m app.main --ticker AAPL --filing 10-K
```

---

## 🔎 Sources (verified 2026-07)

- Groq rate limits: https://console.groq.com/docs/rate-limits
- OpenRouter free router: https://openrouter.ai/openrouter/free
- GitHub Models (prototyping-only terms): https://docs.github.com/github-models/prototyping-with-ai-models
- MTEB embedding leaderboard: https://huggingface.co/spaces/mteb/leaderboard
- vLLM quantization docs: https://docs.vllm.ai/en/latest/features/quantization/
- RunPod pricing: https://www.runpod.io/pricing
- HF Inference Endpoints pricing: https://huggingface.co/docs/inference-endpoints/en/pricing
- Qwen3-VL document parsing: https://qwenlm-qwen3-vl.mintlify.app/capabilities/document-parsing
- LangFuse (ClickHouse-backed, MIT): https://langfuse.com
- RAGAS vs DeepEval vs Promptfoo (2026): https://qaskills.sh/blog/deepeval-vs-ragas-vs-promptfoo-2026
- Guardrails AI ↔ NeMo Guardrails: https://guardrailsai.com/blog/nemoguardrails-integration
- Coqui TTS shutdown (Jan 2024) + idiap fork: https://github.com/coqui-ai/TTS/discussions/3489

---

*NexusDoc — documents into intelligence, one observable agent at a time.*
