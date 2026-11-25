#!/usr/bin/env python3
"""Exercise report graders and both formal report export formats."""

from base64 import b64decode
import json
import os
from pathlib import Path
import re
import runpy
import struct
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
import zlib


EVALS = Path(__file__).resolve().parent
GATE = runpy.run_path(str(EVALS / "check-report-follow-up.py"))
MISSING, NOT_LAST, REPEATED, EMPTY = (GATE[name] for name in ("MISSING", "NOT_LAST", "REPEATED", "EMPTY"))
TITLE = "分诊与下一步复测"
BODY = "#03 用同一人台与面料重开侧平举，确认左袖口零穿插。"


def section(body=f"<p>{BODY}</p>", attributes="", title=TITLE):
    return f"<section {attributes}><h2>{title}</h2>{body}</section>"


class ClosingTriage(unittest.TestCase):
    def check(self, document, suffix):
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / f"report{suffix}"
            path.write_text(document, encoding="utf-8")
            return GATE["read_closing_section"](path)[0]

    def test_markdown_final_section_with_child_headings_and_reference_definitions(self):
        report = f"# 报告\n\n## 附录\n\n## 七、{TITLE}\n\n### 先做\n\n1. {BODY}\n\n[图]: #附录"
        self.assertEqual(self.check(report, ".md"), [])

    def test_markdown_formatted_heading(self):
        self.assertEqual(self.check(f"## **七、{TITLE}**\n\n{BODY}", ".md"), [])

    def test_markdown_explicit_scoped_closure_in_english(self):
        report = "## Triage and Next Follow-up\n\nAll checks in the agreed shoulder scope passed. No retest remains."
        self.assertEqual(self.check(report, ".md"), [])

    def test_markdown_legacy_heading_is_rejected(self):
        self.assertEqual(self.check(f"## 结论与复测标准\n\n{BODY}", ".md"), [MISSING])

    def test_markdown_quoted_or_fenced_examples_are_rejected(self):
        for report in (f"> ## {TITLE}\n> {BODY}", f"```markdown\n## {TITLE}\n\n{BODY}\n```"):
            with self.subTest(report=report):
                self.assertEqual(self.check(report, ".md"), [MISSING])

    def test_markdown_appendix_after_triage_is_rejected(self):
        for appendix in ("## 附录", "附录\n----", "<h2>附录</h2>"):
            with self.subTest(appendix=appendix):
                self.assertEqual(self.check(f"## {TITLE}\n\n{BODY}\n\n{appendix}\n\n附图。", ".md"), [NOT_LAST])

    def test_duplicate_markdown_triage_is_rejected(self):
        report = f"## {TITLE}\n\n{BODY}\n\n## 七、{TITLE}\n\n{BODY}"
        self.assertEqual(self.check(report, ".md"), [REPEATED])

    def test_markdown_placeholder_link_only_or_unsupported_closure_is_rejected(self):
        for body in ("", "**待补充**", "待补证", "〔填写后续〕", "[查看证据](#evidence)", "详见附录。", "已结案。"):
            with self.subTest(body=body):
                self.assertEqual(self.check(f"## {TITLE}\n\n{body}", ".md"), [EMPTY])

    def test_html_scope_ignores_page_footer_outside_the_report(self):
        html = f"<main><article>{section()}</article></main><footer><h2>页脚</h2></footer>"
        self.assertEqual(self.check(html, ".html"), [])

    def test_html_heading_in_navigation_or_script_is_rejected(self):
        for tag in ("nav", "script", "template"):
            with self.subTest(tag=tag):
                self.assertEqual(self.check(f"<main><{tag}>{section()}</{tag}></main>", ".html"), [MISSING])

    def test_html_hidden_heading_cannot_satisfy_the_gate(self):
        for attrs in ('hidden', 'aria-hidden="true"', 'style="display: none"',
                      'style="color: red; VISIBILITY: hidden !important;"'):
            with self.subTest(attrs=attrs):
                self.assertEqual(self.check(f"<main><div {attrs}>{section()}</div></main>", ".html"), [MISSING])

    def test_html_hidden_or_link_only_body_is_rejected(self):
        for body in (f"<p hidden>{BODY}</p>", '<p><a href="#data">查看数据</a></p>', "<p>请见附录 A。</p>"):
            with self.subTest(body=body):
                self.assertEqual(self.check(f"<main>{section(body)}</main>", ".html"), [EMPTY])

    def test_html_rejects_follow_up_when_collapsed(self):
        html = f"<main><details><summary>继续查看</summary>{section()}</details></main>"
        self.assertEqual(self.check(html, ".html"), [MISSING])

    def test_html_second_report_section_cannot_be_hidden_in_an_article_boundary(self):
        for appendix in ("<section><h3>附录</h3></section>", "<details><summary>附录</summary></details>",
                         '<img src="fig.png" alt="补充证据">', "图像附录"):
            with self.subTest(appendix=appendix):
                html = f"<main><article>{section()}</article>{appendix}</main>"
                self.assertEqual(self.check(html, ".html"), [NOT_LAST])

    def test_html_duplicate_heading_is_rejected(self):
        self.assertEqual(self.check(f"<main>{section()}{section()}</main>", ".html"), [REPEATED])

    def test_checker_cli_grades_every_saved_file(self):
        with TemporaryDirectory() as temporary:
            path = Path(temporary)
            good, bad = path / "good.md", path / "bad.html"
            good.write_text(f"## {TITLE}\n\n{BODY}", encoding="utf-8")
            bad.write_text(section(attributes="hidden"), encoding="utf-8")
            result = subprocess.run([sys.executable, str(EVALS / "check-report-follow-up.py"), good, bad],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertEqual([row["passed"] for row in json.loads(result.stdout)], [True, False])

    def test_case_grader_binds_acceptance_terms_to_their_issue(self):
        runner = runpy.run_path(str(EVALS / "run-report-evals.py"))
        case = runner["CASES"][39]
        repair = "Style3D 沿用人台与面料侧平举，左袖口 0 对穿插，包覆保持。见 [R03](#evidence-r03)。"
        pressure = "补采人体侧 kPa 读数，未补齐前阻塞放行。见 [R04](#evidence-r04)。"
        with TemporaryDirectory() as temporary:
            report = Path(temporary) / "report.md"
            for actions, expected in (([repair, pressure], 5), ([pressure, repair], 3)):
                with self.subTest(actions=actions):
                    report.write_text(f"# 复核\n\n#02 已修。\n\n## {TITLE}\n\n"
                                      f"### #03\n\n{actions[0]}\n\n### #04\n\n{actions[1]}", encoding="utf-8")
                    self.assertEqual(runner["grade"](case, report)["summary"]["passed"], expected)


def png(red):
    def chunk(name, data):
        return struct.pack(">I", len(data)) + name + data + struct.pack(">I", zlib.crc32(name + data))

    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(bytes((0, red, 40, 100)))) + chunk(b"IEND", b""))


class BakeReport(unittest.TestCase):
    def setUp(self):
        folder = TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name).resolve() / "package"
        self.root.mkdir()
        self.delivery = self.root.with_name("delivery")
        self.delivery.symlink_to(self.root, target_is_directory=True)
        self.manifest = self.root / "manifest.json"
        self.images = []
        postures = []
        for posture in ("站姿", "垂臂", "侧平举", "前伸"):
            figures = {}
            for kind in ("appearance", "strain", "stress", "pressure", "folds"):
                index = len(self.images)
                data = png(index)
                path = self.root / f"figure-{index}.png"
                path.write_bytes(data)
                self.images.append((path, data))
                figures[kind] = path.name
            postures.append({"name": posture, "images": figures})
        self.data = {"title": "M 码上衣", "revision": "TEST", "size": "M", "postures": postures,
                     "nextSteps": [BODY]}

    def bake(self, suffix):
        self.manifest.write_text(json.dumps(self.data, ensure_ascii=False), encoding="utf-8")
        output = self.delivery / f"report{suffix}"
        command = ["node", EVALS.parent / "scripts" / "bake-report.mjs", self.manifest, output]
        if sharp := os.environ.get("DESIGN_CLOTH_SHARP"):
            command.extend(("--sharp", sharp))
        return output, subprocess.run(command, capture_output=True, text=True)

    def test_bakes_markdown_with_twenty_embedded_evidence_images_and_final_triage(self):
        self.data["recommendation"] = "保留圆领，按已验范围定稿。"
        output, result = self.bake(".md")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(GATE["read_closing_section"](output), ([], BODY))
        from markdown_it import MarkdownIt

        report = output.read_text(encoding="utf-8")
        rendered = MarkdownIt("commonmark", {"html": True}).render(report)
        self.assertLess(rendered.index("<strong>保留圆领"), rendered.index("<details>"))
        self.assertEqual(rendered.split("</details>")[0].count("<img "), 20)
        self.assertLess(rendered.index("</details>"), rendered.index("<h2>分诊与下一步复测"))
        images = re.findall(r'data:image/png;base64,([^"\s]+)', rendered)
        self.assertEqual([b64decode(image, validate=True) for image in images], [data for _, data in self.images])

    def test_bakes_html_with_twenty_original_embeds_and_final_triage(self):
        output, result = self.bake(".html")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(GATE["read_closing_section"](output), ([], BODY))
        images = re.findall(r'data:image/png;base64,([^\"]+)', output.read_text(encoding="utf-8"))
        self.assertEqual([b64decode(image, validate=True) for image in images], [data for _, data in self.images])

    def test_missing_or_blank_next_steps_cannot_replace_an_existing_report(self):
        for suffix in (".md", ".html"):
            output = self.root / f"report{suffix}"
            output.write_bytes(b"previous report")
            for next_steps in (None, [], [" "]):
                with self.subTest(suffix=suffix, next_steps=next_steps):
                    if next_steps is None:
                        self.data.pop("nextSteps", None)
                    else:
                        self.data["nextSteps"] = next_steps
                    _, result = self.bake(suffix)
                    self.assertEqual(result.returncode, 1)
                    self.assertIn("nextSteps", result.stderr)
                    self.assertEqual(output.read_bytes(), b"previous report")


if __name__ == "__main__":
    unittest.main()
