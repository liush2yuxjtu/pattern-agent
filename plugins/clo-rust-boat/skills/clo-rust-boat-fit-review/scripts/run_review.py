#!/usr/bin/env python3
"""Run the native fit checks and package an offline report."""
import argparse
import base64
import csv
from html import escape
import io
import json
from pathlib import Path
import shutil
import subprocess

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.colors import Normalize
import numpy as np
from PIL import Image

from batch_io import NATIVE_MAPS, native_maps, read_manifest, review_seams, run_native, seam_sources


def read_vtk(path):
    with path.open() as source:
        for _ in range(4):
            next(source)
        vertices = int(next(source).split()[1])
        xyz = np.array([next(source).split() for _ in range(vertices)], dtype=float)
        count = int(next(source).split()[1])
        faces = np.array([next(source).split()[1:] for _ in range(count)], dtype=int)
        if next(source).strip() != f"CELL_DATA {count}":
            raise ValueError("VTK 面数据数量与网格不同")
        fields = {}
        for line in source:
            _, name, _, _ = line.split()
            if next(source).strip() != "LOOKUP_TABLE default":
                raise ValueError("VTK 字段格式无效")
            fields[name] = np.fromiter((float(next(source)) for _ in range(count)), float)
    return xyz[faces], fields


def plot(triangles, views, colors, limits, values=None):
    fig, axes = plt.subplots(1, len(views), figsize=(len(views) * 3, 3.15),
                            squeeze=False, layout="constrained")
    lo, hi = limits
    for ax, (horizontal, depth, xsign, depthsign) in zip(axes[0], views):
        order = np.argsort(depthsign * triangles[:, :, depth].mean(axis=1), kind="stable")
        xy = triangles[:, :, [horizontal, 1]].copy()
        xy[:, :, 0] *= xsign
        bounds = sorted((lo[horizontal] * xsign, hi[horizontal] * xsign))
        ax.add_collection(PolyCollection(xy[order], facecolors=colors[order], edgecolors="face",
                                         linewidths=.12, antialiaseds=False))
        ax.set(xlim=bounds, ylim=(lo[1], hi[1]), aspect="equal")
        ax.set_axis_off()
    if values is not None:
        norm, cmap = values
        fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap), ax=axes[0],
                     orientation="horizontal", shrink=.82, aspect=28)
    output = io.BytesIO()
    fig.savefig(output, format="png", dpi=140, facecolor="white")
    plt.close(fig)
    return output.getvalue()


def figure(data, caption, media="image/png"):
    payload = base64.b64encode(data).decode("ascii")
    label = escape(caption)
    return f'<figure><img src="data:{media};base64,{payload}" alt="{label}"><figcaption>{label}</figcaption></figure>'


def validate_native_maps(inputs, poses, strict):
    maps = {}
    for pose in poses:
        pairs = {}
        for kind, sources in native_maps(inputs, pose).items():
            if all(path.is_file() for path in sources):
                for path in sources:
                    with Image.open(path) as image:
                        if image.format != "PNG":
                            raise ValueError(f"需要 CLO 原生 PNG：{path.name}")
                        image.load()
                pairs[kind] = sources
            elif strict:
                raise ValueError(f'{pose["label"]} 缺少{NATIVE_MAPS[kind][0]}正面或背面')
        maps[pose["id"]] = pairs
    return maps


def write_report(output, inputs, manifest, records, draft, seams, maps, runtime_label):
    all_triangles = np.concatenate([item[2].reshape(-1, 3) for item in records])
    lo, hi = all_triangles.min(axis=0), all_triangles.max(axis=0)
    margin = (hi[1] - lo[1]) * .04
    limits = (lo - margin, hi + margin)
    front = [(0, 2, 1, 1)]
    front_back = front + [(0, 2, -1, -1)]
    four = front_back + [(2, 0, -1, 1), (2, 0, 1, -1)]
    first, _, first_triangles, _ = records[0]
    normals = np.cross(first_triangles[:, 1] - first_triangles[:, 0],
                       first_triangles[:, 2] - first_triangles[:, 0])
    length = np.linalg.norm(normals, axis=1)
    light = np.abs(normals[:, 2]) / np.maximum(length, 1e-12)
    greys = .32 + .52 * light
    plain = plot(first_triangles, front, np.repeat(greys[:, None], 3, axis=1), limits)
    design = inputs / "line-art.png"
    contrast = (figure(design.read_bytes(), "FreeSewing 原版正面设计线稿") if design.exists() else "")
    contrast += figure(plain, f"{first['label']} · 正面服装网格外观")
    patterns = "".join(figure(path.read_bytes(), label, "image/svg+xml") for label, path in draft)
    draft_section = ('<section><h2>二维纸样</h2><div class="pair">'+patterns+'</div>'
                     '<p>两组公开量体各出 20 种裁片模板。上游出样警告保存在工程资料中。</p></section>'
                     if patterns else "")
    parts = []
    ranges = (("strain", "engineering_strain_pct", -3, 25, "viridis",
               "应变图 · 主应变（%）· 正面与背面", front_back),
              ("wrinkles", "fold_angle_deg", 0, 45, "magma",
               "褶皱图 · 折角（度）· 正面、背面、两侧", four))
    status = []
    for pose, stats, triangles, fields in records:
        folder = output / "maps" / pose["id"]
        folder.mkdir(parents=True)
        drawings = []
        pose_maps = {}
        for kind, (caption, _) in NATIVE_MAPS.items():
            sources = maps[pose["id"]].get(kind)
            if sources:
                drawings.extend(figure(source.read_bytes(), f"{caption} · CLO 存档 · {side}")
                                for source, side in zip(sources, ("正面", "背面")))
                for source in sources:
                    shutil.copyfile(source, folder / source.name)
                pose_maps[kind] = {"status": "complete", "source": "CLO native PNG",
                                   "files": [f"maps/{pose['id']}/{source.name}" for source in sources]}
            else:
                pose_maps[kind] = {"status": "missing", "source": "CLO native PNG", "files": []}
        for kind, field, low, high, palette, caption, views in ranges:
            norm, cmap = Normalize(low, high, clip=True), matplotlib.colormaps[palette]
            colors = cmap(norm(fields[field]))
            if field == "engineering_strain_pct":
                colors[fields["strain_is_valid"] == 0] = (.7, .74, .78, 1)
            png = plot(triangles, views, colors, limits, (norm, cmap))
            filename = kind + ".png"
            (folder / filename).write_bytes(png)
            pose_maps[kind] = {"status": "complete", "source": "Rust metric pose mesh",
                               "files": [f"maps/{pose['id']}/{filename}"]}
            drawings.append(figure(png, caption))
        missing = "、".join(NATIVE_MAPS[kind][0] for kind, row in pose_maps.items()
                           if row["status"] == "missing")
        if missing:
            drawings.append(f"<p>本姿势缺少 CLO 原生存档：{missing}。</p>")
        status.append({"id": pose["id"], "label": pose["label"], "maps": pose_maps})
        parts.append(f'<section><h2>{escape(pose["label"])}</h2><p>{len(stats)} 片裁片，'
                     f'{len(triangles):,} 个三角面。色标在各姿势间固定。</p>'
                     f'{"".join(drawings)}</section>')
    (output / "map-status.json").write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n")
    seam_text = "".join(f'<li>{escape(item)}</li>' for item in seams)
    html = f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>CLO_RUST 多姿势评估</title><style>
*{{box-sizing:border-box}}body{{margin:0;background:#f6f5ef;color:#192a28;font:16px/1.6 system-ui,sans-serif}}
main{{margin:auto;width:min(1100px,calc(100% - 28px))}}section,header{{padding:18px 0;border-bottom:1px solid #d4ded7}}
h1,h2,p{{margin:0 0 10px}}h1{{font-size:clamp(25px,5vw,44px)}}
figure{{margin:0 0 10px;background:#fff;border:1px solid #d4ded7;border-radius:8px;overflow:hidden}}
figure img{{width:100%;display:block}}figcaption{{padding:8px 12px}}.pair{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}}
.pair img{{height:clamp(210px,42vw,490px);object-fit:contain}}@media(max-width:560px){{.pair img{{height:210px}}figcaption{{font-size:14px}}}}
</style></head><body><main><header><h1>CLO_RUST 多姿势评估</h1>
<p>{escape(runtime_label)} · {escape(manifest["mesh_source"])}</p>
<p>应变与折角来自 Rust 几何复算。试穿分类与应力图来自匹配的 CLO 存档。动态模拟与压力读数需要另外采集。</p></header>
<section><h2>正面外观对照</h2><div class="pair">{contrast}</div>
<p>服装外观图以输入网格正投影生成。不同视角或扣合状态需要回查原工程。</p></section>
{draft_section}{''.join(parts)}
<section><h2>缝合与工程核查</h2><ul>{seam_text}</ul>
<p>逐片数据保存在同批结果的 JSON、CSV 和 VTK。主应变是几何伸长量，折角为相邻三角面夹角。</p></section>
</main></body></html>"""
    (output / "CLO_RUST-试穿评估.html").write_text(html, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", type=Path, nargs="+", metavar="PATH")
    parser.add_argument("--native", type=Path)
    parser.add_argument("--runtime-label", default="Rust 几何复核")
    parser.add_argument("--require-all-maps", action="store_true")
    parser.add_argument("--carlton", action="store_true")
    args = parser.parse_args()
    if len(args.paths) == 3:
        project_dir, inputs, output = (x.resolve() for x in args.paths)
    elif len(args.paths) == 2 and args.native and not args.carlton:
        inputs, output = (x.resolve() for x in args.paths)
        project_dir = None
    else:
        parser.error("使用 PROJECT INPUT OUTPUT 或 INPUT OUTPUT --native PATH")
    native = args.native or (project_dir / "target/release/pattern-native")
    try:
        manifest = read_manifest(inputs)
        maps = validate_native_maps(inputs, manifest["poses"], args.require_all_maps)
    except (OSError, ValueError, KeyError) as exc:
        parser.error(str(exc))
    output.mkdir(parents=True)
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2))

    def run(command, name):
        return run_native(native, output, command, name)

    draft = []
    seam_notes = []
    if args.carlton:
        js = project_dir / "vendor/draft-carlton.mjs"
        for mode, size in (("baseline", 1000), ("chest-plus-40", 1040)):
            source, svg = output/f"draft-{size}.json", output/f"draft-{size}.svg"
            subprocess.run(["node", js, mode, source, svg], check=True)
            project = output/f"carlton-{size}.pattern.json"
            imported = run(["draft-import", source, project], f"draft-audit-{size}")
            reopened = run(["audit", project], f"reopen-{size}")
            if imported != reopened or imported["pieces"] != 20:
                raise ValueError(f"Carlton {size} 毫米纸样重开后审计不一致")
            draft.append((f"胸围 {size} 毫米 · Carlton", svg))
        seam_notes.append("两种尺码分别出样和重开，均通过 Rust 工程审计。")
    if seam_files := seam_sources(inputs):
        seam_notes.extend(review_seams(native, seam_files, output))
    records = []
    rows = []
    for pose in manifest["poses"]:
        stem = pose["id"]
        vtk = output / (stem+".vtk")
        stats = run(["mesh-metrics", inputs/(stem+".glb"), vtk], stem)
        triangles, fields = read_vtk(vtk)
        if sum(piece["triangle_count"] for piece in stats) != len(triangles):
            raise ValueError("JSON 与 VTK 的三角面数量不同")
        records.append((pose, stats, triangles, fields))
        rows.extend({"姿势": pose["label"], **piece} for piece in stats)
    with (output/"逐片数据.csv").open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)
    write_report(output, inputs, manifest, records, draft,
                 seam_notes or ["没有提供既有缝合定义。"], maps, args.runtime_label)
    print(f"完成 {len(records)} 个姿势、{len(rows)} 条裁片统计")


if __name__ == "__main__":
    main()
