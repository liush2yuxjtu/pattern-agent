#!/usr/bin/env python3
"""Verify that the delivered Markdown renders its evidence as standalone images."""

import argparse
from hashlib import sha256
from pathlib import Path
import sys
from urllib.parse import unquote, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from publish_report import MARKDOWN, decode_image
from report_follow_up import markdown_follow_up_errors
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


def local_file(root, base, target):
    location = urlsplit(target)
    if location.scheme or location.netloc:
        raise ValueError(f"需要本地交付路径 {target}")
    path = (base / unquote(location.path)).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError(f"交付目录内找不到文件 {target}")
    return path


def links(tokens):
    for token in tokens:
        target = None
        label = []
        for child in token.children or []:
            if child.type == "link_open":
                target = child.attrGet("href")
                label = []
            elif child.type == "link_close":
                yield target, "".join(label)
                target = None
            elif target is not None:
                label.append(child.content)


def check(reply, evidence):
    root = reply.parent.resolve()
    first_link = next(links(MARKDOWN.parse(reply.read_text(encoding="utf-8"))), None)
    if first_link is None or "报告" not in first_link[1]:
        raise ValueError("最终答复的首个链接须明确标为报告")
    target = first_link[0]
    if not Path(unquote(target)).is_absolute():
        raise ValueError("最终答复中的本地报告链接须使用实际绝对路径")
    report = local_file(root, root, target)
    if report == reply.resolve() or report.suffix.lower() != ".md":
        raise ValueError("报告须为独立 Markdown")

    tokens = MARKDOWN.parse(report.read_text(encoding="utf-8"))
    if errors := markdown_follow_up_errors(tokens):
        raise ValueError("\n".join(errors))
    expected = {
        sha256(local_file(root, report.parent, name).read_bytes()).digest(): name
        for name in evidence
    }
    pictures = set()
    for previous, token in zip(tokens, tokens[1:]):
        if previous.type != "paragraph_open" or not token.children:
            continue
        if len(token.children) != 1 or token.children[0].type != "image":
            continue
        image = token.children[0]
        src = image.attrGet("src")
        if not image.content.strip():
            raise ValueError("插图须有替代文字")
        pictures.add(sha256(decode_image(src)).digest())
    if missing := expected.keys() - pictures:
        raise ValueError("报告缺少独立嵌入图 " + "、".join(sorted(expected[key] for key in missing)))
    for href, _ in links(tokens):
        if href.startswith("data:image/") or Path(unquote(urlsplit(href).path)).suffix.lower() in IMAGE_SUFFIXES:
            raise ValueError(f"证据图须嵌入正文，索引可使用图号 {href}")

    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reply", type=Path, help="候选交付目录内的最终答复 Markdown")
    parser.add_argument("--evidence", nargs="+", default=[
        "reference.jpg", "standing-front.jpg", "standing-back.jpg",
        "angled-front.jpg", "angled-back.jpg",
    ])
    args = parser.parse_args()
    try:
        print(check(args.reply, args.evidence))
    except (OSError, ValueError) as error:
        parser.exit(1, f"{error}\n")
