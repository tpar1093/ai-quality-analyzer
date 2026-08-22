import json
import pytest
from analyzer.rules.base import Finding, Severity
from analyzer.reporter import format_terminal, format_json, _finding_to_dict


def make_finding(**overrides) -> Finding:
    defaults = dict(
        rule_id="AI_LLM_001",
        title="Model not configured",
        severity=Severity.ERROR,
        message="Missing model= argument.",
        rationale="Always pin the model name.",
        file="app/rag.py",
        line=12,
    )
    defaults.update(overrides)
    return Finding(**defaults)


class TestFormatTerminal:
    def test_no_findings_message(self):
        output = format_terminal([])
        assert "No findings" in output

    def test_includes_rule_id(self):
        output = format_terminal([make_finding()])
        assert "AI_LLM_001" in output

    def test_includes_file_and_line(self):
        output = format_terminal([make_finding(file="app/rag.py", line=12)])
        assert "app/rag.py" in output
        assert ":12" in output

    def test_includes_message(self):
        output = format_terminal([make_finding(message="Missing model= argument.")])
        assert "Missing model= argument." in output

    def test_includes_total_count(self):
        findings = [make_finding(), make_finding(rule_id="AI_LLM_002")]
        output = format_terminal(findings)
        assert "2" in output

    def test_no_crash_when_line_is_none(self):
        output = format_terminal([make_finding(line=None)])
        assert "app/rag.py" in output


class TestFormatJson:
    def test_returns_valid_json(self):
        output = format_json([make_finding()])
        data = json.loads(output)
        assert isinstance(data, list)

    def test_includes_all_fields(self):
        output = format_json([make_finding()])
        data = json.loads(output)
        assert data[0]["rule_id"] == "AI_LLM_001"
        assert data[0]["severity"] == "error"
        assert data[0]["file"] == "app/rag.py"
        assert data[0]["line"] == 12

    def test_empty_findings_is_empty_array(self):
        output = format_json([])
        assert json.loads(output) == []

    def test_severity_is_plain_string_not_enum_repr(self):
        output = format_json([make_finding(severity=Severity.WARNING)])
        data = json.loads(output)
        assert data[0]["severity"] == "warning"
        assert "Severity" not in data[0]["severity"]
