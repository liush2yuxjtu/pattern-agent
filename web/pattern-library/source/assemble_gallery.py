"""Assemble the published previews and deterministic editor download."""
from argparse import ArgumentParser
from hashlib import sha256
from pathlib import Path
from shutil import copyfile
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED
import gzip
import json
import sys

from PIL import Image
import yaml

SITE = Path(__file__).resolve().parents[1]
ROOT = next(p for p in SITE.parents if (p / "AGENTS.md").is_file())
sys.path.insert(0, str(SITE / "editor"))
from pattern_tool.legacy.model_reader import drawables, export_svg

VIEWS = ("angle", "front", "back")
SHIRT = ROOT / "web/intent-edit-review/sewn/03_cuff_width"
SHIRT_URL = "../intent-edit-review/sewn/03_cuff_width"
CASE_NAMES = {"sandy-standard": "Sandy 基础款", "sandy-flared": "Sandy 加长增摆"}


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def preview_svg(state):
    """Lay out the exact saved cut and seam polygons in a two-by-two gallery view."""
    pieces = state["panels"]
    points = [p for piece in pieces for p in piece["cutOutline"]]
    min_x, min_y = (min(x[i] for x in points) for i in range(2))
    max_x, max_y = (max(x[i] for x in points) for i in range(2))
    scale = min(.46, 330 / (max_x-min_x), 300 / (max_y-min_y))
    width, height = (max_x-min_x)*scale, (max_y-min_y)*scale
    svg = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 940 840" role="img">',
        '<title>Sandy 的四片裙身</title><desc>实线是含10毫米缝份的裁剪线，虚线是缝线。</desc>',
        '<g fill="#283d35" font-family="Noto Sans CJK SC,sans-serif" font-size="21">',
        '<path d="M60 55h36" stroke="#205d50" stroke-width="3"/><text x="109" y="62">裁剪线</text>',
        '<path d="M237 55h36" stroke="#629789" stroke-width="2" stroke-dasharray="6 4"/><text x="286" y="62">缝线</text>',
    ]
    for i, piece in enumerate(pieces):
        cx, cy = (252 if i % 2 == 0 else 688), (253 if i < 2 else 601)
        left, top = cx-width/2, cy-height/2

        def point(xy):
            return ((xy[0]-min_x)*scale+left, (xy[1]-min_y)*scale+top)

        def coords(vertices):
            return " ".join(f"{x:.5f},{y:.5f}" for x, y in map(point, vertices))

        svg.extend([
            f'<polygon points="{coords(piece["cutOutline"])}" fill="#e6efe4" fill-opacity=".75" stroke="#205d50" stroke-width="2.8"/>',
            f'<polygon points="{coords(piece["polygon"])}" fill="none" stroke="#629789" stroke-width="1.75" stroke-dasharray="6 4"/>',
            f'<text x="{cx}" y="{cy+21:.3f}" text-anchor="middle">裁片 {i+1}</text>',
        ])
    x0, y = 60, 798
    x1 = x0+scale*100
    svg.extend([
        f'<path d="M{x0} {y-8}v16m0-8H{x1:.5f}m0-8v16" stroke="#283d35" stroke-width="1.7" fill="none"/>',
        f'<text x="{x1+13:.5f}" y="{y+7}" font-size="18">100 mm</text>',
        '</g></svg>',
    ])
    return "\n".join(svg) + "\n"


def webp_assets(src, dest):
    for view in VIEWS:
        with Image.open(src / f"{view}.png") as im:
            im.convert("RGB").save(dest / f"{view}.webp", quality=90, method=6)


def paths(id, **changes):
    base = f"gallery/{id}"
    values = {
        "id": id, "preview": f"{base}/preview.svg", "pattern": f"{base}/pattern.svg",
        "native": f"{base}/native.svg", "nativeLabel": "FreeSewing 原始 SVG",
        "model": f"{base}/skirt.obj", "modelLabel": "下载三维 OBJ ↓",
        "evidence": f"{base}/evidence.json",
        "views": {view: f"{base}/{view}.webp" for view in VIEWS},
    }
    values.update(changes)
    return values


def sandy(id, capture, renders):
    src, image_folder = capture / id, renders / id
    state = read(src / "state.json")
    draft = read(src / "draft-report.json")
    render = read(image_folder / "render.json")
    assert draft["independent"]["verdict"] == "PASS"
    assert render["geometry_sha256"] == draft["source_state_sha256"] == digest(src / "state.json")
    assert digest(src / "native.svg") == draft["native_svg_sha256"]
    assert render["vertices"] * 3 == len(state["positions"])
    assert render["faces"] * 3 == len(state["triangles"])
    dest = SITE / "gallery" / id
    dest.mkdir(exist_ok=True)
    for name in ("pattern.svg", "native.svg", "skirt.obj"):
        copyfile(src / name, dest / name)
    (dest / "state.json.gz").write_bytes(gzip.compress((src / "state.json").read_bytes(), mtime=0))
    (dest / "preview.svg").write_text(preview_svg(state), encoding="utf-8")
    webp_assets(image_folder, dest)
    write(dest / "evidence.json", {
        "draft": draft, "render": render, "captured_state": "state.json.gz", "physical_fit": "NOT_RUN",
    })
    case = draft["case"]
    material = {"cotton": "棉质", "linen": "亚麻"}[case["material"]]
    return paths(
        id, name=CASE_NAMES[id],
        state=f"gallery/{id}/state.json.gz",
        scope=f"FreeSewing Sandy 4.10.2 生成纸样。裙身在固定参考人体上以合成{material}参数求解 120 步，再由 Blender 渲染。原始 SVG 包含腰头，三维网格保留裙身。",
        metrics=[["裙长", f"{case['length_mm']} mm"],
                 ["圆摆比例", f"{case['circle_percent']}%"],
                 ["裁片", "4 片"]],
    )


def shirt(renders):
    id = "shirt-cuff"
    dest = SITE / "gallery" / id
    dest.mkdir(exist_ok=True)
    source = ROOT / "experiments/intent-edit-benchmark/results/03_cuff_width/output.dxf"
    decision = read(SHIRT / "decision.json")
    render = read(renders / id / "render.json")
    independent = read(SHIRT / "independent.json")
    assert decision["verdict"] == independent["verdict"] == "PASS"
    assert digest(source) == decision["source_dxf_sha256"] == digest(SHIRT / "source-input.dxf")
    assert digest(SHIRT / "source-spec.yaml") == decision["source_yaml_sha256"]
    assert render["geometry_sha256"] == digest(SHIRT / "files/model.glb")
    spec = yaml.safe_load((SHIRT / "source-spec.yaml").read_bytes())
    previews = export_svg(spec, drawables(spec))
    (dest / "pattern.svg").write_text(previews, encoding="utf-8")
    (dest / "preview.svg").write_text(previews, encoding="utf-8")
    webp_assets(renders / id, dest)
    write(dest / "evidence.json", {
        "decision": {key: decision[key] for key in (
            "id", "label", "verdict", "source_dxf", "source_yaml", "source_dxf_sha256", "source_yaml_sha256",
            "units_assumption", "profile", "model_sha256", "mode", "seaming", "measurements", "seams",
        )},
        "render": render, "verification": f"../../{SHIRT_URL}/independent.json",
        "physical_fit": "NOT_RUN",
    })
    return paths(
        id, name="贴身 T 恤袖口改版",
        scope="由实际袖口加宽 DXF 生成并核对接缝的单层静态外壳，Blender 渲染使用已验证的 GLB。原始 CAD 单位未标定，此处保留图形单位 U。",
        metrics=[["袖口展开宽", "+10 U"], ["接缝", "15 对"], ["外壳", "静态"]],
        native=f"{SHIRT_URL}/files/corrected-seam-lines.svg", nativeLabel="修正缝线 SVG",
        model=f"{SHIRT_URL}/files/model.glb", modelLabel="下载三维 GLB ↓",
    )


def make_editor():
    source = SITE / "editor"
    dest = SITE / "downloads" / "pattern-agent-editor.zip"
    with ZipFile(dest, "w", compression=ZIP_DEFLATED) as archive:
        for path in sorted(source.rglob("*")):
            relative = path.relative_to(source)
            if path.is_file() and not any(x.startswith((".", "__pycache__")) for x in relative.parts):
                info = ZipInfo((Path("pattern-agent-editor") / relative).as_posix(), (1980, 1, 1, 0, 0, 0))
                info.compress_type = ZIP_DEFLATED
                info.external_attr = 0o644 << 16
                archive.writestr(info, path.read_bytes())


def main():
    parser = ArgumentParser()
    parser.add_argument("--capture", type=Path, required=True)
    parser.add_argument("--renders", type=Path, required=True)
    args = parser.parse_args()
    cases = [sandy(id, args.capture, args.renders) for id in CASE_NAMES]
    cases.append(shirt(args.renders))
    make_editor()
    files = {}
    for case in cases:
        assets = (case["preview"], case["pattern"], case["native"], case["model"], case["evidence"], *case["views"].values())
        if "state" in case:
            assets += (case["state"],)
        for file in assets:
            path = (SITE / file).resolve()
            files[file] = digest(path)
    for path in sorted((SITE / "downloads").glob("*")):
        files[str(path.relative_to(SITE))] = digest(path)
    write(SITE / "gallery/manifest.json", {"schema": "pattern-agent-gallery/1", "samples": cases, "sha256": files})


if __name__ == "__main__":
    main()
