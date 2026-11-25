#!/usr/bin/env python3
"""Deterministic release gate regressions, using synthetic controls only."""

from base64 import b64encode
import importlib.util
from pathlib import Path
import struct
from tempfile import TemporaryDirectory
import unittest
import zlib

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check-standalone-html.py"
SPEC = importlib.util.spec_from_file_location("html_gate", SCRIPT)
gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gate)


def image(index):
    # Different pixels keep one evidence figure per pose and category.
    def chunk(kind, payload):
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload))
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(bytes([0, index, 64, 128])))
    return "data:image/png;base64," + b64encode(png + chunk(b"IEND", b"")).decode("ascii")


def fixture():
    prefix = f"""
<!doctype html><title>已核数字验收</title><main>
<section id="focus"><h2>先看结果</h2><p>M 码 V1 四姿势数字验收完成。</p></section>
<section id="evidence"><h2>关键证据</h2><figure><img src="{image(0)}" alt="自然站立正面"><figcaption>自然站立正面，见袖口</figcaption></figure></section>
<section id="audit"><h2>完整证据</h2><details><summary>展开逐姿势图及读数</summary>
"""
    poses = {}
    figures = []
    for pose_index, pose in enumerate(("自然站立", "垂臂", "侧平举", "前伸")):
        methods = {}
        for category_index, category in enumerate(sorted(gate.CATEGORIES)):
            key = f"f{pose_index}-{category}"
            methods[category] = {"status": "pass", "anchor": key,
                                 "basis": "合成夹具的通过依据", "source": "夹具，并非实测"}
            ident = 1 + 5 * pose_index + category_index
            figures.append(f'<figure id="{key}"><img src="{image(ident)}" alt="{pose} {category}"><figcaption>{pose} {category} · 合成图</figcaption></figure>')
        poses[pose] = methods
    review = {"revision": "V1", "sizes": {"M": poses}}
    follow_up = """
<section id="follow-up"><h2>分诊与下一步复测</h2>
<p>版师依自然站立袖口位置核实实样。</p><a href="#evidence">袖口基准图</a></section>
"""
    return prefix + "\n".join(figures) + "</details></section>" + follow_up + "</main>", review


class HtmlGate(unittest.TestCase):
    def errors(self, html, review):
        with TemporaryDirectory() as folder:
            target = Path(folder) / "review.html"
            target.write_text(html, encoding="utf-8")
            return gate.verify(target, review)[0]

    def test_complete_review(self):
        self.assertEqual(self.errors(*fixture()), [])

    def test_follow_up_must_be_the_last_report_section(self):
        html, review = fixture()
        appendix = "<section><h2>附录</h2><p>补充资料。</p></section>"
        self.assertIn(gate.NOT_LAST, self.errors(html.replace("</main>", appendix + "</main>"), review))

    def test_missing_fifth_category(self):
        html, review = fixture()
        del review["sizes"]["M"]["前伸"]["pressure"]
        self.assertTrue(self.errors(html, review))

    def test_three_pose_partial(self):
        html, review = fixture()
        del review["sizes"]["M"]["侧平举"]
        self.assertTrue(self.errors(html, review))

    def test_folded_evidence_cannot_release_pending_pressure(self):
        html, review = fixture()
        review["sizes"]["M"]["垂臂"]["pressure"]["status"] = "pending"
        self.assertTrue(self.errors(html, review))

    def test_figure_anchor_must_not_be_reused(self):
        html, review = fixture()
        pose = review["sizes"]["M"]["自然站立"]
        pose["strain"]["anchor"] = pose["stress"]["anchor"]
        self.assertTrue(self.errors(html, review))

    def test_rejects_relative_image_file(self):
        html, review = fixture()
        self.assertTrue(self.errors(html.replace(image(1), "evidence-stress.png"), review))

    def test_rejects_active_code(self):
        html, review = fixture()
        self.assertTrue(self.errors(html.replace("</main>", "<script>alert(1)</script></main>"), review))

    def test_rejects_missing_next_step_target(self):
        html, review = fixture()
        self.assertTrue(self.errors(html.replace('href="#evidence"', 'href="#missing"'), review))

    def test_rejects_default_open_evidence(self):
        html, review = fixture()
        self.assertTrue(self.errors(html.replace("<details>", "<details open>"), review))

    def test_requires_meaningful_feature_caption(self):
        html, review = fixture()
        self.assertTrue(self.errors(html.replace("自然站立正面，见袖口", " "), review))

    def test_requires_meaningful_fold_summary(self):
        html, review = fixture()
        self.assertTrue(self.errors(html.replace("展开逐姿势图及读数", " "), review))

    def test_requires_visible_summary_and_next_step(self):
        html, review = fixture()
        for section in ("focus", "follow-up"):
            with self.subTest(section=section):
                heading = f'<section id="{section}">'
                before, rest = html.split(heading, 1)
                section_body, suffix = rest.split("</section>", 1)
                encoded = before + '<details><summary>打开</summary>' + heading + section_body + "</section></details>" + suffix
                self.assertTrue(self.errors(encoded, review))


if __name__ == "__main__":
    unittest.main()
