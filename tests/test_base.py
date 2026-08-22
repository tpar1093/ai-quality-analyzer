import ast
import pytest
from analyzer.rules.base import Finding, Severity, Rule, _walk_no_nested_fns


def test_finding_fields_accessible():
    f = Finding(
        rule_id="AI_LLM_001",
        title="Test",
        severity=Severity.ERROR,
        message="msg",
        rationale="why",
        file="test.py",
        line=5,
    )
    assert f.rule_id == "AI_LLM_001"
    assert f.severity == Severity.ERROR
    assert f.line == 5


def test_severity_is_string():
    assert Severity.ERROR == "error"
    assert Severity.WARNING == "warning"
    assert Severity.INFO == "info"


def test_walk_no_nested_fns_skips_inner_function_body():
    code = """
def outer():
    def inner():
        while True:
            pass
"""
    tree = ast.parse(code)
    outer_fn = tree.body[0]
    nodes = list(_walk_no_nested_fns(outer_fn))
    # The while True is inside inner() — should not appear
    assert not any(isinstance(n, ast.While) for n in nodes)
    # inner() itself should not appear either
    assert not any(
        isinstance(n, ast.FunctionDef) and n.name == "inner" for n in nodes
    )


def test_walk_no_nested_fns_finds_direct_while():
    code = """
def outer():
    while True:
        pass
"""
    tree = ast.parse(code)
    outer_fn = tree.body[0]
    nodes = list(_walk_no_nested_fns(outer_fn))
    assert any(isinstance(n, ast.While) for n in nodes)
