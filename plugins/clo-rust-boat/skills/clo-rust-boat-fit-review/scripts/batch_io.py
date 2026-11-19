"""Shared input contract and Rust seam operations for the Boat batch."""
import hashlib
import json
import re
import subprocess

POSE_ID = re.compile(r"pose-[0-9]{2,4}")
SEAM_FILES = ("edges.json", "edge-map.json", "seams.json", "connectivity.json")
NATIVE_MAPS = {
    "fit": ("试穿图", ("fit-front.png", "fit-back.png")),
    "stress": ("应力图", ("stress-front.png", "stress-back.png")),
}


def read_manifest(inputs):
    manifest = json.loads((inputs / "manifest.json").read_text())
    poses = manifest["poses"]
    if manifest["units"] != "mm" or not poses:
        raise ValueError("需要至少一组毫米制姿势")
    labels = [pose["label"] for pose in poses]
    names = [pose["id"] for pose in poses]
    if any(not POSE_ID.fullmatch(name) for name in names):
        raise ValueError("无效姿势文件名")
    if len(set(labels)) != len(labels) or len(set(names)) != len(names):
        raise ValueError("姿势名称和文件编号必须唯一")
    for pose in poses:
        path = inputs / (pose["id"] + ".glb")
        if hashlib.sha256(path.read_bytes()).hexdigest() != pose["input_sha256"]:
            raise ValueError(f'姿势输入摘要不一致：{pose["label"]}')
    return manifest


def seam_sources(inputs, required=False):
    root = inputs / "seams"
    if not root.exists() and not required:
        return ()
    return tuple(root / name for name in SEAM_FILES)


def native_maps(inputs, pose):
    root = inputs / "maps" / pose["id"]
    return {kind: tuple(root / filename for filename in filenames)
            for kind, (_, filenames) in NATIVE_MAPS.items()}


def run_native(native, output, source, name):
    payload = subprocess.check_output([str(native), *map(str, source)])
    parsed = json.loads(payload)
    (output / (name + ".json")).write_bytes(payload)
    return parsed


def review_seams(native, files, output):
    edges, mapping, seams, connection = files
    project = output / "sewn.pattern.json"
    audit = run_native(native, output, ["clo-import", edges, mapping, seams, project], "seam-audit")
    reopened = run_native(native, output, ["audit", project], "seam-reopened")
    if reopened != audit:
        raise ValueError("缝合工程重开后读数不一致")
    constraints = run_native(native, output, ["constraints", project], "constraints")
    net = run_native(native, output, ["connectivity", connection, "--strict"], "connectivity")
    return [f'{audit["declared_seams"]} 组缝合生成 {len(constraints):,} 对约束。',
            f'参照工程 {net["pieces"]} 片、{net["seam_groups"]} 组，'
            f'连成 {len(net["components"])} 个组件。']
