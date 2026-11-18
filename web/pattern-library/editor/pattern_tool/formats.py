"""Schema validation and lossless serialization for the fitted T-shirt profile."""
from copy import deepcopy
from functools import cache
from hashlib import sha256
import json
from pathlib import Path

from jsonschema import Draft202012Validator
import yaml

from .legacy import model_reader

ROOT = Path(__file__).resolve().parents[1]
PROFILE = "pattern-agent/fitted-tshirt-1"
PIECES = {"front": "前片", "back": "后片", "sleeve": "袖片", "neckband": "领条"}
SPEC_FIELDS = {
    "measurements": "关键尺寸",
    "interfaces": "裁片接口",
    "seam_groups": "连接关系",
    "seam_graph": "缝级关系图",
    "cutting": "裁剪清单",
    "fabric": "材料选择",
    "workmanship": "工艺参数",
}
GEOMETRY = "完整二维几何"
COORDINATES = "单位与坐标"


class FormatError(ValueError):
    """A source document cannot be used as submitted."""


def digest(data):
    return sha256(data).hexdigest()


@cache
def validator(kind):
    schema = json.loads((ROOT / "schemas" / f"{kind}.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def check_schema(kind, value):
    err = next(validator(kind).iter_errors(value), None)
    if err:
        location = ".".join(map(str, err.absolute_path)) or kind
        raise FormatError(f"{location}: {err.message[:260]}")
    return value


def load_yaml(data):
    if len(data) > 3_000_000:
        raise FormatError("YAML exceeds the 3 MB input limit")
    text = data.decode("utf-8-sig")
    # For these interchange documents each value has one explicit owner.
    if any(event.anchor for event in yaml.parse(text) if hasattr(event, "anchor")):
        raise FormatError("YAML anchors and aliases are not supported")
    value = yaml.load(text, Loader=model_reader.UniqueLoader)
    if not isinstance(value, dict):
        raise FormatError("A YAML document must contain a mapping")
    return value


class PlainDumper(yaml.SafeDumper):
    def ignore_aliases(self, data):
        return True


def dump_yaml(value):
    return yaml.dump(value, Dumper=PlainDumper, allow_unicode=True, sort_keys=False, width=100).encode()


def point(value):
    return [value["横"], value["高"]]


def legacy_point(value):
    x, y = value
    return {"横": x, "高": y}


def edge_id(name):
    return "e-" + digest(name.encode())[:16]


def split(model, drawing_hash):
    coordinates = deepcopy(model[COORDINATES])
    calibration = coordinates["实际比例"]
    common = {
        "profile": PROFILE,
        "pattern_id": "fitted-tshirt",
        "size": model["款式特征"]["标注尺码"],
    }
    pattern = {
        "schema": "pattern-2d/v1",
        **common,
        "source": {"format": "DXF", "sha256": drawing_hash},
        "coordinates": {
            "units": "U",
            "x_positive": "right",
            "y_positive": "up",
            "mm_per_unit": calibration.get("每U毫米数") if calibration["状态"] == "已标定" else None,
            "source_metadata": coordinates,
        },
        "pieces": {},
    }
    for pid, name in PIECES.items():
        part = model[GEOMETRY][name]
        edges = {
            edge_id(edge["名称"]): {
                "source_name": edge["名称"],
                "kind": "line" if edge["线型"] == "直线" else "polyline",
                "closed": edge["闭合方式"] == "闭合",
                "points": [point(p) for p in edge["点位"]],
            }
            for edge in part["线条"]
        }
        contours = {
            key: {
                "source_name": label,
                "role": "unconfirmed",
                "semantic_status": contour["用途状态"],
                "note": contour["轮廓含义"],
                "edges": [
                    {"edge": edge_id(ref["线条"]), "reverse": ref["方向"] == "反向"}
                    for ref in contour["组成"]
                ],
            }
            for key, (label, contour) in zip(("inner", "outer"), part["轮廓"].items(), strict=True)
        }
        pattern["pieces"][pid] = {
            "source_name": name,
            "layout_origin": point(part["排版放置点"]),
            "origin_note": part["局部坐标原点说明"],
            "contours": contours,
            "edges": edges,
            "edge_order": list(edges),
            "landmarks": {k: point(v) for k, v in part["定位点"].items()},
            "annotations": [
                {"text": row["文字内容"], "position": point(row["位置"])} for row in part["文字"]
            ],
        }
    spec = {
        "schema": "pattern-spec/v1",
        **common,
        **{key: deepcopy(model[src]) for key, src in SPEC_FIELDS.items()},
        "source_specification": {
            k: deepcopy(v) for k, v in model.items() if k not in {GEOMETRY, COORDINATES, *SPEC_FIELDS.values()}
        },
    }
    return pattern, spec


def join(pattern, spec):
    check_schema("pattern-2d", pattern)
    check_schema("pattern-spec", spec)
    for field in ("profile", "pattern_id", "size"):
        if pattern[field] != spec[field]:
            raise FormatError(f"2D and 1D {field} disagree")
    if pattern["profile"] != PROFILE or set(pattern["pieces"]) != set(PIECES):
        raise FormatError("The editor requires the fitted T-shirt profile and its four named pieces")
    if {GEOMETRY, COORDINATES, *SPEC_FIELDS.values()} & spec["source_specification"].keys():
        raise FormatError("source_specification contains a field owned elsewhere")
    model = deepcopy(spec["source_specification"])
    if model["款式特征"]["标注尺码"] != spec["size"]:
        raise FormatError("Size conflicts with the source spec")
    coords = pattern["coordinates"]
    if (
        coords["units"] != "U"
        or coords["x_positive"] != "right"
        or coords["y_positive"] != "up"
    ):
        raise FormatError("Fitted T-shirt coordinates must use U, +x right and +y up")
    model[COORDINATES] = deepcopy(coords["source_metadata"])
    legacy_calibration = model[COORDINATES]["实际比例"]
    if coords["mm_per_unit"] != (legacy_calibration.get("每U毫米数") if legacy_calibration["状态"] == "已标定" else None):
        raise FormatError("Calibration conflicts with its source metadata")
    model.update({src: deepcopy(spec[key]) for key, src in SPEC_FIELDS.items()})
    geometry = {}
    for pid, name in PIECES.items():
        part = pattern["pieces"][pid]
        edges = part["edges"]
        if part["source_name"] != name or set(part["edge_order"]) != set(edges):
            raise FormatError(f"Piece {pid} has invalid identity or edge order")
        if any(key != edge_id(edge["source_name"]) for key, edge in edges.items()):
            raise FormatError(f"Piece {pid} has invalid source edge IDs")
        contours = {}
        for contour in part["contours"].values():
            label = contour["source_name"]
            if label in contours or any(ref["edge"] not in edges for ref in contour["edges"]):
                raise FormatError(f"Piece {pid} has an invalid contour or edge reference")
            contours[label] = {
                "用途状态": contour["semantic_status"],
                "轮廓含义": contour["note"],
                "组成": [
                    {"线条": edges[ref["edge"]]["source_name"], "方向": "反向" if ref["reverse"] else "正向"}
                    for ref in contour["edges"]
                ],
            }
        lines = []
        for key in part["edge_order"]:
            edge = edges[key]
            if edge["kind"] not in ("line", "polyline") or (edge["kind"] == "line" and len(edge["points"]) != 2):
                raise FormatError(f"Piece {pid} contains geometry outside its DXF profile")
            lines.append({
                "名称": edge["source_name"],
                "线型": "直线" if edge["kind"] == "line" else "折线",
                "闭合方式": "闭合" if edge["closed"] else "开放",
                "点位": [legacy_point(p) for p in edge["points"]],
            })
        geometry[name] = {
            "排版放置点": legacy_point(part["layout_origin"]),
            "局部坐标原点说明": part["origin_note"],
            "定位点": {k: legacy_point(v) for k, v in part["landmarks"].items()},
            "轮廓": contours,
            "线条": lines,
            "文字": [{"文字内容": x["text"], "位置": legacy_point(x["position"])} for x in part["annotations"]],
        }
    model[GEOMETRY] = geometry
    model_reader.validate(model)
    return model
