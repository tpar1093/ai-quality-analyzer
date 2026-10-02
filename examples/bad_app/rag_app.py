"""
Intentionally non-compliant RAG application.
Used as the target for ai-quality-analyzer demo scans.

Violations:
  AI_LLM_001  — no model= in messages.create()
  AI_LLM_002  — no temperature= in messages.create()
  AI_LLM_003  — answer() has no try/except around the LLM call
  AI_OUTPUT_001 — raw string returned, no json.loads or schema
  AI_RAG_001  — list comprehension strips source metadata
  AI_RAG_002  — answer() returns raw response text, no sources
  AI_RAG_003  — similarity_search() called with no k= limit
  AI_AGENT_001 — unbounded while True loop in run_agent()
  AI_SECRET_001 — api_key= passed as a hardcoded string literal
  AI_PROMPT_001 — system prompt hardcoded inline instead of externalized
"""
from anthropic import Anthropic

# AI_SECRET_001: hardcoded credential instead of os.getenv(...)
client = Anthropic(api_key="sk-ant-api03-fake-key-for-demo-purposes-only")


class FakeVectorStore:
    """Stub standing in for a real vector store client (Chroma, Pinecone, ...)."""

    def similarity_search(self, query: str) -> list:
        return [
            {"content": "The Eiffel Tower is located in Paris.", "source": "tourism.txt"},
            {"content": "Paris is the capital of France.", "source": "wiki.txt"},
        ]


vectorstore = FakeVectorStore()


def retrieve(query: str) -> list:
    # AI_RAG_003: no k= limit — returns the entire collection
    raw_docs = vectorstore.similarity_search(query)
    # AI_RAG_001: list comprehension strips 'source' — only content survives
    return [doc["content"] for doc in raw_docs]


def answer(question: str, docs: list) -> str:
    context = "\n".join(docs)
    # AI_LLM_001: missing model=
    # AI_LLM_002: missing temperature=
    # AI_LLM_003: no try/except around this call
    # AI_PROMPT_001: long system prompt embedded directly in the call
    response = client.messages.create(
        max_tokens=256,
        system=(
            "You are a customer support assistant for an e-commerce platform. "
            "Always be polite, concise, and never make promises about refunds or "
            "shipping dates that you cannot verify. If you are unsure, say so."
        ),
        messages=[{"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"}],
    )
    # AI_OUTPUT_001: raw string, no schema or json.loads
    # AI_RAG_002: no source attribution in return value
    return response.content[0].text


def run_agent(question: str) -> str:
    # AI_AGENT_001: unbounded while True — no MAX_STEPS guard
    while True:
        docs = retrieve(question)
        result = answer(question, docs)
        if "final answer" in result.lower():
            return result
