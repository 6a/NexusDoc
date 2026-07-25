# Phase 2 — Progress Tracker

> Updated as steps are completed. Check this file before resuming a session.
>
> **Scope:** Corpus curation → PyMuPDF ingest → page-aware chunking → bge-m3 dense embed → Supabase pgvector (HNSW).
> **Walkthrough:** [`02-ingestion-walkthrough.md`](02-ingestion-walkthrough.md)
> **Source of truth:** `DESIGN.md` Phase 2 (~6h)
>
> **Prerequisite:** Phase 1 foundation complete ([`01-foundation-walkthrough-progress.md`](01-foundation-walkthrough-progress.md)).

**Started:** 2026-07-20
**Last session:** 2026-07-25 (Steps 1–4 complete; resume at Step 5)
**Last commit:** none this session (leave working tree as-is)

---

## Step 1 — Corpus curation (~60–90 min)

| # | Task | Status | Notes |
| --- | ------ | -------- | ------- |
| 1.1 | Corpus rules understood | ✅ | Official OEM downloads; URL + date in catalog |
| 1.2 | `data/manuals/{en,ja}/` + gitignore PDFs | ✅ | PDF-only ignore; `.gitkeep` present |
| 1.3 | ≥2 EN + ≥2 JP PDFs downloaded | ✅ | 4 EN + 3 JP |
| 1.4 | `data/README.md` catalog | ✅ | URLs, dates, notes, license, ingest gaps |

**Step 1 complete:** ✅

---

## Step 2 — Dependencies + config (~20 min)

| # | Task | Status | Notes |
| --- | ------ | -------- | ------- |
| 2.1 | Add `pymupdf`, `psycopg[binary]`, `pgvector` | ✅ | psycopg 3.3.4, pymupdf 1.28.0 |
| 2.2 | Extend `Settings` (`supabase_db_url`, embed/chunk knobs) | ✅ | bge-m3 / 1024 / chunk 480·48 / empty≥40 |
| 2.3 | `.env.example` + `.env` updated | ✅ | Session pooler; smoke `(1,)` |
| — | `psycopg.connect(settings.supabase_db_url)` smoke | ✅ | |

**Step 2 complete:** ✅

---

## Step 3 — Schema + HNSW (~30 min)

| # | Task | Status | Notes |
| --- | ------ | -------- | ------- |
| 3.1 | `create extension vector with schema extensions` | ✅ | pgvector 0.8.2 |
| 3.2 | `documents` + `chunks` tables (`vector(1024)`) | ✅ | + `lang_code` enum; RLS on (no policies) |
| 3.3 | HNSW `vector_cosine_ops` index | ✅ | m=16, ef_construction=64; + updated_at trigger |
| 3.4 | SQL saved in-repo | ✅ | `app/ingestion/sql/001_init.sql` + `app/ingestion/sql/002_verify.sql` |

**Step 3 complete:** ✅

---

## Step 4 — PDF parser + empty pages (~45 min)

| # | Task | Status | Notes |
| --- | ------ | -------- | ------- |
| 4.1 | `app/ingestion/` package scaffold | ✅ | `__init__.py` + `sql/` |
| 4.2 | `language.py` heuristic | ✅ | `Language` StrEnum; path prior en/ja only |
| 4.3 | `pdf_parser.py` (`import pymupdf`, `get_text(sort=True)`) | ✅ | |
| 4.4 | Empty-page flag (`EMPTY_PAGE_MIN_CHARS`) | ✅ | forced 999999 → all empty |
| — | Smoke parse one EN + one JP PDF | ✅ | LG 52/2 empty; Hitachi+Panasonic 0 empty |

**Step 4 complete:** ✅

---

## Step 5 — Chunking (~45 min)

| # | Task | Status | Notes |
| --- | ------ | -------- | ------- |
| 5.1 | `chunking.py` page-aware + JP separators | ⬜ | char size ~480 / overlap ~48 |
| 5.2 | `DocumentChunk` with page_start/end + lang | ⬜ | |
| 5.3 | Empty pages → zero chunks | ⬜ | |
| — | Spot-check EN + JP chunk counts | ⬜ | |

**Step 5 complete:** ⬜

---

## Step 6 — Embed + upsert (~60 min)

| # | Task | Status | Notes |
| --- | ------ | -------- | ------- |
| 6.1 | `embeddings.py` — `BAAI/bge-m3`, dim 1024, normalized | ⬜ | First download ~2–3 GB |
| 6.2 | `store.py` — register_vector, upsert doc, replace chunks | ⬜ | |
| 6.3 | `pipeline.py` — parse→chunk→embed→upsert + report | ⬜ | Langfuse optional |
| — | Rows visible in Supabase Table Editor | ⬜ | |

**Step 6 complete:** ⬜

---

## Step 7 — CLI + EN/JP ingest (~45 min)

| # | Task | Status | Notes |
| --- | ------ | -------- | ------- |
| 7.1 | `cli.py` (`--path` / `--dir` / `--all` / `--dry-run`) | ⬜ | |
| 7.2 | Dry-run `--all` | ⬜ | |
| 7.3 | Full ingest EN + JP | ⬜ | |
| 7.4 | SQL group-by counts + optional `<=>` smoke | ⬜ | |
| 7.5 | Update `data/README.md` ingest gaps | ⬜ | |

**Step 7 complete:** ⬜

---

## Final verification

| # | Task | Status | Notes |
| --- | ------ | -------- | ------- |
| — | `scripts/verify_e2e_phase2.py` | ⬜ | ≥1 EN + ≥1 JP; dims; pages |
| — | `ruff check .` | ⬜ | |
| — | `mypy app/` | ⬜ | |
| — | Commit (no PDFs / no secrets) | ⬜ | |

**Phase 2 complete:** ⬜

---

## Pending / deferred (do not sneak in)

| Item | When |
| --- | --- |
| Sparse embeddings / hybrid retrieve / rerank | Phase 3 |
| LangGraph pipeline / cited generate | Phase 4 |
| OCR / Tesseract | Post-Sept (DESIGN cut list) |
| Graph RAG | After Phase 3 only, if evals need multi-hop |
| `vecs` client / Redis / Guardrails | Out of scope |
| OpenRouter + $10 credits | After E2E POC if needed |
| Embedding model swap away from bge-m3 | Avoid — dim lock; document ADR if forced |

---

## Session notes

### 2026-07-25 — Steps 3–4

- **Step 3:** Schema + HNSW; `app/ingestion/sql/001_init.sql` + `002_verify.sql`. vector 0.8.2; `lang_code` enum; RLS on; `updated_at` trigger.
- **Step 4:** `language.py` + `pdf_parser.py`. EN LG: 52 pages / 2 empty. JP Hitachi: 36/0 (catalog “maybe scanned” was wrong — born-digital). Panasonic: 63/0. Forced `min_chars=999999` → 52/52.
- **Resume next:** Step 5 — page-aware chunking + JP separators.
- **Git:** no commit this session unless asked.

### 2026-07-20 — Steps 1–2

- **Done:** Step 1 (corpus) + Step 2 (deps, Settings, env, DB smoke).
- Corpus: 4 EN + 3 JP under `data/manuals/{en,ja}/`; catalog in `data/README.md` (URLs, dates, notes, license, ingest gaps). PDFs gitignored.
- Deps: `pymupdf` 1.28.0, `psycopg` 3.3.4, `pgvector`. IDE must use `.\.venv\Scripts\python.exe`.
- Config: `supabase_db_url` + ingest knobs in `Settings`; `.env` has session pooler URI + optional `SUPABASE_URL` / `sb_secret_…` service key.
- Smoke: `psycopg.connect` → `(1,)`.
- **Git:** no commit this session; leave working tree uncommitted.
- Notes: images/OCR out of scope; no framework over raw `psycopg` for ingest; catalog automation deferred.
