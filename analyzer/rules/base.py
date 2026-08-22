import ast
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass(frozen=True)
class Finding:
    rule_id: str
    title: str
    severity: Severity
    message: str
    rationale: str
    file: str
    line: int | None = None


def _walk_no_nested_fns(node: ast.AST):
    """Yield all AST descendants of node, but do not descend into
    nested FunctionDef, AsyncFunctionDef, or ClassDef nodes."""
    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        yield child
        yield from _walk_no_nested_fns(child)


class Rule(ABC):
    rule_id: str
    title: str
    rationale: str
    severity: Severity

    @abstractmethod
    def check(self, tree: ast.AST, filepath: str) -> list[Finding]:
        ...

    def _finding(self, message: str, filepath: str, line: int | None = None) -> Finding:
        return Finding(
            rule_id=self.rule_id,
            title=self.title,
            severity=self.severity,
            message=message,
            rationale=self.rationale,
            file=filepath,
            line=line,
        )
