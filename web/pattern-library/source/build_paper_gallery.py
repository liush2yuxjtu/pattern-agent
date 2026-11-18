"""Build the public 2D gallery from actual pattern outlines and planar exports."""
from argparse import ArgumentParser
from pathlib import Path
import hashlib
import json
import subprocess
import tempfile

import ezdxf
import numpy as np
from ezdxf.addons.drawing import Frontend, RenderContext, config, layout, svg
from PIL import Image, ImageDraw

LIBRARY = Path(__file__).resolve().parents[1]
ROOT = LIBRARY.parents[1]
OUTPUT = LIBRARY / "paper-gallery"
SIZE = (1600, 1080)
INK = "#31554b"

RESEARCH = (
    ("male_2_1_2D.obj", "男式连帽衫 01", "上衣", ("ZJU-01", "ZJU-02")),
    ("male_2_2_2D.obj", "男式连帽衫 02", "上衣", ("ZJU-03",)),
    ("male_1_top_2D.obj", "男式运动上衣 01", "上衣", ("ZJU-04", "ZJU-05")),
    ("male_1_bottom_2D.obj", "男式运动裤 01", "裤装", ("ZJU-04", "ZJU-05")),
    ("male_2_top_2D.obj", "男式运动上衣 02", "上衣", ("ZJU-06",)),
    ("male_2_bottom_2D.obj", "男式运动裤 02", "裤装", ("ZJU-06",)),
    ("V_neck_T_shirt_2D.obj", "女式 V 领 T 恤", "上衣", ("ZJU-07",)),
    ("round_neck_T_shirt_2D.obj", "女式圆领 T 恤", "上衣", ("ZJU-08", "ZJU-09")),
    ("casual_trousers_1_woman_2D.obj", "女式休闲裤 01", "裤装", ("ZJU-10", "ZJU-11")),
    ("casual_trousers_2_woman_2D.obj", "女式休闲裤 02", "裤装", ("ZJU-12",)),
    ("gown_1_2D.obj", "长礼服 01", "裙装", ("ZJU-13", "ZJU-14")),
    ("gown_2_2D.obj", "长礼服 02", "裙装", ("ZJU-15",)),
    ("lantern_sleeve_dress_1_2D.obj", "灯笼袖连衣裙 01", "裙装", ("ZJU-16", "ZJU-17")),
    ("lantern_sleeve_dress_2_2D.obj", "灯笼袖连衣裙 02", "裙装", ("ZJU-18",)),
    ("polo_dress_2D.obj", "Polo 连衣裙", "裙装", ("ZJU-19",)),
    ("qipao_2D.obj", "旗袍", "裙装", ("ZJU-20",)),
    ("shirt_1_2D.obj", "女式衬衫 01", "上衣", ("ZJU-21", "ZJU-22")),
    ("shirt-2-2D.obj", "女式衬衫 02", "上衣", ("ZJU-23",)),
    ("shirt_2_notched_sleeves_2D.obj", "女式衬衫 02 · 开衩袖", "上衣", ("ZJU-24",)),
)


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def flattened_layout(source, output):
    points = []
    faces = []
    with source.open() as stream:
        for line in stream:
            if line.startswith("v "):
                points.append(tuple(map(float, line.split()[1:4])))
            elif line.startswith("f "):
                faces.append(tuple(int(token.split("/")[0]) - 1 for token in line.split()[1:]))
    xyz = np.asarray(points, dtype=float)
    triangles = np.asarray(faces, dtype=int)
    if xyz.ndim != 2 or not np.isfinite(xyz).all() or np.ptp(xyz[:, 2]) > 1e-5:
        raise ValueError(f"Expected a finite XY-plane export: {source}")
    if triangles.ndim != 2 or triangles.shape[1] != 3 or triangles.min() < 0 or triangles.max() >= len(xyz):
        raise ValueError(f"Expected valid triangular faces: {source}")

    xy, vertex_map = np.unique(xyz[:, :2], axis=0, return_inverse=True)
    triangles = np.unique(np.sort(vertex_map[triangles], axis=1), axis=0)
    edges = np.concatenate((triangles[:, [0, 1]], triangles[:, [1, 2]], triangles[:, [0, 2]]))
    distinct, counts = np.unique(edges, axis=0, return_counts=True)
    outline = distinct[counts == 1]
    if len(outline) < 3 or (np.ptp(xy, axis=0) <= 0).any():
        raise ValueError(f"Expected a nonempty pattern boundary: {source}")

    canvas_size = np.array(SIZE) * 2
    scale = min((canvas_size - 160) / np.ptp(xy, axis=0))
    centered = xy - (xy.min(axis=0) + xy.max(axis=0)) / 2
    pixels = np.rint(centered * [scale, -scale] + canvas_size / 2).astype(int).tolist()
    image = Image.new("RGB", tuple(canvas_size), "#f8faf5")
    draw = ImageDraw.Draw(image)
    for a, b, c in triangles.tolist():
        draw.polygon([tuple(pixels[a]), tuple(pixels[b]), tuple(pixels[c])], fill="#e3eee4")
    for a, b in outline.tolist():
        draw.line([tuple(pixels[a]), tuple(pixels[b])], fill=INK, width=5)
    image.resize(SIZE, Image.Resampling.LANCZOS).save(output, lossless=True, method=6)
    return len(outline)


def dxf_svg(source):
    document = ezdxf.readfile(source)
    backend = svg.SVGBackend()
    settings = config.Configuration(
        color_policy=config.ColorPolicy.CUSTOM, custom_fg_color=INK,
        background_policy=config.BackgroundPolicy.OFF,
        lineweight_policy=config.LineweightPolicy.ABSOLUTE,
    )
    Frontend(RenderContext(document), backend, config=settings).draw_layout(document.modelspace())
    return backend.get_string(
        layout.Page(180, 120, margins=layout.Margins.all(5)),
        settings=layout.Settings(fixed_stroke_width=0.28, output_layers=False),
    ) + "\n"


def build(flattened, vfl_dxf):
    OUTPUT.mkdir(exist_ok=True)
    catalog = json.loads((LIBRARY / "catalog/cad.json").read_text())
    samples = json.loads((LIBRARY / "gallery/manifest.json").read_text())["samples"]
    by_id = {row["id"]: row for row in catalog["entries"]}
    sources = {key: catalog["sources"][key] for key in ("project", "zju", "vfl")}
    sources["freesewing"] = "FreeSewing"
    cards = []

    def add(id_, title, group, source, kind, preview, source_url, *, disk_path=None, **metadata):
        cards.append(dict(
            id=id_, title=title, garment=group, source=source, kind=kind, preview=preview,
            previewSha256=sha(disk_path or (LIBRARY / preview)), sourceUrl=source_url, **metadata,
        ))

    for sample in samples:
        is_skirt = sample["id"].startswith("sandy")
        add(sample["id"], sample["name"], "裙装" if is_skirt else "上衣", "freesewing" if is_skirt else "project",
            "SVG", sample["preview"], "https://freesewing.eu/designs/sandy/" if is_skirt else sample["evidence"],
            download=sample["pattern"], downloadLabel="下载纸样 SVG", sourceSha256=sha(LIBRARY / sample["pattern"]))

    def add_cad(id_, title, group, kind, preview, **metadata):
        row = by_id[id_]
        add(id_.lower(), title, group, row["source"], kind, preview, row["url"],
            catalogIds=[id_], sourceSha256=row["sha256"], sourceMember=row["name"], **metadata)

    add_cad("PA-01", "贴身长袖 T 恤 · 原型", "上衣", "SVG", "edits/original.svg",
            download="editor/samples/input.dxf", downloadLabel="下载原型 DXF")
    skirt = ROOT / "patterns/straight-skirt-eu40/draft-preview.svg"
    add_cad("PA-03", "直筒半身裙 · EU 40", "裙装", "SVG", "../patterns/straight-skirt-eu40/draft-preview.svg",
            disk_path=skirt, download="../patterns/straight-skirt-eu40/cutting-layout.dxf", downloadLabel="下载排版 DXF")

    bodice = LIBRARY / "downloads/bodice-v001.dxf"
    for id_, source in (("PA-04", bodice), ("VFL-02", vfl_dxf)):
        if sha(source) != by_id[id_]["sha256"]:
            raise ValueError(f"CAD bytes do not match {id_}: {source}")
    (OUTPUT / "pa-04.svg").write_text(dxf_svg(bodice), encoding="utf-8")
    add_cad("PA-04", "无袖衣身 · v001", "上衣", "SVG", "paper-gallery/pa-04.svg",
            download="downloads/bodice-v001.dxf", downloadLabel="下载原型 DXF")

    with tempfile.TemporaryDirectory() as directory:
        vector = Path(directory) / "preview.svg"
        raster = vector.with_suffix(".png")
        vector.write_text(dxf_svg(vfl_dxf), encoding="utf-8")
        subprocess.run(
            ["inkscape", str(vector), "--export-width=1600", f"--export-filename={raster}"],
            check=True, capture_output=True,
        )
        with Image.open(raster) as ink:
            preview = Image.new("RGB", ink.size, "#f8faf5")
            preview.paste(ink, mask=ink.getchannel("A"))
            preview.save(OUTPUT / "vfl-02.webp", lossless=True, method=6)
    add_cad("VFL-02", "Virtual Fashion Lab 卫衣", "上衣", "DXF 预览", "paper-gallery/vfl-02.webp")

    members = {file.name: file for file in flattened.rglob("*.obj")}
    for name, title, group, ids in RESEARCH:
        member = members[name]
        slug = name.replace("_2D.obj", "").replace("-2D.obj", "").lower().replace("_", "-")
        id_ = "zju-" + slug
        output = OUTPUT / (id_ + ".webp")
        boundary_edges = flattened_layout(member, output)
        add(id_, title, group, "zju", "OBJ 轮廓", "paper-gallery/" + output.name, by_id[ids[0]]["url"],
            catalogIds=list(ids), sourceMember=member.relative_to(flattened).as_posix(),
            sourceSha256=sha(member), boundaryEdges=boundary_edges)
        print(f"{id_}: {boundary_edges} boundary edges", flush=True)

    manifest = dict(schema="pattern-agent-paper-gallery/1", sources=sources, entries=cards)
    (OUTPUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{len(cards)} 2D previews in {OUTPUT}")


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--flattened", required=True, type=Path, help="Directory containing the extracted ZJU 2D OBJ files")
    parser.add_argument("--vfl-dxf", required=True, type=Path, help="Original Virtual Fashion Lab sweatshirt DXF")
    args = parser.parse_args()
    build(args.flattened, args.vfl_dxf)
