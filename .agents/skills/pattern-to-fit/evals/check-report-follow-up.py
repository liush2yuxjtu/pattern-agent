#!/usr/bin/env python3
"""Grade the final triage section directly from delivered report files."""

import argparse
import json
from pathlib import Path
import runpy
import sys


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))


def check(report):
    match report.suffix.lower():
        case ".md":
            from publish_report import MARKDOWN
            from report_follow_up import markdown_follow_up_errors

            return markdown_follow_up_errors(MARKDOWN.parse(report.read_text(encoding="utf-8")))
        case ".html" | ".htm":
            gate = runpy.run_path(str(SCRIPTS / "check-standalone-html.py"))
            return gate["parse_report"](report).follow_up_errors()
        case _:
            raise ValueError("报告须为 Markdown 或 HTML")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reports", type=Path, nargs="+")
    args = parser.parse_args()
    results = []
    for report in args.reports:
        try:
            errors = check(report)
        except (OSError, ValueError) as exc:
            errors = [str(exc)]
        results.append({"report": str(report), "passed": not errors, "errors": errors})
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0 if all(result["passed"] for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
