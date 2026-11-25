#!/usr/bin/env python3
"""Publish Markdown or HTML with self-contained evidence images."""

import argparse
from base64 import b64decode, b64encode
from html import escape
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import unquote, urlsplit

from markdown_it import MarkdownIt
from PIL import Image


IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp"}
MARKDOWN = MarkdownIt("commonmark", {"html": False}).enable("table")


def decode_image(src):
    header, separator, payload = src.partition(",")
    mime = header.removeprefix("data:").removesuffix(";base64")
    if not separator or mime not in IMAGE_TYPES or header != f"data:{mime};base64":
        raise ValueError("静态报告的图片须为内嵌 PNG、JPEG 或 WebP")
    data = b64decode(payload, validate=True)
    with Image.open(BytesIO(data)) as image:
        image.load()
        if Image.MIME.get(image.format) != mime:
            raise ValueError("内嵌图片的格式与声明不符")
    return data


def embed_images(source, output_suffix):
    content = source.read_text(encoding="utf-8")
    lines = content.splitlines(keepends=True)
    env = {}
    tokens = MARKDOWN.parse(content, env)
    definitions = []
    replacements = []
    count = 0
    for previous, token in zip(tokens, tokens[1:]):
        images = [child for child in token.children or [] if child.type == "image"]
        if not images:
            continue
        if previous.type != "paragraph_open" or len(token.children) != 1 or token.level != 1:
            raise ValueError("每张证据图须独占正文中的一段")
        child = images[0]
        src = child.attrGet("src")
        if not child.content.strip():
            raise ValueError("证据图须有替代文字")
        count += 1
        if src.startswith("data:"):
            decode_image(src)
            continue
        target = urlsplit(src)
        path = (source.parent / unquote(target.path)).resolve()
        if target.scheme or target.netloc or not path.is_relative_to(source.parent):
            raise ValueError(f"证据图须位于报告目录内：{src}")
        data = path.read_bytes()
        with Image.open(BytesIO(data)) as image:
            image.load()
            mime = Image.MIME.get(image.format)
        if mime not in IMAGE_TYPES:
            raise ValueError(f"不支持的证据图格式：{path.name}")
        url = f"data:{mime};base64,{b64encode(data).decode('ascii')}"
        child.attrSet("src", url)
        if output_suffix == ".md":
            label = f"fit-report-embedded-{count}"
            while label.upper() in env.get("references", {}):
                label += "-image"
            alt = child.content.replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]")
            replacements.append((*token.map, f"![{alt}][{label}]\n"))
            definitions.append(f"[{label}]: {url}")
    if not count:
        raise ValueError("报告没有可显示的 Markdown 插图")
    if output_suffix == ".md":
        for first, last, line in reversed(replacements):
            lines[first:last] = [line]
        if not definitions:
            return content, count
        return "".join(lines).rstrip() + "\n\n" + "\n".join(definitions) + "\n", count
    return render_html(source.stem, tokens), count


def render_html(title, tokens):
    body = MARKDOWN.renderer.render(tokens, MARKDOWN.options, {})
    html = f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src data:; style-src 'unsafe-inline'; base-uri 'none'">
<title>{escape(title)}</title>
<style>
body {{ max-width: 58rem; margin: auto; padding: clamp(1rem, 4vw, 2.5rem); color: #172435;
  background: white; font: 1rem/1.65 system-ui, sans-serif; overflow-wrap: anywhere; }}
h1, h2, h3 {{ line-height: 1.28; }}
h2 {{ margin-top: 2.25rem; }}
img {{ display: block; max-width: 100%; height: auto; margin: 1.35rem auto 0.5rem; }}
table {{ border-collapse: collapse; width: 100%; }}
td, th {{ padding: 0.4rem 0.55rem; border-bottom: 1px solid #dce2e8; text-align: left; }}
</style>
</head>
<body>
{body}
</body>
</html>
"""
    return html


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("output", type=Path, help="静态 .md 或 .html，放在原稿同目录以保留数据链接")
    args = parser.parse_args()
    source = args.report.resolve()
    output = args.output.resolve()
    if source.parent != output.parent or output.suffix.lower() not in {".md", ".html"}:
        parser.error("请将静态 .md 或 .html 输出到原稿同目录")
    try:
        content, count = embed_images(source, output.suffix.lower())
    except (OSError, ValueError) as error:
        parser.exit(1, f"{error}\n")
    with TemporaryDirectory(dir=output.parent, prefix=".fit-report-") as folder:
        staged = Path(folder) / output.name
        staged.write_text(content, encoding="utf-8")
        staged.replace(output)
    print(f"{count} 张图已内嵌至 {output}")
