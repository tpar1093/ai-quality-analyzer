import ast
import pytest
from analyzer.rules.output_rules import UnstructuredOutputRule


def parse(code: str) -> ast.AST:
    return ast.parse(code)


class TestUnstructuredOutputRule:
    rule = UnstructuredOutputRule()

    def test_flags_function_returning_raw_llm_string(self):
        code = """
def answer(question, docs):
    response = client.messages.create(
        messages=[{"role": "user", "content": question}],
    )
    return response.content[0].text
"""
        findings = self.rule.check(parse(code), "test.py")
        assert len(findings) == 1
        assert findings[0].rule_id == "AI_OUTPUT_001"

    def test_no_finding_when_json_loads_present(self):
        code = """
import json

def answer(question, docs):
    response = client.messages.create(
        messages=[{"role": "user", "content": question}],
    )
    return json.loads(response.content[0].text)
"""
        findings = self.rule.check(parse(code), "test.py")
        assert findings == []

    def test_no_finding_when_response_format_present(self):
        code = """
def answer(question, docs):
    response = client.messages.create(
        messages=[{"role": "user", "content": question}],
        response_format={"type": "json_object"},
    )
    return response.content[0].text
"""
        findings = self.rule.check(parse(code), "test.py")
        assert findings == []

    def test_no_finding_when_with_structured_output_used(self):
        code = """
def answer(question):
    result = llm.with_structured_output(MyModel).invoke(
        messages=[{"role": "user", "content": question}]
    )
    return result
"""
        findings = self.rule.check(parse(code), "test.py")
        assert findings == []

    def test_no_finding_when_function_has_no_llm_call(self):
        code = """
def greet(name):
    return f"Hello, {name}"
"""
        findings = self.rule.check(parse(code), "test.py")
        assert findings == []

    def test_finding_reported_at_function_line(self):
        code = """\

def answer(q, docs):
    response = client.messages.create(messages=[{"role": "user", "content": q}])
    return response.content[0].text
"""
        findings = self.rule.check(parse(code), "test.py")
        assert findings[0].line == 2
