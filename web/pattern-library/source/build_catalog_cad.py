"""Build the browsable registry from collected original pattern files and verified publisher pages."""
from argparse import ArgumentParser
from collections import Counter
from csv import DictReader, DictWriter
from hashlib import file_digest
from html import unescape
from pathlib import Path
import json
import re

ZJU = "https://github.com/Dancingmader/3D-High-quality-Garment-Dataset"
ZJU_DOWNLOAD = "https://drive.google.com/file/d/14cq_Sa8hkEO3u9HZF5N7jWK2Xu92US29/view?usp=sharing"
SOURCES = {
    "zju": "浙江大学 · 服装皱褶研究",
    "et": "ET 官方学习版",
    "project": "Pattern Agent 原型",
    "vfl": "Virtual Fashion Lab",
    "learn": "Learn 3D Fashion",
    "openpattern": "Open+Pattern",
}
GROUPS = {
    "men's_hoodies": "男式连帽衫", "men's_sports_suits": "男式运动套装",
    "women's_casual_trousers": "女式休闲裤", "women's_gowns": "女式礼服",
    "women's_lantern_sleeve_dresses": "灯笼袖连衣裙", "women's_qipao_polo_dress": "旗袍与 Polo 裙",
    "women's_shirts": "女式衬衫", "women's_T_shirts": "女式 T 恤",
}
SOURCE_THUMBS = {
    "PA-01": "../edits/original.svg",
    "PA-03": "../../patterns/straight-skirt-eu40/draft-preview.svg",
}


def digest(path):
    with path.open("rb") as source:
        return file_digest(source, "sha256").hexdigest()


def earlier(catalog):
    originals = {}
    with catalog.open(encoding="utf-8-sig") as stream:
        for row in DictReader(stream):
            if row["dataset_class"] == "derived_regression" or row["sha256"] in originals:
                continue
            if row["dataset_class"] == "project_baseline":
                source, role = "project", "项目原型"
            elif row["dataset_class"] == "vendor_training":
                source, role = "et", "官方教学样板"
            else:
                source, role = ("learn" if "learn3dfashion" in row["source_url"] else "vfl"), "公开教程工程"
            display_format = row["format"]
            name = row["source_name"]
            audit = "DXF 已重开核对" if display_format == "DXF" else "文件指纹已验证"
            garment = ("" if source == "et" else row["garment_family"])
            result = dict(id=row["asset_id"], title=name, name=name, format=display_format,
                          source=source, garment=garment, url=row["source_url"], member=row["archive_member"],
                          bytes=int(row["bytes"]), sha256=row["sha256"], role=role, audit=audit)
            if row["asset_id"] in SOURCE_THUMBS:
                result["preview"] = SOURCE_THUMBS[row["asset_id"]]
            originals[row["sha256"]] = result
    return list(originals.values())


def research(archive, folder):
    result = []
    for number, file in enumerate(sorted(p for p in folder.rglob("*") if p.is_file() and p.suffix.casefold()==".zprj"), 1):
        member = file.relative_to(folder)
        with file.open("rb") as data:
            assert data.read(16) == b" ZPRJ       CLO ", member
        family = GROUPS[member.parts[1]]
        role = "同款变姿态工程" if file.stem.casefold().endswith("_def") else "参考服装工程"
        result.append(dict(id=f"ZJU-{number:02d}", title=f"{family} · {file.stem.replace('_', ' ')}",
                           name=file.name, format="ZPRJ", source="zju", garment=family, role=role,
                           audit="CLO 文件标记、字节及指纹已验证", url=ZJU, member=member.as_posix(),
                           bytes=file.stat().st_size, sha256=digest(file)))
    return result, {"archive": "dataset.7z", "sha256": digest(archive), "bytes": archive.stat().st_size,
                    "publisher_download": ZJU_DOWNLOAD, "paper": "https://doi.org/10.1016/j.cagd.2021.102020"}


def publisher_records(product_file):
    products = json.loads(product_file.read_text(encoding="utf-8"))
    for product in products:
        plain = unescape(re.sub(r"<[^>]+>", " ", product["description"] + " " + product["short_description"]))
        formats = [kind for kind, tokens in (("DXF", r"\bDXF\b"), ("ZPRJ", r"\bZPRJ\b|\bCLO3D\b"))
                   if re.search(tokens, plain, re.I)]
        if not formats or any(word in product["slug"] for word in ("mask", "backpack", "toile-grid", "boonie-hat", "support-open")):
            continue
        title = unescape(product["name"])
        yield dict(id=f"OP-{product['id']}", title=title, name=title, format=" / ".join(formats), formats=formats,
                   source="openpattern", garment="", role="CC BY 4.0", url=product["permalink"],
                   audit="发布方入口 · 纸样页面提供获取流程")


def main():
    cli = ArgumentParser(description=__doc__)
    for key in ("baseline", "archive", "extracted", "publisher", "output"):
        cli.add_argument("--"+key, type=Path, required=True)
    args = cli.parse_args()
    archived, package = research(args.archive, args.extracted)
    archived.extend(earlier(args.baseline))
    sources = list(publisher_records(args.publisher))
    hashes = [item["sha256"] for item in archived]
    assert len(hashes) == len(set(hashes))
    packages = Counter(item["format"] for item in archived)
    out = {"schema": "pattern-agent-cad/1", "sources": SOURCES,
           "counts": {"archived": len(archived), "publisher_records": len(sources), "formats": dict(packages)},
           "research_archive": package, "entries": [*archived, *sources]}
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output/"cad.json").write_text(json.dumps(out, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    fields = ("id", "title", "name", "format", "source", "garment", "role", "audit", "url", "member", "bytes", "sha256")
    for name, rows in (("cad-origins.csv", archived), ("cad-publisher-links.csv", sources)):
        with (args.output/name).open("w", encoding="utf-8-sig", newline="") as stream:
            writer = DictWriter(stream, fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
    print(json.dumps(out["counts"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
