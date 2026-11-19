#!/usr/bin/env python3
"""Embed report images from local files without redrawing the evidence."""

import argparse
import base64
from html import escape
from html.parser import HTMLParser
from itertools import accumulate
from pathlib import Path
from urllib.parse import unquote, urlsplit

IMAGE_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".svg": "image/svg+xml",
}


class ReportImages(HTMLParser):
    def __init__(self, source, markup):
        super().__init__(convert_charrefs=False)
        self.directory = source.parent
        self.line_offsets = [0, *accumulate(len(line) + 1 for line in markup.split("\n"))]
        self.edits = []
        self.images = 0
        self.data_uris = {}

    def handle_starttag(self, tag, attrs):
        if tag == "source" and any(key == "srcset" for key, _ in attrs):
            raise ValueError("请用一个 img 元素显示每张报告图像")
        if tag != "img":
            return
        attributes = dict(attrs)
        src = attributes.get("src")
        if not src or len(attributes) != len(attrs) or "srcset" in attributes:
            raise ValueError("每张报告图像需要一个有效的 src，且只能指定一个图像来源")
        self.images += 1
        if src.startswith("data:image/"):
            return
        address = urlsplit(src)
        if address.scheme or address.netloc or address.query or address.fragment:
            raise ValueError(f"请先将图像保存到本地文件：{src}")
        image = (self.directory / unquote(address.path)).resolve()
        media_type = IMAGE_TYPES.get(image.suffix.lower())
        if not media_type:
            raise ValueError(f"图像需使用 PNG、JPEG、WebP 或 SVG：{src}")
        if image not in self.data_uris:
            data = image.read_bytes()
            if not data:
                raise ValueError(f"图像文件为空：{src}")
            payload = base64.b64encode(data).decode("ascii")
            self.data_uris[image] = f"data:{media_type};base64,{payload}"
        attributes["src"] = self.data_uris[image]
        new_tag = "<img" + "".join(
            f' {key}="{escape(value, quote=True)}"' if value is not None else f" {key}"
            for key, value in attributes.items()
        ) + ">"
        line, column = self.getpos()
        start = self.line_offsets[line - 1] + column
        self.edits.append((start, start + len(self.get_starttag_text()), new_tag))


def inline_images(source):
    markup = source.read_text(encoding="utf-8")
    parser = ReportImages(source, markup)
    parser.feed(markup)
    parser.close()
    if not parser.images:
        raise ValueError("报告中没有可见的 img 图像元素")
    chunks = []
    cursor = 0
    for start, end, replacement in parser.edits:
        chunks.extend((markup[cursor:start], replacement))
        cursor = end
    chunks.append(markup[cursor:])
    return "".join(chunks), parser.images


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("source", type=Path)
    cli.add_argument("output", type=Path)
    args = cli.parse_args()
    if args.source.resolve() == args.output.resolve():
        cli.error("HTML 草稿和交付文件需要不同的路径")
    try:
        markup, images = inline_images(args.source)
        args.output.write_text(markup, encoding="utf-8")
    except (OSError, ValueError) as error:
        cli.exit(1, f"图像内嵌失败：{error}\n")
    print(f"已处理 {images} 张正文图像")


if __name__ == "__main__":
    main()
