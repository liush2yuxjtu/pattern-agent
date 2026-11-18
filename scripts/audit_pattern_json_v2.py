#!/usr/bin/env python3
"""Reopen the YAML, original DXF and JSON contract without importing its converter."""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "patterns/fitted-tshirt/input-spec.yaml"
DXF = ROOT / "patterns/fitted-tshirt/input.dxf"
SCHEMA = ROOT / "tools/pattern-json-v2/pattern-json-v2.schema.json"
SOURCE_SHA = "88a84e697273724cdb5b4a05116c00cd53b0cb75a4d7e6bdfa5d0b7fd34f181e"
DXF_SHA = "1f82b2c4ca094983657ce49fc73cf06aec24d3329a53dcc3472dd5ca2cee87f4"
spec = importlib.util.spec_from_file_location(
    "source_geometry_audit", ROOT / "experiments/intent-edit-benchmark/audit_benchmark.py"
)
geometry_audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(geometry_audit)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def identity(kind, *names):
    return kind + ":" + hashlib.sha256(canonical(list(names))).hexdigest()


def pointer(document, path):
    value = document
    for part in path.split("/")[1:]:
        key = part.replace("~1", "/").replace("~0", "~")
        value = value[int(key)] if isinstance(value, list) else value[key]
    return value


def audit_contract(raw, document, manifest, schema):
    failures = []

    def check(condition, message):
        if not condition:
            failures.append(message)

    def equal(actual, expected, message):
        check(canonical(actual) == canonical(expected), message)

    try:
        failures.extend("schema: /" + "/".join(map(str, e.absolute_path)) + " violates " + e.validator
                        for e in Draft202012Validator(schema).iter_errors(manifest))
        equal(manifest["source_document"], document, "source document changed")
        check(manifest["provenance"]["source_sha256"] == hashlib.sha256(raw).hexdigest(),
              "source byte digest mismatch")
        semantic_sha = hashlib.sha256(canonical(document)).hexdigest()
        check(manifest["provenance"]["semantic_sha256"] == semantic_sha,
              "semantic digest mismatch")
        check(manifest["revision"]["revision_id"] == "sha256:" + semantic_sha,
              "revision does not identify source content")
        check(manifest["schema"]["version"] == "2.1.0", "unexpected contract version")
        if manifest["provenance"]["reference_assets"]:
            equal(manifest["provenance"]["reference_assets"], [{
                "source_path": "patterns/fitted-tshirt/input.dxf", "sha256": DXF_SHA,
                "role": "reference-only",
            }], "reference DXF binding changed")
        check(manifest["units"]["coordinate_unit"] == "U" and
              manifest["units"]["mm_per_unit"] is None, "uncalibrated units changed")
        check(manifest["garment"]["production_ready"] is False and
              manifest["status"]["production_release"] is False, "false production release")
        equal(manifest["garment"], {
            "garment_id": "golden-garment:fitted-tshirt-m", "name": document["文件约定"]["名称"],
            "category": document["款式特征"]["品类"], "size": document["款式特征"]["标注尺码"],
            "state": "baseline", "production_ready": False,
        }, "garment source fields changed")
        check(manifest["revision"]["spec_patch"] is None and
              manifest["revision"]["geometry_patch"] is None and manifest["review_events"] == [],
              "baseline claims unperformed edits or reviews")

        for target, source in {
            "geometry": "完整二维几何", "cutting": "裁剪清单",
            "component_roles": "成衣部件角色", "materials": "材料选择",
            "reference_size_table": "参考尺码表", "workflow": "制版流程",
            "validation": "版型校验与测试",
        }.items():
            equal(manifest[target], document[source], target + " projection changed")
        for target, source in {
            "style_sheet": "结构化款式单", "block_layers": "原型与部件分层",
            "derivations": "尺寸推导", "decisions": "结构决策与操作方案",
            "execution": "确定性执行与输出",
        }.items():
            equal(manifest["construction"][target], document[source], "construction field changed")
        equal(manifest["status"]["delivery"], document["交付状态"], "delivery source state changed")
        for target, source in [("reference_size_unit", "参考尺码单位"), ("angle_unit", "角度单位")]:
            check(manifest["units"][target] == document["单位与坐标"][source], "source unit changed")

        geometry = document["完整二维几何"]
        pieces = {p["name"]: p for p in manifest["pieces"]}
        check(set(pieces) == set(geometry) and len(manifest["pieces"]) == 4,
              "piece inventory changed")
        for name, piece in pieces.items():
            check(piece["piece_id"] == {"前片": "front-bodice", "后片": "back-bodice",
                                        "袖片": "sleeve", "领条": "neckband"}[name], "piece identity changed")
            equal(pointer(document, piece["source_path"]), geometry[name], "piece source path")
            equal(piece["geometry"], geometry[name], "piece geometry changed")
            equal(piece["cutting"], document["裁剪清单"][name], "piece cutting projection changed")
            expected_roles = {k: v for k, v in document["成衣部件角色"].items()
                              if isinstance(v, dict) and v.get("采用裁片") == name}
            roles = {r["name"]: r["source_record"] for r in piece["roles"]}
            equal(roles, expected_roles, "piece roles lost: " + name)
            check(len(roles) == len(piece["roles"]), "duplicate role")
            for role in piece["roles"]:
                equal(pointer(document, role["source_path"]), role["source_record"],
                      "role source path mismatch")

        for collection, id_key in [("pieces", "piece_id"), ("edges", "edge_id"),
                                   ("interfaces", "interface_id"),
                                   ("measurements", "measurement_id"),
                                   ("seam_relations", "relation_id"), ("seam_pairs", "seam_id")]:
            values = [x[id_key] for x in manifest[collection]]
            check(len(values) == len(set(values)), "duplicate " + id_key)

        edge_map = {}
        for edge in manifest["edges"]:
            line = pointer(document, edge["source_path"])
            check(edge["name"] == line["名称"], "edge source name mismatch")
            piece_name = next(n for n, p in pieces.items() if p["piece_id"] == edge["piece_id"])
            check(edge["source_path"].startswith(pieces[piece_name]["source_path"] + "/线条/"),
                  "edge attached to wrong piece")
            check(edge["edge_id"] == identity("edge", piece_name, edge["name"]), "edge identity changed")
            edge_map[piece_name, edge["name"]] = edge["edge_id"]
        check(len(edge_map) == 204 and len(manifest["edges"]) == 204, "edge inventory changed")
        check(set(edge_map) == {(p, l["名称"]) for p, g in geometry.items() for l in g["线条"]},
              "missing source line")

        interfaces = {(i["piece"], i["name"]): i for i in manifest["interfaces"]}
        check(len(interfaces) == len(manifest["interfaces"]) == 25, "interface inventory changed")
        for (piece_name, name), interface in interfaces.items():
            source = document["裁片接口"][piece_name][name]
            equal(pointer(document, interface["source_path"]), source, "interface source path")
            equal({k: interface[k] for k in source}, source, "interface source fields changed")
            expected = [{"edge_id": edge_map[piece_name, x["线条"]], "direction": x["方向"]}
                        for x in source["组成"]]
            equal(interface["edge_chain"], expected, "edge chain changed")
            check(interface["interface_id"] == identity("interface", piece_name, name),
                  "interface identity changed")
            check(interface["piece_id"] == pieces[piece_name]["piece_id"], "interface piece mismatch")

        for records, source_records, field in [
            (manifest["measurements"], document["关键尺寸"]["项目"], None),
            (manifest["seam_relations"], document["连接关系"], "value"),
        ]:
            check({r["name"] for r in records} == set(source_records), "source record inventory")
            for record in records:
                source = source_records[record["name"]]
                equal(pointer(document, record["source_path"]), source, "record source path")
                equal(record[field] if field else {k: record[k] for k in source},
                      source, "measurement or summary changed")
                id_field, kind = ("relation_id", "summary") if field else ("measurement_id", "measurement")
                check(record[id_field] == identity(kind, record["name"]), "record identity changed")

        source_seams = document["缝级关系图"]["缝级记录"]
        check(len(manifest["seam_pairs"]) == len(source_seams) == 11, "seam inventory changed")
        check({s["name"] for s in manifest["seam_pairs"]} == {s["关系名称"] for s in source_seams},
              "seam source inventory changed")
        check(len({s["source_path"] for s in manifest["seam_pairs"]}) == 11,
              "duplicate seam source path")
        unresolved = 0
        for seam in manifest["seam_pairs"]:
            source = pointer(document, seam["source_path"])
            check(source in source_seams, "seam not bound to source seam records")
            equal(seam["source_record"], source, "seam source record changed")
            equal(pointer(document, seam["source_path"]), source, "seam source path")
            check(seam["name"] == source["关系名称"], "seam name changed")
            check(seam["seam_id"] == identity("seam", seam["name"]), "seam identity changed")
            for target, key in [("side_a", "边一"), ("side_b", "边二")]:
                side, refs = seam[target], source[key]
                pending = isinstance(refs, dict)
                refs = refs["候选接口"] if pending else refs
                ids = [interfaces[x["裁片"], x["接口"]]["interface_id"] for x in refs]
                equal(side, {"status": "UNRESOLVED" if pending else "RESOLVED",
                             "interface_ids": None if pending else ids,
                             "candidate_interface_ids": ids if pending else []}, "seam side changed")
                unresolved += int(pending)
        check(unresolved == 4, "sleeve assignment invented")

        manufacturing = manifest["manufacturing"]["pieces"]
        check({p["piece_id"] for p in manufacturing} == {p["piece_id"] for p in pieces.values()},
              "manufacturing piece inventory")
        allowance_ids = []
        for piece in manufacturing:
            for key in ("cut_quantity", "grainline", "seam_line", "cut_line", "notches", "grading"):
                field = piece[key]
                check(field["value"] is None and field["status"] in ("UNKNOWN", "MISSING"),
                      "unapproved manufacturing value: " + key)
                equal(pointer(document, field["source_path"]) if field["source_path"] else None,
                      field["source_record"], "manufacturing provenance")
            for allowance in piece["edge_allowances"]:
                allowance_ids.append(allowance["edge_id"])
                check(allowance["edge_id"] in {e["edge_id"] for e in manifest["edges"]
                                               if e["piece_id"] == piece["piece_id"]},
                      "allowance attached to wrong piece")
                check(allowance["value"] is None and allowance["status"] == "UNKNOWN",
                      "unapproved seam allowance")
        equal(sorted(allowance_ids), sorted(edge_map.values()), "per-edge allowance coverage")

        artifacts = manifest["derived_artifacts"]
        check(set(artifacts) == {"geometry", "mesh", "physics", "debugger", "timeline", "validation"},
              "missing result invalidation category")
        for artifact in artifacts.values():
            check((artifact["result"] is None) == (artifact["source_revision_id"] is None),
                  "result and source revision must be present together")
            state = ("NOT_RUN" if artifact["result"] is None else "CURRENT"
                     if artifact["source_revision_id"] == manifest["revision"]["revision_id"] else "STALE")
            check(artifact["status"] == state, "stale result labelled current")
    except (KeyError, TypeError, ValueError, StopIteration) as exc:
        failures.append("cannot reopen contract: " + str(exc))
    return failures


def fault_controls(raw, document, manifest, schema):
    mutations = {
        "guessed_millimeters": lambda m: m["units"].update(mm_per_unit=1),
        "missing_seam": lambda m: m["seam_pairs"].pop(),
        "duplicate_edge_id": lambda m: m["edges"][1].update(edge_id=m["edges"][0]["edge_id"]),
        "dangling_edge": lambda m: m["interfaces"][0]["edge_chain"][0].update(edge_id="missing"),
        "changed_coordinate": lambda m: m["geometry"]["前片"]["线条"][0]["点位"][0].update(横=999),
        "lost_left_sleeve_role": lambda m: next(p for p in m["pieces"] if p["name"] == "袖片")["roles"].pop(),
        "source_digest": lambda m: m["provenance"].update(source_sha256="0" * 64),
        "wrong_piece_cutting": lambda m: m["pieces"][0]["cutting"]["批准裁数"].update(状态="已批准", 数值=999),
        "wrong_stable_id": lambda m: m["measurements"][0].update(measurement_id="arbitrary-unique-id"),
        "wrong_garment_name": lambda m: m["garment"].update(name="wrong garment"),
        "unbound_result": lambda m: m["derived_artifacts"]["physics"].update(
            status="STALE", source_revision_id=None, result={"fixture": True}),
        "false_current_result": lambda m: m["derived_artifacts"]["physics"].update(
            status="CURRENT", source_revision_id="sha256:" + "0" * 64, result={"fixture": True}),
    }
    results = {}
    for name, mutate in mutations.items():
        changed = deepcopy(manifest)
        mutate(changed)
        findings = audit_contract(raw, document, changed, schema)
        results[name] = {"rejected": bool(findings), "findings": findings}
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    raw, dxf = SOURCE.read_bytes(), DXF.read_bytes()
    document = geometry_audit.read_model(SOURCE)
    manifest, schema = json.loads(args.manifest.read_text()), json.loads(SCHEMA.read_text())
    findings = audit_contract(raw, document, manifest, schema)
    if hashlib.sha256(raw).hexdigest() != SOURCE_SHA or hashlib.sha256(dxf).hexdigest() != DXF_SHA:
        findings.append("frozen Golden Garment source digest mismatch")
    cad_rows, cad_counts = geometry_audit.read_cad(dxf)
    source_geometry = geometry_audit.measure_model(document)
    if geometry_audit.canonical(cad_rows) != geometry_audit.canonical(geometry_audit.model_rows(document)):
        findings.append("YAML does not preserve the original DXF at six decimal places")
    controls = fault_controls(raw, document, manifest, schema) if not findings else {}
    if controls and not all(c["rejected"] for c in controls.values()):
        findings.append("independent fault control accepted corrupt data")
    report = {
        "verdict": "FAIL" if findings else "PASS",
        "scope": "Golden YAML/DXF preservation and JSON contract, not fit or production release",
        "source_sha256": hashlib.sha256(raw).hexdigest(), "dxf_sha256": hashlib.sha256(dxf).hexdigest(),
        "manifest_sha256": hashlib.sha256(args.manifest.read_bytes()).hexdigest(),
        "source_geometry": cad_counts, "measurements_recomputed": len(source_geometry["dimensions"]),
        "interfaces_recomputed": len(source_geometry["ports"]), "seam_records": len(manifest.get("seam_pairs", [])),
        "max_interface_rounding_error_U": source_geometry["max_interface_rounding_error_U"],
        "preserved_front_hem_gap_U": document["裁片接口"]["前片"]["下摆"]["段间间隙"],
        "fault_controls": controls, "findings": findings,
        "physical_fit": "NOT_RUN", "production_release": False,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False, separators=(",", ":")))
    return int(bool(findings))


if __name__ == "__main__":
    raise SystemExit(main())
