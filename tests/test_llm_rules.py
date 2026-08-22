import ast
import pytest
from analyzer.rules.llm_rules import ModelNotConfiguredRule, TemperatureNotConfiguredRule


def parse(code: str) -> ast.AST:
    return ast.parse(code)


class TestModelNotConfiguredRule:
    rule = ModelNotConfiguredRule()

    def test_flags_api_call_missing_model(self):
        code = """
response = client.messages.create(
    messages=[{"role": "user", "content": "hi"}],
    max_tokens=100,
)
"""
        findings = self.rule.check(parse(code), "test.py")
        assert len(findings) == 1
        assert findings[0].rule_id == "AI_LLM_001"
        assert findings[0].severity == "error"

    def test_no_finding_when_model_present_in_api_call(self):
        code = """
response = client.messages.create(
    model="claude-3-haiku-20240307",
    messages=[{"role": "user", "content": "hi"}],
    max_tokens=100,
)
"""
        findings = self.rule.check(parse(code), "test.py")
        assert findings == []

    def test_flags_langchain_constructor_missing_model(self):
        code = """
from langchain_openai import ChatOpenAI
llm = ChatOpenAI(temperature=0.0)
"""
        findings = self.rule.check(parse(code), "test.py")
        assert len(findings) == 1
        assert findings[0].rule_id == "AI_LLM_001"

    def test_no_finding_for_non_llm_create_call(self):
        code = """
record = db.records.create(name="test", value=42)
"""
        findings = self.rule.check(parse(code), "test.py")
        assert findings == []

    def test_finding_includes_line_number(self):
        code = """\
response = client.messages.create(
    messages=[{"role": "user", "content": "hi"}],
)
"""
        findings = self.rule.check(parse(code), "test.py")
        assert findings[0].line == 1


class TestTemperatureNotConfiguredRule:
    rule = TemperatureNotConfiguredRule()

    def test_flags_api_call_missing_temperature(self):
        code = """
response = client.messages.create(
    model="claude-3-haiku-20240307",
    messages=[{"role": "user", "content": "hi"}],
)
"""
        findings = self.rule.check(parse(code), "test.py")
        assert len(findings) == 1
        assert findings[0].rule_id == "AI_LLM_002"
        assert findings[0].severity == "warning"

    def test_no_finding_when_temperature_present(self):
        code = """
response = client.messages.create(
    model="claude-3-haiku-20240307",
    temperature=0.0,
    messages=[{"role": "user", "content": "hi"}],
)
"""
        findings = self.rule.check(parse(code), "test.py")
        assert findings == []

    def test_flags_langchain_constructor_missing_temperature(self):
        code = """
from langchain_openai import ChatOpenAI
llm = ChatOpenAI(model="gpt-4o")
"""
        findings = self.rule.check(parse(code), "test.py")
        assert len(findings) == 1
        assert findings[0].rule_id == "AI_LLM_002"
