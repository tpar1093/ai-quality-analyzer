import json
from .rules.base import Finding, Severity

_COLORS = {
    Severity.ERROR: "\033[91m",
    Severity.WARNING: "\033[93m",
    Severity.INFO: "\033[94m",
}
_RESET = "\033[0m"


def _finding_to_dict(f: Finding) -> dict:
    return {
        "rule_id": f.rule_id,
        "title": f.title,
        "severity": f.severity.value,
        "message": f.message,
        "rationale": f.rationale,
        "file": f.file,
        "line": f.line,
    }


def format_terminal(findings: list[Finding]) -> str:
    if not findings:
        return "No findings. All checks passed.\n"
    lines: list[str] = []
    for f in findings:
        color = _COLORS.get(f.severity, "")
        location = f"{f.file}:{f.line}" if f.line is not None else f.file
        lines.append(f"{color}[{f.severity.upper()}]{_RESET} {f.rule_id}: {f.title}")
        lines.append(f"  Location : {location}")
        lines.append(f"  Finding  : {f.message}")
        lines.append(f"  Rationale: {f.rationale}")
        lines.append("")
    lines.append(f"Total: {len(findings)} finding(s)")
    return "\n".join(lines)


def format_json(findings: list[Finding]) -> str:
    return json.dumps([_finding_to_dict(f) for f in findings], indent=2)
