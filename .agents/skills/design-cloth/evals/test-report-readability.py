#!/usr/bin/env python3
"""Focused controls for designer-facing report and reply grading."""

from pathlib import Path
import runpy
import unittest

GRADER = runpy.run_path(str(Path(__file__).with_name("grade-report-readability.py")))
grade = GRADER["grade"]

REPORT = """# S 码试穿评审

**暂缓定稿。** 保留圆领和衣长。

<details>
<summary>落臂后前领和下摆仍抬高 · S 码</summary>

落臂后前领升高 2.43 cm，前下摆升高 4.00 cm。

![落臂后正面](证据/回位.png)

</details>

## 分诊与下一步复测

1. 版师试调腋下活动量。检查落臂以后领口和下摆是否回位。
"""
REPLY = "[试穿评审报告](/path/to/report.md)建议暂缓定稿。"


class ReportReadability(unittest.TestCase):
    def checks(self, report=REPORT, reply=REPLY, delivery=(True, "fixture check")):
        return {name: (ok, evidence) for name, ok, evidence in grade(report, reply, 43, delivery)}

    def check(self, results, prefix):
        return next(ok for name, (ok, _) in results.items() if name.startswith(prefix))

    def test_readable_report_passes_and_image_path_is_transport(self):
        self.assertTrue(all(ok for ok, _ in self.checks().values()))

    def test_raw_artifacts_in_closed_details_fail(self):
        raw = "原生交叉对数分别为 344、81。压力样本有 53,734 个。网格顶点有 53,930 个。"
        report = REPORT.replace("</details>", f"{raw}\n\n</details>")
        self.assertFalse(self.check(self.checks(report), "正文和全部折叠区"))

    def test_file_links_and_sample_stats_fail(self):
        raw = "[读数](metrics.csv) · [工程](project.zprj) · 第 150 帧 · 领条 P95 为 0.84 kPa。"
        report = REPORT.replace("</details>", f"{raw}\n\n</details>")
        self.assertFalse(self.check(self.checks(report), "正文和全部折叠区"))

    def test_raw_pressure_value_without_percentile_fails(self):
        errors = GRADER["artifact_errors"](GRADER["visible"]("可能受压的位置在领条。原始读数为 0.84 kPa。"))
        self.assertTrue(errors)
        self.assertFalse(GRADER["artifact_errors"](GRADER["visible"]("前领仍高 2.4 cm。舒适度未验证。")))

    def test_reply_harness_fields_and_image_folder_handoff_fail(self):
        for leak in ("Markdown 评审在 `report` 字段。", "转发时请将报告和原图放在同一目录。"):
            with self.subTest(leak=leak):
                self.assertFalse(self.check(self.checks(reply=REPLY + "\n\n" + leak), "交付答复"))

    def test_human_simulation_handoff_and_technical_tail_fail(self):
        tail = "请版师先复跑 CLO。请用户选择仿真设置。"
        report = REPORT + "\n" + tail
        checks = self.checks(report)
        self.assertFalse(self.check(checks, "不让用户"))
        self.assertFalse(self.check(checks, "末节只列"))

    def test_technical_operation_in_table_tail_fails(self):
        report = REPORT + "\n| # | 事项 | 归类 |\n| --- | --- | --- |\n| 2 | 重跑仿真 | 自动做 |\n"
        self.assertFalse(self.check(self.checks(report), "末节只列"))

    def test_explicit_no_garment_action_is_valid(self):
        report = REPORT.split("1. 版师")[0] + "本轮无设计或纸样待办。"
        self.assertTrue(self.check(self.checks(report), "末节只列"))

    def test_neutral_metadata_before_opinion_fails(self):
        report = REPORT.replace("**暂缓定稿。**", "本轮为 S 码。\n\n**暂缓定稿。**")
        self.assertFalse(self.check(self.checks(report), "首段明确"))

    def test_missing_displacement_fails_case_semantics(self):
        report = REPORT.replace("4.00 cm", "少许")
        self.assertFalse(self.check(self.checks(report), "保留本款"))

    def test_pressure_scope_can_use_garment_language(self):
        text = ("侧举时双袖脱离上臂，右肩有非设计露肤。保留左露肩开口。"
                "四个姿势的人体侧叠层颜色只提示可能受压的位置。"
                "人体侧读数尚无法与图上身体部位可靠对应，舒适度未验证。")
        self.assertTrue(GRADER["garment_result"](35, text, "暂缓定稿。")[0])

    def test_does_not_claim_native_simulation_verified(self):
        results = self.checks()
        evidence = next(evidence for name, (_, evidence) in results.items() if name.startswith("不让用户"))
        self.assertIn("未验证原生执行", evidence)

    def test_delivery_fail_is_a_failed_expectation(self):
        self.assertFalse(self.check(self.checks(delivery=(False, "no embedded image")), "报告链接"))


if __name__ == "__main__":
    unittest.main()
