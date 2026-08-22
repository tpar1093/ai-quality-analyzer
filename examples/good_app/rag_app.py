"""
Compliant RAG application — passes all ai-quality-analyzer checks.
"""
import json
from dataclasses import dataclass
from anthropic import Anthropic

MODEL = "claude-3-haiku-20240307"
TEMPERATURE = 0.0
MAX_STEPS = 10

client = Anthropic()


@dataclass
class Document:
    content: str
    source: str


@dataclass
class AttributedAnswer:
    answer: str
    sources: list[str]


def retrieve(query: str) -> list[Document]:
    # AI_RAG_001 ✓: full Document objects preserve source metadata
    return [
        Document("The Eiffel Tower is located in Paris.", "tourism.txt"),
        Document("Paris is the capital of France.", "wiki.txt"),
    ]


def answer(question: str, docs: list[Document]) -> AttributedAnswer:
    context = "\n".join(f"[{doc.source}] {doc.content}" for doc in docs)
    # AI_LLM_001 ✓: model= explicit
    # AI_LLM_002 ✓: temperature= explicit
    response = client.messages.create(
        model=MODEL,
        temperature=TEMPERATURE,
        max_tokens=512,
        messages=[{
            "role": "user",
            "content": (
                f"Context:\n{context}\n\n"
                f"Answer in JSON with keys 'answer' (string) and 'sources' (list of strings):\n"
                f"{question}"
            ),
        }],
    )
    # AI_OUTPUT_001 ✓: structured output via json.loads
    data = json.loads(response.content[0].text)
    # AI_RAG_002 ✓: AttributedAnswer includes source list
    return AttributedAnswer(answer=data["answer"], sources=data["sources"])


def run_agent(question: str) -> str:
    # AI_AGENT_001 ✓: bounded by MAX_STEPS, no while True
    for _step in range(MAX_STEPS):
        docs = retrieve(question)
        result = answer(question, docs)
        if result.answer:
            return result.answer
    return "Max steps reached without a conclusive answer."
