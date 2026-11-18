#!/usr/bin/env python3
"""Import Golden Garment YAML 1.1 into a source-bound Pattern JSON v2 contract."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import re
import tempfile
import sys
from typing import Any

import jsonschema
import yaml

SOURCE_VERSION = "1.1"
PATTERN_SCHEMA = "2.1.0"
SOURCE_PATH = "patterns/fitted-tshirt/input-spec.yaml"
PIECES = {"前片": "front-bodice", "后片": "back-bodice", "袖片": "sleeve", "领条": "neckband"}
ARTIFACTS = ("geometry", "mesh", "physics", "debugger", "timeline", "validation")
EXPECTED_COUNTS = {"裁片": 4, "折线": 126, "直线": 78, "文字": 27, "折线顶点": 1487}
SCHEMA_PATH = Path(__file__).with_name("pattern-json-v2.schema.json")


class Yaml11Loader(yaml.SafeLoader):
    def construct_mapping(self, node, deep=False):
        self.flatten_mapping(node)
        mapping = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if not isinstance(key, str):
                raise ValueError("YAML mapping keys must be strings")
            if key in mapping:
                raise ValueError(f"Duplicate YAML key: {key}")
            mapping[key] = self.construct_object(value_node, deep=deep)
        return mapping


Yaml11Loader.yaml_implicit_resolvers = {
    first: [(tag, rx) for tag, rx in resolvers if tag != "tag:yaml.org,2002:bool"]
    for first, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
}
Yaml11Loader.add_implicit_resolver(
    "tag:yaml.org,2002:bool", re.compile(r"^(?:true|false|True|False|TRUE|FALSE)$"), list("tTfF")
)


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def pointer(*parts: Any) -> str:
    return "/" + "/".join(str(part).replace("~", "~0").replace("/", "~1") for part in parts)


def stable_id(kind: str, *names: str) -> str:
    return f"{kind}:" + digest(canonical(list(names)))


def interface_id(piece: str, name: str) -> str:
    return stable_id("interface", piece, name)


def parse_source(raw: bytes) -> dict[str, Any]:
    doc = yaml.load(raw.decode("utf-8"), Loader=Yaml11Loader)
    if not isinstance(doc, dict):
        raise ValueError("Golden Garment YAML root must be a mapping")
    canonical(doc)
    validate_source(doc)
    return doc


def validate_source(doc: dict[str, Any]) -> None:
    if doc["文件约定"]["格式版本"] != SOURCE_VERSION:
        raise ValueError("Source format version must be 1.1")
    units = doc["单位与坐标"]
    if units["坐标单位"] != "U":
        raise ValueError("Golden Garment coordinate unit must remain U")
    ratio = units["实际比例"]
    if ratio["状态"] != "未标定" or ratio.get("每U毫米") is not None or ratio.get("mm_per_unit") is not None:
        raise ValueError("Golden Garment scale must remain uncalibrated with no mm_per_unit")
    geometry = doc["完整二维几何"]
    if set(geometry) != set(PIECES) or set(doc["裁片接口"]) != set(PIECES):
        raise ValueError("Golden Garment must contain its four named pieces")
    counts = {key: 0 for key in EXPECTED_COUNTS}
    counts["裁片"] = len(geometry)
    line_names = {}
    for piece, geom in geometry.items():
        names = [line["名称"] for line in geom["线条"]]
        if len(set(names)) != len(names) or any(not isinstance(name, str) or not name for name in names):
            raise ValueError(f"Duplicate or empty line name in {piece}")
        line_names[piece] = set(names)
        for line in geom["线条"]:
            if line["线型"] not in {"直线", "折线"}:
                raise ValueError("Unsupported source line type")
            counts[line["线型"]] += 1
            points = line["点位"]
            if len(points) < 2:
                raise ValueError("Every line needs at least two points")
            for point in points:
                for axis in ("横", "高"):
                    coordinate = point[axis]
                    if type(coordinate) not in (float, int) or not math.isfinite(coordinate):
                        raise ValueError("Coordinates must be finite numbers")
            if line["线型"] == "折线":
                counts["折线顶点"] += len(points)
        counts["文字"] += len(geom["文字"])
        for contour in geom["轮廓"].values():
            check_edge_chain(contour["组成"], line_names[piece])
        for interface in doc["裁片接口"][piece].values():
            check_edge_chain(interface["组成"], line_names[piece])
    if counts != EXPECTED_COUNTS or doc["文件约定"]["几何清单预期"] != counts:
        raise ValueError(f"Golden Garment geometry inventory mismatch: {counts}")
    measures = doc["关键尺寸"]["项目"]
    interfaces = doc["裁片接口"]
    if len(measures) != 23 or sum(map(len, interfaces.values())) != 25:
        raise ValueError("Golden Garment requires 23 measurements and 25 interfaces")
    for measure in measures.values():
        if "裁片" in measure:
            piece = measure["裁片"]
            for name in measure.get("线条", []):
                if name not in line_names[piece]:
                    raise ValueError(f"Missing measurement line: {piece}/{name}")
            for name in measure.get("定位点", []):
                if name not in geometry[piece]["定位点"]:
                    raise ValueError(f"Missing measurement point: {piece}/{name}")
        check_interface_refs(measure.get("接口", []), interfaces)
        if any(name not in measures for name in measure.get("尺寸项目", [])):
            raise ValueError("Missing measurement dependency")
    active, visited = set(), set()

    def visit_measurement(name):
        if name in active:
            raise ValueError(f"Cyclic measurement dependency: {name}")
        if name in visited:
            return
        active.add(name)
        for dependency in measures[name].get("尺寸项目", []):
            visit_measurement(dependency)
        active.remove(name)
        visited.add(name)

    for name in measures:
        visit_measurement(name)
    check_interface_tree(doc["连接关系"], interfaces)
    seams = doc["缝级关系图"]["缝级记录"]
    if len(seams) != 11 or len({seam["关系名称"] for seam in seams}) != 11 or len(doc["连接关系"]) != 9:
        raise ValueError("Golden Garment requires 11 named seam records and 9 summaries")
    for seam in seams:
        if seam["汇总关系名称"] not in doc["连接关系"]:
            raise ValueError("Missing seam summary")
        for side in (seam["边一"], seam["边二"]):
            refs = side if isinstance(side, list) else side["候选接口"]
            check_interface_refs(refs, interfaces)
    for role in doc["成衣部件角色"].values():
        if isinstance(role, dict) and role.get("采用裁片") not in PIECES:
            raise ValueError("Unknown role piece")


def check_edge_chain(chain, names) -> None:
    if not chain:
        raise ValueError("Empty edge chain")
    for segment in chain:
        if segment["线条"] not in names or segment["方向"] not in {"正向", "反向"}:
            raise ValueError(f"Invalid edge reference or direction: {segment}")


def check_interface_refs(refs, interfaces) -> None:
    if not refs:
        return
    for ref in refs:
        if ref["裁片"] not in interfaces or ref["接口"] not in interfaces[ref["裁片"]]:
            raise ValueError(f"Missing interface: {ref}")


def check_interface_tree(value, interfaces) -> None:
    if isinstance(value, dict):
        if "裁片" in value and "接口" in value:
            check_interface_refs([value], interfaces)
        for child in value.values():
            check_interface_tree(child, interfaces)
    elif isinstance(value, list):
        for child in value:
            check_interface_tree(child, interfaces)


def unknown(source_path=None, source_record=None) -> dict[str, Any]:
    return {"status": "UNKNOWN" if source_path else "MISSING", "value": None,
            "source_path": source_path, "source_record": copy.deepcopy(source_record)}


def seam_side(side) -> dict[str, Any]:
    unresolved = isinstance(side, dict)
    refs = side["候选接口"] if unresolved else side
    ids = [interface_id(ref["裁片"], ref["接口"]) for ref in refs]
    return {"status": "UNRESOLVED" if unresolved else "RESOLVED",
            "interface_ids": None if unresolved else ids,
            "candidate_interface_ids": ids if unresolved else []}


def project(doc: dict[str, Any], source_sha: str, source_path: str, reference_assets=None) -> dict[str, Any]:
    geometry = doc["完整二维几何"]
    pieces, edges, interfaces, manufacturing = [], [], [], []
    for name in PIECES:
        geom = geometry[name]
        piece_id = PIECES[name]
        roles = [{"name": role_name, "source_path": pointer("成衣部件角色", role_name), "source_record": copy.deepcopy(role)}
                 for role_name, role in sorted(doc["成衣部件角色"].items())
                 if isinstance(role, dict) and role.get("采用裁片") == name]
        pieces.append({"piece_id": piece_id, "name": name, "source_path": pointer("完整二维几何", name),
                       "roles": roles, "cutting": copy.deepcopy(doc["裁剪清单"][name]), "geometry": copy.deepcopy(geom)})
        for index, line in enumerate(geom["线条"]):
            edges.append({"edge_id": stable_id("edge", name, line["名称"]), "piece_id": piece_id,
                          "name": line["名称"], "source_path": pointer("完整二维几何", name, "线条", index)})
        for interface_name, record in sorted(doc["裁片接口"][name].items()):
            interfaces.append({**copy.deepcopy(record), "interface_id": interface_id(name, interface_name),
                               "piece_id": piece_id, "piece": name, "name": interface_name,
                               "source_path": pointer("裁片接口", name, interface_name),
                               "edge_chain": [{"edge_id": stable_id("edge", name, segment["线条"]), "direction": segment["方向"]}
                                              for segment in record["组成"]]})
        cutting = doc["裁剪清单"][name]
        manufacturing.append({"piece_id": piece_id,
                              "cut_quantity": unknown(pointer("裁剪清单", name, "批准裁数"), cutting["批准裁数"]),
                              "grainline": unknown(pointer("裁剪清单", name, "纱向"), cutting["纱向"]),
                              "seam_line": unknown(pointer("确定性执行与输出", "净样与毛样"), doc["确定性执行与输出"]["净样与毛样"]),
                              "cut_line": unknown(pointer("裁剪清单", name, "可用裁剪轮廓"), cutting["可用裁剪轮廓"]),
                              "notches": unknown(), "grading": unknown(),
                              "edge_allowances": [{"edge_id": stable_id("edge", name, line["名称"]), "status": "UNKNOWN",
                                                   "value": None, "source_path": pointer("工艺参数", "缝份")}
                                                  for line in geom["线条"]]})
    semantic_sha = digest(canonical(doc))
    info, units = doc["文件约定"], doc["单位与坐标"]
    result = {
        "schema": {"name": "pattern-json-v2", "version": PATTERN_SCHEMA, "dialect": "JSON"},
        "garment": {"garment_id": "golden-garment:fitted-tshirt-m", "name": info["名称"],
                    "category": doc["款式特征"]["品类"], "size": doc["款式特征"]["标注尺码"],
                    "state": "baseline", "production_ready": False},
        "revision": {"revision_id": "sha256:" + semantic_sha, "source_spec_version": SOURCE_VERSION,
                     "parent_revision": None, "status": "frozen-input", "stale_propagation": list(ARTIFACTS),
                     "spec_patch": None, "geometry_patch": None},
        "provenance": {"source_path": source_path, "source_sha256": source_sha, "semantic_sha256": semantic_sha,
                       "source_format": "YAML", "source_yaml_version": SOURCE_VERSION,
                       "source_document_is_authoritative": True, "dxf_is_reference_only": True,
                       "reference_assets": copy.deepcopy(reference_assets or [])},
        "units": {"coordinate_unit": "U", "mm_per_unit": None, "reference_size_unit": units["参考尺码单位"],
                  "angle_unit": units["角度单位"], "scale_status": units["实际比例"]["状态"]},
        "pieces": pieces, "edges": edges, "interfaces": interfaces,
        "measurements": [{**copy.deepcopy(record), "measurement_id": stable_id("measurement", name),
                          "name": name, "source_path": pointer("关键尺寸", "项目", name)}
                         for name, record in sorted(doc["关键尺寸"]["项目"].items())],
        "seam_relations": [{"relation_id": stable_id("summary", name), "name": name,
                            "source_path": pointer("连接关系", name), "value": copy.deepcopy(record)}
                           for name, record in sorted(doc["连接关系"].items())],
        "seam_pairs": [{"seam_id": stable_id("seam", record["关系名称"]), "name": record["关系名称"],
                        "source_path": pointer("缝级关系图", "缝级记录", index), "source_record": copy.deepcopy(record),
                        "side_a": seam_side(record["边一"]), "side_b": seam_side(record["边二"])}
                       for index, record in enumerate(doc["缝级关系图"]["缝级记录"])],
        "manufacturing": {"pieces": manufacturing}, "review_events": [],
        "construction": {field: copy.deepcopy(doc[key]) for field, key in {
            "style_sheet": "结构化款式单", "block_layers": "原型与部件分层", "derivations": "尺寸推导",
            "decisions": "结构决策与操作方案", "execution": "确定性执行与输出"}.items()},
        "derived_artifacts": {kind: {"status": "NOT_RUN", "source_revision_id": None, "result": None} for kind in ARTIFACTS},
        "status": {"delivery": copy.deepcopy(doc["交付状态"]), "unknowns_are_preserved": True,
                   "null_is_not_zero": True, "unit_conversion_guessed": False, "production_release": False},
        "source_document": copy.deepcopy(doc), "geometry": copy.deepcopy(geometry),
    }
    for field, key in {"cutting": "裁剪清单", "component_roles": "成衣部件角色", "materials": "材料选择",
                       "reference_size_table": "参考尺码表", "workflow": "制版流程", "validation": "版型校验与测试"}.items():
        result[field] = copy.deepcopy(doc[key])
    return result


def artifact_status(revision_id: str, artifact: dict[str, Any]) -> str:
    if artifact["result"] is None:
        return "NOT_RUN"
    return "CURRENT" if artifact["source_revision_id"] == revision_id else "STALE"


def validate_invariants(manifest: dict[str, Any], expected_sha256: str | None = None) -> list[str]:
    errors = []
    try:
        canonical(manifest)
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator.check_schema(schema)
        jsonschema.validate(manifest, schema)
        doc = manifest["source_document"]
        validate_source(doc)
        expected = project(doc, manifest["provenance"]["source_sha256"], SOURCE_PATH, manifest["provenance"]["reference_assets"])
        for field, value in expected.items():
            if field not in {"revision", "derived_artifacts"} and canonical(manifest[field]) != canonical(value):
                errors.append(f"Source projection mismatch: {field}")
        revision = {**manifest["revision"], "parent_revision": None}
        if revision != expected["revision"]:
            errors.append("Revision does not match source content")
        for kind, artifact in manifest["derived_artifacts"].items():
            if artifact["status"] != artifact_status(manifest["revision"]["revision_id"], artifact):
                errors.append(f"Incorrect derived artifact status: {kind}")
            if (artifact["result"] is None) != (artifact["source_revision_id"] is None):
                errors.append(f"Missing artifact result or revision: {kind}")
        for field, key in (("pieces", "piece_id"), ("edges", "edge_id"), ("interfaces", "interface_id"),
                           ("measurements", "measurement_id"), ("seam_pairs", "seam_id"), ("seam_relations", "relation_id")):
            ids = [record[key] for record in manifest[field]]
            if len(ids) != len(set(ids)):
                errors.append(f"Duplicate ID: {field}")
        if expected_sha256 and manifest["provenance"]["source_sha256"] != expected_sha256:
            errors.append("Source SHA-256 mismatch")
    except (ValueError, TypeError, KeyError, jsonschema.ValidationError, jsonschema.SchemaError) as error:
        errors.append(str(error))
    return errors


def import_golden_garment(raw: bytes, source_path: str = SOURCE_PATH, previous=None, *, reference_dxf: bytes | None = None) -> dict[str, Any]:
    if source_path != SOURCE_PATH:
        raise ValueError(f"Logical source_path must be {SOURCE_PATH}")
    doc = parse_source(raw)
    assets = [] if reference_dxf is None else [{"source_path": "patterns/fitted-tshirt/input.dxf",
                                              "sha256": digest(reference_dxf), "role": "reference-only"}]
    result = project(doc, digest(raw), source_path, assets)
    if previous is not None:
        errors = validate_invariants(previous)
        if errors:
            raise ValueError("Invalid previous manifest: " + "; ".join(errors))
        previous_revision = previous["revision"]["revision_id"]
        if previous_revision != result["revision"]["revision_id"]:
            result["revision"]["parent_revision"] = previous_revision
        else:
            result["revision"]["parent_revision"] = previous["revision"]["parent_revision"]
        for kind in ARTIFACTS:
            artifact = copy.deepcopy(previous["derived_artifacts"][kind])
            artifact["status"] = artifact_status(result["revision"]["revision_id"], artifact)
            result["derived_artifacts"][kind] = artifact
    errors = validate_invariants(result)
    if errors:
        raise ValueError("; ".join(errors))
    return result


def read_manifest(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"), parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--expected-sha256")
    parser.add_argument("--previous", type=Path)
    parser.add_argument("--reference-dxf", type=Path)
    args = parser.parse_args()
    temporary = None
    try:
        protected_inputs = [args.input, *([args.reference_dxf] if args.reference_dxf else [])]
        if any(args.output.resolve() == path.resolve() for path in protected_inputs):
            raise ValueError("Output must not overwrite the source YAML or reference DXF")
        raw = args.input.read_bytes()
        if args.expected_sha256 and digest(raw) != args.expected_sha256:
            raise ValueError("Source SHA-256 mismatch")
        previous = read_manifest(args.previous) if args.previous else None
        reference_dxf = args.reference_dxf.read_bytes() if args.reference_dxf else None
        result = import_golden_garment(raw, previous=previous, reference_dxf=reference_dxf)
        serialized = json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=args.output.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(serialized)
        os.replace(temporary, args.output)
        temporary = None
        if args.check:
            print(json.dumps({"status": "PASS", "schema": PATTERN_SCHEMA, "source_sha256": digest(raw),
                              "pieces": len(result["pieces"]), "edges": len(result["edges"]),
                              "measurements": len(result["measurements"]), "interfaces": len(result["interfaces"]),
                              "seam_pairs": len(result["seam_pairs"]), "seam_summaries": len(result["seam_relations"]),
                              "entities": 231, "polyline_vertices": 1487, "coordinate_unit": "U",
                              "mm_per_unit": None, "production_release": False}, sort_keys=True))
        return 0
    except (OSError, UnicodeError, ValueError, TypeError, KeyError, yaml.YAMLError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
