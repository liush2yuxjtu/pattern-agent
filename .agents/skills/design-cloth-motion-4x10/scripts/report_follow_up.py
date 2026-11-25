"""Validate the closing triage and follow-up section of a fit report."""

import re
import unicodedata


SECTION_TITLE = "分诊与下一步复测"
MISSING = "报告缺少「分诊与下一步复测」章节"
REPEATED = "报告应只有一个「分诊与下一步复测」章节"
NOT_LAST = "「分诊与下一步复测」须是报告正文的最后一节"
EMPTY = "「分诊与下一步复测」须有具体待办或明确结案说明"
TRIAGE_COLUMNS = ("#", "事项", "归类", "依据", "可撤销做法", "超时默认", "选项")


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


def has_triage_table_action(tokens):
    """Only count actual action and method cells in the canonical triage table."""
    columns = []
    cells = []
    for previous, token in zip(tokens, tokens[1:]):
        if token.type in {"table_open", "table_close"}:
            columns = []
        elif token.type == "tr_open":
            cells = []
        elif token.type == "inline" and previous.type == "th_open":
            columns.append(paragraph_text(token).strip())
        elif token.type == "inline" and previous.type == "td_open":
            cells.append(paragraph_text(token))
        elif token.type == "tr_close" and tuple(columns) == TRIAGE_COLUMNS:
            if len(cells) == len(TRIAGE_COLUMNS) and all(
                has_follow_up_text(cells[index]) for index in (1, 4)
            ):
                return True
    return False


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
    ) and not has_triage_table_action(tokens[start + 1 : following]):
        errors.append(EMPTY)
    return errors
