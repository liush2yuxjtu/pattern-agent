#!/usr/bin/env python3
"""Check the five evidence groups and the rendered Markdown structure for one fit state."""

import argparse
import csv
from hashlib import sha256
from io import BytesIO
import json
from math import isfinite
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from publish_report import MARKDOWN, decode_image
from report_follow_up import markdown_follow_up_errors


MAPS = ("appearance", "strain", "stress", "pressure", "folds")
VIEWS = {"front", "back", "left", "right", "front_left_45"}
FIELDS = {"state", "region", "metric", "observed", "unit", "coverage", "criterion"}
VERDICTS = {"PASS", "FAIL", "PENDING"}
COVERAGE_HEADER = ("验证项", "图审", "表审")
SUMMARY_HEADER = ("验证项", "图号", "部位", "读数或观察", "单位及覆盖", "通过判据")


def evidence_path(root, name):
    if not isinstance(name, str) or not name.strip() or Path(name).is_absolute():
        raise ValueError("证据路径须为清单目录内的相对路径")
    path = (root / name).resolve()
    if not path.is_relative_to(root):
        raise ValueError("证据路径须位于清单目录内")
    return path


def check_image(root, image, state):
    if image.get("state") != state:
        raise ValueError("图像状态与清单不符")
    data = evidence_path(root, image.get("path")).read_bytes()
    with Image.open(BytesIO(data)) as decoded:
        if decoded.format not in {"PNG", "JPEG", "WEBP"}:
            raise ValueError("须为 PNG、JPEG 或 WebP")
        pixels = decoded.convert("RGBA")
        identity = (pixels.size, sha256(pixels.tobytes()).hexdigest())
    return sha256(data).hexdigest(), identity


def check_csv(root, name, category, state):
    path = evidence_path(root, name)
    with path.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        if not FIELDS.issubset(reader.fieldnames or []):
            raise ValueError("CSV 缺必需表头")
        count = 0
        for row in reader:
            count += 1
            if row["state"] != state or not all((row[key] or "").strip() for key in FIELDS):
                raise ValueError(f"CSV 第 {reader.line_num} 行缺值或状态不符")
            if category != "appearance" and not isfinite(float(row["observed"])):
                raise ValueError(f"CSV 第 {reader.line_num} 行读数须为有限数字")
        if not count:
            raise ValueError("CSV 缺数据行")
    return path


def grade_group(root, category, group, state, seen):
    errors, hashes = [], set()
    images = group.get("images") or {}
    if category == "appearance" and set(images) != VIEWS:
        errors.append("缺少规定的五个外观视角")
    if not images:
        errors.append("缺少证据图")
    for label, image in images.items():
        try:
            digest, identity = check_image(root, image, state)
            if identity in seen:
                raise ValueError("与另一证据图像素重复")
            hashes.add(digest)
            seen.add(identity)
        except (OSError, ValueError) as error:
            errors.append(f"{label}: {error}")
    visual_ready = not errors
    table = None
    try:
        table = check_csv(root, group.get("table"), category, state)
    except (OSError, ValueError, csv.Error) as error:
        errors.append(f"表: {error}")
    review = group.get("review") or {}
    reason = review.get("reason", "")
    if (not isinstance(reason, str) or not reason.strip()
            or any(review.get(key) not in VERDICTS for key in ("visual", "tabular"))):
        errors.append("缺少独立图审、表审或理由")
        review = {}
    results = {
        "visual": review.get("visual", "PENDING") if visual_ready else "PENDING",
        "tabular": review.get("tabular", "PENDING") if table else "PENDING",
        "issues": errors,
    }
    return results, hashes, table


def report_tables(tokens, subject):
    tables, headings = {}, []
    section = unit = None
    for index, token in enumerate(tokens):
        if token.type == "heading_open":
            title = re.sub(r"^[一二三四五六七八九十0-9]+[、.：:)）]\s*", "", tokens[index + 1].content)
            if token.tag == "h2":
                headings.append(title)
                section, unit = title, None
            elif token.tag == "h3":
                unit = title
        if (token.type == "table_open" and section == "集中统计与验收"
                and unit == f"证据单元 {subject}"):
            rows = []
            for cell in tokens[index + 1:]:
                if cell.type == "table_close":
                    break
                if cell.type == "tr_open":
                    rows.append([])
                if cell.type == "inline":
                    rows[-1].append(cell.content.strip())
            if rows:
                tables.setdefault(tuple(rows[0]), []).append(rows[1:])
    return headings, tables


def grade_report(report, subject, groups, expected_images, expected_tables):
    if report.suffix.lower() != ".md":
        return ["默认交付须为 Markdown"]
    tokens = MARKDOWN.parse(report.read_text(encoding="utf-8"))
    errors = markdown_follow_up_errors(tokens)
    headings, tables = report_tables(tokens, subject)
    if headings[:2] != ["先看哪里", "看整体上身"] or "集中统计与验收" not in headings:
        errors.append("须按模板安排结论、整体上身和集中统计")
    expected_rows = [[key, row["visual"], row["tabular"]] for key, row in groups.items()]
    coverage = tables.get(COVERAGE_HEADER, [])
    if len(coverage) != 1 or sorted(coverage[0]) != sorted(expected_rows):
        errors.append(f"{subject} 的五项覆盖表缺失或与复核结论不符")
    summaries = tables.get(SUMMARY_HEADER, [])
    if (len(summaries) != 1
            or {row[0] for row in summaries[0]} != set(MAPS)
            or not all(len(row) == len(SUMMARY_HEADER) and all(row) for row in summaries[0])):
        errors.append(f"{subject} 的读数摘要表须覆盖五类，并填写图号、部位、读数、覆盖和判据")

    embedded, links = set(), set()
    for index, token in enumerate(tokens):
        for child in token.children or []:
            if child.type == "image":
                try:
                    if (tokens[index - 1].type != "paragraph_open" or len(token.children) != 1
                            or token.level != 1 or not child.content.strip()):
                        raise ValueError("每张证据图须独占一段并有替代文字")
                    embedded.add(sha256(decode_image(child.attrGet("src"))).hexdigest())
                except (OSError, ValueError) as error:
                    errors.append(f"报告图像: {error}")
            if child.type == "link_open":
                url = urlsplit(child.attrGet("href"))
                if not url.scheme and not url.netloc and url.path:
                    links.add((report.parent / unquote(url.path)).resolve())
    if expected_images - embedded:
        errors.append("报告缺少一张或多张与清单对应的内嵌图")
    if expected_tables - links:
        errors.append("报告缺少一份或多份对应 CSV 的链接")
    return errors


def grade(manifest, report):
    data = json.loads(manifest.read_text(encoding="utf-8"))
    subject, state = data["subject"], data["state"]
    if any(not isinstance(value, str) or not value.strip() for value in (subject, state)):
        raise ValueError("清单须提供 subject 和 state")
    declared = data["maps"]
    if set(declared) != set(MAPS):
        raise ValueError("清单须包含五类验证的条目")
    groups, images, tables, seen = {}, set(), set(), set()
    for category in MAPS:
        groups[category], hashes, table = grade_group(
            manifest.parent, category, declared[category], state, seen
        )
        images.update(hashes)
        if table:
            tables.add(table)
    report_errors = grade_report(report, subject, groups, images, tables)
    outcomes = {row[key] for row in groups.values() for key in ("visual", "tabular")}
    verdict = "FAIL" if "FAIL" in outcomes else "PENDING" if "PENDING" in outcomes else "PASS"
    result = {
        "subject": subject,
        "evidence_verdict": verdict,
        "maps": groups,
        "report_pass": not report_errors,
        "report_issues": report_errors,
    }
    status = 1 if report_errors or verdict == "FAIL" else 2 if verdict == "PENDING" else 0
    return result, status


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    try:
        result, status = grade(args.manifest.resolve(), args.report.resolve())
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        result, status = {"error": str(error)}, 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return status


if __name__ == "__main__":
    raise SystemExit(main())
