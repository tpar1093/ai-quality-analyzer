"""
Intentionally non-compliant RAG application.
Used as the target for ai-quality-analyzer demo scans.

Violations:
  AI_LLM_001  — no model= in messages.create()
  AI_LLM_002  — no temperature= in messages.create()
  AI_OUTPUT_001 — raw string returned, no json.loads or schema
  AI_RAG_001  — list comprehension strips source metadata
  AI_RAG_002  — answer() returns raw response text, no sources
  AI_AGENT_001 — unbounded while True loop in run_agent()
"""
from anthropic import Anthropic

client = Anthropic()


def retrieve(query: str) -> list:
    raw_docs = [
        {"content": "The Eiffel Tower is located in Paris.", "source": "tourism.txt"},
        {"content": "Paris is the capital of France.", "source": "wiki.txt"},
    ]
    # AI_RAG_001: list comprehension strips 'source' — only content survives
    return [doc["content"] for doc in raw_docs]


def answer(question: str, docs: list) -> str:
    context = "\n".join(docs)
    # AI_LLM_001: missing model=
    # AI_LLM_002: missing temperature=
    response = client.messages.create(
        max_tokens=256,
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
