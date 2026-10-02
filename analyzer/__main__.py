import argparse
import sys
from pathlib import Path

from .scanner import scan_directory, scan_file, ALL_RULES
from .reporter import format_terminal, format_json


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="python -m analyzer",
        description="AI Quality Analyzer — static analysis for LLM/RAG applications.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    scan_cmd = sub.add_parser("scan", help="Scan a Python file or directory.")
    scan_cmd.add_argument("path", type=Path, help="File or directory to scan.")
    scan_cmd.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text).",
    )
    scan_cmd.add_argument(
        "--rule",
        action="append",
        dest="rule_ids",
        metavar="RULE_ID",
        help="Only run this rule (e.g. AI_LLM_001). Repeat to run a subset of rules.",
    )

    args = parser.parse_args()

    if args.command == "scan":
        target: Path = args.path
        if not target.exists():
            print(f"Error: path does not exist: {target}", file=sys.stderr)
            sys.exit(2)

        rules = ALL_RULES
        if args.rule_ids:
            known_ids = {r.rule_id for r in ALL_RULES}
            unknown = [rid for rid in args.rule_ids if rid not in known_ids]
            if unknown:
                print(f"Error: unknown rule ID(s): {', '.join(unknown)}", file=sys.stderr)
                print(f"Available rule IDs: {', '.join(sorted(known_ids))}", file=sys.stderr)
                sys.exit(2)
            selected = set(args.rule_ids)
            rules = [r for r in ALL_RULES if r.rule_id in selected]

        findings = scan_directory(target, rules) if target.is_dir() else scan_file(target, rules)

        if args.format == "json":
            print(format_json(findings))
        else:
            print(format_terminal(findings))

        sys.exit(1 if findings else 0)


if __name__ == "__main__":
    main()
