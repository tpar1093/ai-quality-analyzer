import ast
from .base import Finding, Rule, Severity, _walk_no_nested_fns


def _is_while_true(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.While)
        and isinstance(node.test, ast.Constant)
        and node.test.value is True
    )


def _is_blocking_input_call(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "input"
    )


def _is_human_paced(while_node: ast.While) -> bool:
    """True if the loop blocks on input() somewhere in its own body — a
    human pacing each iteration is a different risk profile than an
    autonomous loop calling an LLM with nothing gating each iteration."""
    return any(_is_blocking_input_call(n) for n in _walk_no_nested_fns(while_node))


def _is_sleep_call(node: ast.AST) -> bool:
    if not isinstance(node, ast.Call):
        return False
    if isinstance(node.func, ast.Attribute):
        return node.func.attr == "sleep"
    if isinstance(node.func, ast.Name):
        return node.func.id == "sleep"
    return False


def _is_rate_limited(while_node: ast.While) -> bool:
    """True if the loop paces itself with a sleep(...) call somewhere in its
    own body — the idiomatic shape of polling an external job until it
    completes, a different risk profile than an unbounded retry that
    hammers an LLM call immediately on every failure."""
    return any(_is_sleep_call(n) for n in _walk_no_nested_fns(while_node))


class UnboundedAgentLoopRule(Rule):
    rule_id = "AI_AGENT_001"
    title = "Agent workflow has no maximum step limit"
    rationale = (
        "Unbounded agent loops (while True) can run indefinitely, exhausting "
        "tokens and budget. Define an explicit MAX_STEPS or use a bounded range loop."
    )
    severity = Severity.ERROR

    def check(self, tree: ast.AST, filepath: str) -> list[Finding]:
        findings = []
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for child in _walk_no_nested_fns(node):
                if _is_while_true(child) and not _is_human_paced(child) and not _is_rate_limited(child):
                    findings.append(self._finding(
                        f"Function '{node.name}' contains an unbounded 'while True' loop "
                        f"with no step limit.",
                        filepath,
                        child.lineno,
                    ))
        return findings
