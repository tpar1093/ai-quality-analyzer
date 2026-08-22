import ast
import pytest
from analyzer.rules.rag_rules import MetadataStrippedRule, SourceAttributionMissingRule


def parse(code: str) -> ast.AST:
    return ast.parse(code)


class TestMetadataStrippedRule:
    rule = MetadataStrippedRule()

    def test_flags_comprehension_stripping_dict_content_only(self):
        code = """
contents = [doc["content"] for doc in raw_docs]
"""
        findings = self.rule.check(parse(code), "test.py")
        assert len(findings) == 1
        assert findings[0].rule_id == "AI_RAG_001"

    def test_flags_comprehension_stripping_attribute_only(self):
        code = """
texts = [doc.page_content for doc in documents]
"""
        findings = self.rule.check(parse(code), "test.py")
        assert len(findings) == 1
        assert findings[0].rule_id == "AI_RAG_001"

    def test_no_finding_when_full_object_passed(self):
        code = """
docs = [doc for doc in raw_docs]
"""
        findings = self.rule.check(parse(code), "test.py")
        assert findings == []

    def test_no_finding_when_dict_with_multiple_fields(self):
        code = """
pairs = [{"content": doc["content"], "source": doc["source"]} for doc in raw_docs]
"""
        findings = self.rule.check(parse(code), "test.py")
        assert findings == []

    def test_no_finding_for_fstring_with_multiple_accesses(self):
        code = """
lines = [f"[{doc.source}] {doc.content}" for doc in docs]
"""
        findings = self.rule.check(parse(code), "test.py")
        assert findings == []


class TestSourceAttributionMissingRule:
    rule = SourceAttributionMissingRule()

    def test_flags_return_of_raw_anthropic_response_text(self):
        code = """
def answer(question, docs):
    response = client.messages.create(
        messages=[{"role": "user", "content": question}],
    )
    return response.content[0].text
"""
        findings = self.rule.check(parse(code), "test.py")
        assert len(findings) == 1
        assert findings[0].rule_id == "AI_RAG_002"

    def test_no_finding_when_returning_attributed_object(self):
        code = """
def answer(question, docs):
    response = client.messages.create(
        messages=[{"role": "user", "content": question}],
    )
    data = json.loads(response.content[0].text)
    return AttributedAnswer(answer=data["answer"], sources=data["sources"])
"""
        findings = self.rule.check(parse(code), "test.py")
        assert findings == []

    def test_no_finding_when_no_llm_call_in_function(self):
        code = """
def format_result(text):
    return text.upper()
"""
        findings = self.rule.check(parse(code), "test.py")
        assert findings == []

    def test_flags_openai_style_content_return(self):
        code = """
def answer(q, docs):
    resp = client.chat.completions.create(
        messages=[{"role": "user", "content": q}],
    )
    return resp.choices[0].message.content
"""
        findings = self.rule.check(parse(code), "test.py")
        assert len(findings) == 1
        assert findings[0].rule_id == "AI_RAG_002"
