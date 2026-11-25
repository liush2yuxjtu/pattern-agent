#!/usr/bin/env python3
"""Run a report regression using tool-less Codex headless."""

import argparse
import concurrent.futures
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


EVALS = Path(__file__).resolve().parent
FIXTURES = Path(os.environ.get("DESIGN_CLOTH_REPORT_FIXTURES", EVALS / "fixtures")).resolve()
REPORT_CASES = {
    case["id"]: case
    for case in json.loads((EVALS / "evals.json").read_text(encoding="utf-8"))["evals"]
    if case["id"] in {19, 35, 43}
}
FEATURES_OFF = (
    "shell_tool", "plugins", "skill_search", "tool_search",
    "multi_agent", "image_generation", "view_image", "sleep_tool",
)


def run(folder, skill, schema, model, case):
    folder.mkdir()
    notes, *images = [FIXTURES / file.removeprefix("fixtures/") for file in case["files"]]
    evidence = [image.relative_to(notes.parent) for image in images]
    for image, path in zip(images, evidence):
        target = folder / path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(image, target)
    references = ["SKILL.md"] + [
        "references/" + file for file in case.get("references", ["workflows.md", "试穿报告模板.md"])
    ]
    skill_text = "" if skill is None else "\n\n".join(
        (skill / file).read_text(encoding="utf-8") for file in references
    )
    instructions = (
        "Work only from the supplied evidence. Do not use tools or claim new execution. "
        "The user receives the Markdown report and the handoff message, never the machine envelope. "
        "Write each as actual reader-facing copy. The handoff message must link the report "
        f"using this exact absolute destination and human-readable name: [试穿评审报告]({folder / 'report.md'}). "
        "Use the image paths in the fixture to cite supplied images. The publisher embeds referenced "
        "images in the report, so do not instruct the reader to keep or forward sidecar images. "
        "Keep JSON field names, fixture directories, the output harness and storage details "
        "out of both pieces of reader-facing copy.\n\n"
    ) + skill_text
    prompt = case["prompt"] + "\n\n" + notes.read_text(encoding="utf-8")
    (folder / "eval_metadata.json").write_text(json.dumps({
        "eval_id": case["id"], "eval_name": case["name"], "prompt": case["prompt"],
        "assertions": case["assertions"], "injected_skill_bytes": len(skill_text.encode("utf-8")),
    }, ensure_ascii=False, indent=2) + "\n")
    result_file = folder / "result.json"
    command = [
        "codex", "-a", "never", "exec", "--ignore-user-config", "--ignore-rules",
        "--ephemeral", "--skip-git-repo-check", "--json", "-C", str(folder),
        "-s", "read-only", "-m", model, "-c", 'model_reasoning_effort="low"',
        "-c", 'web_search="disabled"',
        "-c", "developer_instructions=" + json.dumps(instructions, ensure_ascii=False),
        "--enable", "skip_host_skill_discovery", "--output-schema", str(schema),
        "--output-last-message", str(result_file),
    ]
    for feature in FEATURES_OFF:
        command.extend(["--disable", feature])
    attachments = case.get("image_attachments", [path.name for path in evidence])
    for image in evidence:
        if image.name in attachments:
            command.extend(["--image", str(folder / image)])
    events_file = folder / "events.jsonl"
    with events_file.open("w") as events, (folder / "run.err").open("w") as err:
        result = subprocess.run(command, input=prompt, text=True, stdout=events, stderr=err, timeout=180)
    if result.returncode:
        raise RuntimeError(f"Codex failed. See {folder / 'run.err'}")
    events = [json.loads(line) for line in events_file.read_text().splitlines()]
    item_types = {event.get("item", {}).get("type") for event in events}
    if item_types - {None, "agent_message", "reasoning", "error"}:
        raise RuntimeError(f"Unexpected tool activity. See {events_file}")
    if not any(event["type"] == "turn.completed" for event in events):
        raise RuntimeError(f"Turn did not complete. See {events_file}")
    payload = json.loads(result_file.read_text(encoding="utf-8"))
    report = folder / "report.md"
    if payload["report"].strip():
        report.write_text(payload["report"], encoding="utf-8")
        publish = subprocess.run([
            sys.executable, str(EVALS.parent / "scripts" / "publish_report.py"),
            str(report), str(report),
        ], text=True, capture_output=True)
        (folder / "publish.log").write_text(publish.stdout + publish.stderr, encoding="utf-8")
    reply = folder / "reply.md"
    reply.write_text(payload["reply"], encoding="utf-8")
    command = [sys.executable, str(EVALS / "check-report-delivery.py"), str(reply),
               "--evidence", *(str(path) for path in evidence)]
    check = subprocess.run(command, text=True, capture_output=True)
    (folder / "delivery-check.json").write_text(json.dumps({
        "passed": check.returncode == 0, "evidence_count": len(evidence),
        "detail": (check.stdout or check.stderr).strip(),
    }, ensure_ascii=False, indent=2) + "\n")
    grade = subprocess.run([
        sys.executable, str(EVALS / "grade-report-readability.py"),
        str(folder), "--case", str(case["id"]),
    ], text=True, capture_output=True)
    (folder / "grading.log").write_text(grade.stdout + grade.stderr, encoding="utf-8")
    if not (folder / "grading.json").is_file():
        raise RuntimeError(f"Report grader produced no score. See {folder / 'grading.log'}")
    print(f"{folder.name}: {'PASS' if not check.returncode and not grade.returncode else 'FAIL'} "
          f"{(check.stdout or check.stderr).strip()}", flush=True)
    return check.returncode or grade.returncode


def main():
    parser = argparse.ArgumentParser(description=__doc__, epilog=(
        "Review report.md and reply.md against the semantic assertions in evals.json. "
        "The checker verifies file delivery, rendered evidence, and the closing triage and follow-up section."
    ))
    parser.add_argument("output", type=Path, help="New directory for evaluation artifacts")
    comparison = parser.add_mutually_exclusive_group()
    comparison.add_argument("--baseline", type=Path, help="Optional pre-change skill snapshot")
    comparison.add_argument("--without-skill", action="store_true",
                            help="Also run an independent control with no injected skill text")
    parser.add_argument("--case", type=int, choices=REPORT_CASES, default=19)
    parser.add_argument("--model", default="gpt-6.2-sol")
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True)
    schema = output / "schema.json"
    schema.write_text(json.dumps({
        "type": "object", "additionalProperties": False,
        "properties": {"report": {"type": "string", "description": "Complete Markdown for the report reader"},
            "reply": {"type": "string", "description": "Final user-facing delivery message"}},
        "required": ["report", "reply"],
    }))
    with concurrent.futures.ThreadPoolExecutor() as pool:
        case = REPORT_CASES[args.case]
        current = pool.submit(run, output / "current", EVALS.parent, schema, args.model, case)
        if args.baseline or args.without_skill:
            baseline_skill = args.baseline.resolve() if args.baseline else None
            baseline_name = "without_skill" if args.without_skill else "baseline"
            baseline = pool.submit(run, output / baseline_name, baseline_skill, schema, args.model, case)
            baseline.result()
        return current.result()


if __name__ == "__main__":
    raise SystemExit(main())
