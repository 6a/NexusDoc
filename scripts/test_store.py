"""
Test the store functions.
"""

import numpy as np

from app.core.config import settings
from app.ingestion.chunking import DocumentChunk
from app.ingestion.language import Language
from app.ingestion.store import get_db_connection, replace_chunks, upsert_document

doc_id = upsert_document(
    source_path="data/manuals/en/_smoke_chunks.pdf",
    filename="_smoke_chunks.pdf",
    language=Language.ENGLISH,
    page_count=1,
    empty_page_count=0,
    chunks=[],
    embeddings=np.zeros((0, settings.embedding_dim), np.float32),
)
chunks = [
    DocumentChunk(content="hello washer", chunk_index=0, page_start=1, page_end=1, language=Language.ENGLISH, token_estimate=6),
    DocumentChunk(content="error code UE", chunk_index=1, page_start=1, page_end=1, language=Language.ENGLISH, token_estimate=6),
]
# unit-ish fake embeddings (not real model output — fine for DB plumbing)
emb = np.zeros((2, settings.embedding_dim), np.float32)
emb[0, 0] = 1.0
emb[1, 1] = 1.0
with get_db_connection() as conn:
    n = replace_chunks(conn, document_id=doc_id, chunks=chunks, embeddings=emb, embedding_model="test")
    n2 = replace_chunks(conn, document_id=doc_id, chunks=chunks[:1], embeddings=emb[:1], embedding_model="test")
    count = conn.cursor().execute("select count(*) from chunks where document_id = %s", (doc_id,)).fetchone()
    print(n, n2, count)
