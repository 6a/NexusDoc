"""
Implements the storage backend for documents and their associated embeddings + chunks.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date
from typing import Any
from uuid import UUID

import numpy as np
import psycopg
from pgvector.psycopg import register_vector

from app.core.config import settings
from app.ingestion.chunking import DocumentChunk
from app.ingestion.language import Language
from app.ingestion.sql.template import SQL_TEMPLATE_DELETE_CHUNKS_FOR_DOCUMENT, SQL_TEMPLATE_INSERT_CHUNK, SQL_TEMPLATE_UPSERT_DOCUMENT


@contextmanager
def get_db_connection() -> Iterator[psycopg.Connection]:
    """
    Opens and returns a short-lived DB connection with pgvector adapters registered.

    Use in a with statement, handles rollback and cleanup after use.
    """

    if not settings.supabase_db_url:
        raise RuntimeError("SUPABASE_DB_URL is not set")

    db_connection = psycopg.connect(settings.supabase_db_url)

    try:
        register_vector(db_connection)

        yield db_connection

        db_connection.commit()
    except Exception:
        db_connection.rollback()
        raise
    finally:
        db_connection.close()


def upsert_document(
    *,
    source_path: str,
    filename: str,
    language: Language,
    page_count: int,
    empty_page_count: int,
    chunks: list[DocumentChunk],
    embeddings: np.ndarray,
    manufacturer: str | None = None,
    model: str | None = None,
    source_url: str | None = None,
    accessed_on: date | None = None,
    checksum_sha256: str | None = None,
) -> UUID:
    """
    Upserts a document, and its associated chunks + embeddings into the storage backend.

    Currently only upserts the document row - chunks and embeddings to be added later.
    """

    with get_db_connection() as db_connection:
        row = db_connection.execute(
            SQL_TEMPLATE_UPSERT_DOCUMENT,
            {
                "source_path": source_path,
                "filename": filename,
                "lang": language,
                "manufacturer": manufacturer,
                "model": model,
                "page_count": page_count,
                "empty_page_count": empty_page_count,
                "source_url": source_url,
                "accessed_on": accessed_on,
                "checksum_sha256": checksum_sha256,
            },
        ).fetchone()

    assert row is not None

    # Have to validate the type of row[0] as it is not typed in the returned row.
    document_id = row[0]
    if not isinstance(document_id, UUID):
        raise TypeError(f"expected UUID, got {type(document_id)}")

    return document_id


def replace_chunks(db_connection: psycopg.Connection, *, document_id: UUID, chunks: list[DocumentChunk], embeddings: np.ndarray, embedding_model: str | None = None) -> int:
    """
    Deletes existing chunks for the specified document, and inserts new ones.

    Returns the number of rows inserted into the chunks table.
    """

    if embeddings.shape != (len(chunks), settings.embedding_dim):
        raise ValueError(f"Embedding shape mismatch. Expected ({len(chunks)}, {settings.embedding_dim}). Actual: {embeddings.shape}")

    db_connection.execute(SQL_TEMPLATE_DELETE_CHUNKS_FOR_DOCUMENT, {"document_id": document_id})

    chunk_data: list[dict[str, Any]] = []

    embedding_model = embedding_model or settings.embedding_model

    for chunk_idx, chunk in enumerate[DocumentChunk](chunks):
        if chunk.content == "" or chunk.content.isspace():
            raise ValueError(f"Chunk #{chunk.chunk_index} is empty or only contains whitespace")

        chunk_data.append(
            {
                "document_id": document_id,
                "chunk_index": chunk.chunk_index,
                "content": chunk.content,
                "page_start": chunk.page_start,
                "page_end": chunk.page_end,
                "lang": chunk.language.value,
                "token_estimate": chunk.token_estimate,
                "embedding": embeddings[chunk_idx].tolist(),
                "embedding_model": embedding_model,
            }
        )

    with db_connection.cursor() as cursor:
        cursor.executemany(SQL_TEMPLATE_INSERT_CHUNK, chunk_data)

    return len(chunk_data)
