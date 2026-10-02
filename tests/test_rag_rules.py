import ast
from analyzer.rules.rag_rules import (
    MetadataStrippedRule,
    SourceAttributionMissingRule,
    UnboundedRetrievalRule,
)


def parse(code: str) -> ast.AST:
    return ast.parse(code)


class TestMetadataStrippedRule:
    rule = MetadataStrippedRule()

    def test_flags_comprehension_stripping_dict_content_only(self):
        code = """
docs = [d["content"] for d in raw_docs]
"""
        findings = self.rule.check(parse(code), "test.py")
        assert len(findings) == 1
        assert findings[0].rule_id == "AI_RAG_001"

    def test_flags_comprehension_stripping_attribute_only(self):
        code = """
docs = [d.page_content for d in raw_docs]
"""
        findings = self.rule.check(parse(code), "test.py")
        assert len(findings) == 1

    def test_no_finding_when_full_object_passed(self):
        code = """
docs = [d for d in raw_docs]
"""
        findings = self.rule.check(parse(code), "test.py")
        assert findings == []

    def test_no_finding_when_dict_with_multiple_fields(self):
        code = """
docs = [{"text": d.page_content, "source": d.metadata["source"]} for d in raw_docs]
"""
        findings = self.rule.check(parse(code), "test.py")
        assert findings == []

    def test_no_finding_for_fstring_with_multiple_accesses(self):
        code = """
docs = [f"[{d.source}] {d.content}" for d in raw_docs]
"""
        findings = self.rule.check(parse(code), "test.py")
        assert findings == []


class TestSourceAttributionMissingRule:
    rule = SourceAttributionMissingRule()

    def test_flags_return_of_raw_anthropic_response_text(self):
        code = """
def answer(question, docs):
    response = client.messages.create(
        model="claude-sonnet-5",
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
        model="claude-sonnet-5",
        messages=[{"role": "user", "content": question}],
    )
    return {"answer": response.content[0].text, "sources": [d.source for d in docs]}
"""
        findings = self.rule.check(parse(code), "test.py")
        assert findings == []

    def test_no_finding_when_no_llm_call_in_function(self):
        code = """
def helper(x):
    return x.content[0].text
"""
        findings = self.rule.check(parse(code), "test.py")
        assert findings == []

    def test_flags_openai_style_content_return(self):
        code = """
def answer(question):
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": question}],
    )
    return response.choices[0].message.content
"""
        findings = self.rule.check(parse(code), "test.py")
        assert len(findings) == 1


class TestUnboundedRetrievalRule:
    rule = UnboundedRetrievalRule()

    def test_flags_similarity_search_without_k(self):
        code = """
docs = vectorstore.similarity_search(query)
"""
        findings = self.rule.check(parse(code), "test.py")
        assert len(findings) == 1
        assert findings[0].rule_id == "AI_RAG_003"
        assert findings[0].severity == "warning"

    def test_no_finding_when_k_present(self):
        code = """
docs = vectorstore.similarity_search(query, k=5)
"""
        findings = self.rule.check(parse(code), "test.py")
        assert findings == []

    def test_no_finding_when_top_k_present(self):
        code = """
docs = vectorstore.similarity_search(query, top_k=5)
"""
        findings = self.rule.check(parse(code), "test.py")
        assert findings == []

    def test_flags_max_marginal_relevance_search_without_k(self):
        code = """
docs = vectorstore.max_marginal_relevance_search(query)
"""
        findings = self.rule.check(parse(code), "test.py")
        assert len(findings) == 1

    def test_no_finding_for_unrelated_method_call(self):
        code = """
record = db.records.create(name="test")
"""
        findings = self.rule.check(parse(code), "test.py")
        assert findings == []

    def test_finding_includes_line_number(self):
        code = """\
docs = vectorstore.similarity_search(query)
"""
        findings = self.rule.check(parse(code), "test.py")
        assert findings[0].line == 1
