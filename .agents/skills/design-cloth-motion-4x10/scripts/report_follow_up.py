"""Validate the closing triage and follow-up section of a fit report."""

import re
import unicodedata


SECTION_TITLE = "分诊与下一步复测"
MISSING = "报告缺少「分诊与下一步复测」章节"
REPEATED = "报告应只有一个「分诊与下一步复测」章节"
NOT_LAST = "「分诊与下一步复测」须是报告正文的最后一节"
EMPTY = "「分诊与下一步复测」须有具体待办或明确结案说明"


def is_follow_up_heading(title):
    title = unicodedata.normalize("NFKC", title).strip().casefold()
    title = re.sub(r"^[0-9一二三四五六七八九十]+\s*[.、):]\s*", "", title)
    title = re.sub(r"[\s\-–—]+", " ", title).strip()
    return title in {SECTION_TITLE, "triage and next follow up", "triage next follow up"}


def has_follow_up_text(text):
    text = re.sub(r"〔[^〕]*〕", "", text)
    text = re.sub(r"\s+", " ", unicodedata.normalize("NFKC", text)).strip()
    return bool(any(char.isalpha() for char in text)) and not re.match(
        r"^(?:待补充?|待填写|暂无|未填写|todo|tbd)(?:[\s.。、!！:：?？]|$)", text, re.IGNORECASE
    )


def paragraph_text(inline):
    parts = []
    inside_link = False
    for child in inline.children or []:
        if child.type == "link_open":
            inside_link = True
        elif child.type == "link_close":
            inside_link = False
        elif not inside_link and child.type in {"text", "code_inline", "softbreak", "hardbreak"}:
            parts.append(child.content or " ")
    return "".join(parts)


def markdown_follow_up_errors(tokens):
    headings = [
        (i, int(token.tag[1]), tokens[i + 1].content)
        for i, token in enumerate(tokens)
        if token.type == "heading_open" and token.level == 0
    ]
    matches = [(i, level) for i, level, text in headings if is_follow_up_heading(text)]
    if not matches:
        return [MISSING]
    if len(matches) > 1:
        return [REPEATED]

    start, level = matches[0]
    following = next((i for i, depth, _ in headings if i > start and depth <= level), len(tokens))
    errors = [NOT_LAST] if following < len(tokens) else []
    if not any(
        token.type == "inline" and tokens[i - 1].type == "paragraph_open"
        and has_follow_up_text(paragraph_text(token))
        for i, token in enumerate(tokens)
        if start < i < following
    ):
        errors.append(EMPTY)
    return errors
