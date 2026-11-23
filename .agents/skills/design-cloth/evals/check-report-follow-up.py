#!/usr/bin/env python3
"""Check for a visible, substantive closing triage section in Markdown or HTML."""

import argparse
from dataclasses import dataclass, field
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import unicodedata


SECTION_TITLE = "分诊与下一步复测"
MISSING = "报告缺少可见的「分诊与下一步复测」章节"
REPEATED = "报告应只有一个「分诊与下一步复测」章节"
NOT_LAST = "「分诊与下一步复测」须是报告正文的最后一节"
EMPTY = "「分诊与下一步复测」须有具体待办或明确结案说明"

HEADINGS = {f"h{level}" for level in range(1, 7)}
VOID = set("area base br col embed hr img input link meta param source track wbr".split())
NON_REPORT = {"head", "nav", "script", "style", "template"}
TEXT_BLOCKS = {"p", "li", "dd"}
CONTENT = TEXT_BLOCKS | {"blockquote", "details", "figure", "img", "pre", "section", "table", "video"}


def is_follow_up_heading(title):
    title = unicodedata.normalize("NFKC", title).strip().casefold()
    title = re.sub(r"^[0-9一二三四五六七八九十]+\s*[.、):]\s*", "", title)
    title = re.sub(r"[\s\-–—]+", " ", title).strip()
    return title in {SECTION_TITLE, "triage and next follow up", "triage next follow up"}


def has_follow_up_text(text):
    text = re.sub(r"〔[^〕]*〕", "", text)
    text = " ".join(unicodedata.normalize("NFKC", text).split()).strip(" .。!！？?、")
    if not any(char.isalpha() for char in text):
        return False
    return not (
        re.match(r"^(?:待补充?|待填写|暂无|未填写|todo|tbd)(?:[\s.:。]|$)", text, re.IGNORECASE)
        or re.fullmatch(r"(?:请\s*)?(?:(?:详|参)?见|参阅|查看)\s*(?:上文|正文|附录|附件|数据|链接|表格|报告)"
                        r"\s*[a-zA-Z0-9]*", text)
        or text in {"已通过", "已结案", "无需复测", "无待复测事项", "待定", "待补证", "待复测", "暂无结论"}
    )


@dataclass(eq=False)
class Element:
    tag: str
    identifier: str = ""
    hidden: bool = False
    collapsed: bool = False
    children: list = field(default_factory=list)

    def elements(self, parents=()):
        for child in self.visible_children():
            if isinstance(child, Element):
                yield child, parents + (self,)
                yield from child.elements(parents + (self,))
            elif child.strip():
                yield Element("#text", children=[child]), parents + (self,)

    def visible_children(self):
        for child in self.children:
            if self.collapsed:
                if isinstance(child, Element) and child.tag == "summary" and not child.hidden:
                    yield child
                    return
            elif isinstance(child, str) or not child.hidden:
                yield child

    def text(self, exclude=()):
        if self.tag in exclude:
            return ""
        return "".join(
            child if isinstance(child, str) else child.text(exclude)
            for child in self.visible_children()
        )


class ReportHTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self.root = Element("document")
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        style = re.sub(r"/\*.*?\*/", "", attrs.get("style") or "", flags=re.DOTALL)
        hidden = (
            tag in NON_REPORT or "hidden" in attrs or (attrs.get("aria-hidden") or "").strip().lower() == "true"
            or bool(re.search(r"(?:^|;)\s*(?:display\s*:\s*none|visibility\s*:\s*(?:hidden|collapse))"
                              r"\s*(?:!\s*important\s*)?(?:;|$)", style, re.IGNORECASE))
        )
        node = Element(tag, attrs.get("id") or "", hidden, tag == "details" and "open" not in attrs)
        self.stack[-1].children.append(node)
        if tag == "br":
            self.stack[-1].children.append(" ")
        if tag not in VOID:
            self.stack.append(node)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                break

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def closing_section(html):
    """Return errors and the visible prose in the closing section."""
    page = ReportHTML()
    page.feed(html)
    page.close()
    scope = next((node for node, _ in page.root.elements() if node.tag == "main"), None)
    if scope is None:
        scope = next((node for node, _ in page.root.elements() if node.tag == "body"), page.root)
        scope.children = [node for node in scope.children if not isinstance(node, Element) or node.tag != "footer"]
    nodes = list(scope.elements())
    headings = [
        (index, int(node.tag[1]), node, parents)
        for index, (node, parents) in enumerate(nodes)
        if node.tag in HEADINGS and not any(parent.tag in {"blockquote", "li", "pre"} for parent in parents)
    ]
    matches = [item for item in headings if is_follow_up_heading(item[2].text())]
    if not matches:
        return [MISSING], ""
    if len(matches) > 1:
        return [REPEATED], ""

    start, level, _, parents = matches[0]
    boundary = next((i for i, depth, _, _ in headings if i > start and depth <= level), len(nodes))
    container = next((node for node in reversed(parents) if node is not scope and (
        node.tag in {"section", "article"} or node.identifier == "follow-up"
    )), None)
    errors = [NOT_LAST] if boundary < len(nodes) else []
    if container is not None:
        boundary = min(boundary, next((i for i in range(start + 1, len(nodes))
                                       if container not in nodes[i][1]), len(nodes)))
        if not errors and any(node.tag in HEADINGS | CONTENT or node.text().strip()
                              for node, _ in nodes[boundary:]):
            errors.append(NOT_LAST)

    blocks = [node for node, parents in nodes[start + 1:boundary]
              if node.tag in TEXT_BLOCKS | HEADINGS and not any(parent.tag == "blockquote" for parent in parents)]
    if not any(has_follow_up_text(node.text({"a", "pre", "blockquote"})) for node in blocks if node.tag in TEXT_BLOCKS):
        errors.append(EMPTY)
    return errors, "\n".join(node.text({"pre", "blockquote"}) for node in blocks)


def read_closing_section(report):
    content = report.read_text(encoding="utf-8-sig")
    if report.suffix.lower() == ".md":
        try:
            from markdown_it import MarkdownIt
        except ModuleNotFoundError as exc:
            raise ValueError("检查 Markdown 需要 markdown-it-py。见 evals/README.md。") from exc
        content = MarkdownIt("commonmark").enable("table").render(content)
    elif report.suffix.lower() not in {".html", ".htm"}:
        raise ValueError("报告须为 Markdown 或 HTML")
    return closing_section(content)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reports", type=Path, nargs="+")
    results = []
    for report in parser.parse_args().reports:
        try:
            errors, _ = read_closing_section(report)
        except (OSError, ValueError) as exc:
            errors = [str(exc)]
        results.append({"report": str(report), "passed": not errors, "errors": errors})
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0 if all(result["passed"] for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
