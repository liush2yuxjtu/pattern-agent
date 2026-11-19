#!/usr/bin/env python3
"""Extract compact cloth-only geometry from meter-verified pose meshes."""
import argparse
import hashlib
import json
import struct
from pathlib import Path

JSON = 0x4E4F534A
BIN = 0x004E4942
MAGIC = 0x46546C67
WIDTH = {5121: 1, 5123: 2, 5125: 4, 5126: 4}


def unpack(path):
    data = path.read_bytes()
    if struct.unpack_from("<III", data) != (MAGIC, 2, len(data)):
        raise ValueError(f"无效 GLB：{path}")
    chunks = {}
    offset = 12
    while offset < len(data):
        size, kind = struct.unpack_from("<II", data, offset)
        offset += 8
        if offset + size > len(data):
            raise ValueError(f"GLB 分块越界：{path}")
        chunks[kind] = memoryview(data)[offset:offset + size]
        offset += size
    return json.loads(bytes(chunks[JSON])), chunks[BIN], hashlib.sha256(data).hexdigest()


def sanitize(path):
    source, binary, original_sha = unpack(path)
    meshes = source["meshes"]
    if len(meshes) != 1 or meshes[0].get("name") != "Cloth_mesh":
        raise ValueError("需要有公制纸样坐标的单一服装网格，不能携带人体")
    exported = {"asset": {"version": "2.0"}, "accessors": [], "bufferViews": [],
                "buffers": [], "meshes": [{"name": "Cloth_mesh", "primitives": []}],
                "nodes": [{"mesh": 0}], "scenes": [{"nodes": [0]}], "scene": 0}
    packed = bytearray()
    topology = hashlib.sha256()

    def copy_accessor(index, shape, allowed):
        accessor = source["accessors"][index]
        view = source["bufferViews"][accessor["bufferView"]]
        kind, count = accessor["componentType"], accessor["count"]
        if (accessor["type"] != shape or kind not in allowed or count < 1 or
                accessor.get("sparse") or accessor.get("normalized") or view["buffer"] != 0):
            raise ValueError("需要原始浮点坐标和无符号索引")
        width = WIDTH[kind] * {"VEC3": 3, "VEC2": 2, "SCALAR": 1}[shape]
        stride = view.get("byteStride", width)
        outer = view.get("byteOffset", 0)
        inner = accessor.get("byteOffset", 0)
        offset = outer + inner
        if (stride < width or min(outer, inner) < 0 or
                inner + (count-1)*stride + width > view["byteLength"] or
                outer + view["byteLength"] > len(binary)):
            raise ValueError("GLB 几何访问器越界")
        values = (bytes(binary[offset:offset + width*count]) if stride == width else
                  b"".join(binary[offset+i*stride:offset+i*stride+width] for i in range(count)))
        packed.extend(b"\x00" * (-len(packed) % 4))
        pos = len(packed)
        packed.extend(values)
        new_index = len(exported["accessors"])
        exported["bufferViews"].append({"buffer": 0, "byteOffset": pos, "byteLength": len(values)})
        exported["accessors"].append({"bufferView": new_index, "componentType": kind,
                                      "count": count, "type": shape,
                                      **{k: accessor[k] for k in ("min", "max") if k in accessor}})
        if shape != "VEC3":
            topology.update(struct.pack("<II", kind, count))
            topology.update(values)
        return new_index, count

    for primitive in meshes[0]["primitives"]:
        if primitive.get("mode", 4) != 4 or primitive.get("targets"):
            raise ValueError("只接受静态三角面")
        attributes = primitive["attributes"]
        pos, vertices = copy_accessor(attributes["POSITION"], "VEC3", {5126})
        uv, flat = copy_accessor(attributes["TEXCOORD_0"], "VEC2", {5126})
        ind, indices = copy_accessor(primitive["indices"], "SCALAR", {5121, 5123, 5125})
        if vertices != flat or indices % 3:
            raise ValueError("坐标、索引或裁片数据不匹配")
        exported["meshes"][0]["primitives"].append(
            {"attributes": {"POSITION": pos, "TEXCOORD_0": uv}, "indices": ind})
    exported["buffers"] = [{"byteLength": len(packed)}]
    raw = json.dumps(exported, separators=(",", ":")).encode()
    raw += b" " * (-len(raw) % 4)
    packed.extend(b"\0" * (-len(packed) % 4))
    data = (struct.pack("<IIIII", MAGIC, 2, 28+len(raw)+len(packed), len(raw), JSON) +
            raw + struct.pack("<II", len(packed), BIN) + packed)
    return data, topology.hexdigest(), original_sha


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("--mesh-source", required=True)
    parser.add_argument("--pose", action="append", nargs=2, required=True, metavar=("姿势", "GLB"))
    args = parser.parse_args()
    labels = [label for label, _ in args.pose]
    if len(labels) != len(set(labels)):
        parser.error("姿势名称必须唯一")
    prepared = [sanitize(Path(path)) for _, path in args.pose]
    if len({row[1] for row in prepared}) != 1:
        parser.error("姿势之间的裁片 UV 或三角面索引不一致")
    args.output.mkdir(parents=True)
    poses = []
    for number, (label, (data, _, source_sha)) in enumerate(zip(labels, prepared), 1):
        stem = f"pose-{number:02}"
        (args.output / f"{stem}.glb").write_bytes(data)
        poses.append({"id": stem, "label": label, "source_sha256": source_sha,
                      "input_sha256": hashlib.sha256(data).hexdigest()})
    manifest = {"mesh_source": args.mesh_source, "units": "mm", "pose_topology_sha256": prepared[0][1],
                "poses": poses}
    (args.output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    print(f"已验证 {len(poses)} 个服装姿势的拓扑，仅保留计算所用几何")


if __name__ == "__main__":
    main()
