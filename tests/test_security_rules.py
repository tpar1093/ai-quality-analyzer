import ast
from analyzer.rules.security_rules import HardcodedCredentialRule


def parse(code: str) -> ast.AST:
    return ast.parse(code)


class TestHardcodedCredentialRule:
    rule = HardcodedCredentialRule()

    def test_flags_literal_api_key_in_constructor_call(self):
        code = """
client = Anthropic(api_key="sk-ant-abc123")
"""
        findings = self.rule.check(parse(code), "test.py")
        assert len(findings) == 1
        assert findings[0].rule_id == "AI_SECRET_001"
        assert findings[0].severity == "error"

    def test_no_finding_when_loaded_from_env(self):
        code = """
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
"""
        findings = self.rule.check(parse(code), "test.py")
        assert findings == []

    def test_no_finding_when_loaded_from_variable(self):
        code = """
client = Anthropic(api_key=API_KEY)
"""
        findings = self.rule.check(parse(code), "test.py")
        assert findings == []

    def test_no_finding_for_empty_string(self):
        code = """
client = Anthropic(api_key="")
"""
        findings = self.rule.check(parse(code), "test.py")
        assert findings == []

    def test_flags_other_credential_kwarg_names(self):
        code = """
session = requests.Session()
session.headers.update(auth_token="abc123xyz")
"""
        findings = self.rule.check(parse(code), "test.py")
        assert len(findings) == 1

    def test_no_finding_for_unrelated_kwarg(self):
        code = """
record = db.records.create(name="test", value=42)
"""
        findings = self.rule.check(parse(code), "test.py")
        assert findings == []

    def test_finding_includes_line_number(self):
        code = """\
client = Anthropic(api_key="sk-ant-abc123")
"""
        findings = self.rule.check(parse(code), "test.py")
        assert findings[0].line == 1
