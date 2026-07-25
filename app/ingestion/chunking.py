"""
Chunking implementation.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import settings
from app.ingestion.language import Language
from app.ingestion.pdf_parser import PageText


@dataclass(frozen=True)
class DocumentChunk:
    content: str
    chunk_index: int
    page_start: int
    page_end: int
    language: Language
    token_estimate: int


SEPARATORS: list[str] = [
    "\n\n",
    "\n",
    ". ",
    "\u3002",  # Japanese full stop
    "\u3001",  # Japanese comma
    " ",
    "",
]


def chunk_pages(pages: list[PageText], language: Language) -> list[DocumentChunk]:
    """
    Chunks non-empty pages.

    Overlaps are bounded by page boundaries.
    """

    chunk_size = settings.chunk_size
    overlap = settings.chunk_overlap

    if not (0 <= overlap < chunk_size):
        raise ValueError(f"chunk_overlap must satisfy 0 <= overlap < chunk_size; got {overlap=}, {chunk_size=}")

    chunks: list[DocumentChunk] = []
    chunk_index = 0

    for page in pages:
        if page.is_empty:
            continue

        segments = _get_segments_recursive(page.text, SEPARATORS, chunk_size)

        for chunk in _chunkify_segments(segments, chunk_size, overlap):
            chunk = chunk.strip()

            if not chunk:
                continue

            chunks.append(
                DocumentChunk(content=chunk, chunk_index=chunk_index, page_start=page.page_number, page_end=page.page_number, language=language, token_estimate=len(chunk) // 2)
            )

            chunk_index += 1

    return chunks


def _get_segments_recursive(text: str, separators: list[str], chunk_size: int) -> list[str]:
    """
    Recursively splits text into segments using the given separators.
    """

    text = text.strip()

    if not text:
        return []

    if len(text) <= chunk_size:
        return [text]

    current_separator = separators[0]

    if current_separator == "":
        # If we get to the last separator (technically not a separator at all), we just split by chunk size.
        # Should never really happen as it would require a `chunk_size` long string of characters, but not impossible.
        return [text[chunk_idx : chunk_idx + chunk_size] for chunk_idx in range(0, len(text), chunk_size)]

    text_segments = text.split(current_separator)

    segments: list[str] = []

    for text_segment in text_segments:
        text_segment = text_segment.strip()
        if not text_segment:
            continue
        if len(text_segment) <= chunk_size:
            segments.append(text_segment)
        else:
            segments.extend(_get_segments_recursive(text_segment, separators[1:], chunk_size))

    return segments


def _chunkify_segments(segments: list[str], chunk_size: int, overlap: int) -> list[str]:
    """
    Packs segments into chunks.

    Assumes that the size of each segment is <= chunk_size.
    """

    if not segments:
        return []

    chunks: list[str] = []

    current_chunk: str = ""

    for segment in segments:
        # If the current chunk we are building is empty, we set the segment as the chunk candidate.
        # Otherwise, we append the segment to the current chunk.
        chunk_candidate = segment if not current_chunk else f"{current_chunk} {segment}"

        # If the current chunk has content and the candidate would exceed chunk_size...
        #   - Discard chunk_candidate
        #   - Append the current chunk to the output
        #   - Start a new chunk from overlap-tail + this segment (hard-split in the while below only if that new buffer is still larger than chunk_size).
        # If the current chunk is empty (start of input) or the candidate fits, the else branch just accepts chunk_candidate and keeps accumulating.
        if current_chunk and len(chunk_candidate) > chunk_size:
            # Add the current chunk to the list of output chunks
            chunks.append(current_chunk)

            # Grab the last 'overlap' characters from the current chunk, and then prefix the next chunk with them.
            tail = current_chunk[-overlap:] if overlap > 0 else ""
            current_chunk = f"{tail} {segment}".strip() if tail else segment

            # keep splitting the new current chunk into chunks of size chunk_size until it is <= 'chunk_size'
            while len(current_chunk) > chunk_size:
                chunks.append(current_chunk[:chunk_size])
                current_chunk = current_chunk[(chunk_size - overlap) :] if overlap else current_chunk[chunk_size:]
        else:
            current_chunk = chunk_candidate

    # If there is any content left in the current chunk, we add it to the list of output chunks
    if current_chunk:
        chunks.append(current_chunk)

    return chunks
