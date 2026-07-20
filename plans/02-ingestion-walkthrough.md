# Phase 2 — Ingestion Walkthrough

> **Role:** Senior-dev-led tutorial for a system/tool programmer pivoting into Japan AI FDE / applied AI integration.
> **Estimated total time:** ~6 hours (`DESIGN.md` Phase 2)
> **Prerequisite:** Phase 1 complete (registry, Langfuse, hello-RAG on sample excerpts). Progress: [`01-foundation-walkthrough-progress.md`](01-foundation-walkthrough-progress.md)
> **Outcome:** Curated EN+JP appliance manuals → PyMuPDF parse → page-aware chunks → dense embed (`bge-m3`) → upsert into Supabase pgvector (HNSW) via a CLI. Empty / scan-failed pages flagged, not silently embedded.
>
> **📋 Progress tracking:** [`02-ingestion-walkthrough-progress.md`](02-ingestion-walkthrough-progress.md)
>
> **Verified against docs (2026-07):**
> - Supabase pgvector + HNSW: <https://supabase.com/docs/guides/ai/vector-indexes/hnsw-indexes>
> - Supabase connect (direct vs pooler ports): <https://supabase.com/docs/guides/database/connecting-to-postgres>
> - PyMuPDF (`import pymupdf`, not legacy `fitz`): <https://pymupdf.readthedocs.io/> / PyPI `pymupdf` 1.28.x
> - BGE-M3 dense dim **1024**: <https://huggingface.co/BAAI/bge-m3>
> - pgvector-python + psycopg3: <https://github.com/pgvector/pgvector-python>

---

## Before We Start — What You're Actually Building

Phase 1 proved retrieve→generate with an **in-memory** store and a toy excerpt. Phase 2 replaces the toy store with a real ingest path:

```
data/manuals/*.pdf
        │
        ▼
┌───────────────────────────────────────┐
│  app/ingestion/                       │
│  1. parse PDF (PyMuPDF) → pages       │
│  2. flag near-empty / OCR-gap pages   │
│  3. chunk (page-aware, EN+JP safe)    │
│  4. embed dense (BAAI/bge-m3, 1024d)  │
│  5. upsert → Supabase Postgres        │
└───────────────────┬───────────────────┘
                    ▼
┌───────────────────────────────────────┐
│  documents  +  chunks (pgvector HNSW) │
│  citation metadata: file, page, lang  │
└───────────────────────────────────────┘
```

**Deliverable (from `DESIGN.md`):** a CLI that ingests EN and JP manuals into Supabase.

**What this is not:** hybrid sparse retrieval, reranking, or the full Q&A graph. Those are Phase 3–4. You are building the **document / corpus pipeline** — the part Japan FDE interviews actually care about when they say “RAG.”

**Expert decisions (do not bikeshed these):**

| Decision | Choice | Why |
| --- | --- | --- |
| DB client | **`psycopg` (v3) + SQL**, not `vecs` / not PostgREST bulk | You own the schema, upserts, and indexes. Interviewers expect SQL fluency; `vecs` hides it. |
| Embedding model **now** | **`BAAI/bge-m3` → `vector(1024)`** | Dimension is locked once HNSW exists. MiniLM (384d) would force a painful migration in Phase 3. bge-m3 is multilingual (EN+JP). Sparse vectors wait for Phase 3. |
| Chunking | Page-aware recursive split ~**480 chars** with ~**10% overlap**, JP-aware separators | Pragmatic Phase 2 start (char-sized, JP-safe). Industry guides often quote ~400–512 **tokens** — tune in Phase 5. Page metadata is non-negotiable for citations. |
| Empty pages | Detect + **skip embed**; record in parse report | DESIGN rule: never silently embed OCR voids. |
| PDF storage | **Gitignore binaries**; catalog URLs in `data/README.md` | Legal + size. Resume story is the catalog, not 2 GB of PDFs in git. |
| OCR | **Out of scope** | On the DESIGN cut list. Flag scanned pages; do not build Tesseract. |

---

## Concepts — What You Need to Know Before Coding

*Skim if you already know these; the empty-page and citation-metadata parts are the ones people get wrong.*

### 1. Ingestion is a product surface, not a script

In game tools you already know this pattern: **import asset → validate → normalize → write to runtime store**. Document RAG is the same pipeline with uglier inputs.

| Game tool | RAG ingest |
| --- | --- |
| FBX import | PDF parse |
| Mesh validation (degenerate tris) | Empty-page / encoding checks |
| LODs / chunk streaming | Text chunking |
| GPU upload | Embedding + vector upsert |

FDEs who ship “RAG” without a disciplined ingest path ship **hallucination machines**. Your portfolio differentiator is: *we know which page the chunk came from, and we refused to index garbage.*

### 2. Why page metadata beats “smart” chunking theater

Citations in support workflows must answer: **which manual, which page, which language**. If your chunker throws away page boundaries, Phase 4 “cited answers” becomes fiction.

**Rule for this phase:** every stored chunk carries at least:

- `document_id` / source filename
- `page_start` / `page_end` (1-based, matching the PDF viewer)
- `lang` (`en` | `ja` | `mixed` | `unknown`)
- `char_count` / `is_empty` (for pages that failed extract)

Chunk *text* can overlap pages only when a section truly spans a page break — still record the page range.

### 3. pgvector + HNSW (what you actually need)

- **pgvector** = Postgres extension that adds a `vector(n)` column type and distance operators.
- **Cosine distance** operator: `<=>` (use with normalized embeddings; sentence-transformers / bge typically L2-normalize dense vecs).
- **HNSW** = approximate nearest-neighbor index. Supabase docs: *default choice* over IVFFlat for new builds; safe to create **before** data exists (unlike IVFFlat).

```sql
-- operator class must match how you query
create index on chunks using hnsw (embedding vector_cosine_ops);
```

Docs: <https://supabase.com/docs/guides/ai/vector-indexes/hnsw-indexes>

You will **not** build a fancy `match_documents` RPC yet unless you want a smoke query — Phase 3 owns retrieval. Phase 2 proves **rows land with correct metadata and non-null embeddings**.

### 4. Empty / scanned pages (the honesty rule)

Born-digital manuals: `page.get_text()` returns real text.  
Scanned image-only pages: extract returns `""` or whitespace — **embedding that yields a near-zero or noise vector that pollutes retrieval**.

Phase 2 policy:

1. Extract text per page.
2. If stripped length &lt; `EMPTY_PAGE_MIN_CHARS` (start at **40**), mark `is_empty=true`, log it, **do not chunk/embed**.
3. Record OCR gaps in the ingest report / `data/README.md` notes. OCR itself is post-Sept.

### 5. PyMuPDF license (interview honesty)

PyMuPDF is **AGPL-3.0** (or commercial from Artifex). For this **open portfolio repo**, AGPL is fine. If a customer later wants a closed SaaS, you either open-source the service under AGPL or buy a commercial license / swap parser. Say that out loud in interviews — it signals production judgment, not cargo-cult stack picking.

Use modern import:

```python
import pymupdf  # recommended; `fitz` is legacy alias
```

### 6. Supabase connection strings (Windows gotcha)

From [Supabase connecting docs](https://supabase.com/docs/guides/database/connecting-to-postgres) (post–2025 port clarification):

| Mode | Port | Use for Phase 2 |
| --- | --- | --- |
| Direct `db.<ref>.supabase.co` | 5432 | Fine if your network is IPv6 |
| **Session pooler** `*.pooler.supabase.com` | **5432** | **Prefer on Windows / IPv4-only** |
| Transaction pooler | **6543** | Serverless; disable prepared statements |

For a local CLI ingest worker: **session pooler** is the pragmatic default on consumer Windows.

Also remember: **Supabase free projects pause after insufficient DB activity over ~7 days** (not merely skipping the dashboard) — wake the project before demos (`DESIGN.md`).

---

## Prerequisites

### Accounts / infra

| Item | Action |
| --- | --- |
| **Supabase** project | Create free project if you have not. Dashboard → **Connect** → copy **Session pooler** URI. |
| **Database password** | Set/reset in Project Settings → Database. Put it only in `.env`, never in git. |
| Phase 1 stack | `uv`, Docker/Langfuse optional for this phase (ingest need not be traced yet; optional `@observe` is a nice-to-have). |

### Verify before coding

```powershell
uv --version
# Optional: confirm Phase 1 still works
uv run python scripts/verify_e2e_phase1.py
```

Wake Supabase if the project shows paused.

---

## Step 1 — Curate the corpus (~60–90 min)

**Goal:** Legal EN+JP manuals on disk + an honest catalog. You do **not** need all 15–30 PDFs before writing code — start with **≥2 EN + ≥2 JP** for the CLI smoke, then grow toward 15–30.

### 1.1 Rules (locked in `DESIGN.md`)

1. Official manufacturer support downloads only (or clearly licensed research sets — prefer OEM).
2. Record **source URL + access date** in `data/README.md`.
3. Prefer text-extractable PDFs; note scan-heavy files honestly.
4. Golden questions (Phase 5) must be answerable from this corpus — pick models you’ll actually query.

### 1.2 Suggested manufacturers (examples — pick what you can legally download)

White-goods / appliance support PDFs are commonly available from brands such as:

- Panasonic support
- Sharp
- Hitachi
- Toshiba
- Daikin (AC)
- Samsung / LG (often strong EN manuals)
- Whirlpool / GE / Electrolux (EN)

**Do not** bulk-scrape. Download like a support agent would: one product page → “Manual” / owner’s manual PDF.

Mix product types if possible (washer, fridge, microwave, AC) so error-code / procedure questions are diverse.

### 1.3 Layout on disk

```text
data/
├── README.md                 # catalog + licenses + access dates
├── manuals/
│   ├── en/
│   │   └── <brand>_<model>_<doc>.pdf
│   └── ja/
│       └── <brand>_<model>_<doc>.pdf
└── sample_docs/              # Phase 1 excerpts — keep
```

Add to `.gitignore` (if not already):

```gitignore
# Large / redistributable manuals — catalog lives in data/README.md
data/manuals/**/*.pdf
!data/manuals/**/.gitkeep
```

Create placeholder dirs:

```powershell
New-Item -ItemType Directory -Force data/manuals/en, data/manuals/ja | Out-Null
New-Item -ItemType File -Force data/manuals/en/.gitkeep, data/manuals/ja/.gitkeep | Out-Null
```

### 1.4 Write `data/README.md`

Use a table like this (fill with your real downloads):

```markdown
# NexusDoc corpus

Appliance / white-goods support manuals for RAG. **Not redistributed in git** — download from the URLs below.

| ID | Lang | Brand | Model / product | Filename | Source URL | Accessed | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| en-001 | en | … | … | `en/….pdf` | https://… | 2026-07-20 | born-digital |
| ja-001 | ja | … | … | `ja/….pdf` | https://… | 2026-07-20 | some scan pages? |

## License / use

Personal portfolio / research use of manufacturer-published support PDFs.
Do not claim redistribution rights. Respect each site’s terms.

## Ingest gaps

Document empty-page / OCR failures here after first ingest run.
```

### Step 1 checkpoint

- [ ] ≥2 EN + ≥2 JP PDFs under `data/manuals/{en,ja}/`
- [ ] `data/README.md` filled with URLs + dates
- [ ] PDFs gitignored; `.gitkeep` present
- [ ] You can open each PDF and see selectable text on most pages (spot-check)

---

## Step 2 — Dependencies + config (~20 min)

### 2.1 Add packages

Edit `pyproject.toml` dependencies — add:

```toml
  "pymupdf>=1.25.0",
  "psycopg[binary]>=3.2.0",
  "pgvector>=0.3.6",
```

Then:

```powershell
uv sync
# or, if you still use editable + optional dev extras the way Phase 1 did:
uv pip install -e ".[dev]"
```

Confirm:

```powershell
uv run python -c "import pymupdf, psycopg, pgvector; print(pymupdf.__doc__[:40] if pymupdf.__doc__ else 'ok', psycopg.__version__)"
```

### 2.2 Extend settings

Add to `app/core/config.py` (keep existing fields):

```python
    # Supabase / Postgres (Phase 2+)
    # URL / service key unused by Phase 2 ingest (psycopg uses supabase_db_url); keep for later API clients
    supabase_url: str = Field(default="", repr=False)
    supabase_service_key: str = Field(default="", repr=False)
    # Prefer Session pooler URI on Windows/IPv4 — copy verbatim from Dashboard → Connect
    supabase_db_url: str = Field(default="", repr=False)

    # Ingestion / embeddings
    embedding_model: str = Field(default="BAAI/bge-m3")
    embedding_dim: int = Field(default=1024)
    empty_page_min_chars: int = Field(default=40)
    chunk_size: int = Field(default=480)
    chunk_overlap: int = Field(default=48)
```

### 2.3 Extend `.env.example` / `.env`

```bash
# Supabase (Phase 2+)
# Optional in Phase 2 — ingest uses SUPABASE_DB_URL only; these are for later HTTP/API clients
SUPABASE_URL=
SUPABASE_SERVICE_KEY=
# Session pooler URI: copy verbatim from Dashboard → Connect (do not invent the host).
# Shape: postgresql://postgres.<project-ref>:<password>@aws-<region>.pooler.supabase.com:5432/postgres
# Real hosts vary (aws-0-…, aws-1-…, etc.) — paste what the dashboard gives you.
SUPABASE_DB_URL=

# Ingestion
EMBEDDING_MODEL=BAAI/bge-m3
EMBEDDING_DIM=1024
EMPTY_PAGE_MIN_CHARS=40
CHUNK_SIZE=480
CHUNK_OVERLAP=48
```

Copy values into `.env`. **Never commit `.env`.**

### Step 2 checkpoint

- [ ] Packages import cleanly
- [ ] `Settings` exposes `supabase_db_url` and embedding knobs
- [ ] You can connect with a one-liner (next step will use this)

Smoke connection (replace nothing if `.env` is loaded via Settings):

```powershell
uv run python -c "import psycopg; from app.core.config import settings; conn=psycopg.connect(settings.supabase_db_url); print(conn.execute('select 1').fetchone()); conn.close()"
```

If this fails with network / IPv6 errors, switch to the **Session pooler** URI from the dashboard.

---

## Step 3 — Schema + HNSW (~30 min)

**Goal:** Two tables — `documents` (one row per PDF) and `chunks` (embeddable units). Run SQL in the Supabase **SQL Editor**.

### 3.1 Enable pgvector

```sql
create extension if not exists vector
with schema extensions;
```

(Supabase often already has `vector` available; this is idempotent.)

### 3.2 Create tables

Use **1024** dimensions for bge-m3. Keep embeddings nullable only for empty-page bookkeeping rows if you store page stubs — prefer **not** inserting empty pages into `chunks` at all.

```sql
-- One row per ingested PDF
-- gen_random_uuid() is core Postgres since PG13 (no pgcrypto needed on Supabase)
create table if not exists public.documents (
  id uuid primary key default gen_random_uuid(),
  source_path text not null unique,          -- e.g. data/manuals/en/foo.pdf
  filename text not null,
  lang text not null check (lang in ('en', 'ja', 'mixed', 'unknown')),
  manufacturer text,
  model text,
  page_count int not null default 0,
  empty_page_count int not null default 0,
  source_url text,
  accessed_on date,
  checksum_sha256 text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Embeddable chunks with citation metadata
create table if not exists public.chunks (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references public.documents (id) on delete cascade,
  chunk_index int not null,
  content text not null,
  page_start int not null,
  page_end int not null,
  lang text not null check (lang in ('en', 'ja', 'mixed', 'unknown')),
  token_estimate int,
  embedding extensions.vector(1024) not null,
  embedding_model text not null default 'BAAI/bge-m3',
  created_at timestamptz not null default now(),
  unique (document_id, chunk_index)
);

create index if not exists chunks_document_id_idx on public.chunks (document_id);
create index if not exists chunks_lang_idx on public.chunks (lang);

-- HNSW for cosine distance (<=> / vector_cosine_ops)
-- Safe to create before bulk load (unlike IVFFlat).
-- Opclass: use unqualified vector_cosine_ops (matches Supabase docs); column type stays extensions.vector(...)
create index if not exists chunks_embedding_hnsw
  on public.chunks
  using hnsw (embedding vector_cosine_ops)
  with (m = 16, ef_construction = 64);
```

> **Why `extensions.vector`?** Supabase enables the type in the `extensions` schema. If your project resolves bare `vector(...)`, either form works — match what `create extension` used. Keep the **opclass** unqualified (`vector_cosine_ops`) unless search_path resolution fails.

> **Why not IVFFlat?** Supabase recommends HNSW for new work; IVFFlat needed a populated table to build well. See HNSW docs linked above.

### 3.3 Optional: save SQL in-repo

Create `app/ingestion/sql/001_init.sql` with the same statements so a clean checkout can re-run them. You still apply via SQL Editor (or `psycopg` later) — do not invent a migration framework in this phase.

### 3.4 Verify

```sql
select extname, extversion from pg_extension where extname = 'vector';

select table_name
from information_schema.tables
where table_schema = 'public'
  and table_name in ('documents', 'chunks');

select indexname from pg_indexes
where tablename = 'chunks';
```

### Step 3 checkpoint

- [ ] `vector` extension present
- [ ] `documents` + `chunks` exist
- [ ] HNSW index `chunks_embedding_hnsw` listed
- [ ] SQL checked into `app/ingestion/sql/001_init.sql`

---

## Step 4 — PDF parser + empty-page flagging (~45 min)

**Goal:** `app/ingestion/pdf_parser.py` — open PDF, yield per-page text + flags.

### 4.1 Directory scaffold

```text
app/ingestion/
  __init__.py
  pdf_parser.py
  chunking.py
  language.py
  embeddings.py
  store.py
  pipeline.py
  cli.py
  sql/
    001_init.sql
```

### 4.2 Language heuristic (keep it boring)

File: `app/ingestion/language.py`

Do **not** pull a heavy detector for v1. Heuristic:

- Count codepoints in Hiragana/Katakana/CJK Unified Ideographs ranges.
- If CJK ratio ≥ 0.08 → `ja`; if Latin letters dominate → `en`; if both significant → `mixed`; else `unknown`.

Document-level lang can be the majority of non-empty pages (or folder `en/` vs `ja/` as a prior — folder wins when you curated that way).

### 4.3 Parser sketch

File: `app/ingestion/pdf_parser.py`

```python
from __future__ import annotations

from dataclasses import dataclass

import pymupdf

from app.core.config import settings


@dataclass(frozen=True)
class PageText:
    page_number: int  # 1-based
    text: str
    char_count: int
    is_empty: bool


@dataclass(frozen=True)
class ParsedDocument:
    path: str
    page_count: int
    pages: list[PageText]
    empty_page_count: int


def parse_pdf(path: str, *, min_chars: int | None = None) -> ParsedDocument:
    threshold = settings.empty_page_min_chars if min_chars is None else min_chars
    pages: list[PageText] = []

    with pymupdf.open(path) as doc:
        for i, page in enumerate(doc):
            # sort=True → more natural reading order for multi-column layouts
            text = page.get_text("text", sort=True) or ""
            stripped = text.strip()
            char_count = len(stripped)
            pages.append(
                PageText(
                    page_number=i + 1,
                    text=stripped,
                    char_count=char_count,
                    is_empty=char_count < threshold,
                )
            )

    empty = sum(1 for p in pages if p.is_empty)
    return ParsedDocument(
        path=path,
        page_count=len(pages),
        pages=pages,
        empty_page_count=empty,
    )
```

> **API note:** Current PyMuPDF docs recommend `import pymupdf` and `page.get_text(...)`. Prefer verifying against the installed package (`uv run python -c "import pymupdf; help(pymupdf.Page.get_text)"`) if anything drifts.

### 4.4 Unit-ish smoke

```powershell
uv run python -c "from app.ingestion.pdf_parser import parse_pdf; p=parse_pdf('data/manuals/en/YOUR_FILE.pdf'); print(p.page_count, p.empty_page_count); print(p.pages[0].text[:200])"
```

### Step 4 checkpoint

- [ ] Parser returns 1-based pages
- [ ] Empty pages flagged on a known scan or blank page (or artificially with a high threshold once)
- [ ] No OCR code introduced

---

## Step 5 — Chunking with page + language metadata (~45 min)

**Goal:** Replace Phase 1’s naive Latin sentence splitter with something that works for **JP** manuals too.

### 5.1 Why Phase 1’s splitter is wrong for JP

```python
re.split(r"(?<=[.!?])\s+", text)  # breaks JP sentence punctuation; ignores page boundaries
len(sentence.split())             # whitespace "words" are a poor signal for JP
```

Phase 1 already left a TODO in `pipeline.py`. **Do not “fix” the Phase 1 in-memory path yet** unless you have spare time — build the new chunker under `app/ingestion/chunking.py` and use it from the ingest CLI.

### 5.2 Strategy (locked for Phase 2)

1. Concatenate **non-empty** pages with explicit markers *or* chunk **per page first**, then split long pages.
2. Prefer **per-page chunking** for citation clarity: each chunk’s `page_start == page_end` unless you deliberately merge a short remainder.
3. Within a page, recursive split on separators (include JP full-stop / comma via Unicode escapes so the chunker works on JP manuals):

   ```python
   SEPARATORS = [
       "\n\n",
       "\n",
       "\u3002",  # ideographic full stop
       ". ",
       "\u3001",  # ideographic comma
       " ",
       "",
   ]
   ```

4. Size by **characters** (not whitespace words): `chunk_size≈480`, `overlap≈48` (~10%). This is a pragmatic JP-safe Phase 2 default — common RAG guides quote similar ranges in **tokens**, not chars. Revisit after Phase 5 evals.
5. Skip empty pages entirely.

### 5.3 Data model

```python
@dataclass(frozen=True)
class DocumentChunk:
    content: str
    chunk_index: int
    page_start: int
    page_end: int
    lang: str
    token_estimate: int  # len(content) // 2 is a fine crude estimate for now
```

### 5.4 Implement `chunk_pages(pages: list[PageText], lang: str) -> list[DocumentChunk]`

Requirements:

- Deterministic order
- No empty `content`
- Stable `chunk_index` from 0..n-1
- Overlap only within the same page (simpler citations)

### Step 5 checkpoint

- [ ] EN manual produces multiple chunks with correct `page_start`
- [ ] JP manual produces chunks (not one giant blob / not zero chunks)
- [ ] Empty pages contribute **zero** chunks

---

## Step 6 — Embed + upsert (~60 min)

### 6.1 Embeddings module

File: `app/ingestion/embeddings.py`

Use `sentence_transformers.SentenceTransformer` with `BAAI/bge-m3` (already in deps from Phase 1).

```python
from functools import lru_cache

import numpy as np
from sentence_transformers import SentenceTransformer

from app.core.config import settings


@lru_cache(maxsize=1)
def get_embedding_model() -> SentenceTransformer:
    return SentenceTransformer(settings.embedding_model)


def embed_texts(texts: list[str]) -> np.ndarray:
    model = get_embedding_model()
    # normalize_embeddings=True → cosine via <=> is meaningful
    vectors = model.encode(
        texts,
        batch_size=16,
        show_progress_bar=len(texts) > 16,
        normalize_embeddings=True,
    )
    arr = np.asarray(vectors, dtype=np.float32)
    if arr.ndim != 2 or arr.shape[1] != settings.embedding_dim:
        raise ValueError(f"Expected (*, {settings.embedding_dim}), got {arr.shape}")
    return arr
```

**First run:** model download is ~2–3 GB (weights ≈2.27 GB plus HF cache). Use `HF_TOKEN` if you hit Hub rate limits (already in `.env.example`).

> **Phase 3 note:** Sparse / ColBERT channels from bge-m3 (via FlagEmbedding) come later. Dense-only is correct for Phase 2.

### 6.2 Store module

File: `app/ingestion/store.py`

Patterns to follow ([pgvector-python](https://github.com/pgvector/pgvector-python)):

```python
import psycopg
from pgvector.psycopg import register_vector
from pgvector import Vector

conn = psycopg.connect(settings.supabase_db_url)
register_vector(conn)
```

**Upsert document** by `source_path` (`ON CONFLICT (source_path) DO UPDATE … RETURNING id`).

**Replace chunks on re-ingest:** simplest correct approach for a portfolio CLI:

1. Upsert `documents` row.
2. `DELETE FROM chunks WHERE document_id = %s`.
3. `executemany` / multi `INSERT` for new chunks.

(Fancy per-chunk upserts are unnecessary until docs change often.)

Insert embedding as `Vector(embedding.tolist())` or let `register_vector` adapt a list — match the pgvector-python example for your installed version.

### 6.3 Pipeline orchestration

File: `app/ingestion/pipeline.py`

```text
parse_pdf → detect lang → chunk_pages → embed_texts → upsert document+chunks → return IngestReport
```

`IngestReport` should print:

- pages total / empty skipped
- chunks written
- document id
- elapsed seconds

Optional: wrap with Langfuse `@observe(name="ingest_document")` — nice continuity from Phase 1, not required for the deliverable.

### Step 6 checkpoint

- [ ] Embedding shape `(n, 1024)`
- [ ] Re-running ingest on the same file replaces chunks (no duplicates)
- [ ] Supabase Table Editor shows rows in `documents` and `chunks`

---

## Step 7 — CLI: ingest EN + JP (~45 min)

**Goal:** One entrypoint a recruiter-speed demo can run.

### 7.1 CLI

File: `app/ingestion/cli.py` (or `scripts/ingest_manuals.py` — either is fine; prefer `python -m app.ingestion.cli` if package layout cooperates).

Suggested interface:

```text
uv run python -m app.ingestion.cli --path data/manuals/en/foo.pdf
uv run python -m app.ingestion.cli --dir data/manuals/en --lang en
uv run python -m app.ingestion.cli --dir data/manuals/ja --lang ja
uv run python -m app.ingestion.cli --all
```

Flags:

- `--path` single file
- `--dir` directory of PDFs
- `--lang` override (`en`|`ja`) when folder convention is used
- `--all` both `en/` and `ja/`
- `--dry-run` parse+chunk only (no embed/DB) for fast validation

Use `argparse` (stdlib). No Click/Typer unless you already want it.

### 7.2 Run for real

```powershell
# Dry-run first
uv run python -m app.ingestion.cli --all --dry-run

# Full ingest (first bge-m3 download may take a while)
uv run python -m app.ingestion.cli --all
```

### 7.3 SQL smoke (retrieval preview — not Phase 3)

In SQL Editor, after ingest:

```sql
select d.filename, d.lang, d.page_count, d.empty_page_count, count(c.id) as chunks
from documents d
left join chunks c on c.document_id = d.id
group by d.id
order by d.lang, d.filename;
```

Optional nearest-neighbor sanity (pick any chunk embedding as query):

```sql
select c.content, c.page_start, d.filename
from chunks c
join documents d on d.id = c.document_id
order by c.embedding <=> (
  select embedding from chunks limit 1
)
limit 5;
```

You should see same-document neighbors — proves HNSW + vectors are alive.

### Step 7 checkpoint

- [ ] CLI ingests at least one EN and one JP PDF end-to-end
- [ ] Empty pages reflected in `documents.empty_page_count`
- [ ] Counts in SQL match the CLI report
- [ ] `data/README.md` updated with any OCR/empty-page notes

---

## Phase 2 — Final Verification

Create `scripts/verify_e2e_phase2.py` that:

1. Loads Settings; fails clearly if `SUPABASE_DB_URL` missing.
2. Connects; `select count(*)` from `documents` / `chunks` — asserts ≥1 EN and ≥1 JP document (by `lang` or path).
3. Asserts every chunk has `page_start >= 1`, `length(content) > 0`, and embedding dimension 1024 (via `vector_dims(embedding)`).
4. Optionally runs one `<=>` query.

```powershell
uv run python scripts/verify_e2e_phase2.py
```

### Final checklist

- [ ] ≥2 EN + ≥2 JP manuals cataloged; target path to 15–30 documented
- [ ] PyMuPDF parse + empty-page flags working
- [ ] Chunks carry page + lang metadata
- [ ] Supabase `documents` / `chunks` populated; HNSW index present
- [ ] CLI ingest works for EN and JP
- [ ] `verify_e2e_phase2.py` green
- [ ] `ruff check .` / `mypy app/` clean on new modules
- [ ] Git commit: Phase 2 ingestion (schema SQL, parser, chunker, embed, CLI) — **no PDFs, no secrets**

---

## What You Actually Learned

| Skill | Where | Why FDE / AI integration roles care |
| --- | --- | --- |
| **Corpus hygiene** | `data/README.md`, legal downloads | Japan applied-AI / document-use work starts with provenance, not prompts |
| **PDF extract realism** | empty-page flags | Production RAG fails quietly on scans without this |
| **Citation-ready chunking** | page_start/end + lang | Support-desk answers without sources are unusable |
| **pgvector schema + HNSW** | SQL + upsert | Default 2026 Postgres vector stack; you can explain operators |
| **Dimension lock / model choice** | bge-m3 @ 1024 | Migrating embedding dims is a production incident — you avoided it |
| **Ops reality** | pooler vs direct, pause-on-idle | Deploy engineers hit this on day one with Supabase free tier |

---

## What's Next (Phase 3 Preview)

Phase 3 turns the store into **hybrid retrieval**:

- Sparse channel (bge-m3 sparse and/or lexical) + dense
- Cross-encoder rerank (`bge-reranker-v2-m3`)
- Citation plumbing into answers on **real** manuals

Your Phase 2 tables and metadata should not be thrown away — retrieval reads `chunks.content` + page fields you just stored.

**Graph RAG** remains an optional extension *after* hybrid works (`DESIGN.md`) — do not insert it here.

---

## If You Get Stuck

1. **`connection refused` / timeout to `db.*.supabase.co`:** Use **Session pooler** (`*.pooler.supabase.com:5432`). Direct is often IPv6-only.
2. **`password authentication failed`:** Reset DB password in Supabase; update `SUPABASE_DB_URL`. URL-encode special characters in the password.
3. **`type "vector" does not exist`:** Run `create extension vector with schema extensions;` and qualify as `extensions.vector(1024)`.
4. **HNSW create fails on dim &gt; 2000:** Not your problem at 1024. If you ever use huge dims, see halfvec in Supabase HNSW docs.
5. **bge-m3 download / OOM:** Close other GPU apps; sentence-transformers can run on CPU (slow but fine for 15–30 manuals). Set `CUDA_VISIBLE_DEVICES=` to force CPU if the GPU path misbehaves on Blackwell drivers.
6. **JP chunks empty:** You still split on spaces only — include ideographic full stop / comma (`\u3002` / `\u3001`) in separators and size by characters.
7. **Duplicate chunks after re-ingest:** Ensure delete-by-`document_id` before insert, or unique `(document_id, chunk_index)` upsert.
8. **Project paused:** Open Supabase dashboard and wake the project before demos.
9. **AGPL questions in interview:** Portfolio OSS + honest “commercial license or swap parser for closed SaaS” is the correct answer.

---

*Phase 2 complete when EN and JP manuals are in pgvector with honest page metadata. That is the foundation every later “cited answer” claim stands on.*
