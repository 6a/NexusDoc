-- Note: we are using "if not exists" guards to make this script idempotent. Does not alter columns if table already exists, do not create indexes if they already exist etc.
-- Creation of types uses an anonymous "do" block that discards "duplicate_object" exceptions as creation of a "type" doesn't support "if not exists".
-- Creation of triggers and functions use create or replace as recreating them is harmless and allows changes to the definition.

-- Postgres doesn't ship with a native vector type, so we need to enable the "pgvector" extension (which is confusingly named "vector").
-- Allows us to use types like extensions.vector(1024) to store vectors.
-- We install the vector extension's types/operators into the existing extensions schema.
-- See: https://supabase.com/docs/guides/database/extensions/pgvector.
create extension if not exists vector with schema extensions;

-- Create a custom enum type for language codes (single source of truth).
-- See: https://stackoverflow.com/questions/79938164/create-type-if-not-exists-in-postgres.
do $$
begin
  create type public.lang_code as enum ('en', 'ja', 'mixed', 'unknown');
exception
  when duplicate_object then null;
end $$;

-- Create a table called "documents" in the public schema.
-- This table stores metadata about the documents we index.
create table if not exists public.documents (
  id uuid primary key default gen_random_uuid(), -- Surrogate PK; random UUID (PG13+).
  source_path text not null unique, -- Repo-relative source file path; unique upsert key for re-ingest (ON CONFLICT).
  filename text not null, -- File name for display/citation etc.
  lang public.lang_code not null, -- Source file's language.
  manufacturer text, -- Official brand (optional).
  model text, -- Official product ID (optional).
  page_count int not null default 0, -- Number of pages in the source file. Gathered during ingest.
  empty_page_count int not null default 0, -- Pages skipped due to being fully or near-empty (no embed). Gathered during ingest.
  source_url text, -- The URL from which the source file was originally fetched (optional).
  accessed_on date, -- The date on which the source file was procured (optional).
  checksum_sha256 text, -- The Hex SHA-256 checksum of the source file's contents, for detecting changes. Gathered during ingest (optional).
  created_at timestamptz not null default now(), -- Timestamp of when the row was inserted.
  updated_at timestamptz not null default now() -- Timestamp of when the row was last updated (automatically updated by "documents_updated_at_trg" on upserts)
);

-- Lock down PostgREST/anon access. No policies yet = deny via API.
alter table public.documents enable row level security;

-- Create a table called "chunks" in the public schema.
-- This table stores content, embedding, and metadata for each embeddable text unit. Each row (chunk) is associated with its parent document via FK.
create table if not exists public.chunks (
  id uuid primary key default gen_random_uuid(), -- Surrogate PK; random UUID (PG13+).
  document_id uuid not null references public.documents (id) on delete cascade, -- FK to public.documents.id. Row gets deleted if parent is deleted due to ON DELETE CASCADE.
  chunk_index int not null, -- Index that represents the position of this chunk in its parent document. Used for sorting and deduplication.
  content text not null, -- Chunk text that was embedded; ingest must not insert empty strings.
  page_start int not null, -- Page number that the chunk starts on. Starts at 1.
  page_end int not null, -- Page number that the chunk ends on. Starts at 1.
  lang public.lang_code not null, -- The chunk's language.
  token_estimate int, -- Estimated size of the chunk in tokens, for logging, and budget analytics (optional).
  embedding extensions.vector(1024) not null, -- The dense vector embedding of the chunk's text. 1024 dimensions for bge-m3. Requires column and chunks_embedding_hnsw rebuild if vector dimension changes. Should be L2 normalized at encode time.
  embedding_model text not null default 'BAAI/bge-m3', -- The model used to generate the embedding; don't mix models in one search.
  created_at timestamptz not null default now(), -- Timestamp of when the row was inserted.
  unique (document_id, chunk_index) -- Unique constraint to ensure that each document only has one chunk per index number.
);

-- Lock down PostgREST/anon access. No policies yet = deny via API.
alter table public.chunks enable row level security;

-- Creates an index on the public.chunks.document_id column to speed up WHERE/DELETE by document_id.
-- A foreign key column doesn't always generate a standalone index, so we create it manually.
-- See: https://www.postgresql.org/docs/current/ddl-constraints.html.
create index if not exists chunks_document_id_idx
  on public.chunks (document_id);

-- Creates an index on the public.chunks.lang column to speed up WHERE by lang.
create index if not exists chunks_lang_idx
  on public.chunks (lang);

-- Creates an approximate nearest-neighbor (ANN) index over chunk embeddings (pgvector HNSW).
-- Speeds ORDER BY embedding <=> query_vector (cosine distance). Without it, Postgres scans every chunk row.
-- HNSW = graph of "nearby" vectors (approximate matches, not a B-tree exact lookup).
-- Safe to create on an empty table (unlike IVFFlat, which wants data first so clusters fit).
-- Opclass must match the query operator: vector_cosine_ops goes with <=> .
-- Embed with L2 normalization so cosine distance is meaningful.
-- See: https://supabase.com/docs/guides/ai/vector-indexes/hnsw-indexes
-- See: https://supabase.com/docs/guides/ai/going-to-prod#hnsw-understanding-efconstruction--efsearch--and-m
create index if not exists chunks_embedding_hnsw
  on public.chunks
  using hnsw (embedding vector_cosine_ops) -- Index embedding; optimize for cosine (<=>).
  with (m = 16, ef_construction = 64); -- m = links per node; ef_construction = build-time search effort (higher = better quality, slower/heavier build). 16 / 64 are the default values.

-- Shared helper function: Updates the "updated_at" column with the current timestamp.
create or replace function public.set_updated_at()
  returns trigger
  language plpgsql
  as $$
  begin
    new.updated_at = now();
    return new;
  end;
  $$;

-- Keep public.documents.updated_at current on every UPDATE.
-- CREATE OR REPLACE so re-running this script refreshes the trigger definition.
create or replace trigger documents_updated_at_trg
  before update on public.documents
  for each row
  execute function public.set_updated_at();