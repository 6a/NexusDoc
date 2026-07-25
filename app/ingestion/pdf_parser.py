"""
Parses PDF files and extracts text.

No OCR yet.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

import pymupdf

from app.core.config import settings


@dataclass(frozen=True)
class PageText:
    page_number: int
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
    """
    Parses the specified PDF file.

    Currently only supports text extraction.
    """

    threshold = settings.empty_page_min_chars if min_chars is None else min_chars

    pages: list[PageText] = []

    # PyMuPDF Document stubs are incomplete so cast the untyped types. To keep the type checker happy...

    with pymupdf.open(path) as document:  # type: ignore[no-untyped-call]
        page_count = cast(int, document.page_count)
        for page_idx in range(page_count):
            page = cast(Any, document[page_idx])
            raw = page.get_text("text", sort=True)
            text = raw if isinstance(raw, str) else ""
            stripped_text = text.strip()
            char_count = len(stripped_text)
            is_empty = char_count < threshold

            pages.append(PageText(page_number=page_idx + 1, text=stripped_text, char_count=char_count, is_empty=is_empty))

    empty_page_count = sum(1 for page in pages if page.is_empty)

    return ParsedDocument(path=path, page_count=page_count, pages=pages, empty_page_count=empty_page_count)
