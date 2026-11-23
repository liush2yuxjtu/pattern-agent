"""Derive fold angles from the exact CLO garment mesh recorded at each frame."""
import base64
import hashlib
import json
from pathlib import Path
import struct
import sys

FIT_EXPORT = Path(__file__).resolve().parents[1].parent / "clo-fit-export" / "scripts"


def binary_glb(mesh):
    if mesh.read_bytes()[:4] == b"glTF":
        return mesh
    source = json.loads(mesh.read_text(encoding="utf-8"))
    buffer, = source["buffers"]
    uri = buffer.pop("uri")
    mime, data = uri.split(",", 1)
    if not mime.startswith("data:") or not mime.endswith(";base64"):
        raise ValueError("CLO GLTF export did not embed its geometry")
    binary = base64.b64decode(data, validate=True)
    if len(binary) != buffer["byteLength"]:
        raise ValueError("CLO GLTF buffer length mismatch")
    doc = json.dumps(source, separators=(",", ":")).encode()
    doc += b" " * (-len(doc) % 4)
    binary += b"\0" * (-len(binary) % 4)
    glb = mesh.with_suffix(".glb")
    glb.write_bytes(struct.pack("<4sII", b"glTF", 2, 28 + len(doc) + len(binary))
                    + struct.pack("<I4s", len(doc), b"JSON") + doc
                    + struct.pack("<I4s", len(binary), b"BIN\0") + binary)
    return glb


def add_folds(folder, receipt, lookup):
    if not any(frame.get("cloth_mesh") for frame in receipt.get("frames", [])):
        return
    sys.path.insert(0, str(FIT_EXPORT))
    from export_fit import read_cloth
    from fold_preview import measure_folds, render_folds

    geometry_hashes = set()
    for frame in receipt["frames"]:
        mesh = lookup(folder, frame.get("cloth_mesh"))
        if not mesh:
            continue
        try:
            pieces = read_cloth(binary_glb(mesh))
            checksum = hashlib.sha256()
            geometry, values = {}, []
            for number, (positions, uv, faces) in enumerate(pieces):
                checksum.update(positions.tobytes())
                data, spatial = measure_folds(positions * 1000, uv, faces, 30)
                if data["fold_p95_deg"] is not None:
                    values.append(data["fold_p95_deg"])
                    geometry[str(number)] = spatial
            geometry_hashes.add(checksum.hexdigest())
            if values:
                image = mesh.with_name("fold.png")
                spatial, _ = render_folds(geometry, f"CLO frame {frame['index']}", 30, 100)
                image.write_bytes(spatial)
                frame["maps"]["fold"] = {"frame": frame["index"], "source": "CLO mesh dihedral",
                                         "unit": "deg", "value": max(values),
                                         "image": image.relative_to(folder.resolve()).as_posix()}
        except (ValueError, KeyError, OSError) as error:
            frame["fold_error"] = str(error)
    receipt["recording"]["cloth_geometry_changed"] = len(geometry_hashes) > 1
