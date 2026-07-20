"""
Minimal RAG pipeline for phase 1 of the project.

Simple by design: In-memory, no pgvector, no reranker - we will add these in phases 2-3.
The goal here is to prove the full pipeline works end-to-end with tracing, so every future phase inherits working observability.
"""

import re
from dataclasses import dataclass, field

import langfuse
import numpy as np
from dotenv import load_dotenv
from langfuse import Langfuse, propagate_attributes
from sentence_transformers import SentenceTransformer

from app.core.config import settings
from app.core.model_registry import get_provider
from app.core.providers.base import ChatMessage, Role

_langfuse: Langfuse | None = None


def get_langfuse() -> Langfuse:
    """
    Get the Langfuse client. Creates a new one if it doesn't exist.
    """
    global _langfuse

    if _langfuse is None:
        _langfuse = Langfuse(secret_key=settings.langfuse_secret_key, public_key=settings.langfuse_public_key, host=settings.langfuse_host)

    return _langfuse


def chunk_text(text: str, chunk_size: int = 300, overlap: int = 50) -> list[str]:
    """
    Split text into overlapping chunks by sentence boundaries.
    """

    # This is currently naiive and only really handles latin-based scripts with spaces as word boundaries.
    # TODO: Switch to structured chunking later (phase 2+).
    sentences: list[str] = re.split(r"(?<=[.!?])\s+", text)

    # Finished chunks, as a list of strings that represent sentences.
    chunks: list[str] = []

    # Current chunk, as a list of sentences.
    current_chunk: list[str] = []

    # The number of words in the current chunk.
    current_chunk_word_count: int = 0

    for sentence in sentences:
        # This only really works for scripts that use spaces as word boundaries.
        words = len(sentence.split())

        # If adding this sentence would exceed the chunk size, and the current chunk already contains sentences, add the current chunk to the list of chunks and start a new chunk.
        # Otherwise, just add the sentence to the current chunk.
        if (current_chunk_word_count + words) > chunk_size and current_chunk:
            # Add the current chunk to the list of chunks - with each sentence joined by a space.
            chunks.append(" ".join(current_chunk))

            # Naiive implementation for grabbing some text from the end of the current chunk to use as a prefix for the next chunk.
            # TODO: Switch to a more robust implementation later (phase 2+).
            overlap_text: str = " ".join(current_chunk[-max(1, overlap // 10) :])

            # Start a new chunk with the overlap text as a prefix, and the current sentence as the first sentence.
            # If there is no overlap text, just use the current sentence as the first sentence.
            current_chunk = [overlap_text, sentence] if overlap_text else [sentence]

            # Update the number of words in the current chunk.
            current_chunk_word_count = len(overlap_text.split()) + words if overlap_text else words

        else:
            current_chunk.append(sentence)
            current_chunk_word_count += words

    # Once all the sentences have been processed, if the current chunk contains sentences, add it to the list of chunks.
    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks


class Embedder:
    """
    The embedding model

    Currently using a lightweight local model: all-MiniLM-L6-v2 - ~80MB, 384 dimensions, runs on CPU.
    TODO: Switch to a more powerful model (bge-m3 etc.), and/or configure it to run on GPU.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        print(f"Initializing embedding model: {model_name}")
        self._model = SentenceTransformer(model_name)

    def embed(self, texts: list[str]) -> np.ndarray:
        return np.asarray(self._model.encode(texts, show_progress_bar=False, convert_to_numpy=True))


class InMemoryVectorStore:
    """
    Basic in-memory vector store.

    Currently only supports one document at a time.

    TODO: Implement multi-document support.
    """

    def __init__(self, embedder: Embedder) -> None:
        self._embedder = embedder
        self._chunks: list[str] = []
        self._vectors: np.ndarray | None = None

    @property
    def chunk_count(self) -> int:
        """
        The number of chunks in the vector store.
        """

        return len(self._chunks)

    @langfuse.observe(name="index_document")
    def set_document(self, text: str) -> None:
        """
        Add a document to the vector store.
        """

        self._chunks = chunk_text(text)
        self._vectors = self._embedder.embed(self._chunks)

    @langfuse.observe(name="vector_search")
    def search(self, query: str, top_k: int = 3) -> list[tuple[str, float]]:
        """
        Find the top-k most similar chunks to the query.
        """

        if self._vectors is None:
            return []

        # Generate a vector from the query text.
        # Embed expects a list of strings: ndarray shape (n, D) --> One query: (1, D)
        #   * n is the number of inputs; in this case the entire query is treated as a single input
        #   * D is the dimension of the embedding model
        # [0] selects the first and only row.
        # np.asarray is used to ensure that the output is a numpy array of 64-bit floats (pins dtype) - mostly to keep the type checker happy.
        query_vector = np.asarray(self._embedder.embed([query])[0], dtype=np.float64)

        # Calculate the cosine similarity between the query's vector, and each vector in the vector store.
        # 1. Perform a dot product between the query's vector and each vector in the vector store
        # 2. Calculate the norm of each vector in the vector store (axis=1 means calculate the norm for each row of vectors)
        # 3. Calculate the norm of the query's vector
        # 4. Multiply each chunk's norm by the query norm to get the per-chunk denominators
        # 5. Divide the dot product by the product of the norms to get the cosine similarity between the query and each vector in the vector store
        dot_products = np.dot(self._vectors, query_vector)
        vector_store_norms = np.linalg.norm(self._vectors, axis=1)
        query_norm = np.linalg.norm(query_vector)
        norms = vector_store_norms * query_norm
        similarities = dot_products / norms

        # Pick the top-k most similar indices from the similarities array.
        #   * Originally used [::-1] to reverse the result of argsort, but NumPy added a descending order parameter at some point.
        #   * [:top_k] slices the result to only include the top-k indices.
        #   * [start:stop:step] --> NumPy array slicing syntax. You can omit the last ':' in most cases unless you want any other step than 1.
        #     * Step is known as stride in other languages.
        top_indices: list[int] = np.argsort(similarities, descending=True)[:top_k].tolist()

        # Annotates the current Langfuse span with details about what was searched, and what came back.
        # input: The query text
        # output: For each index in the list of top indices:
        #   1. Get up to 100 chars of the chunk
        #   2. Get the cosine similarity score, casted to a float as NumPy scalars can be awkward when printed
        #   3. Pack them into a tuple (preview, score)
        #   4. Add to the output list
        # metadata: Total number of chunks in the chunk store (corpus size), and how many closest chunks (neighbours) were returned.
        get_langfuse().update_current_span(
            input=query,
            output={"top_chunks": [(self._chunks[i][:100], float(similarities[i])) for i in top_indices]},
            metadata={"total_chunks": len(self._chunks), "top_k": top_k},
        )

        return [(self._chunks[i], float(similarities[i])) for i in top_indices]


@dataclass
class RagQueryResult:
    """
    The result of a RAG query.
    """

    answer: str
    sources: list[dict[str, str | float]] = field(default_factory=list)
    usage: dict[str, int] = field(default_factory=dict)
    model: str = ""
    provider: str = ""
    trace_id: str | None = None


@langfuse.observe(name="rag_query")
def rag_query(query: str, vector_store: InMemoryVectorStore, top_k: int = 3) -> RagQueryResult:
    """
    Run a RAG query against the specified vector store.
    """

    langfuse = get_langfuse()

    with propagate_attributes(user_id="phase1-tutorial-user", session_id="phase1-tutorial-session-id", trace_name="rag_query"):
        langfuse.update_current_span(input=query)

        results: list[tuple[str, float]] = vector_store.search(query, top_k)

        if not results:
            langfuse.update_current_span(output="No results found")
            langfuse.flush()
            return RagQueryResult(answer="No relevant documents found.")

        context_text = "\n\n---\n\n".join(f"[Source {i + 1}] {chunk}" for i, (chunk, _) in enumerate[tuple[str, float]](results))

        system_prompt = (
            "You are a helpful assistant that answers questions based on the "
            "provided document context. If the answer is not in the context, "
            "say so. Always cite which source(s) you used.\n"
            "Output template:\n"
            "<answer details>\n"
            "<blank line>\n"
            "<List of sources used in the following format: [SOURCE <source number>] <brief source description>"
            " --> <specific metadata about the source like page, section, title, chapter, short summary>>"
        )

        user_prompt = f"""
            Document context:\n\n{context_text}

            Question: {query}

            Answer the question based on the context above. Cite sources by number.
        """

        provider = get_provider()
        with langfuse.start_as_current_observation(
            as_type="generation",
            name="llm_generation",
            input=[{"system": system_prompt[:500]}, {"user": user_prompt[:500]}],
            metadata={"provider": provider.provider_name},
        ) as generation:
            result = provider.chat(messages=[ChatMessage(Role.SYSTEM, system_prompt), ChatMessage(Role.USER, user_prompt)], temperature=0.0, max_tokens=512)

            generation.update(
                model=result.model,
                output=result.content[:1000],
                usage_details={
                    "input_tokens": result.usage.get("prompt_tokens", 0),
                    "output_tokens": result.usage.get("completion_tokens", 0),
                    "total_tokens": result.usage.get("total_tokens", 0),
                },
            )

        langfuse.update_current_span(
            output={"answer": result.content[:200], "sources_count": len(results)},
            metadata={"provider": provider.provider_name, "model": result.model},
        )

        trace_id = langfuse.get_current_trace_id()
        langfuse.flush()

        return RagQueryResult(
            answer=result.content,
            sources=[{"chunk": chunk[:200] + "...", "score": round(score, 4)} for chunk, score in results],
            usage=result.usage,
            model=result.model,
            provider=provider.provider_name,
            trace_id=trace_id,
        )


# Load .env into os.environ so that we send authenticated requests to HuggingFace by default.
load_dotenv()


# Eager-init so the Langfuse singleton exists before any @observe call.
# Otherwise the first observed function builds a disabled client from empty env.
# Once we construct a real client, it gets registered inside the LangFuse module and subsequent calls work as expected.
# TODO: Figure out a more elegant solution.
get_langfuse()
