#!/usr/bin/env python3
"""Run paired report evaluations with Codex and grade the saved Markdown."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import re
import runpy
import subprocess
import time


EVALS = Path(__file__).resolve().parent
CASES = {case["id"]: case for case in json.loads((EVALS / "evals.json").read_text(encoding="utf-8"))["evals"]
         if case.get("runner") == Path(__file__).name}
read_closing_section = runpy.run_path(str(EVALS / "check-report-follow-up.py"))["read_closing_section"]
REFERENCES = ("SKILL.md", "references/workflows.md", "references/试穿报告模板.md")
FEATURES_OFF = ("shell_tool", "apps", "plugins", "skill_search", "tool_search",
                "multi_agent", "image_generation", "view_image", "sleep_tool")
ISSUE = re.compile(r"#([0-9]{2,})")


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def grade(case, path):
    errors, closing = read_closing_section(path)
    report = path.read_text(encoding="utf-8")
    checks = []

    def record(text, passed, evidence):
        checks.append({"text": text, "passed": passed, "evidence": evidence})

    record("报告的可见尾节是「分诊与下一步复测」，内有待办或有依据的结案说明", not errors,
           "；".join(errors) if errors else "已从拟交付文件读取尾节正文")
    numbers = set(ISSUE.findall(report))
    record("报告保留归档中的问题编号", set(case["issue_ids"]) <= numbers,
           "检测到 " + ", ".join(sorted(numbers)))
    if case["open_issues"]:
        order = list(dict.fromkeys(ISSUE.findall(closing)))
        observed = [number for number in order if number in case["open_issues"]]
        record("尾节按优先级沿用待办的问题编号", observed == case["open_issues"],
               "尾节编号 " + ", ".join(order))
    issue_lines = {}
    current = None
    for line in closing.splitlines():
        issue = ISSUE.search(line)
        if issue:
            current = issue[1]
        issue_lines.setdefault(current, []).append(line)
    for check in case["closing_assertions"]:
        excerpt = "\n".join(issue_lines.get(check["issue"], [])) if "issue" in check else closing
        missing = [" / ".join(group) for group in check["contains"]
                   if not any(term.casefold() in excerpt.casefold() for term in group)]
        record(check["text"], not missing,
               "缺少 " + "；".join(missing) if missing else excerpt.strip())
    passed = sum(check["passed"] for check in checks)
    return {"expectations": checks, "summary": {"passed": passed, "failed": len(checks) - passed,
                                                "total": len(checks), "pass_rate": passed / len(checks)}}


def run(case, skill, case_dir, arm, model):
    folder = case_dir / arm / "run-1"
    output = folder / "outputs"
    output.mkdir(parents=True)
    report = output / "report.md"
    instructions = ("按题面写完整的报告文件内容，以 Markdown 直接输出。仅使用给定的归档证据。"
                    "\n\n" + "\n\n".join((skill / ref).read_text(encoding="utf-8") for ref in REFERENCES))
    command = ["codex", "-a", "never", "exec", "--ignore-user-config", "--ignore-rules", "--ephemeral",
               "--skip-git-repo-check", "--json", "-C", str(output), "-s", "read-only", "-m", model,
               "-c", 'model_reasoning_effort="low"', "-c", 'web_search="disabled"',
               "-c", "suppress_unstable_features_warning=true",
               "-c", "developer_instructions=" + json.dumps(instructions, ensure_ascii=False),
               "--enable", "skip_host_skill_discovery", "--output-last-message", str(report)]
    for feature in FEATURES_OFF:
        command.extend(("--disable", feature))
    start = time.monotonic()
    events_path = folder / "events.jsonl"
    with events_path.open("w", encoding="utf-8") as events, (folder / "run.err").open("w") as errors:
        process = subprocess.run(command, input=case["prompt"], text=True, stdout=events, stderr=errors, timeout=180)
    events = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines()]
    usage = next((event.get("usage") for event in events if event["type"] == "turn.completed"), None)
    unexpected = {event.get("item", {}).get("type") for event in events} - {"reasoning", "agent_message", None}
    if process.returncode or usage is None or unexpected or not report.is_file():
        raise RuntimeError(f"Codex did not complete a tool-free report. See {folder}")
    write_json(folder / "timing.json", {"total_duration_seconds": time.monotonic() - start,
                                        "total_tokens": usage["input_tokens"] + usage["output_tokens"],
                                        "usage": usage, "model": model})
    result = grade(case, report)
    write_json(folder / "grading.json", result)
    score = result["summary"]
    print(f"{case['id']} {arm}: {score['passed']}/{score['total']}", flush=True)
    return score["failed"] == 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="new directory for reports, events and grades")
    parser.add_argument("--baseline", type=Path, help="skill directory containing a prior revision")
    parser.add_argument("--ids", nargs="+", type=int, choices=CASES, default=list(CASES))
    parser.add_argument("--model", default="gpt-6.2-sol")
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True)
    runs = {}
    with ThreadPoolExecutor(max_workers=4) as pool:
        for case_id in dict.fromkeys(args.ids):
            case = CASES[case_id]
            case_dir = output / f"eval-{case_id}"
            case_dir.mkdir()
            write_json(case_dir / "eval_metadata.json", {"eval_id": case_id, "eval_name": case["name"],
                                                         "prompt": case["prompt"]})
            arms = {"new_skill": EVALS.parent}
            if args.baseline:
                arms["old_skill"] = args.baseline.resolve()
            for arm, skill in arms.items():
                (case_dir / arm).mkdir()
                write_json(case_dir / arm / "eval_metadata.json", {"eval_id": case_id, "prompt": case["prompt"]})
                runs[case_id, arm] = pool.submit(run, case, skill, case_dir, arm, args.model)
        results = {key: future.result() for key, future in runs.items()}
    return 0 if all(result for (_, arm), result in results.items() if arm == "new_skill") else 1


if __name__ == "__main__":
    raise SystemExit(main())
