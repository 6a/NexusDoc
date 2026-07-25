"""
Implements embedding logic
"""

from functools import lru_cache

import numpy as np
from sentence_transformers import SentenceTransformer

from app.core.config import settings


@lru_cache(maxsize=1)
def get_embedding_model() -> SentenceTransformer:
    return SentenceTransformer(settings.embedding_model)  # type: ignore[no-any-return]


def embed_texts(texts: list[str]) -> np.ndarray:
    """
    Embeds the given text as a L2 normalized float32 array of shape (len(text), embedding_dimension).
    L2 normalization is when you normalize the vector so that the magnitude is 1 (a unit vector).

    L2 normalization is required so pgvector cosine distance calculations are meaningful.
    """

    if not texts:
        return np.zeros((0, settings.embedding_dim), dtype=np.float32)

    model = get_embedding_model()

    vectors = model.encode(texts, batch_size=16, show_progress_bar=len(texts) > 16, normalize_embeddings=True)

    embeddings = np.asarray(vectors, dtype=np.float32)

    if embeddings.ndim != 2 or embeddings.shape[0] != len(texts) or embeddings.shape[1] != settings.embedding_dim:
        raise ValueError(f"Expected ({len(texts)}, {settings.embedding_dim}), got {embeddings.shape}")

    return embeddings
