#!/usr/bin/env python3
"""Deterministic Golden Garment YAML 1.1 -> Pattern JSON v2 importer."""
from __future__ import annotations
import argparse, copy, hashlib, json, re
from pathlib import Path
from typing import Any
import yaml

SOURCE_VERSION = "1.1"
PATTERN_SCHEMA = "2.0.0"

class Yaml11Loader(yaml.SafeLoader):
    pass

# Copy the resolver table before changing it. Otherwise the subclass can
# mutate SafeLoader's shared resolver map.
Yaml11Loader.yaml_implicit_resolvers = {
    first: list(resolvers)
    for first, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
}

# Keep YAML 1.1 presentation strings such as yes/no/on/off as strings.
# Explicit !!bool remains supported by the YAML constructor.
for first, resolvers in list(Yaml11Loader.yaml_implicit_resolvers.items()):
    Yaml11Loader.yaml_implicit_resolvers[first] = [
        (tag, rx) for tag, rx in resolvers
        if tag != "tag:yaml.org,2002:bool"
    ]

def slug(value: str) -> str:
    aliases = {"前片":"front-bodice","后片":"back-bodice","袖片":"sleeve","领条":"neckband"}
    value = str(value)
    if value in aliases:
        return aliases[value]
    value = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "-", value).strip("-").lower()
    return value or "unnamed"

def get_path(root: dict[str, Any], *keys: str, default: Any = None) -> Any:
    value: Any = root
    for key in keys:
        if not isinstance(value, dict) or key not in value:
            return default
        value = value[key]
    return value

def deep_copy(value: Any) -> Any:
    return copy.deepcopy(value)

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def extract_pieces(doc: dict[str, Any]) -> list[dict[str, Any]]:
    geometry = get_path(doc, "完整二维几何", default={})
    roles = get_path(doc, "成衣部件角色", default={})
    cutting = get_path(doc, "裁剪清单", default={})
    pieces = []
    for name, geom in (geometry.items() if isinstance(geometry, dict) else []):
        role = None
        role_quantity = None
        if isinstance(roles, dict):
            for role_name, role_value in roles.items():
                if isinstance(role_value, dict) and role_value.get("采用裁片") == name:
                    role, role_quantity = role_name, role_value.get("角色数量")
        pieces.append({
            "piece_id": slug(name),
            "name": name,
            "source_path": f"/完整二维几何/{name}",
            "role": role,
            "role_quantity": role_quantity,
            "cutting": deep_copy(cutting.get(name) if isinstance(cutting, dict) else None),
            "geometry": deep_copy(geom),
        })
    return pieces

def extract_measurements(doc: dict[str, Any]) -> list[dict[str, Any]]:
    project = get_path(doc, "关键尺寸", "项目", default={})
    return [{
        "measurement_id": f"measurement:{slug(name)}",
        "name": name,
        "source_path": f"/关键尺寸/项目/{name}",
        **deep_copy(value if isinstance(value, dict) else {"value": value}),
    } for name, value in (project.items() if isinstance(project, dict) else [])]

def extract_interfaces(doc: dict[str, Any]) -> list[dict[str, Any]]:
    source = get_path(doc, "裁片接口", default={})
    out = []
    for piece_name, interfaces in (source.items() if isinstance(source, dict) else []):
        if not isinstance(interfaces, dict):
            continue
        for edge_name, value in interfaces.items():
            record = {
                "interface_id": f"interface:{slug(piece_name)}:{slug(edge_name)}",
                "piece_id": slug(piece_name),
                "piece": piece_name,
                "name": edge_name,
                "source_path": f"/裁片接口/{piece_name}/{edge_name}",
            }
            record.update(deep_copy(value if isinstance(value, dict) else {"value": value}))
            out.append(record)
    return out

def extract_relations(doc: dict[str, Any]) -> list[dict[str, Any]]:
    source = get_path(doc, "连接关系", default={})
    return [{
        "relation_id": f"seam:{slug(name)}",
        "name": name,
        "source_path": f"/连接关系/{name}",
        "value": deep_copy(value),
    } for name, value in (source.items() if isinstance(source, dict) else [])]

def build_v2(doc: dict[str, Any], raw: bytes, source_path: str) -> dict[str, Any]:
    file_info = get_path(doc, "文件约定", default={})
    units = get_path(doc, "单位与坐标", default={})
    delivery = get_path(doc, "交付状态", default={})
    ratio = get_path(units, "实际比例", default={})
    mm_per_unit = None
    if isinstance(ratio, dict) and ratio.get("状态") not in {"未标定", "待确认"}:
        mm_per_unit = ratio.get("每U毫米", ratio.get("mm_per_unit"))
    return {
        "schema": {"name":"pattern-json-v2","version":PATTERN_SCHEMA,"dialect":"JSON"},
        "garment": {
            "garment_id":"golden-garment:fitted-tshirt-m",
            "name":get_path(file_info,"名称"),
            "category":get_path(doc,"款式特征","品类"),
            "size":get_path(doc,"款式特征","标注尺码"),
            "state":"baseline",
            "production_ready":False,
        },
        "revision": {
            "revision_id":"golden-garment-yaml-1.1:baseline",
            "source_spec_version":SOURCE_VERSION,
            "parent_revision":None,
            "status":"frozen-input",
            "stale_propagation":["pattern-geometry","derived-mesh","physics-results","debugger-results","timeline-results","validation-results"],
        },
        "provenance": {
            "source_path":source_path,
            "source_sha256":sha256_bytes(raw),
            "source_format":"YAML",
            "source_yaml_version":SOURCE_VERSION,
            "source_document_is_authoritative":True,
            "dxf_is_reference_only":True,
        },
        "units": {
            "coordinate_unit":get_path(units,"坐标单位"),
            "mm_per_unit":mm_per_unit,
            "reference_size_unit":get_path(units,"参考尺码单位"),
            "angle_unit":get_path(units,"角度单位"),
            "scale_status":get_path(units,"实际比例","状态"),
        },
        "pieces":extract_pieces(doc),
        "measurements":extract_measurements(doc),
        "interfaces":extract_interfaces(doc),
        "seam_relations":extract_relations(doc),
        "cutting":deep_copy(get_path(doc,"裁剪清单",default={})),
        "component_roles":deep_copy(get_path(doc,"成衣部件角色",default={})),
        "materials":deep_copy(get_path(doc,"材料选择",default={})),
        "reference_size_table":deep_copy(get_path(doc,"参考尺码表",default={})),
        "workflow":deep_copy(get_path(doc,"制版流程",default={})),
        "construction":{
            "style_sheet":deep_copy(get_path(doc,"结构化款式单",default={})),
            "block_layers":deep_copy(get_path(doc,"原型与部件分层",default={})),
            "derivations":deep_copy(get_path(doc,"尺寸推导",default={})),
            "decisions":deep_copy(get_path(doc,"结构决策与操作方案",default={})),
            "execution":deep_copy(get_path(doc,"确定性执行与输出",default={})),
        },
        "validation":deep_copy(get_path(doc,"版型校验与测试",default={})),
        "geometry":deep_copy(get_path(doc,"完整二维几何",default={})),
        "status":{
            "delivery":deep_copy(delivery),
            "unknowns_are_preserved":True,
            "null_is_not_zero":True,
            "unit_conversion_guessed":False,
            "production_release":False,
        },
        "source_document":deep_copy(doc),
    }

def validate_invariants(v2: dict[str, Any], expected_sha256: str | None = None) -> list[str]:
    errors=[]
    if v2["schema"]["version"] != PATTERN_SCHEMA: errors.append("wrong schema version")
    if v2["provenance"]["source_yaml_version"] != SOURCE_VERSION: errors.append("wrong YAML source version")
    if v2["units"]["coordinate_unit"] != "U": errors.append("coordinate unit must remain U")
    if v2["units"]["mm_per_unit"] is not None: errors.append("Golden Garment U->mm must remain null until calibrated")
    if len(v2["pieces"]) != 4: errors.append(f"expected 4 pieces, got {len(v2['pieces'])}")
    if len(v2["measurements"]) != 23: errors.append(f"expected 23 measurements, got {len(v2['measurements'])}")
    if len(v2["interfaces"]) != 25: errors.append(f"expected 25 interfaces, got {len(v2['interfaces'])}")
    if not v2["geometry"]: errors.append("geometry must not be empty")
    if v2["status"]["production_release"]: errors.append("Golden Garment must not be production-released")
    if expected_sha256 and v2["provenance"]["source_sha256"] != expected_sha256: errors.append("source SHA-256 mismatch")
    return errors

def main() -> int:
    parser=argparse.ArgumentParser()
    parser.add_argument("input",type=Path)
    parser.add_argument("output",type=Path)
    parser.add_argument("--check",action="store_true")
    parser.add_argument("--expected-sha256")
    args=parser.parse_args()
    raw=args.input.read_bytes()
    doc=yaml.load(raw.decode("utf-8"),Loader=Yaml11Loader)
    if not isinstance(doc,dict): raise SystemExit("Golden Garment YAML root must be a mapping")
    result=build_v2(doc,raw,str(args.input))
    errors=validate_invariants(result,args.expected_sha256)
    if errors: raise SystemExit("\n".join(f"ERROR: {e}" for e in errors))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    if args.check:
        print(json.dumps({
            "status":"PASS","schema":result["schema"]["version"],
            "source_sha256":result["provenance"]["source_sha256"],
            "pieces":len(result["pieces"]),"measurements":len(result["measurements"]),
            "interfaces":len(result["interfaces"]),
            "coordinate_unit":result["units"]["coordinate_unit"],
            "mm_per_unit":result["units"]["mm_per_unit"],
            "production_release":result["status"]["production_release"],
        },ensure_ascii=False,sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
