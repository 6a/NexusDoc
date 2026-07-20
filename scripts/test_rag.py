"""
Hello-world RAG with langfuse tracing.
"""

from pathlib import Path

from app.rag.pipeline import Embedder, InMemoryVectorStore, rag_query
from scripts.utils import print_full_width_divider

doc_path = Path("data/sample_docs/appliance_manual_excerpt.txt")
text = doc_path.read_text(encoding="utf-8")

print("Building vector store...")

embedder = Embedder()
store = InMemoryVectorStore(embedder)

store.set_document(text)

print(f"Vector store ready --> Generated {store.chunk_count} chunks.")

questions = ["What does error code E12 mean?", "How do I clean the drain filter?", "What should I do for an unbalanced load E27?"]

for question in questions:
    print()
    print_full_width_divider()
    print(f"Question:\n{question}")

    result = rag_query(question, store)

    print(f"\nAnswer:\n{result.answer}")
    print(f"\n  Provider: {result.provider} | Model: {result.model}")
    print(f"  Tokens: {result.usage.get('total_tokens', '?')}")
    print(f"    Input tokens: {result.usage.get('prompt_tokens', '?')}")
    print(f"    Output tokens: {result.usage.get('completion_tokens', '?')}")
    print(f"  Trace: {result.trace_id or '<unknown>'}")

print()
print_full_width_divider()
print("All queries executed and traced. Check the langfuse dashboard for details.")
