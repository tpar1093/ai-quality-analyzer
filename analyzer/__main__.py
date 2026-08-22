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

    args = parser.parse_args()

    if args.command == "scan":
        target: Path = args.path
        if not target.exists():
            print(f"Error: path does not exist: {target}", file=sys.stderr)
            sys.exit(2)

        findings = scan_directory(target) if target.is_dir() else scan_file(target)

        if args.format == "json":
            print(format_json(findings))
        else:
            print(format_terminal(findings))

        sys.exit(1 if findings else 0)


if __name__ == "__main__":
    main()
