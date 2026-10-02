import ast
import pytest
from analyzer.rules.llm_rules import (
    ModelNotConfiguredRule,
    TemperatureNotConfiguredRule,
    NoErrorHandlingRule,
    NoMaxTokensLimitRule,
)


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


class TestNoErrorHandlingRule:
    rule = NoErrorHandlingRule()

    def test_flags_llm_call_with_no_try_in_function(self):
        code = """
def answer(question):
    response = client.messages.create(
        model="claude-sonnet-5",
        messages=[{"role": "user", "content": question}],
    )
    return response.content[0].text
"""
        findings = self.rule.check(parse(code), "test.py")
        assert len(findings) == 1
        assert findings[0].rule_id == "AI_LLM_003"
        assert findings[0].severity == "warning"

    def test_no_finding_when_wrapped_in_try(self):
        code = """
def answer(question):
    try:
        response = client.messages.create(
            model="claude-sonnet-5",
            messages=[{"role": "user", "content": question}],
        )
        return response.content[0].text
    except Exception:
        return "error"
"""
        findings = self.rule.check(parse(code), "test.py")
        assert findings == []

    def test_no_finding_when_no_llm_call(self):
        code = """
def helper(x):
    return x + 1
"""
        findings = self.rule.check(parse(code), "test.py")
        assert findings == []

    def test_finding_includes_line_number(self):
        code = """\
def answer(question):
    response = client.messages.create(
        messages=[{"role": "user", "content": question}],
    )
    return response.content[0].text
"""
        findings = self.rule.check(parse(code), "test.py")
        assert findings[0].line == 2


class TestNoMaxTokensLimitRule:
    rule = NoMaxTokensLimitRule()

    def test_flags_api_call_missing_max_tokens(self):
        code = """
response = client.messages.create(
    model="claude-sonnet-5",
    messages=[{"role": "user", "content": "hi"}],
)
"""
        findings = self.rule.check(parse(code), "test.py")
        assert len(findings) == 1
        assert findings[0].rule_id == "AI_LLM_004"
        assert findings[0].severity == "warning"

    def test_no_finding_when_max_tokens_present(self):
        code = """
response = client.messages.create(
    model="claude-sonnet-5",
    max_tokens=512,
    messages=[{"role": "user", "content": "hi"}],
)
"""
        findings = self.rule.check(parse(code), "test.py")
        assert findings == []

    def test_no_finding_when_max_completion_tokens_present(self):
        code = """
response = client.chat.completions.create(
    model="gpt-4",
    max_completion_tokens=512,
    messages=[{"role": "user", "content": "hi"}],
)
"""
        findings = self.rule.check(parse(code), "test.py")
        assert findings == []

    def test_no_finding_for_non_llm_call(self):
        code = """
record = db.records.create(name="test", value=42)
"""
        findings = self.rule.check(parse(code), "test.py")
        assert findings == []

    def test_flags_ollama_style_chat_call_missing_max_tokens(self):
        code = """
response = ollama.chat(model="llama3.2", messages=messages, tools=TOOLS)
"""
        findings = self.rule.check(parse(code), "test.py")
        assert len(findings) == 1
        assert findings[0].rule_id == "AI_LLM_004"
