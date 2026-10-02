import ast
from pathlib import Path

from .rules.base import Finding, Rule
from .rules.llm_rules import ModelNotConfiguredRule, TemperatureNotConfiguredRule, NoErrorHandlingRule
from .rules.output_rules import UnstructuredOutputRule
from .rules.rag_rules import MetadataStrippedRule, SourceAttributionMissingRule, UnboundedRetrievalRule
from .rules.agent_rules import UnboundedAgentLoopRule
from .rules.security_rules import HardcodedCredentialRule
from .rules.prompt_rules import HardcodedSystemPromptRule

ALL_RULES: list[Rule] = [
    ModelNotConfiguredRule(),
    TemperatureNotConfiguredRule(),
    NoErrorHandlingRule(),
    UnstructuredOutputRule(),
    MetadataStrippedRule(),
    SourceAttributionMissingRule(),
    UnboundedRetrievalRule(),
    UnboundedAgentLoopRule(),
    HardcodedCredentialRule(),
    HardcodedSystemPromptRule(),
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
