# NexusDoc — Appliance Support Document Intelligence

**A production-style RAG system for appliance / white-goods support manuals (EN + JP): hybrid retrieval + reranking → cited troubleshooting answers + short procedure summaries, with a real eval harness, self-hosted observability, local inference on an RTX 5080, and a public deploy on a cheap VPS.**

> **Goal (meta):** Portfolio piece to move from game-systems / tool programming into a **Japan AI FDE / applied AI integration** role (LayerX / Stockmark / SB OAI Japan–style), built part-time within a **~45-hour budget**. One finished, deployed system beats a half-built multi-agent zoo.
>
> **Primary market:** Japan (bilingual EN/JP, Japanese company experience, customer-facing support background). Remote US/EU applied-AI is a secondary option after this wedge ships.

---

## What It Does

NexusDoc helps a support desk answer from product manuals instead of hunting through PDFs.

**Persona (interview story):** Mid-size 白物メーカー support center. Agents spend too long finding 手順 / error-code meaning in multi-language manuals. NexusDoc returns **cited answers** and short procedures grounded in the corpus.

**Input:**

- Curated set of **15–30 official manufacturer appliance manuals** (washer, fridge, AC, microwave, etc.)
- **English + Japanese** PDFs, downloaded legally from manufacturer support sites (no bulk scrapers)
- Prefer born-digital PDFs; document OCR gaps honestly when scans fail

**Output:**

- Cited Q&A answers (chunk → page / section)
- Short procedure summary (bullets → one-liner) when asked
- Optional structured JSON (model, error code, steps, sources)
- Thin chat UI with streamed, cited answers

**Problem:** Support staff search dense, bilingual manuals under time pressure. NexusDoc fuses **ingest + hybrid RAG + evals + observability + local + cloud deploy** into one measurable pipeline.

> **Why not arXiv / RFCs / “risk classification”:** Academic corpora and fake compliance tags do not match Japan FDE work (資料を読み解き、業務に落とす). Appliance manuals map to real support workflows and to the author’s on-site support / IT Manager background.

---

## Core Capabilities

| Capability | Implementation |
| --- | --- |
| Document ingestion | Manual PDF corpus; **PyMuPDF** → text + page metadata; skip/flag empty OCR pages |
| Hybrid retrieval | pgvector dense (**bge-m3** or nomic-embed-text-v2) + sparse → **bge-reranker-v2-m3** |
| Pipeline | **Single LangGraph (or linear) graph:** retrieve → generate (cited QA) → optional summarize → validate citations — **not** a multi-agent supervisor zoo |
| Evaluation | **RAGAS** (or DeepEval if CI is easier): faithfulness, context recall, answer relevancy; **15 curated EN+JP cases**; CI gate |
| Observability | **Langfuse** self-hosted via **official** docker compose (web + worker + Postgres + ClickHouse + Redis + MinIO); instrument with **Python SDK v3+** (`observe`, `start_as_current_observation`) |
| Model access | Provider registry: **Groq** (public/demo primary) + **Ollama on RTX 5080** (self-host) + OpenRouter only after **$10** credits if needed |
| Deploy | App on **Hetzner** (~€4–6/mo) calling Groq + Supabase; local Ollama stays on the workstation |

### Explicitly cut / deferred (do not touch before Sept apply window)

| Cut | Reason |
| --- | --- |
| Multi-agent supervisor + “risk” agent | Cargo-cult; one justified graph is stronger in design review |
| Redis + RedisVL semantic cache | Nice-to-have; not an FDE differentiator under time pressure |
| Guardrails AI / NeMo | Thin Pydantic/regex PII check only if needed; do not overclaim “safety” |
| Colab / rented GPU vLLM as the “deployment story” | RTX 5080 (Blackwell) + vLLM is a source-build landmine; Ollama is the honest self-host path |
| arXiv / RFC / SEC domains | Wrong story for Japan support-desk FDE |
| VLM / OCR pipeline / Prefect / TTS | Out of scope for ~45h |
| Graph RAG before hybrid+evals | Premature; optional after Phase 3 only — see roadmap note |

**Post-Sept optional:** vLLM on 5080 via WSL2 build-from-source; OCR pass; Redis cache; real Guardrails; tool-calling into a ticketing API; **Graph RAG** (see roadmap note below — only after hybrid vector RAG is solid).

---

## Architecture

### High-level flow

```
┌──────────────────────────────────────────────────────────────┐
│                     Support agent / demo UI                    │
│              (Streamlit — thin, vibe-coded)                    │
└────────────────────────────┬─────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────┐
│                    FastAPI (thin) + pipeline                   │
│  ingest manuals → chunk → embed → hybrid retrieve → rerank   │
│       → LLM cited answer / short procedure (+ validate)        │
└───────┬───────────────────────────────┬──────────────────────┘
        │                               │
        ▼                               ▼
┌───────────────────┐         ┌───────────────────────────────┐
│ pgvector          │         │ Model registry                │
│ (Supabase free)   │         │ Groq | Ollama(5080) | OR*     │
└───────────────────┘         └───────────────────────────────┘
        │
        ▼
┌───────────────────┐
│ Langfuse (local   │  *OpenRouter only after $10 lifetime
│ official compose) │    credits (else 50 RPD free cap)
└───────────────────┘

Public demo (Hetzner VPS):  App → Groq + Supabase
Local self-host story:      App → Ollama on RTX 5080
```

### Model serving (honest)

| Environment | LLM | Notes |
| --- | --- | --- |
| Public URL (Hetzner) | Groq free tier | VPS does **not** run the model; it calls APIs — this is normal production architecture |
| Local / interview laptop | Ollama on **RTX 5080 (16GB)** | Real self-host; wire as `SELF_HOST` / `ollama` provider |
| vLLM | **Deferred** | Blackwell consumer GPUs often need source builds; do not block Sept on CUDA |

ADR-002 documents: why Groq on VPS + Ollama locally; why vLLM was deferred; when you’d put inference in a customer VPC.

### Pipeline state (keep small)

```python
class DocumentState(TypedDict):
    doc_id: str
    source: str            # manufacturer / model / lang
    file_path: str
    chunks: list[DocumentChunk]

class QueryState(TypedDict):
    doc_ids: list[str] | None
    query: str
    lang: str              # "en" | "ja" | "auto"
    retrieval_result: dict | None
    answer: dict | None    # {text, citations, confidence}
    summary: dict | None   # optional {bullets, one_liner}
    errors: list[str]
```

---

## Cost Strategy

| Phase | Spend | What |
| --- | --- | --- |
| Until hello-RAG traced works | **$0** | Groq + local Ollama + Supabase free + Langfuse local |
| After E2E POC | **~$5–10 once** | Optional OpenRouter $10 → unlocks 1000 RPD on free models |
| Public demo | **~€4–6/mo** | Hetzner CX22 (or similar) for always-on URL |
| Avoid until needed | RunPod / paid GPU / Railway Hobby | No ROI vs Ollama on 5080 |

### Verified free / cheap limits (do not trust old notes)

| Component | Reality |
| --- | --- |
| Groq free | ~30 RPM / ~1k RPD per model — primary for demo |
| OpenRouter `:free` | **50 RPD** until ≥$10 lifetime credits; then 1000 RPD; failed requests still count |
| Supabase free | pgvector; **pauses after ~7 days idle** — wake before demos |
| Langfuse | MIT; official compose needs ClickHouse + Redis + MinIO + worker — **not** a single container |
| Hetzner | Paid small VPS; reliable Docker host |
| Local GPU | RTX 5080 16GB via Ollama (e.g. Qwen2.5 7B / Llama 3.1 8B class) |

---

## Tech Stack

| Category | Choice | Why |
| --- | --- | --- |
| Orchestration | LangGraph **or** plain functions → thin graph | Prefer one retrieve→generate graph; add LangGraph when state/branching needs it |
| Glue | LangChain only where it saves time (loaders/retrievers) | Do not wrap everything in LCEL for fashion |
| Vector store | pgvector on Supabase | Free, hybrid-capable |
| Embeddings / rerank | bge-m3 + bge-reranker-v2-m3 (local) | Solid open-weight baseline |
| Ingest | PyMuPDF + curated manual corpus | Japan-enterprise 資料 story |
| LLM | Groq + Ollama (5080) | Public vs self-host |
| Eval | RAGAS and/or DeepEval + CI | Measure before resume claims |
| Observability | Langfuse (official compose) | Traces from day one |
| Backend | FastAPI (thin) | REST surface for VPS |
| Frontend | Streamlit (vibe-coded) | Demo only |
| Deploy | Docker on Hetzner | Real SSH/Docker/firewall signal |
| CI | GitHub Actions + pytest | Eval gate on PRs |
| Testing | pytest + VCR.py | Offline unit tests |

---

## Resume-Ready Impact (honest language)

### Measured targets (targets until reproduced)

| Metric | Target | How |
| --- | --- | --- |
| Corpus | 15–30 EN+JP manuals | Integration tests |
| Eval set | 15 curated Q/A (both languages) | Golden set in repo |
| Faithfulness / context recall | Track honestly; no fake >90% | RAGAS/DeepEval |
| Latency | Trace p50/p95 in Langfuse | Demo queries |
| Deploy | Public HTTPS URL | Hetzner |

### Portfolio statements (defensible)

> Built NexusDoc — cited RAG over EN/JP appliance support manuals (hybrid pgvector + cross-encoder rerank), eval harness with CI gate, Langfuse tracing, and a public Docker deploy on a VPS that calls Groq while local inference runs via Ollama on an RTX 5080.

> Designed a provider-agnostic model registry (Groq / Ollama) with retry and rate-limit fallback; documented deploy split (app on Hetzner, vectors on Supabase, inference API vs local GPU) in ADRs.

> Wrote a short discovery brief for a fictional white-goods support desk (problem → constraints → wedge → success metrics) — the FDE motion, not only the stack.

**Do not claim:** “production multi-agent platform,” “self-served vLLM in production,” or “enterprise guardrails” unless true.

### How this maps to Japan FDE / applied AI roles

| JD signal | NexusDoc evidence |
| --- | --- |
| RAG / 資料活用 | Manual corpus + hybrid retrieve + citations |
| Evals / 精度 | Golden set + CI gate |
| Customer / 現場 | Discovery writeup + support-background narrative |
| Deploy / 本番 | Live Hetzner URL + Docker Compose |
| Self-host awareness | Ollama on 5080 + ADR on VPS vs GPU split |
| Bilingual | EN+JP corpus and eval cases |

---

## ~45-Hour Roadmap (part-time → Sept/Oct apply)

Compressed from the earlier 12-phase fantasy. Buffer ~5h for interview prep / resume outside build hours.

```
Phase 1 (~5h)  : Foundation — uv, registry (Groq+Ollama), Langfuse official compose, traced hello-RAG
Phase 2 (~6h)  : Corpus — 15–30 EN+JP manuals, PyMuPDF ingest, bge-m3 dense → pgvector (HNSW), empty-page handling
Phase 3 (~6h)  : Retrieval — hybrid (dense + sparse) + rerank + citations on Phase 2 rows
Phase 4 (~4h)  : Pipeline — single retrieve→generate→(optional summary) graph; structured citations
Phase 5 (~6h)  : Eval — 15 golden cases (EN+JP) + RAGAS/DeepEval + CI gate
Phase 6 (~3h)  : Local serve — Ollama on 5080 wired in registry; smoke vs Groq
Phase 7 (~5h)  : Deploy — Docker app on Hetzner → public URL (Groq + Supabase)
Phase 8 (~4h)  : Harden — reproduce metrics, 3–4 ADRs, discovery writeup, demo video, resume bullets
Phase 9 (~2h)  : UI polish — Streamlit chat + citations (vibe-coded, timebox hard)
                 ≈ 41h core + ~4h buffer
```

### Phase 1 — Foundation (~5h)

- Repo: `uv`, `pyproject.toml` (**editable install** so `scripts/` can `import app`), pre-commit, `.env.example`
- Registry: Groq + Ollama; **retry + 429 fallback** (may still be deferred until after hello-RAG)
- Langfuse: **official docker-compose** (Postgres + ClickHouse + Redis + MinIO + web + worker) — not a single-container hack
- Langfuse **Python SDK v3+** (verified against installed package; do not use removed APIs):
  - Smoke: `start_as_current_observation` + `flush()` (not `.trace()`)
  - App tracing: `from langfuse import observe, propagate_attributes` (not `langfuse.decorators`)
  - Generations: `start_as_current_observation(as_type="generation", …)` (not `.generation()` on a legacy trace)
- Hello-world traced RAG on one sample manual excerpt (`data/sample_docs/appliance_manual_excerpt.txt` + JP stub)
- **Deliverable:** one traced, cited-ish answer from an in-memory or single-doc store

### Phase 2 — Ingestion (~6h)

- Curate 15–30 manuals (EN+JP); document sources + licenses in `data/README.md`
- PyMuPDF → chunks + page + language metadata
- Dense embed with **bge-m3** (`vector(1024)`) + pgvector upsert (HNSW); flag near-empty pages
- **Deliverable:** CLI ingests EN and JP manuals into Supabase

### Phase 3 — Hybrid retrieval (~6h)

- Query-time dense retrieve on Phase 2 rows + sparse channel + rerank (`bge-reranker-v2-m3`)
- Citation plumbing (chunk → file → page)
- **Deliverable:** cited hybrid answers on real manuals

#### Optional extension — Graph RAG (after Phase 3, not a core phase)

**Do not** insert Graph RAG between Phase 1–3 or replace hybrid retrieval. Ship **vector (+ hybrid) RAG with citations** first.

**When it earns a slot:** multi-hop manual questions where edges matter more than chunk similarity alone — e.g. error code → linked procedure § → shared part number → safety note across pages/languages.

**How it would fit:** as a **retriever plugin** behind the same pipeline interface (`retrieve → generate → validate`), not a second product. Typical shape: entity/relation extract at ingest → graph store (e.g. Neo4j / Postgres recursive / lightweight NetworkX for demos) → graph-augmented or hybrid graph+vector retrieval → same Langfuse-traced generate path.

**Budget:** Post-Sept / stretch only unless a golden-set failure mode clearly needs multi-hop structure. Prefer documenting the miss in ADR-003 over boiling the ocean before evals (Phase 5).

### Phase 4 — Pipeline (~4h)

- One graph/pipeline: retrieve → generate → validate citations present  
  (**“graph” here = LangGraph / linear control flow**, not Graph RAG)
- Optional summarize node (same graph, not a second “agent”)
- Typed state, timeouts, clear errors
- **Deliverable:** end-to-end Q&A on a real error-code / procedure query

### Phase 5 — Eval (~6h)

- 15 golden cases spanning EN and JP
- RAGAS and/or DeepEval; separate judge model where needed
- GitHub Actions: fail PR on regression
- **Deliverable:** reproducible suite; CI green

### Phase 6 — Local serving (~3h)

- Ollama model on RTX 5080; registry `ollama` provider
- Side-by-side smoke: Groq vs Ollama on 3 golden questions
- ADR notes quality/latency tradeoff
- **Deliverable:** `DEFAULT_PROVIDER=ollama` answers from local GPU

### Phase 7 — Deploy (~5h)

- Dockerfile + compose for **app only** on Hetzner
- Secrets via env; HTTPS (Caddy or provider proxy)
- Point app at Groq + Supabase; wake Supabase before demos
- **Deliverable:** public URL recruiter can open

### Phase 8 — Harden + FDE artifacts (~4h)

- Reproduce metrics from clean checkout
- ADRs (below)
- **Discovery writeup** (1–2 pages): support-desk problem → constraints → wedge → metrics → week-1 questions
- 2–3 min demo video + resume bullets
- **Deliverable:** portfolio-ready repo

### Phase 9 — UI (~2h, hard timebox)

- Streamlit: query, language, citations, source snippets
- Stop when demoable

---

## Planned File Structure

```
nexusdoc/
├── README.md
├── DESIGN.md                       # this file — source of truth
├── docs/
│   ├── adr/
│   │   ├── ADR-001-provider-registry.md
│   │   ├── ADR-002-inference-deploy-split.md
│   │   ├── ADR-003-retrieval-reranking.md
│   │   └── ADR-004-eval-strategy.md
│   └── discovery-support-desk.md   # FDE discovery brief
├── plans/
├── app/
│   ├── ingestion/                  # pdf_parser, chunking, corpus_load
│   ├── rag/                        # embeddings, vector_store, hybrid, reranker
│   ├── pipeline/                   # retrieve → generate → validate (not multi-agent/)
│   ├── core/                       # config, model_registry, schemas
│   ├── eval/
│   ├── ui/                         # streamlit (vibe-coded)
│   └── main.py
├── tests/
├── data/
│   ├── manuals/                    # curated EN+JP PDFs (git-lfs or download script)
│   ├── sample_docs/                # tiny excerpts for Phase 1
│   └── test_cases/                 # 15 golden Q/A
├── docker-compose.yml              # Langfuse official stack (dev)
├── docker-compose.app.yml          # app for Hetzner
├── Dockerfile
├── pyproject.toml
└── .env.example
```

---

## Architecture Decision Records

- **ADR-001 — Provider registry:** Groq + Ollama; retry/429; cost of abstraction vs lock-in.
- **ADR-002 — Inference / deploy split:** Hetzner app → Groq; local Ollama on 5080; why not vLLM yet (Blackwell); when customer VPC would host inference.
- **ADR-003 — Hybrid retrieval + rerank:** bge-m3 + reranker; when rerank is not worth latency.
- **ADR-004 — Eval + CI gate:** RAGAS vs DeepEval; golden set bilingual; merge blocker.

---

## Document Domain (locked)

**Chosen:** Appliance / white-goods **support manuals**, EN + JP, curated 15–30 PDFs.

**Tasks:** cited troubleshooting Q&A; short procedure summaries.

**Out:** risk classification, arXiv, RFCs, SEC, datasheet-first corpus.

**Corpus rules:**

1. Official manufacturer downloads only (or clearly licensed research sets if used).
2. Record source URL + access date in `data/README.md`.
3. Prefer text-extractable PDFs; log OCR failures instead of silently embedding empty chunks.
4. Golden questions must be answerable from the checked-in corpus.

---

## Future Enhancements (post-MVP / post-Sept)

- OCR pass for scanned manuals
- vLLM on 5080 (WSL2 source build) if wheels improve
- Tool-calling into a fake ticketing API (stronger FDE signal than multi-agent chat)
- Redis semantic cache under free-tier pressure
- Multi-tenant / auth for a “customer” demo
- Thin cloud-native note: “same compose on customer VPC / Cloud Run”

---

## Transferable Skills (sell these)

| Background | Maps to |
| --- | --- |
| Game systems / tools | Pipelines, budgets, determinism, profiling → latency/cost/eval budgets |
| On-site support / IT Manager | Discovery, ambiguous tickets, stakeholder communication — **core FDE** |
| Bilingual EN/JP + Japan tech cos | Japan FDE / SI client work |
| Prior OpenAI API tools | Not a cold start; extend into RAG + evals + deploy |

Interview line: stack is necessary; **現場で問題を切り分けて届ける** is the differentiator.

---

## Development Principles

1. Provider abstraction for every LLM call; never hardcode Groq in agents.
2. Eval-driven: golden cases early; regressions block merge.
3. Observability from day one (Langfuse official stack).
4. Honest metrics and honest serving claims.
5. Free until POC; then small, justified spend (OpenRouter $10 and/or Hetzner).
6. Deep on RAG / evals / deploy; vibe-code UI and glue.
7. DESIGN.md + ADRs are source of truth — update before scope creeps back.
8. **No feature returns from the cut list before Sept without deleting something else.**

---

## Getting Started (Phase 1)

```bash
git clone <repo>
cd nexusdoc
cp .env.example .env          # GROQ_API_KEY; Ollama local
# Use official Langfuse compose (see langfuse docs / repo docker-compose.yml)
docker compose up -d
uv sync
uv run python -m app.main --query "How do I clear error E12?"
```

Public deploy (Phase 7): build app image → Hetzner → HTTPS → Groq + Supabase.

---

## Sources (verified 2026-07)

- Groq rate limits: <https://console.groq.com/docs/rate-limits>
- OpenRouter free limits (50 vs 1000 RPD): <https://openrouter.ai/pricing>
- Langfuse self-host (ClickHouse required): <https://langfuse.com/self-hosting>
- Langfuse official compose: <https://github.com/langfuse/langfuse/blob/main/docker-compose.yml>
- FDE hiring signals: <https://getperspective.ai/blog/2026-fde-hiring-trends-what-1000-job-posts-reveal>
- Japan FDE examples: LayerX <https://tech.layerx.co.jp/entry/ai-llm-fde>, Stockmark FDE JDs
- vLLM + RTX 50-series friction: <https://github.com/vllm-project/vllm/issues/35432>

---

*NexusDoc — manuals into cited support answers, measured and deployable.*
