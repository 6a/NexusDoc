# NexusDoc — Multi-Agent Document Intelligence Platform

**A production-style AI system that ingests dense document corpora, runs a multi-agent LangGraph pipeline over them (hybrid retrieval + reranking → risk classification → multi-level summarization → structured report), with a real LLM-as-judge eval harness, guardrails, self-hosted observability, and self-served model inference via vLLM.**

> **Goal of this project (meta):** A portfolio piece to transition the author from game-systems / tool programming into an **AI deployment engineer / AI forward-deployed engineer / AI solutions engineer** role, built part-time within a **~40-hour budget**. Scope is deliberately bounded: one focused, *finished*, deployed system beats two half-built ones.

---

## 🧭 What It Does

NexusDoc turns dense, multi-format documents into structured intelligence.

**Input:**

- **arXiv research papers** (PDF, fetched via the free arXiv API + `arxiv` Python package — no S3 requester-pays, no per-doc cost)
- **IETF RFCs** (plain-text, bulk-fetched via rsync) — gives a clean PDF-vs-text ingestion contrast
- *(See "Document domains" below — second domain is provisional and easy to swap.)*

**Output:**

- Structured JSON report (extracted fields, risk tags, key terms, source citations)
- Multi-level summary (paragraph → bullets → one-liner)
- Interactive chat UI with cited, streamed answers over the document set

**Problem:** Analysts, engineers, and compliance teams spend significant time manually extracting information from documents that mix prose, tables, and structure. NexusDoc fuses **document ingest + hybrid retrieval + multi-agent reasoning + evaluation + self-hosted serving** into one observable pipeline.

> **Why these domains (not SEC filings):** The original plan used SEC EDGAR filings. The author is based in Japan, where SEC filings are not relatable to most reviewers or recruiters. arXiv + RFCs are internationally recognized, **bulk-downloadable for free** (no per-doc scraping), and give a natural PDF-vs-plain-text ingestion contrast.

---

## 🧠 Core Capabilities (what the system actually does)

The earlier "9 HuggingFace task categories" framing is gone — in 2026 the right tool for QA, classification, and summarization is a **strong general LLM with structured output**, not a chain of specialized HF models. Task coverage is a *consequence* of good design, not a goal.

| Capability | Implementation (2026-appropriate) |
| --- | --- |
| Document ingestion | arXiv API + RFC rsync fetch; **PyMuPDF** for PDF → text + page metadata; simple text loading for RFCs |
| Hybrid retrieval | pgvector dense (**bge-m3** / nomic-embed-text-v2) + sparse, with a **cross-encoder reranker** (bge-reranker-v2-m3) |
| Multi-agent orchestration | **LangGraph** StateGraph: supervisor routes to a retriever/QA agent and a summarizer/risk agent |
| Risk classification | LLM structured output + zero-shot fallback |
| Summarization | LLM with controlled prompts (paragraph → bullet → one-liner) |
| Evaluation | **RAGAS** (faithfulness, context recall, answer relevancy) + LLM-as-judge, **15–20 curated cases** |
| Guardrails | **Guardrails AI** — one PII validator on input + output (thin but present; signals production discipline) |
| Observability | **LangFuse** self-hosted (tracing, token/cost attribution, eval dashboards) |
| Semantic caching | **Redis + RedisVL** intercepts every registry LLM call (content-hash + vector-similarity ~0.85); embedding cache avoids re-embedding unchanged chunks; cache-hit-rate traced in LangFuse |
| Model serving | **vLLM** serving a quantized 7–8B model behind an OpenAI-compatible endpoint — **the real "deployment" story** |

> **Dropped from the earlier plan:** the Qwen3-VL document/table-understanding pass. Multi-modal doc AI is a niche, not core to AI *deployment* roles, and the author's gaps are RAG/agents/evals/serving — not vision. Text-only RAG with simple table heuristics covers the role-relevant skills. The VLM can return as a post-MVP enhancement.

---

## 🏗️ Architecture

### High-Level System Flow

```
┌───────────────────────────────────────────────────────────────┐
│                       User Input Layer                        │
│  ┌───────────────────────────┐ ┌───────────────────────────┐  │
│  │      arXiv ID / PDF       │ │        RFC number         │  │
│  └─────────────┬─────────────┘ └─────────────┬─────────────┘  │
│                │                             │                │
│                ▼                             ▼                │
│                                                               │
│                Ingestion (script + cron, thin)                │
│                                                               │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐  │
│  │ arXiv/RFC fetch │ │  PyMuPDF parse  │ │  Text Chunking  │  │
│  └────────┬────────┘ └────────┬────────┘ └────────┬────────┘  │
│           │                   │                   │           │
│           ▼                   ▼                   ▼           │
│  ┌─────────────────────────────────────────────────────────┐  │
│              Vector Store (pgvector on Supabase)              │
│       ┌─────────────────────┐   ┌─────────────────────┐       │
│       │     Text Chunks     │   │     Page/Source     │       │
│       └─────────────────────┘   └─────────────────────┘       │
│  └────────────────────────────┬────────────────────────────┘  │
│                               │                               │
│                               ▼                               │
│    Hybrid Retrieve (dense+sparse) → Rerank (bge-reranker)     │
│                               │                               │
│                               ▼                               │
│  ┌─────────────────────────────────────────────────────────┐  │
│                     Redis Semantic Cache                      │
│                   intercepts every LLM call                   │
│    ↑ hit → return cached answer                               │
│    ↓ miss → provider → store                                  │
│  └─────────────────────────────────────────────────────────┘  │
│                               │                               │
│                               ▼                               │
│                                                               │
│              LangGraph Multi-Agent Orchestrator               │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐  │
│                Supervisor Agent (StateGraph)                  │
│              Classify doc type + query intent                 │
│                                                               │
│                       route_to_agents                         │
│                               │                               │
│                               ▼                               │
│                                                               │
│            ┌─────────────────┐ ┌─────────────────┐            │
│            │  Retriever/QA   │ │ Summarizer/Risk │            │
│            │  Agent          │ │ Agent           │            │
│            └────────┬────────┘ └───────┬─────────┘            │
│                     │                  │                      │
│                     │                  │                      │
│                     └─────────┬────────┘                      │
│                               │                               │
│                               ▼                               │
│                 collect → validate → format                   │
│  └─────────────────────────────────────────────────────────┘  │
│                               │                               │
│                               ▼                               │
│                                                               │
│                         Output Layer                          │
│                                                               │
│  ┌───────────────────────────┐ ┌───────────────────────────┐  │
│  │      Structured JSON      │ │    Chat UI (Streamlit)    │  │
│  └───────────────────────────┘ └───────────────────────────┘  │
│                                                               │
│  Observability: LangFuse (self-hosted) — every span traced    │
│  Guardrails:   Guardrails AI — PII on input & output          │
│  Cache:         Redis semantic cache (cache-hit traced)       │
└───────────────────────────────────────────────────────────────┘
```

### Model Serving Layer (the "deployment engineer" story)

Every model call goes through a **provider-agnostic registry**. Crucially, one of those providers is a **self-hosted vLLM endpoint** — not just third-party APIs. This is the differentiator between "app that calls APIs" and "engineer who can deploy models," and it is the author's single biggest knowledge gap (zero prior experience), so it stays deep.

```
┌───────────────────────────────────────────────────────────────┐
│              Model Registry (provider-agnostic)               │
│                                                               │
│  DEFAULT_PROVIDER   = groq        # free-tier primary         │
│  FALLBACK_PROVIDER  = openrouter  # rate-limit overflow       │
│  SELF_HOST_PROVIDER = vllm        # ← the deployment story    │
│  OFFLINE_PROVIDER   = ollama      # local dev, no internet    │
│  EVAL_PROVIDER      = openrouter  # separate model for judge  │
│                                                               │
│  Embeddings: bge-m3 / nomic-embed-text-v2 (local)             │
│  Reranker:   bge-reranker-v2-m3    (local)                    │
│  Cache:      Redis + RedisVL (semantic LLM cache)             │
└───────────────────────────────────────────────────────────────┘
```

**vLLM serving spike (Phase 7):** the deployment story, achieved at **$0**. Two-part approach driven by the reality that **no free persistent GPU endpoint exists in 2026**: (1) **Benchmark** a quantized (AWQ) 7–8B instruct model (Qwen2.5-7B-Instruct-AWQ or Llama-3.1-8B-Instruct-AWQ) with vLLM on **Google Colab's free T4 GPU** (15–16 GB VRAM — enough for a 7B AWQ model) as a one-shot notebook: measure **TTFT, throughput (tok/s), concurrent requests, and quantization quality-loss** vs. the full-precision baseline. (2) For the **live demo**, serve the model via **Ollama on your own machine** (already in the registry) — Colab's free tier prohibits background execution and third-party service exposure, so it's for benchmarking only. Wire the vLLM benchmark results into the registry's `SELF_HOST_PROVIDER` config. Write an ADR documenting the latency/throughput/cost tradeoffs **and why a zero-cost persistent GPU serving endpoint isn't achievable in 2026** (Colab/HF Spaces/Oracle Cloud free-tier constraints) — this cost-aware tradeoff analysis is itself a deployment-engineer signal.

### State Management (LangGraph)

```python
class DocumentState(TypedDict):
    doc_id: str
    source: str            # "arxiv" | "rfc" | "upload"
    file_path: str
    chunks: list[DocumentChunk]

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

## 💸 Cost Strategy (verified 2026 limits) — **$0 total spend**

Designed to run entirely on free tiers and always-free solutions for development and demo. **No paid services, no free trials that expire.** The earlier plan included ~$2–5 of RunPod GPU spend for the vLLM spike; this has been replaced with a free Colab-T4 benchmark + Ollama-served demo (see Phase 7), so the project is now genuinely zero-cost.

### Free tier (development & demo — all verified permanent/always-free, not trials)

| Component | Solution | Real 2026 limits |
| --- | --- | --- |
| **LLM inference (primary)** | Groq free tier | **30 RPM, ~1,000 RPD** per model — permanent free tier, no credit card, no expiry |
| **LLM fallback** | OpenRouter free router (`:free` model suffix or `openrouter/free`) | 20 RPM, 1,000 RPD; permanent free models, no credit card |
| **LLM local (also the live-demo serving path)** | Ollama (Llama 3.1 8B, Qwen2.5 7B, Gemma 3) | Free; needs 8GB+ VRAM for 7B quantized |
| **vLLM benchmark GPU** | Google Colab free tier (T4, 15–16 GB VRAM) | ~12h sessions, no background exec, ToS ban third-party exposure — fine for one-shot benchmarks, NOT a persistent endpoint |
| **Embeddings** | bge-m3 / nomic-embed-text-v2 (local) | Free, local, no API calls |
| **Reranker** | bge-reranker-v2-m3 (local) | Free, local |
| **Vector store** | pgvector on Supabase free | 500 MB Postgres + pgvector + auth; always-free (not a trial), **auto-pauses after 7 days inactivity — wake with a scheduled ping before demo** |
| **Observability** | LangFuse self-hosted (Docker) | MIT-licensed, ClickHouse-backed since Jan 2026 |
| **Doc parsing** | PyMuPDF (local) | Free, local |
| **Doc corpus** | arXiv API + `arxiv` package + IETF RFC rsync | arXiv API: free, 1 req / 3s; RFC rsync: free |
| **Cache** | Redis (self-hosted Docker) | Free, local; semantic LLM cache via RedisVL |
| **Eval judge** | Ollama local LLM (separate from the system-under-test) | Free; avoids burning paid-API quota on eval runs |
| **Deploy (live URL)** | Railway/Fly.io/Render free tier or self-host | Free tier with sleep-on-inactivity (wake before demo) |

> ⚠️ **What was removed to hit $0:** RunPod RTX 4090 ($0.34/hr) and HuggingFace Inference Endpoints ($0.80/hr) for the vLLM spike → replaced by Colab free T4 benchmark + Ollama demo. Paid Groq/OpenRouter tiers for eval overflow → replaced by spreading eval runs across days (within free RPD) and/or using Ollama as the local eval judge. **GitHub Models free tier is intentionally *not* used as a production provider** — its terms restrict use to prototyping/experimentation only.

### Why this strategy works (and where the earlier plan was wrong)

- The earlier plan claimed ~$2–5 of "intentional paid spend" for the vLLM spike. Research showed this is **avoidable**: Colab's free T4 runs the vLLM benchmark as a one-shot notebook, and Ollama serves the live demo. The ADR now documents *why* no free persistent GPU endpoint exists (Colab session/no-background-exec/ToS; HF Spaces free-CPU sleeps after ~48h; Oracle Always Free = CPU only, no GPU) — which is a stronger cost-awareness story than "I rented a GPU."
- A multi-agent run is 8–15 LLM calls per document, so the **~1,000 RPD** ceiling (not tokens) is what bites — realistically **~60–120 documents/day**, and the 30 RPM cap adds wall-clock time. Planning around requests, not tokens, is what makes the eval phase actually finishable **within the free tier**.
- Eval overflow is handled by spreading cases across days and/or using a **local Ollama model as the LLM-as-judge** — keeps eval fully free and offline-capable.
- Embeddings + reranker stay local and free — no per-vector API costs that silently grow.
- Supabase's 7-day inactivity auto-pause is the one operational caveat: a scheduled wake (e.g. a GitHub Actions cron hitting the project URL weekly) keeps it live for demo. This is itself a small LLMOps/uptime story.

---

## 🛠️ Tech Stack

| Category | Choice | Why (2026-grounded) |
| --- | --- | --- |
| **Agent orchestration** | **LangGraph** | Industry standard for graph-shaped, stateful, auditable agent workflows in 2026 |
| **Framework glue** | LangChain | Tool binding, loaders, retrievers, LCEL |
| **Vector store** | pgvector on Supabase | Hybrid search + transactional queries; generous free tier |
| **Embeddings** | **bge-m3** or **nomic-embed-text-v2** (local) | Modern open-weight leaders; `all-MiniLM-L6-v2` is dated and dropped |
| **Reranker** | **bge-reranker-v2-m3** (local) | Lightweight open-weight cross-encoder; cheap RAG quality win |
| **Doc ingestion** | arXiv API + IETF RFC rsync + **PyMuPDF** | Free, bulk, internationally-recognized corpora; one PDF parser, no VLM |
| **LLM inference** | Groq / OpenRouter / **vLLM (self-hosted)** / Ollama | Configurable; the vLLM provider is the deployment story |
| **Model serving** | **vLLM** (AWQ quantized) | Production standard; OpenAI-compatible server; quantization supported |
| **Summarization / risk** | Groq/OpenRouter LLMs w/ structured output | Pydantic-validated outputs |
| **Eval** | **RAGAS** + LLM-as-judge | RAG-specific metrics (faithfulness, context recall, answer relevancy) |
| **Caching** | **Redis + RedisVL** (semantic LLM cache) | 2026 production standard: content-hash + vector-similarity match; directly attacks the RPD free-tier constraint |
| **Guardrails** | **Guardrails AI** (one PII validator) | Lighter than NeMo; signals safety discipline at low cost |
| **Observability** | LangFuse self-hosted | Open-source tracing + cost attribution; framework-agnostic via OpenTelemetry |
| **Backend** | FastAPI (thin) | Async, type-safe, auto-docs for the app's REST surface |
| **Frontend** | **Streamlit** (only, vibe-coded) | Rapid chat UI + report viewer; not a learning focus — built fast |
| **CI/CD** | GitHub Actions + pytest | Eval-gated merges |
| **Containers** | Docker + docker-compose | Reproducible: app + LangFuse + DB in one stack |
| **Testing** | pytest + VCR.py (cassettes) | Deterministic unit tests without network |

### Deliberately cut from the earlier plan (and why)

| Cut | Reason |
| --- | --- |
| **Qwen3-VL doc/table understanding** | Multi-modal doc AI is a niche, not core to *deployment* roles; author's gaps are RAG/agents/evals/serving, not vision. Saves ~5 hrs. |
| **SEC EDGAR filings → arXiv + RFCs** | Author is Japan-based; SEC filings aren't relatable locally. arXiv + RFCs are free, bulk-downloadable, and give a PDF-vs-text contrast. |
| **3 doc domains → 2** | Less ingest/eval plumbing; two domains still prove generality. |
| **40–50 eval cases → 15–20** | Quality over quantity; part-time reality. A CI gate on 15 curated cases signals more than 50 padded ones. |
| **Full guardrails (PII+topic+toxicity) → one PII validator** | Presence signals production discipline (lean teams hire for it) at a fraction of the time. |
| **Human-in-the-loop LangGraph checkpoint** | Cute but not role-relevant; auto retry/timeout covers reliability. |
| **TTS / audio briefings (Coqui)** | Coqui shut down Jan 2024; TTS is off-goal for an AI *deployment* role. |
| **Prefect** | Overkill for demo ingestion; script + cron is enough. |
| **TAPAS, LayoutLMv3, Table Transformer** | Dated/specialized; dropped with the VLM. |
| **NeMo Guardrails (primary)** | Heavyweight; one Guardrails AI validator covers the signal. |
| **FastAPI + Streamlit both first-class** | Streamlit is the only UI; FastAPI kept thin for the REST/serving surface. Streamlit UI is vibe-coded, not a learning focus. |
| **"9 HuggingFace tasks" framing** | Reads as a model-zoo checklist, not engineering. Removed. |

---

## 📋 Resume-Ready Impact (honest language)

### Measured targets (stated as targets until reproduced)

| Metric | Target | How measured |
| --- | --- | --- |
| Document types handled | 2 (arXiv PDF, RFC text) | Integration tests |
| RAG faithfulness / context recall | >90% recall, low hallucination | RAGAS on 15–20 curated cases |
| End-to-end latency | <30s for a 50-page doc | LangFuse traces |
| Eval cases | 15–20 curated Q/A pairs | Dedicated eval set |
| Guardrail recall | High PII detection | Directed test suite |
| vLLM serving | Quantized 7–8B at target TTFT + throughput | Benchmark script |

> **Honesty rule:** no metric goes on the resume until a clean, reproducible run produces it. Targets below are written as *"targeted and measured via…"*, not as achieved facts.

### Portfolio statement (resume-ready, defensible)

> *"Built NexusDoc — a multi-agent document-intelligence platform: hybrid RAG (pgvector + bge-m3 + cross-encoder reranking) over arXiv and RFC corpora, a LangGraph supervisor/worker graph, RAGAS-evaluated pipelines (15+ curated cases with a CI eval gate), Guardrails-AI PII safety, and self-hosted LangFuse tracing. Processes real documents end-to-end with citations and structured risk/summary output."*

> *"Designed the LLMOps stack: provider-agnostic model registry (Groq / OpenRouter / Ollama / self-hosted vLLM) with a Redis semantic cache (RedisVL) intercepting every LLM call, RAGAS eval harness wired into GitHub Actions to block merges on regression, and LangFuse cost/latency attribution per agent step."*

> *"Self-served a quantized 7–8B model via vLLM, benchmarked TTFT, throughput, and quantization quality-loss vs. full-precision on Google Colab's free T4 GPU (zero-cost), served the live demo via local Ollama, and documented — in an architecture decision record — the latency/throughput/cost tradeoffs and why no free persistent GPU serving endpoint exists in 2026 (Colab/HF Spaces/Oracle Cloud free-tier constraints)."*

### How it maps to real AI engineering jobs (2026)

Based on 2026 job-market research (AI deployment / forward-deployed / solutions / application engineer JDs), the dominant signals are: **RAG is now baseline** (necessary, not differentiating), **multi-agent orchestration** (LangGraph is the production standard), **evals + guardrails** (lean AI-native teams hire for production-readiness), and **model serving/deployment** (vLLM is the industry default and the strongest "deployment" differentiator). A **live deployed URL** is what recruiters actually check.

| JD requirement | NexusDoc evidence |
| --- | --- |
| **Production RAG with hybrid search + reranking** | pgvector + bge-m3 + bge-reranker-v2-m3 (dense+sparse → cross-encoder rerank) |
| **Multi-agent orchestration** | LangGraph supervisor/worker StateGraph with typed state |
| **Model serving / deployment** ⬅ key gap-filler | vLLM serving quantized model, OpenAI-compatible, benchmarked |
| **Quantization & inference tradeoffs** ⬅ key gap-filler | AWQ vs full-precision benchmark + ADR |
| **Semantic caching & inference cost optimization** | Redis + RedisVL cache intercepting every registry call; cache-hit-rate traced in LangFuse |
| **LLMOps & evaluation** | RAGAS + LangFuse + CI eval gate |
| **Guardrails & safety** | Guardrails AI PII validator on input + output |
| **Vector databases & indexing** | pgvector + HNSW indexing |
| **Structured output** | Pydantic → JSON reports |
| **Observability** | LangFuse self-hosted (spans, token tracking, cost) |
| **Cost-optimized inference** | Provider registry, free-tier-first, measured spend + Redis semantic cache |
| **Containerization & deployment** | Docker / docker-compose → live deploy + CI/CD |

> Model serving + quantization is the single most marketable artifact — without it the project reads as "app engineering," not "deployment engineering." That's why it stays deep despite the time crunch.

---

## 🗺️ 40-Hour Part-Time Roadmap (~10–12 hrs/week → ~4 weeks, or flexible)

The earlier 12-week / 144–180-hr plan is compressed ~4–5x. Trims are driven by three forces: (1) job-market research (what signals hiring), (2) the author's existing knowledge (deep only where there's a real gap), (3) vibe-coding glue that isn't a learning objective.

```
Phase 1 (~4h) : Foundation — repo, uv, model registry (Groq+OpenRouter+Ollama),
                LangFuse up, hello-world traced RAG (in-memory)
Phase 2 (~4h) : Ingestion — arXiv/RFC fetch, PyMuPDF parse, chunking, pgvector schema
Phase 3 (~5h) : Retrieval — bge-m3 embeddings + hybrid search + bge-reranker-v2-m3
Phase 4 (~5h) : LangGraph multi-agent — supervisor + Retriever/QA + Summarizer/Risk
Phase 5 (~5h) : Eval harness — RAGAS + 15–20 curated cases + LLM-as-judge + CI gate
Phase 6 (~3h) : Caching — Redis (RedisVL) semantic LLM-response cache + content-hash
                embedding cache in the registry; cache-hit-rate traced in LangFuse
Phase 7 (~7h) : Model serving spike (DEEP) — vLLM (AWQ) benchmarked on free Colab T4,
                wire into registry, ADR-002      ← the deployment story + author's biggest gap
Phase 8 (~2h) : Guardrails (one PII validator) + LangFuse cost/latency dashboard
Phase 9 (~1h) : Streamlit UI — vibe-coded: streaming chat, citations, report viewer
Phase 10(~4h) : Docker compose + CI/CD + live deploy (guided hands-on) → get a live URL
Phase 11(~2h) : Eval hardening — reproduce all metrics, write 4–5 ADRs, honest numbers
Phase 12(~1h) : Demo video + portfolio writeup + resume bullets
```

> ~43 hours total (still ~40 within the existing buffer). Reserve a little extra (call it ~2–4 hrs buffer) outside the build for resume finalization, a 3-min demo video, and interview prep. Phases are flexible — feel free to compress Phase 1 once you're comfortable with the registry pattern.

### Phase 1 — Foundation (~4h)

- Repo scaffold, `pyproject.toml` (uv), pre-commit, `.env.example`
- Model registry: Groq + OpenRouter + Ollama providers, env-switchable *(author has API-integration experience → accelerate the concepts; focus on the registry pattern itself)*
- LangFuse self-hosted via docker-compose (single container)
- Hello-world traced RAG: embed one doc, answer one query, see it traced
- **Deliverable:** a traced RAG query against a single doc. *(Vibe-code-able scaffold once the registry pattern is clear.)*

### Phase 2 — Ingestion (~4h)

- arXiv fetch (arxiv PyPI package) + RFC fetch (rsync plain-text archives)
- PyMuPDF → text chunks + page metadata (PDF path); text-loader (RFC path)
- pgvector schema (HNSW index) + upsert pipeline
- **Deliverable:** CLI ingests an arXiv PDF and an RFC into pgvector.

### Phase 3 — Hybrid Retrieval + Reranking (~5h)

- bge-m3 (or nomic-embed-text-v2) local embeddings
- Dense + sparse hybrid retrieval (pgvector)
- bge-reranker-v2-m3 cross-encoder rerank (top-K)
- Citation plumbing (chunk → page/section)
- **Deliverable:** cited hybrid-RAG answers with reranking. *(Core RAG skill — author's gap.)*

### Phase 4 — Multi-Agent Orchestration (~5h)

- LangGraph StateGraph: supervisor classifies doc type + query intent
- Retriever/QA agent (cited answers) + Summarizer/Risk agent (summary + risk tags)
- Typed agent state, error handling, retry/timeout
- **Dropped:** human-in-the-loop checkpoint (not role-relevant)
- **Deliverable:** end-to-end multi-agent run on a real document.

### Phase 5 — Eval Harness (~5h)

- RAGAS pipeline (faithfulness, context recall, answer relevancy)
- 15–20 curated Q/A pairs across 2 doc types (quality > quantity)
- LLM-as-judge using a *separate* eval provider
- GitHub Actions gate: PR blocks on eval regression
- **Deliverable:** reproducible eval suite; CI gates merges.

### Phase 6 — Caching: Semantic LLM Cache (~3h)

- **Redis + RedisVL** semantic LLM-response cache wired into the model registry (intercepts every LLM call): embed the incoming prompt, reuse a past answer if cosine similarity ≥ ~0.85; on a miss, fall through to the provider and store the result.
- Content-hash **embedding cache** so unchanged chunks are never re-embedded.
- Track **cache-hit-rate** as a LangFuse span/metric so the win is visible and reproducible.
- *(Builds on Phase 5: the eval suite quantifies how caching reduces the effective LLM-call count per run.)*
- **Deliverable:** repeat/similar queries served from cache; cache-hit-rate traceable in LangFuse.

### Phase 7 — Model Serving Spike (~7h, DEEP — the deployment story)

- **Benchmark** quantized (AWQ) Qwen2.5-7B-Instruct or Llama-3.1-8B-Instruct with **vLLM on Google Colab's free T4** (one-shot notebook — Colab ToS allow benchmarking, prohibit persistent third-party exposure)
- vLLM OpenAI-compatible server (launched in the Colab notebook for the benchmark run)
- Benchmark: TTFT, throughput (tok/s), concurrency, quantization quality-loss vs full-precision
- **Live demo** serves the model via **Ollama on your own machine** (already in the registry) — zero-cost, no GPU rental
- Wire the vLLM benchmark results into `SELF_HOST_PROVIDER` config
- Write ADR documenting latency/throughput/cost tradeoffs **and the free-tier GPU-hosting landscape analysis** (why no $0 persistent GPU endpoint exists in 2026)
- **Deliverable:** reproducible Colab benchmark notebook + benchmark results + ADR; live demo answers real queries via Ollama. *(Author's biggest gap + strongest differentiator — do NOT trim this. The cost-awareness ADR is itself a deployment-engineer signal.)*

### Phase 8 — Guardrails + Observability Polish (~2h)

- Guardrails AI: one PII validator on input + output
- LangFuse: span traces for every agent/tool call, cost + latency dashboards
- Guardrail test cases in the suite
- **Deliverable:** traced, guarded end-to-end run.

### Phase 9 — Streamlit UI (~1h, vibe-coded)

- Chat UI with streaming responses + inline citations
- arXiv ID / RFC number / PDF upload input
- Structured report viewer (JSON + markdown)
- **Deliverable:** usable web UI. *(Vibe-coded fast — frontend is not a learning objective.)*

### Phase 10 — Docker + CI/CD + Deploy (~4h, guided hands-on)

- docker-compose: app + LangFuse + Postgres + Redis
- GitHub Actions: lint → unit → eval gate → build
- Deploy (Railway/Fly.io/Render free tier, or self-host) → **live URL**
- **Deliverable:** reproducible `docker compose up` demo + a public URL. *(Author has some exposure but wants a guided walkthrough.)*

### Phase 11 — Eval Hardening + ADRs (~2h)

- Reproduce every resume metric from a clean checkout
- Write 4–5 ADRs (serving/quantization, retrieval, eval strategy, provider abstraction, caching)
- Fix anything that doesn't reproduce
- **Deliverable:** honest, defensible numbers + decision writeups.

### Phase 12 — Demo + Portfolio (~1h)

- 3-min demo video (real arXiv/RFC doc, end-to-end)
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
├── plans/                          # per-phase walkthroughs
├── app/
│   ├── ingestion/                  # arxiv_fetch, rfc_fetch, pdf_parser, chunking
│   ├── rag/                        # embeddings, vector_store, hybrid_retriever, reranker
│   ├── agents/                     # supervisor, retriever_qa, summarizer_risk
│   ├── core/                       # config, model_registry, state, schemas
│   ├── guardrails/                 # Guardrails AI PII validator
│   ├── eval/                       # ragas_pipeline, test_cases, ci_gate
│   ├── serving/                    # vllm benchmark scripts + deploy notes
│   ├── cache/                      # redis semantic cache (RedisVL) + content-hash embedding cache
│   ├── ui/                         # streamlit app + components (vibe-coded)
│   └── main.py
├── tests/
│   ├── ingestion/  rag/  agents/  guardrails/  cache/  eval/  serving/
├── data/
│   ├── sample_docs/                # seed arXiv PDFs, RFCs
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
- **ADR-002 — vLLM benchmarking + AWQ quantization (zero-cost):** why benchmark on Colab free T4 + serve the demo via Ollama (no $0 persistent GPU endpoint exists in 2026); why AWQ over GPTQ/FP8/GGUF for T4/Ada-class hardware (15–16 GB VRAM); measured quality-loss; the free-tier GPU-hosting landscape analysis (Colab ToS, HF Spaces sleep, Oracle Always Free = CPU only); when to switch to paid RunPod/HF for real production throughput.
- **ADR-003 — Hybrid retrieval + cross-encoder reranking:** why bge-m3 + bge-reranker-v2-m3; latency cost of the rerank stage vs. recall gain; when a reranker is *not* worth it.
- **ADR-004 — RAGAS + CI eval gate:** why RAGAS over DeepEval/Promptfoo for this RAG-centric scope; why a CI gate (eval regression as a merge blocker).
- **ADR-005 — Redis semantic caching:** why Redis/RedisVL over GPTCache/in-memory; why cosine ≥ ~0.85 threshold; measured call-count and cost savings vs. latency/consistency tradeoffs; when *not* to cache (freshness-critical answers).

---

## 📄 Document Domains (decision + alternatives)

**Chosen (default):** arXiv research papers (PDF, via the free arXiv API + `arxiv` Python package — 1 req / 3s, single connection; no S3 requester-pays needed for a portfolio-scale handful of papers) + IETF RFCs (plain text, via rsync). Both are free, bulk-downloadable, internationally recognized, and give a clean PDF-vs-text ingestion contrast — ideal for proving the ingest pipeline handles two formats without VLM.

**Alternative second domain** (to finalize together before Phase 2):

- **Product / user manuals** (manufacturer PDFs) — more "real-world business document" feel, internationally relatable; downside: no clean bulk API (curated set of ~20–50 PDFs).
- **Electronics datasheets** (TI / STMicro) — very tabular, ties to author's game-systems/embedded background; downside: niche, very dense.
- **OpenStax textbooks** — structured chapters + exercises, free PDFs; downside: large, somewhat academic.

> The second domain is swappable with minimal code change (the ingestion layer abstracts source → text + page/section metadata). Pick the one that best matches the story you want to tell in interviews.

---

## 🔮 Future Enhancements (post-MVP)

- **VLM document pass (Qwen3-VL)** — add the multi-modal table-extraction layer that was scoped out, if targeting doc-AI roles specifically.
- **Multi-document comparison** — metrics across RFC revisions or paper versions.
- **Fine-tuned classifier** — replace zero-shot risk tagging once eval data accumulates.
- **Human-in-the-loop annotations** — analyst corrections feed an eval/fine-tune dataset.
- **Real-time watch** — poll arXiv/RFC for new matching documents.
- **Cache eviction & TTL policies** — per-provider TTLs, invalidation on doc re-ingest, and cache-warming for demo queries.

---

## 🧬 Transferable Skills (game-systems / tool programming → AI deployment)

This isn't called out in most learning plans, but it's a real marketability lever:

- **Performance & profiling** (frame budgets → TTFT/throughput budgets)
- **Systems/tooling** (build pipelines, asset pipelines → data/eval/serving pipelines)
- **Determinism & reproducibility** (deterministic builds → reproducible evals, VCR cassettes)
- **Resource budgets** (memory/CPU on consoles → VRAM/latency/cost on GPUs)
- **C++/low-level comfort** → comfortable reading vLLM/kernel internals when needed

Frame these explicitly in interviews and the resume — they directly map to the "deployment" half of the target title and explain the fast ramp on the vLLM spike.

---

## 📝 Development Principles

1. **Provider abstraction first** — every model call through the registry; never hardcode a provider.
2. **Eval-driven development** — write test cases before/alongside agents; a PR that degrades eval scores does not merge.
3. **Deterministic by default** — unit tests use VCR.py cassettes; they pass without network.
4. **Observability from day one** — every agent step, LLM call, and retriever query traced in LangFuse.
5. **Self-host at least one model** — the vLLM spike is non-negotiable; it's the deployment story.
6. **Honest metrics** — nothing on the resume that hasn't been reproduced from a clean checkout.
7. **Free-tier-first, measured spend** — default to $0; spend only on the serving spike and eval overflow.
8. **Deep where it counts, vibe-coded where it doesn't** — RAG/agents/evals/serving are hands-on learning; the Streamlit UI and scaffold are vibe-coded to protect the 40-hr budget.
9. **Documentation as code** — this README + ADRs are the source of truth; update them first.

---

## 🚀 Getting Started (Phase 1 scaffold)

```bash
git clone https://github.com/yourusername/nexusdoc.git
cd nexusdoc
cp .env.example .env          # add free-tier keys (Groq, OpenRouter, Supabase)
docker compose up -d          # LangFuse + Postgres
python -m app.main --arxiv 2401.12345
python -m app.main --rfc 9110
```

---

## 🔎 Sources (verified 2026-07)

- Groq rate limits: <https://console.groq.com/docs/rate-limits>
- OpenRouter free router: <https://openrouter.ai/openrouter/free>
- GitHub Models (prototyping-only terms): <https://docs.github.com/github-models/prototyping-with-ai-models>
- MTEB embedding leaderboard: <https://huggingface.co/spaces/mteb/leaderboard>
- vLLM quantization docs: <https://docs.vllm.ai/en/latest/features/quantization/>
- arXiv API terms of use (free, 1 req / 3s): <https://info.arxiv.org/help/api/tou.html>
- arxiv PyPI package: <https://pypi.org/project/arxiv/>
- arXiv bulk data (S3 requester-pays — intentionally NOT used, documented as a cost trap): <https://info.arxiv.org/help/bulk_data.html>
- Google Colab free tier (T4 GPU, ~12h sessions, ToS): <https://research.google.com/colaboratory/tos_v5.html> and <https://research.google.com/colaboratory/intl/en-GB/faq.html>
- HuggingFace Spaces free tier (CPU sleeps ~48h, not for production): <https://huggingface.co/docs/hub/main/spaces-sdks-docker>
- Oracle Cloud Always Free (no GPU — Ampere A1 CPU only): <https://www.oracle.com/cloud/free/>
- 2026 AI engineering job-market signals (FDE / deployment / solutions roles): <https://epinium.com/en/blog/ai-deployment-engineer/> , <https://theaimarketpulse.com/insights/trends/most-in-demand-skills/> , <https://www.boundev.ai/blog/ai-engineer-skills-2026-job-posts>
- Portfolio scope guidance (live URL, depth > breadth): <https://gitgood.dev/blog/ai-side-project-that-gets-you-hired-2026>

---

*NexusDoc — documents into intelligence, one observable agent at a time.*
