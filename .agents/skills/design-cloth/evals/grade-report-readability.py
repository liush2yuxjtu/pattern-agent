#!/usr/bin/env python3
"""Grade a fit report and its handoff as read by a designer or pattern maker."""

import argparse
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import unquote, urlsplit

from markdown_it import MarkdownIt

EVALS = Path(__file__).resolve().parent
FIXTURES = Path(os.environ.get("DESIGN_CLOTH_REPORT_FIXTURES", EVALS / "fixtures")).resolve()
sys.path.insert(0, str(EVALS.parent / "scripts"))
from report_follow_up import is_follow_up_heading

MARKDOWN = MarkdownIt("commonmark", {"html": True}).enable("table")
CASES = {
    19: (("裤脚",), ("磨白", "洗水"), ("版师", "设计师")),
    35: (("双袖", "两侧袖"), ("右肩",), ("左肩", "左露肩")),
    43: (("领口", "前领"), ("下摆",), ("落臂", "放臂", "回位")),
}
ARTIFACTS = {
    "原始文件或工程链接": re.compile(
        r"(?:[\w/%.-]|[\u3400-\u9fff])+\.(?:csv|jsonl?|zprj|zpac|obj|fbx|ply|stl|log|py|mjs|sh|mp4|mov)\b",
        re.I,
    ),
    "原生帧号": re.compile(
        r"(?:源帧|源动作帧|原生帧|峰值帧|帧号)\s*(?:为|[:：])?\s*\d"
        r"|(?:源动作|原生|CLO)[^\n。；]{0,22}第?\s*\d+\s*帧"
        r"|第\s*\d+\s*帧",
        re.I,
    ),
    "原始工程计数": re.compile(
        r"(?:交叉对数|穿插对数|网格顶点|压力样本|采样点|覆盖探测点)"
        r"[^\n。；]{0,48}\d|\d[\d,，]*\s*(?:组|个|对)?\s*(?:压力样本|网格顶点|交叉对|探测点)",
        re.I,
    ),
    "求解配置": re.compile(
        r"粒子间距|碰撞(?:偏移|间距)|求解(?:器|参数|设置)|根节点|子步|\d+\s*帧预热|"
        r"(?:新\s*fork|Boat\s*沙盒|运行日志|发布清单|调试日志)",
        re.I,
    ),
    "原始分位或压力读数": re.compile(
        r"\bP\s*95\b|第\s*95\s*百分位|\d+(?:[.,]\d+)?\s*kPa\b", re.I
    ),
    "交付实现细节": re.compile(
        r"(?:report|reply)\s*字段|评测器落盘|相对路径|内嵌数据定义|"
        r"(?:证据|images|outputs|fixtures)/[^\s。，；）)]+/?|"
        r"(?:转交|转发|发送|一同|同一目录)[^。；\n]{0,55}(?:原图|附件图片|图片目录|证据目录|目录)|"
        r"(?:原图|附件图片|图片目录|证据目录)[^。；\n]{0,55}(?:同一目录|一起发|一同发)",
        re.I,
    ),
}
TECH_ACTION = (
    r"(?:复跑|重跑|启动|运行|复现|补跑|导出|补采|取证|采集|采图|复开|回读|记录|选择|确认|"
    r"重开|打开|复制|检查|排查|定位|更新|匹配|配对|读取|另存)"
)
TECH_OBJECT = (
    r"(?:仿真|Style3D|CLO|Boat|姿势设置|求解|原生工程|工程副本|原生回放|原始网格|技术补证|"
    r"原生读数|压力(?:配对|样本)|帧号|峰值帧|同帧|正式验收补证|量化指标补证|"
    r"(?:图层|叠层|人台碰撞参数))"
)
USER_TECH = re.compile(
    r"(?:请(?:你|用户|版师|设计师|开发者|工程师|仿真员|仿真人员)?|"
    r"(?:由|交给|分派给|转给)(?:你|用户|版师|设计师|开发者|工程师|仿真员|仿真人员)|"
    r"(?:你|用户|版师|设计师|开发者|工程师|仿真员|仿真人员)(?:[：:，,]|须|需|应|先|直接|负责))"
    r"[^。；！？\n]{0,34}" + TECH_ACTION + r"[^。；！？\n]{0,20}" + TECH_OBJECT
    + r"|(?:请|让|由)(?:你|用户|版师|设计师|开发者|工程师)?[^。；！？\n]{0,13}"
    r"(?:选(?:择)?|决定|批准|审批)[^。；！？\n]{0,12}(?:仿真|软件|求解设置|复跑姿势|复测顺序)"
    + r"|(?:由|交给|转给)(?:开发者|工程师|仿真员|仿真人员)[^。；！？\n]{0,30}(?:复测|仿真|取证|补证)",
    re.I,
)
TAIL_TECH = re.compile(
    TECH_ACTION + r"[^。；！？\n]{0,14}" + TECH_OBJECT
    + r"|(?:仿真|技术补证|仿真复测)[^。；！？\n]{0,12}(?:自动做|由智能体执行|待执行|由我执行)"
    + r"|(?:原生)?(?:工程|仿真|CLO|Style3D|Boat)[^。；！？\n]{0,15}(?:复开|重开|复跑|待启动|取证|补证)",
    re.I,
)
HUMAN_ROLE = re.compile(r"版师|设计师|工艺师|设计方")
HUMAN_ACTION = re.compile(r"调整|试调|核对|确认|比较|检查|选择|保留|修改|增加|减少|试改|确定|评估|复核|看|验证|测量|量测|恢复")
NO_HUMAN = re.compile(r"本轮无(?:需)?(?:设计或纸样|设计与纸样|设计师或版师|服装|人工)(?:待办|决定|调整|事项|改动)")
OPINION = re.compile(r"暂缓|暂不|暂不能|不宜|不予|不建议|可定稿|建议定稿|可以定稿|同意定稿|"
                     r"不(?:能|可|得)定稿|维持(?:现状|设计)|(?:先|优先)(?:修|改|调整)|"
                     r"(?:试穿|验收|复核)[^。；\n]{0,8}(?:未通过|不通过|通过)")


class VisibleContent(HTMLParser):
    """Collect all report text, including collapsed sections, without image payloads."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hrefs = []
        self.summaries = 0

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            href = dict(attrs).get("href")
            if href:
                self.hrefs.append(unquote(href))
        if tag == "img":
            self.parts.append(dict(attrs).get("alt", ""))
        if tag == "summary":
            self.summaries += 1
        if tag not in {"a", "b", "strong", "em", "i", "span", "code"}:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag not in {"a", "b", "strong", "em", "i", "span", "code"}:
            self.parts.append("\n")

    def handle_data(self, data):
        self.parts.append(data)

    @property
    def text(self):
        return "".join(self.parts)


def visible(markdown):
    result = VisibleContent()
    result.feed(MARKDOWN.render(markdown))
    result.close()
    return result


def first_opinion(report):
    tokens = MARKDOWN.parse(report)
    in_title = False
    for index, token in enumerate(tokens):
        if token.type == "heading_open" and token.level == 0:
            if not in_title and token.tag == "h1":
                in_title = True
                continue
            return ""
        if token.type == "inline" and token.level == 1 and tokens[index - 1].type == "paragraph_open":
            return visible(token.content).text.strip()
    return ""


def closing_source(report):
    tokens = MARKDOWN.parse(report)
    for i, token in enumerate(tokens):
        if token.type == "heading_open" and token.level == 0 and is_follow_up_heading(tokens[i + 1].content):
            return "\n".join(report.splitlines()[token.map[1]:])
    return ""


def hits(pattern, text):
    return [match.group(0).strip() for match in pattern.finditer(text)]


def artifact_errors(content):
    errors = []
    for category, pattern in ARTIFACTS.items():
        excerpts = hits(pattern, content.text)
        if category == "原始文件或工程链接":
            for href in content.hrefs:
                path = urlsplit(href).path
                if path and pattern.search(path):
                    excerpts.append(path)
        if excerpts:
            errors.append(f"{category}：{'、'.join(list(dict.fromkeys(excerpts))[:3])}")
    return errors


def delivery_check(directory, case_id):
    case = next(case for case in json.loads((EVALS / "evals.json").read_text())["evals"] if case["id"] == case_id)
    notes, *images = [FIXTURES / path.removeprefix("fixtures/") for path in case["files"]]
    image_paths = [str(image.relative_to(notes.parent)) for image in images]
    result = subprocess.run(
        [sys.executable, str(EVALS / "check-report-delivery.py"), str(directory / "reply.md"), "--evidence", *image_paths],
        capture_output=True, text=True,
    )
    return result.returncode == 0, (result.stdout if result.returncode == 0 else result.stderr).strip()


def garment_result(case_id, text, opening):
    hold = re.search(r"暂缓|暂不|暂不能|无法|不宜|不予|不建议|不能|不(?:可|得)|未通过", opening)
    if case_id == 19:
        checks = {
            "直立与斜站外观范围": re.search(r"直立|站立|站姿", text) and "斜站" in text and "外观" in text,
            "整衣暂缓": hold and re.search(r"未验证|未采证|未采|尚缺|待验", text),
        }
    elif case_id == 35:
        checks = {
            "侧举双袖脱离": re.search(r"侧举|T\s*姿势", text)
            and re.search(r"(?:双袖|两侧袖|两只袖|左右袖|两袖)[^。；\n]{0,28}(?:脱离|滑脱|失去覆盖|未包覆|不包覆)", text),
            "右肩露肤": re.search(r"右肩[^。；\n]{0,22}(?:露肤|外露|暴露|失去覆盖|未覆盖|盖不住)", text),
            "保留左肩设计开口": re.search(r"(?:保留|保持)[^。；\n]{0,16}(?:左露肩|左肩)", text)
            or re.search(r"(?:左肩|左露肩)[^。；\n]{0,12}(?:设计开口|设计露肤|款式开口)", text),
            "人体侧压力限于定性": re.search(r"(?:人体侧压力|身体侧压力|人体侧)[^。；\n]{0,44}"
                r"(?:定性|(?:仅|只)[^。；\n]{0,18}(?:定位|位置)|"
                r"(?:定量|量化)[^。；\n]{0,12}(?:未验证|待核|待确认|不能|不可)|"
                r"(?:读数|数值)[^。；\n]{0,16}(?:无法|尚不能|未能)[^。；\n]{0,12}对应)",
                text,
            ),
        }
    else:
        checks = {
            "前领上移约 2.4 cm": re.search(r"(?:2\.[34]\d*\s*(?:cm|厘米)|24(?:\.3[012345])?\s*(?:mm|毫米))", text, re.I),
            "前下摆上移约 4 cm": re.search(r"(?:4(?:\.0+)?\s*(?:cm|厘米)|(?:39\.9\d*|40(?:\.0+)?)\s*(?:mm|毫米))", text, re.I),
            "暂缓定稿": hold,
        }
    missing = [label for label, passed in checks.items() if not passed]
    return not missing, ("缺少：" + "、".join(missing) if missing else "已体现：" + "、".join(checks))


def grade(report, reply, case_id, delivery):
    report_view, reply_view = visible(report), visible(reply)
    tail = visible(closing_source(report)).text
    report_errors = artifact_errors(report_view)
    reply_errors = artifact_errors(reply_view)
    handoffs = hits(USER_TECH, report_view.text) + hits(USER_TECH, reply_view.text)
    tail_technical = hits(TAIL_TECH, tail)
    opening = first_opinion(report)
    anchors = CASES[case_id]
    absent = ["/".join(group) for group in anchors if not any(name in report_view.text for name in group)]
    has_human_action = bool(
        NO_HUMAN.search(tail) or
        (HUMAN_ROLE.search(tail) and HUMAN_ACTION.search(tail))
    )
    return [
        ("首段明确给定稿意见", bool(OPINION.search(opening[:110])), opening[:200] or "首段缺少定稿意见。"),
        ("服装问题能用于设计与纸样决定，并可展开查看", bool(report_view.summaries and not absent),
         f"找到 {report_view.summaries} 个折叠摘要。"
         + ("缺少服装定位：" + "、".join(absent) if absent else "所需服装部位与问题已出现。")),
        ("保留本款影响定稿的证据与范围", *garment_result(case_id, report_view.text, opening)),
        ("正文和全部折叠区没有开发者工件", not report_errors, "；".join(report_errors) or "未见开发者工件。"),
        ("交付答复没有开发者工件或评测内部字段", not reply_errors, "；".join(reply_errors) or "未见开发者工件。"),
        ("不让用户选择或批准仿真，也不把仿真交给人工角色", not handoffs,
         "；".join(handoffs[:4]) or "没有发现人工仿真选择或执行指派。未验证原生执行。"),
        ("末节只列时装设计师和版师的服装行动", bool(tail and has_human_action and not tail_technical),
         "技术操作：" + "；".join(tail_technical[:4]) if tail_technical else
         ("含服装待办或明确无待办。" if has_human_action else "缺少角色对应的服装行动或无待办说明。")),
        ("报告链接、独立原图及末节通过交付检查", *delivery),
    ]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--case", required=True, type=int, choices=CASES)
    args = parser.parse_args()
    directory = args.run_dir.resolve()
    report_path, reply_path = (directory / name for name in ("report.md", "reply.md"))
    report = report_path.read_text(encoding="utf-8") if report_path.is_file() else ""
    reply = reply_path.read_text(encoding="utf-8") if reply_path.is_file() else ""
    checks = grade(report, reply, args.case, delivery_check(directory, args.case))
    expectations = [dict(text=text, passed=passed, evidence=evidence) for text, passed, evidence in checks]
    passed = sum(item["passed"] for item in expectations)
    total = len(expectations)
    result = {
        "expectations": expectations,
        "summary": {"passed": passed, "failed": total - passed, "total": total, "pass_rate": passed / total},
        "limitations": ["报告用例基于附件，未执行或验证原生仿真。"],
    }
    (directory / "grading.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{directory.name}: {passed}/{total}")
    for item in expectations:
        if not item["passed"]:
            print(f"FAIL {item['text']}：{item['evidence']}")
    return int(passed != total)


if __name__ == "__main__":
    raise SystemExit(main())
