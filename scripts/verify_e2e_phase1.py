"""
E2E verification script for Phase 1
"""

import sys
import time
from pathlib import Path

from app.core.config import settings
from app.core.model_registry import get_provider
from app.core.providers.base import ChatMessage, Role
from app.rag.pipeline import Embedder, InMemoryVectorStore, rag_query
from scripts.utils import print_full_width_divider, suppress_print

_check_count = 0


def check(step: str, condition: bool) -> None:
    global _check_count
    _check_count += 1

    status = "PASS" if condition else "FAIL"
    print(f"{_check_count:02d}. {step}: {status}")

    if not condition:
        sys.exit(1)


def main() -> None:
    print_full_width_divider()
    print("Initializing NexusDoc Phase 1 E2E Verification")
    print_full_width_divider()

    t_start = time.perf_counter()

    # Config
    check("Settings were loaded from the .env file, or the machines environment variables", bool(settings.groq_api_key) and bool(settings.langfuse_secret_key))

    # Model registry
    provider = get_provider()
    check(f"Provider '{provider.provider_name}' initialized", True)

    models = provider.list_models()
    check(f"Provider returned {len(models)} model(s)", len(models) > 0)

    # LLM Call
    with suppress_print():
        result = provider.chat(messages=[ChatMessage(role=Role.USER, content="Say exactly: nexusdoc-ok")], max_tokens=10)
    check("Provider returned a valid completion", "nexusdoc" in result.content.lower())

    # RAG Pipeline
    with suppress_print():
        embedder = Embedder()
        store = InMemoryVectorStore(embedder)
        doc_path = Path("data/sample_docs/appliance_manual_excerpt.txt")
        store.set_document(doc_path.read_text(encoding="utf-8"))
    check(f"Document chunked ({store.chunk_count} chunk(s) found)", store.chunk_count > 0)

    with suppress_print():
        rag_result = rag_query("What does error code E12 mean?", store)
    check("RAG returned answer", len(rag_result.answer) > 0)
    check("RAG returned sources", len(rag_result.sources) > 0)
    check("RAG returned total token usage", rag_result.usage.get("total_tokens", 0) > 0)
    check("RAG returned input token usage", rag_result.usage.get("prompt_tokens", 0) > 0)
    check("RAG returned output token usage", rag_result.usage.get("completion_tokens", 0) > 0)

    # LangFuse Tracing
    check(f"Trace created: {rag_result.trace_id}", rag_result.trace_id is not None)

    # Summary
    print_full_width_divider()
    print("ALL CHECKS PASSED")
    print(f"- Runtime:  {time.perf_counter() - t_start:.2f} seconds")
    print(f"- Provider: {rag_result.provider}")
    print(f"- Model:    {rag_result.model}")

    inpt_tokens = rag_result.usage.get("prompt_tokens", 0)
    outpt_tokens = rag_result.usage.get("completion_tokens", 0)
    total_tokens = rag_result.usage.get("total_tokens", 0)
    print(f"- Tokens:   Input: {inpt_tokens} | Output: {outpt_tokens} | Total: {total_tokens}")

    print(f"- Trace ID: {rag_result.trace_id}")
    print_full_width_divider()


if __name__ == "__main__":
    main()
