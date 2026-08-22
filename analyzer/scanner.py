import ast
from pathlib import Path

from .rules.base import Finding, Rule
from .rules.llm_rules import ModelNotConfiguredRule, TemperatureNotConfiguredRule
from .rules.output_rules import UnstructuredOutputRule
from .rules.rag_rules import MetadataStrippedRule, SourceAttributionMissingRule
from .rules.agent_rules import UnboundedAgentLoopRule

ALL_RULES: list[Rule] = [
    ModelNotConfiguredRule(),
    TemperatureNotConfiguredRule(),
    UnstructuredOutputRule(),
    MetadataStrippedRule(),
    SourceAttributionMissingRule(),
    UnboundedAgentLoopRule(),
]


def scan_file(path: Path, rules: list[Rule] = ALL_RULES) -> list[Finding]:
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
    except (SyntaxError, UnicodeDecodeError):
        return []
    findings: list[Finding] = []
    for rule in rules:
        findings.extend(rule.check(tree, str(path)))
    return findings


def scan_directory(path: Path, rules: list[Rule] = ALL_RULES) -> list[Finding]:
    findings: list[Finding] = []
    for py_file in sorted(path.rglob("*.py")):
        findings.extend(scan_file(py_file, rules))
    return findings
