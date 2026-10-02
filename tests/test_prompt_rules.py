import ast
from analyzer.rules.prompt_rules import HardcodedSystemPromptRule


def parse(code: str) -> ast.AST:
    return ast.parse(code)


LONG_PROMPT = "You are a helpful assistant. " * 6  # > 120 chars


class TestHardcodedSystemPromptRule:
    rule = HardcodedSystemPromptRule()

    def test_flags_long_system_kwarg_literal(self):
        code = f"""
response = client.messages.create(
    model="claude-sonnet-5",
    system="{LONG_PROMPT}",
    messages=[{{"role": "user", "content": "hi"}}],
)
"""
        findings = self.rule.check(parse(code), "test.py")
        assert len(findings) == 1
        assert findings[0].rule_id == "AI_PROMPT_001"
        assert findings[0].severity == "warning"

    def test_no_finding_when_system_loaded_from_variable(self):
        code = """
response = client.messages.create(
    model="claude-sonnet-5",
    system=SYSTEM_PROMPT,
    messages=[{"role": "user", "content": "hi"}],
)
"""
        findings = self.rule.check(parse(code), "test.py")
        assert findings == []

    def test_no_finding_for_short_system_kwarg(self):
        code = """
response = client.messages.create(
    model="claude-sonnet-5",
    system="You are a helpful assistant.",
    messages=[{"role": "user", "content": "hi"}],
)
"""
        findings = self.rule.check(parse(code), "test.py")
        assert findings == []

    def test_flags_long_openai_style_system_message(self):
        code = f"""
response = client.chat.completions.create(
    model="gpt-4",
    messages=[
        {{"role": "system", "content": "{LONG_PROMPT}"}},
        {{"role": "user", "content": "hi"}},
    ],
)
"""
        findings = self.rule.check(parse(code), "test.py")
        assert len(findings) == 1
        assert findings[0].rule_id == "AI_PROMPT_001"

    def test_no_finding_for_short_openai_style_system_message(self):
        code = """
response = client.chat.completions.create(
    model="gpt-4",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "hi"},
    ],
)
"""
        findings = self.rule.check(parse(code), "test.py")
        assert findings == []

    def test_no_finding_for_user_role_dict(self):
        code = f"""
messages = [{{"role": "user", "content": "{LONG_PROMPT}"}}]
"""
        findings = self.rule.check(parse(code), "test.py")
        assert findings == []

    def test_finding_includes_line_number(self):
        code = f"""\
response = client.messages.create(system="{LONG_PROMPT}")
"""
        findings = self.rule.check(parse(code), "test.py")
        assert findings[0].line == 1
