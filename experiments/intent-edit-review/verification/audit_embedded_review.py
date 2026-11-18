"""Independently check a single-file review's source bytes, SVG and mesh lineage.

No UI builder, renderer, benchmark generator or mesh generator is imported.
"""
from __future__ import annotations

import argparse
import base64
import bisect
from collections import Counter, defaultdict
from copy import deepcopy
from decimal import Decimal
import hashlib
from html.parser import HTMLParser
import json
import math
from pathlib import Path
import re
import subprocess
from xml.etree import ElementTree as ET

import yaml

REPO = Path(__file__).resolve().parents[3]
CASES = ("01_sleeve_length", "02_body_length", "03_cuff_width", "04_front_neck")
PIECES = ("前片", "后片", "袖片", "领条")
UNCHANGED = {"01_sleeve_length": {"前片", "后片", "领条"}, "02_body_length": {"袖片", "领条"}, "03_cuff_width": {"前片", "后片", "领条"}, "04_front_neck": {"后片", "袖片"}}
NUM = r"[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?"


class AuditFailure(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise AuditFailure(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def finite(value):
    require(not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value), "Nonfinite or nonnumeric coordinate")
    return float(value)


class PayloadParser(HTMLParser):
    def __init__(self, identity):
        super().__init__(convert_charrefs=False)
        self.identity, self.active, self.payloads = identity, False, []
        self.chunks = []

    def handle_starttag(self, tag, attrs):
        if tag == "script" and dict(attrs).get("id") == self.identity:
            require(not self.active, "Nested data script")
            self.active = True; self.chunks = []

    def handle_data(self, data):
        if self.active:
            self.chunks.append(data)

    def handle_endtag(self, tag):
        if tag == "script" and self.active:
            self.payloads.append("".join(self.chunks)); self.active = False


def extract_payload(raw, identity="app-data"):
    parser = PayloadParser(identity)
    parser.feed(raw.decode("utf-8"))
    require(len(parser.payloads) == 1 and not parser.active, "Expected exactly one complete application JSON script")
    return json.loads(parser.payloads[0])


def paths_for(case):
    if case == "baseline":
        return {"yaml": "patterns/fitted-tshirt/input-spec.yaml", "dxf": "patterns/fitted-tshirt/input.dxf"}
    require(case in CASES, "Unexpected review case")
    prefix = "experiments/intent-edit-benchmark/results/" + case + "/"
    return {"yaml": prefix + "new-spec.yaml", "dxf": prefix + "output.dxf", "spec_diff": prefix + "spec-diff.json", "geometry_patch": prefix + "geometry-patch.json"}


def source_files(case, committed=True):
    data = {}
    for kind, path in paths_for(case).items():
        raw = (REPO / path).read_bytes()
        if committed:
            stored = subprocess.check_output(["git", "show", "HEAD:" + path], cwd=REPO)
            require(stored == raw, "Review input differs from committed repository: " + path)
        data[kind] = raw
    return data


def decode_record(record, key="base64"):
    raw = base64.b64decode(record[key], validate=True)
    require(len(raw) == record["byte_length"], "Embedded byte length is incomplete")
    require(sha(raw) == record["sha256"], "Embedded file digest mismatch")
    return raw


def read_dxf(raw):
    lines = raw.decode("gb18030").splitlines()
    require(len(lines) % 2 == 0, "Unpaired CAD tag")
    pairs = [(int(lines[i]), lines[i + 1]) for i in range(0, len(lines), 2)]
    records = []
    for code, value in pairs:
        if code == 0:
            records.append([value.strip(), {}])
        elif records:
            records[-1][1][code] = value
    rows, poly_index = [], 0
    for i, (kind, values) in enumerate(records):
        if kind == "POLYLINE":
            points = []; j = i + 1
            while j < len(records) and records[j][0] == "VERTEX":
                t = records[j][1]; points.append([finite(float(t[10])), finite(float(t[20]))]); j += 1
            require(j < len(records) and records[j][0] == "SEQEND", "Unterminated CAD polyline")
            rows.append({"kind": kind, "points": points, "closed": bool(int(values.get(70, 0)) & 1), "polyline_index": poly_index}); poly_index += 1
        elif kind == "LINE":
            rows.append({"kind": kind, "points": [[finite(float(values[10])), finite(float(values[20]))], [finite(float(values[11])), finite(float(values[21]))]], "closed": False})
        elif kind == "TEXT":
            rows.append({"kind": kind, "points": [[finite(float(values[10])), finite(float(values[20]))]], "text": values.get(1, "")})
    require(Counter(r["kind"] for r in rows) == Counter(POLYLINE=126, LINE=78, TEXT=27), "CAD entity inventory changed")
    require(sum(len(r["points"]) for r in rows if r["kind"] == "POLYLINE") == 1487, "CAD vertex inventory changed")
    declared_units = next((pairs[i + 1][1] for i, p in enumerate(pairs[:-1]) if p == (9, "$INSUNITS")), None)
    return rows, declared_units


def curve_key(row, with_kind=True):
    points = tuple(tuple(round(finite(v), 6) for v in p) for p in row["points"])
    if row["kind"] == "TEXT":
        return ("TEXT", row.get("text", ""), points)
    return (row["kind"] if with_kind else "CURVE", points, bool(row.get("closed", False)))


def yaml_rows(model):
    rows = []
    for piece, part in model["完整二维几何"].items():
        origin = part["排版放置点"]
        def global_point(p):
            return [float(Decimal(str(p[k])) + Decimal(str(origin[k]))) for k in ("横", "高")]
        for line in part["线条"]:
            rows.append({"kind": "LINE" if line["线型"] == "直线" else "POLYLINE", "points": [global_point(p) for p in line["点位"]], "closed": line["闭合方式"] == "闭合", "piece": piece, "name": line["名称"]})
        for text in part["文字"]:
            rows.append({"kind": "TEXT", "points": [global_point(text["位置"])], "text": text["文字内容"], "piece": piece})
    return rows


def multiply(a, b):
    aa, ab, ac, ad, ae, af = a; ba, bb, bc, bd, be, bf = b
    return (aa*ba+ac*bb, ab*ba+ad*bb, aa*bc+ac*bd, ab*bc+ad*bd, aa*be+ac*bf+ae, ab*be+ad*bf+af)


def svg_transform(text):
    matrix = (1., 0., 0., 1., 0., 0.)
    for name, args in re.findall(r"([A-Za-z]+)\s*\(([^)]*)\)", text or ""):
        values = [float(v) for v in re.findall(NUM, args)]
        if name == "matrix":
            require(len(values) == 6, "SVG matrix arity"); local = tuple(values)
        elif name == "scale":
            require(len(values) in (1, 2), "SVG scale arity"); local = (values[0], 0, 0, values[-1], 0, 0)
        elif name == "translate":
            require(len(values) in (1, 2), "SVG translate arity"); local = (1, 0, 0, 1, values[0], values[1] if len(values) == 2 else 0)
        elif name == "rotate":
            require(len(values) in (1, 3), "SVG rotate arity")
            angle = math.radians(values[0]); c, s = math.cos(angle), math.sin(angle)
            local = (c, s, -s, c, 0, 0)
            if len(values) == 3:
                local = multiply(multiply((1, 0, 0, 1, values[1], values[2]), local), (1, 0, 0, 1, -values[1], -values[2]))
        else:
            raise AuditFailure("Unsupported SVG transform: " + name)
        matrix = multiply(matrix, local)
    return matrix


def svg_curve_points(svg):
    result = []
    root = ET.fromstring(svg)
    def visit(node, parent):
        matrix = multiply(parent, svg_transform(node.get("transform")))
        kind = node.tag.rsplit("}", 1)[-1]
        points = None
        if kind == "polyline":
            numbers = [float(v) for v in re.findall(NUM, node.get("points", ""))]
            require(len(numbers) >= 4 and len(numbers) % 2 == 0, "Invalid SVG polyline")
            points = list(zip(numbers[::2], numbers[1::2]))
        elif kind == "line":
            points = [(float(node.get("x1", 0)), float(node.get("y1", 0))), (float(node.get("x2", 0)), float(node.get("y2", 0)))]
        if points is not None:
            a, b, c, d, e, f = matrix
            result.append(tuple((round(a*x+c*y+e, 6), round(b*x+d*y+f, 6)) for x, y in points))
        for child in node:
            visit(child, matrix)
    visit(root, (1, 0, 0, 1, 0, 0))
    return Counter(result)


def audit_two_d(record, source, model):
    raw, units = read_dxf(source["dxf"])
    require(record["source_dxf_sha256"] == sha(source["dxf"]), "2D DXF lineage mismatch")
    require(record["source_yaml_sha256"] == sha(source["yaml"]), "2D YAML lineage mismatch")
    expected = Counter(curve_key(r) for r in raw)
    require(expected == Counter(curve_key(r) for r in yaml_rows(model)), "YAML and actual CAD geometry differ")
    primitives = record["primitives"]
    require(Counter(curve_key(r) for r in primitives) == expected, "Embedded 2D primitives are stale or incomplete")
    expected_svg = Counter(tuple((round(p[0], 6), round(-p[1], 6)) for p in r["points"]) for r in raw if r["kind"] != "TEXT")
    require(svg_curve_points(record["svg"]) == expected_svg, "Actual SVG geometry does not match the embedded/source DXF")
    return {"entities": len(raw), "curves": sum(r["kind"] != "TEXT" for r in raw), "text_annotations": sum(r["kind"] == "TEXT" for r in raw), "raw_declared_INSUNITS": units, "unit": "YAML U, physical scale uncalibrated"}


def decode_mesh(record):
    raw = base64.b64decode(record["artifact_base64"], validate=True)
    require(len(raw) == record["byte_length"] and sha(raw) == record["artifact_sha256"], "3D artifact byte digest mismatch")
    model = json.loads(raw)
    if "model" in record:
        require(record["model"] == model, "Viewer model differs from artifact JSON")
    return model, raw


def audit_mesh_geometry(model, source, case):
    require(model["format"] == "source-bound-static-assembly/1" and model["id"] == case, "Wrong static-model profile or case")
    require(model["source_dxf_sha256"] == sha(source["dxf"]) and model["source_spec_sha256"] == sha(source["yaml"]), "3D source lineage mismatch")
    require(model["units"] == "U" and model["mode"] == "static_geometric_assembly", "3D units/mode misrepresented")
    for key in ("physical_fit", "cloth_simulation", "sewing_validation"):
        require(model[key] == "NOT_RUN", "Static model promoted to an untested physical result")
    sources, baseline = independent_piece_sources(source["dxf"])
    pose = model["pose"]
    validate_pose(pose, baseline)
    require({p["id"] for p in model["panels"]} == {"front", "back", "sleeve_a", "sleeve_b", "band"}, "3D instance inventory incomplete")
    reports, signatures = [], {}
    for panel in model["panels"]:
        piece = panel["source_piece"]
        require(piece in PIECES, "Unknown source piece")
        data = sources[piece]
        positions = vectors(panel["positions"], 3)
        uv = vectors(panel["uv"], 2)
        normal = vectors(panel["normals"], 3)
        require(len(positions) == len(uv) == len(normal), "Mesh arrays are inconsistent")
        triangles = panel["triangles"]
        binding = panel["binding"]
        require(binding["uv_coordinate_system"] == "piece-local DXF U coordinates", "Unknown UV coordinate system")
        require(max_error(binding["dxf_layout_origin_U"], data["origin"]) < 1e-7, "Wrong UV layout origin")
        expected_hash = sha(json.dumps(data["curves"], sort_keys=True, separators=(',', ':')).encode())
        require(binding["source_piece_polyline_sha256"] == expected_hash, "3D piece-curve digest differs from actual DXF")
        boundary, refs, joins = source_boundary(data)
        B = len(boundary)
        require(binding["boundary_vertex_count"] == B == len(binding["boundary_sources"]), "Boundary source inventory differs")
        boundary_error = max(max_error(a, b) for a, b in zip(uv[:B], boundary))
        require(boundary_error <= 1.1e-6, "3D boundary UV does not match the actual case DXF")
        for a, b in zip(binding["boundary_sources"], refs):
            require(all(a[k] == b[k] for k in ("curve", "polyline_index", "vertex_index")), "Boundary point provenance differs from actual DXF")
            require(abs(a["walk_parameter"] - b["walk_parameter"]) <= 1e-7, "Wrong source arc-length parameter")
        require(len(binding["joins"]) == len(joins), "Display joins not fully recorded")
        for actual, expected in zip(binding["joins"], joins):
            require(actual["incoming_curve"] == expected[0] and abs(actual["gap_U"] - expected[1]) < 1e-6, "Display join metadata is not from the source DXF")
        require(max(g for _, g in joins) < .05 and binding["display_junction_tolerance_U"] == .05, "Display contour bridges an unapproved large gap")
        neighbors, area = mesh_topology(uv, triangles, B)
        source_area = abs(sum(a[0]*b[1]-b[0]*a[1] for a, b in zip(boundary, boundary[1:]+boundary[:1]))) / 2
        require(abs(area - source_area) <= max(1e-4, source_area*1e-9), "Triangulation UV area does not cover the actual source contour")
        require(all(abs(math.sqrt(sum(v*v for v in n)) - 1) <= 2e-6 for n in normal), "Nonunit mesh normal")
        construction = panel["construction"]
        if piece in ("前片", "后片"):
            targets = [body_point(data, piece, point, ref, pose) for point, ref in zip(boundary, refs)]
            error = max(max_error(a, b) for a, b in zip(positions[:B], targets))
            require(error < 3e-5, "Body 3D boundary is not the documented source-based placement")
            require(max(max_error(a, b) for a, b in zip(construction["boundary_targets_U"], targets)) < 3e-5, "Body boundary targets misstate source placement")
            distances = [distance_to_loop(p, boundary) for p in uv]
            require(max(abs(a-b) for a, b in zip(construction["distance_to_boundary_U"], distances)) < 1e-6, "Body boundary distances not from source UV")
            sign = 1 if piece == "前片" else -1
            unbulged = [p[:] for p in positions]
            for i in range(B, len(uv)):
                unbulged[i][2] -= sign*48*(1-math.exp(-distances[i]/35))
            residual = harmonic_residual(unbulged, neighbors, B)
            require(residual < 3e-5, "Body interior fails its source-bound harmonic construction")
        elif piece == "袖片":
            domains, config = sleeve_boundary_domains(data, boundary, refs)
            declared_domains = vectors(construction["domain"], 2)
            require(len(declared_domains) == len(uv), "Sleeve domain length mismatch")
            require(max(max_error(a, b) for a, b in zip(declared_domains[:B], domains)) < 2e-6, "Sleeve boundary domains differ from source dimensions")
            residual = harmonic_residual(declared_domains, neighbors, B)
            require(residual < 2e-6, "Sleeve harmonic domain was not solved on this mesh")
            sign = -1 if panel["id"] == "sleeve_a" else 1
            require(construction["instance_sign"] == sign, "Sleeve display mirror changed")
            targets = [sleeve_point(data, q, config, pose, sign) for q in declared_domains]
            error = max(max_error(a, b) for a, b in zip(positions, targets))
            require(error < 3e-5, "Sleeve 3D positions do not respond to this DXF's length/width")
            for key in ("axis_length_U", "underarm_source_y_U", "side_length_mean_U", "cuff_source_y_U", "cuff_width_U"):
                require(abs(construction["source_config"][key]-config[key]) < 2e-6, "Sleeve source parameters stale")
        else:
            targets, ring = band_positions(data, uv, sources, pose)
            error = max(max_error(a, b) for a, b in zip(positions, targets))
            require(error < 3e-5, "Band 3D is not based on the current front/back neckline")
            require(max(max_error(a, b) for a, b in zip(construction["source_config"]["neck_ring_U"], ring)) < 3e-5, "Displayed neck ring reused from another design")
            residual = 0.
        require(all(triangle_area_3d(positions[a], positions[b], positions[c]) > 1e-8 for a, b, c in triangles), "Degenerate 3D triangle")
        signature = sha(json.dumps({k: panel[k] for k in ("positions", "triangles", "uv")}, separators=(',', ':')).encode())
        signatures[panel["id"]] = {"source_piece": piece, "signature": signature}
        reports.append({"id": panel["id"], "source_piece": piece, "vertices": len(uv), "triangles": len(triangles), "boundary_source_error_U": boundary_error, "maximum_3D_formula_error_U": error, "harmonic_residual_U": residual, "source_max_display_join_U": max(g for _, g in joins)})
    return {"panels": reports, "units": "U", "mode": "static_geometric_assembly", "physical_fit": "NOT_RUN", "cloth_simulation": "NOT_RUN"}, signatures


def vectors(values, size):
    require(isinstance(values, list) and bool(values), "Missing mesh array")
    require(all(isinstance(row, list) and len(row) == size for row in values), "Wrong mesh array dimensions")
    return [[finite(v) for v in row] for row in values]


def max_error(a, b):
    require(len(a) == len(b), "Vector dimensions differ")
    return max(abs(x-y) for x, y in zip(a, b))


def independent_piece_sources(raw):
    base = source_files("baseline", committed=False)
    baseline = yaml.safe_load(base["yaml"])
    before, _ = read_dxf(base["dxf"])
    after, _ = read_dxf(raw)
    lookup = defaultdict(list)
    for row in before:
        if row["kind"] == "POLYLINE":
            lookup[curve_key(row)].append(row["polyline_index"])
    current = {row["polyline_index"]: row["points"] for row in after if row["kind"] == "POLYLINE"}
    result = {name: {"curves": {}, "indices": {}, "origin": [part["排版放置点"][k] for k in ("横", "高")], "contour": part["轮廓"]["内圈"]["组成"]} for name, part in baseline["完整二维几何"].items()}
    for row in yaml_rows(baseline):
        if row["kind"] != "POLYLINE":
            continue
        candidates = lookup[curve_key(row)]
        require(bool(candidates), "Cannot identify a source DXF curve")
        index = candidates.pop(0); target = result[row["piece"]]
        target["indices"][row["name"]] = index
        target["curves"][row["name"]] = [[p[j]-target["origin"][j] for j in (0, 1)] for p in current[index]]
    return result, baseline


def chain_length(points):
    return sum(math.dist(a, b) for a, b in zip(points, points[1:]))


def source_boundary(source):
    points, refs, joins = [], [], []
    for member in source["contour"]:
        name = member["线条"]; raw = source["curves"][name]
        indices = list(range(len(raw)))
        if member["方向"] == "反向": indices.reverse()
        walked = [raw[i] for i in indices]
        total = chain_length(walked); cumulative = [0.]
        for a, b in zip(walked, walked[1:]): cumulative.append(cumulative[-1]+math.dist(a, b))
        start = 0
        if points:
            joins.append((name, math.dist(points[-1], walked[0]))); start = 1
        for j in range(start, len(indices)):
            points.append(walked[j][:]); refs.append({"curve": name, "polyline_index": source["indices"][name], "vertex_index": indices[j], "walk_parameter": cumulative[j]/total})
    joins.append((source["contour"][0]["线条"], math.dist(points[-1], points[0])))
    return points[:-1], refs[:-1], joins


def interpolate(x, samples):
    ordered = sorted(samples, key=lambda p: p[0])
    unique = {}
    for a, b in ordered:
        if a not in unique: unique[a] = b
    xs, ys = list(unique), list(unique.values())
    if x <= xs[0]: return ys[0]
    if x >= xs[-1]: return ys[-1]
    j = bisect.bisect_right(xs, x)
    ratio = (x-xs[j-1])/(xs[j]-xs[j-1])
    return ys[j-1]+ratio*(ys[j]-ys[j-1])


def clamp(value, low, high):
    return max(low, min(high, value))


def validate_pose(pose, baseline):
    require(pose["units"] == "U", "Placement unit changed")
    for piece in ("前片", "后片"):
        marks = baseline["完整二维几何"][piece]["定位点"]
        cfg = pose["body"][piece]
        expected = {"underarm_y_U": sum(marks[piece+"图面"+side+"侧腋下点"]["高"] for side in ("左", "右"))/2, "shoulder_y_U": sum(marks[piece+"图面"+side+"侧肩袖交点"]["高"] for side in ("左", "右"))/2, "neck_half_width_U": sum(abs(marks[piece+"图面"+side+"侧领肩交点"]["横"]) for side in ("左", "右"))/2, "neck_depth_display_U": 65 if piece == "前片" else 48, "arm_depth_display_U": 70, "hem_depth_display_U": 92, "interior_bulge_U": 48}
        for key, value in expected.items():
            require(abs(cfg[key]-value) < 1e-6, "Placement is not the fixed baseline recipe")
    require(abs(pose["body"]["前片"]["y_offset_U"]) < 1e-8, "Front placement changed")
    require(abs(pose["body"]["后片"]["y_offset_U"]-(pose["body"]["前片"]["shoulder_y_U"]-pose["body"]["后片"]["shoulder_y_U"])) < 1e-6, "Back placement changed")
    front = baseline["完整二维几何"]["前片"]["定位点"]; back = baseline["完整二维几何"]["后片"]["定位点"]
    shoulder = [(abs(front["前片图面右侧肩袖交点"]["横"])+abs(back["后片图面右侧肩袖交点"]["横"]))/2, pose["body"]["前片"]["shoulder_y_U"]]
    under = [(abs(front["前片图面右侧腋下点"]["横"])+abs(back["后片图面右侧腋下点"]["横"]))/2*.72, (pose["body"]["前片"]["underarm_y_U"]+pose["body"]["后片"]["underarm_y_U"]+pose["body"]["后片"]["y_offset_U"])/2]
    require(max_error(pose["sleeve_root_center_U"], [(a+b)/2 for a, b in zip(shoulder, under)]+[0]) < 1e-6, "Sleeve root center changed")
    require(max_error(pose["sleeve_root_major_U"], [(a-b)/2 for a, b in zip(shoulder, under)]+[0]) < 1e-6, "Sleeve root axis changed")
    require(max_error(pose["sleeve_axis"], [.36, -math.sqrt(1-.36**2), 0]) < 1e-6 and pose["sleeve_transition_U"] == 45 and pose["sleeve_root_depth_U"] == 70, "Sleeve display recipe changed")
    cuff = baseline["完整二维几何"]["袖片"]["定位点"]
    require(abs(pose["sleeve_underarm_source_y_U"]-(cuff["袖片图面左侧腋下点"]["高"]+cuff["袖片图面右侧腋下点"]["高"])/2) < 1e-6, "Sleeve baseline source anchor changed")
    require(pose["band_fold_display"]["height_fraction_of_flat_width"] == .5 and pose["band_fold_display"]["radial_fraction_of_flat_width"] == .05, "Band display fold recipe changed")


def body_point(source, piece, uv, ref, pose):
    x, y = uv; cfg = pose["body"][piece]
    sides = {}
    for side in ("左", "右"):
        samples = [(p[1], p[0]) for name, curve in source["curves"].items() if "图面"+side+"侧边" in name for p in curve]
        sides[side] = interpolate(y, samples)
    half = (sides["右"]-sides["左"])/2
    theta = clamp(x/half, -1, 1)*math.pi/2
    weight = clamp((y-cfg["underarm_y_U"])/(cfg["shoulder_y_U"]-cfg["underarm_y_U"]), 0, 1)
    X = (1-weight)*half*.72*math.sin(theta)+weight*x
    name = ref["curve"]
    if "领口" in name: depth = cfg["neck_depth_display_U"]*max(0, math.cos(math.pi*x/(2*cfg["neck_half_width_U"])))
    elif "袖窿" in name: depth = 70*math.sin(math.pi*ref["walk_parameter"])
    elif "下摆" in name: depth = 92*max(0, math.cos(theta))
    else: depth = 0
    return [X, y+cfg["y_offset_U"], depth*(1 if piece == "前片" else -1)]


def distance_to_loop(point, boundary):
    best = math.inf
    for a, b in zip(boundary, boundary[1:]+boundary[:1]):
        vx, vy = b[0]-a[0], b[1]-a[1]
        factor = clamp(((point[0]-a[0])*vx+(point[1]-a[1])*vy)/(vx*vx+vy*vy), 0, 1)
        best = min(best, math.hypot(point[0]-a[0]-factor*vx, point[1]-a[1]-factor*vy))
    return best


def mesh_topology(uv, triangles, B):
    require(len(uv) >= B > 2, "Incomplete boundary mesh")
    edges = Counter(); neighbors = [set() for _ in uv]; area = 0.
    used = set()
    for tri in triangles:
        require(isinstance(tri, list) and len(tri) == 3 and all(type(i) is int and 0 <= i < len(uv) for i in tri) and len(set(tri)) == 3, "Invalid triangle index")
        a, b, c = [uv[i] for i in tri]
        signed = ((b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]))/2
        require(signed > 1e-8, "UV foldover or degenerate triangle")
        area += signed; used.update(tri)
        for a, b in zip(tri, tri[1:]+tri[:1]):
            edges[tuple(sorted((a, b)))] += 1; neighbors[a].add(b); neighbors[b].add(a)
    require(len(used) == len(uv) and max(edges.values()) == 2 and min(edges.values()) == 1, "Unused/nonmanifold mesh vertex or edge")
    require({edge for edge, count in edges.items() if count == 1} == {tuple(sorted((i, (i+1)%B))) for i in range(B)}, "Mesh boundary omits or substitutes source points")
    require(len(uv)-len(edges)+len(triangles) == 1, "Unexpected mesh holes or components")
    return neighbors, area


def harmonic_residual(values, neighbors, B):
    result = 0.
    for i in range(B, len(values)):
        require(bool(neighbors[i]), "Isolated harmonic vertex")
        for axis, value in enumerate(values[i]):
            result = max(result, abs(value-sum(values[j][axis] for j in neighbors[i])/len(neighbors[i])))
    return result


def sleeve_boundary_domains(source, boundary, refs):
    curves = source["curves"]
    sides = [points for name, points in curves.items() if "袖底边" in name and "外" not in name]
    require(len(sides) == 2, "Sleeve source side edges missing")
    side_length_mean = sum(chain_length(q) for q in sides)/2
    cuffs = [p for name, q in curves.items() if name.startswith("袖片袖口横线") for p in q]
    xmin, xmax = min(p[0] for p in cuffs), max(p[0] for p in cuffs)
    underarm = sum(max(p[1] for p in q) for q in sides)/2
    cuff_y = sum(p[1] for p in cuffs)/len(cuffs)
    L = underarm-cuff_y
    require(L > 0, "Nonpositive source sleeve axial span")
    apex = max((p for name, q in curves.items() if "袖山弧线" in name for p in q), key=lambda p: p[1])
    result = []
    for p, ref in zip(boundary, refs):
        name = ref["curve"]; raw = curves[name]; index = ref["vertex_index"]
        factor = chain_length(raw[:index+1])/chain_length(raw)
        if "袖山" in name:
            if math.dist(raw[-1], apex) < math.dist(raw[0], apex): factor = 1-factor
            result.append([0., (1 if "图面左" in name else -1)*math.pi*factor])
        elif "袖底边" in name:
            if raw[0][1] < raw[-1][1]: factor = 1-factor
            result.append([L*factor, math.pi if "图面左" in name else -math.pi])
        else:
            require("袖口" in name, "Unknown sleeve boundary role")
            result.append([L, math.pi-2*math.pi*(p[0]-xmin)/(xmax-xmin)])
    return result, {"axis_length_U": L, "underarm_source_y_U": underarm, "side_length_mean_U": side_length_mean, "cuff_source_y_U": cuff_y, "cuff_width_U": xmax-xmin}


def sleeve_point(source, domain, config, pose, sign):
    u, angle = domain; L = config["axis_length_U"]
    source_y = config["underarm_source_y_U"]+clamp(u/L, 0, 1)*(config["cuff_source_y_U"]-config["underarm_source_y_U"])
    sides = {side: interpolate(source_y, [(p[1], p[0]) for p in source["curves"]["袖片图面"+side+"袖底边"]]) for side in ("左", "右")}
    radius = (sides["右"]-sides["左"])/(2*math.pi)
    require(radius > 0, "Invalid source-based sleeve radius")
    w = clamp(u/45, 0, 1); w = w*w*(3-2*w)
    axis = pose["sleeve_axis"][:]; axis[0] *= sign
    normal = [-axis[1]*sign, abs(axis[0]), 0]
    root = pose["sleeve_root_major_U"][:]; root[0] *= sign
    major = [(1-w)*a+w*radius*b for a, b in zip(root, normal)]
    minor = (1-w)*70+w*radius
    center = pose["sleeve_root_center_U"][:]; center[0] *= sign
    result = [c+u*a+m*math.cos(angle) for c, a, m in zip(center, axis, major)]
    result[2] += minor*math.sin(angle)
    return result


def band_positions(source, uv, sources, pose):
    sections = []
    for piece in ("前片", "后片"):
        segment = []
        for side in ("左", "右"):
            name = piece+"图面"+side+"领口"
            points = sources[piece]["curves"][name]
            ordered = points if points[0][0] <= points[-1][0] else points[::-1]
            if segment: ordered = ordered[1:]
            segment.extend(body_point(sources[piece], piece, p, {"curve": name}, pose) for p in ordered)
        sections.append(segment)
    ring = sections[0]+sections[1][::-1]+sections[0][:1]
    distances = [0.]
    for a, b in zip(ring, ring[1:]): distances.append(distances[-1]+math.dist(a, b))
    flat = [p for name, q in source["curves"].items() if name in {m["线条"] for m in source["contour"]} for p in q]
    xmin, xmax = min(p[0] for p in flat), max(p[0] for p in flat)
    ymin, ymax = min(p[1] for p in flat), max(p[1] for p in flat)
    width = ymax-ymin
    result = []
    for x, y in uv:
        t, v = clamp((x-xmin)/(xmax-xmin), 0, 1), clamp((y-ymin)/width, 0, 1)
        target = [interpolate(t*distances[-1], list(zip(distances, [p[j] for p in ring]))) for j in range(3)]
        radial_length = max(math.hypot(target[0], target[2]), 1e-12)
        offset = width*.05*math.sin(2*math.pi*v)
        target[0] += target[0]/radial_length*offset; target[2] += target[2]/radial_length*offset
        target[1] += width*.5*math.sin(math.pi*v)
        result.append(target)
    return result, ring


def triangle_area_3d(a, b, c):
    u = [x-y for x, y in zip(b, a)]; v = [x-y for x, y in zip(c, a)]
    return math.sqrt(sum(x*x for x in (u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0])))/2


def audit_payload(payload, committed=True):
    require("schema_version" in payload and len(payload["cases"]) == 4, "Incomplete review payload")
    records = {"baseline": payload["baseline"]}
    for case in payload["cases"]:
        require(case["id"] in CASES and case["id"] not in records, "Case IDs duplicated or unexpected")
        records[case["id"]] = case
    require(set(records) == {"baseline", *CASES}, "Review cases incomplete")
    reports, mesh_signatures, common_pose = [], {}, None
    for case, record in records.items():
        source = source_files(case, committed=committed)
        for kind in source:
            require(decode_record(record["files"][kind]) == source[kind], case + ": embedded full source bytes differ")
        if case != "baseline":
            intent_path = "experiments/intent-edit-benchmark/results/" + case + "/intent.txt"
            intent = (REPO / intent_path).read_bytes()
            if committed:
                require(subprocess.check_output(["git", "show", "HEAD:" + intent_path], cwd=REPO) == intent, "Design intent differs from committed source")
            require(record["intent"].strip() == intent.decode("utf-8").strip(), "Displayed design intent differs from committed request")
        yaml_model = yaml.safe_load(source["yaml"].decode("utf-8"))
        two_d = audit_two_d(record["twoD"], source, yaml_model)
        mesh, mesh_bytes = decode_mesh(record["threeD"])
        require(record["threeD"]["source_dxf_sha256"] == sha(source["dxf"]) and record["threeD"]["source_yaml_sha256"] == sha(source["yaml"]), "3D wrapper source lineage mismatch")
        require(record["threeD"]["units"] == "U" and record["threeD"]["mode"] == "static_geometric_assembly", "3D wrapper units/mode misrepresented")
        if common_pose is None: common_pose = mesh["pose"]
        else: require(mesh["pose"] == common_pose, "Case re-centered or re-scaled the fixed baseline placement")
        geometry, signatures = audit_mesh_geometry(mesh, source, case)
        formal_artifact = REPO / "experiments/intent-edit-review/geometry" / (case + ".mesh.json")
        require(mesh_bytes == formal_artifact.read_bytes(), "Embedded 3D bytes differ from the finalized source artifact")
        mesh_signatures[case] = signatures
        reports.append({"case": case, "files": {k: {"bytes": len(v), "sha256": sha(v)} for k, v in source.items()}, "twoD": two_d, "threeD": geometry, "artifact_sha256": sha(mesh_bytes), "artifact_bytes_match_finalized_source": True})
    response = []
    base = mesh_signatures["baseline"]
    for case in CASES:
        current = mesh_signatures[case]
        require(set(base) == set(current), "Mesh instance inventory changed")
        changed = []
        for instance, value in current.items():
            piece = value["source_piece"]
            same = base[instance]["signature"] == value["signature"]
            require(same if piece in UNCHANGED[case] else not same, f"{case}: changed/unchanged 3D response is wrong for {instance}/{piece}")
            if not same:
                changed.append(instance)
        response.append({"case": case, "changed_instances": changed, "unchanged_piece_response": "PASS"})
    return {"verdict": "PASS", "cases": reports, "responses": response, "production_readiness": "BLOCKED", "physical_fit": "NOT_RUN"}


def replace_payload(html, payload, identity):
    parser = PayloadParser(identity); parser.feed(html.decode("utf-8"))
    require(len(parser.payloads) == 1, "Fault probe needs exactly one application payload")
    text = html.decode("utf-8"); original = parser.payloads[0]
    require(text.count(original) == 1, "Ambiguous payload replacement")
    return text.replace(original, json.dumps(payload, ensure_ascii=False, separators=(',', ':'))).encode("utf-8")


def set_model(record, model):
    raw = (json.dumps(model, ensure_ascii=False, separators=(',', ':')) + '\n').encode()
    record.update(artifact_base64=base64.b64encode(raw).decode(), artifact_sha256=sha(raw), byte_length=len(raw))


def adversarial_controls(html, identity="app-data"):
    original = extract_payload(html, identity)
    def stale_svg(payload):
        payload["cases"][0]["twoD"]["svg"] = payload["baseline"]["twoD"]["svg"]
    def stale_primitives(payload):
        payload["cases"][0]["twoD"]["primitives"] = deepcopy(payload["baseline"]["twoD"]["primitives"])
    def old_model(payload):
        case = payload["cases"][0]; source = source_files(case["id"])
        model, _ = decode_mesh(payload["baseline"]["threeD"])
        model["id"] = case["id"]; model["source_dxf_sha256"] = sha(source["dxf"]); model["source_spec_sha256"] = sha(source["yaml"])
        sources, _ = independent_piece_sources(source["dxf"])
        for panel in model["panels"]:
            panel["binding"]["source_piece_polyline_sha256"] = sha(json.dumps(sources[panel["source_piece"]]["curves"], sort_keys=True, separators=(',', ':')).encode())
        set_model(case["threeD"], model)
    def altered_position(payload):
        record = payload["cases"][0]["threeD"]; model, _ = decode_mesh(record)
        model["panels"][0]["positions"][20][0] += .137
        set_model(record, model)
    def truncated_yaml(payload):
        record = payload["cases"][0]["files"]["yaml"]; raw = decode_record(record)[:4096]
        record.update(base64=base64.b64encode(raw).decode(), byte_length=len(raw), sha256=sha(raw))
    controls = [
        ("stale_SVG_with_fresh_source_digests", stale_svg, "Actual SVG geometry"),
        ("stale_primitives_with_fresh_source_digests", stale_primitives, "2D primitives"),
        ("old_3D_with_forged_case_and_piece_digests", old_model, "boundary UV"),
        ("altered_3D_positions_with_valid_artifact_digest", altered_position, "3D boundary"),
        ("truncated_YAML_with_self_consistent_length_and_digest", truncated_yaml, "full source bytes differ"),
        ("missing_design_intent_case", lambda p: p["cases"].pop(), "Incomplete review payload"),
    ]
    result = []
    for name, change, expected in controls:
        payload = deepcopy(original); change(payload)
        variant = replace_payload(html, payload, identity)
        try:
            audit_payload(extract_payload(variant, identity))
        except AuditFailure as error:
            require(expected in str(error), "Fault probe was rejected at an unintended boundary: " + name + ": " + str(error))
            result.append({"control": name, "verdict": "PASS", "actual_rejection": str(error), "mutated_html_sha256": sha(variant)})
        else:
            raise AuditFailure("False-success fault probe accepted: " + name)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--html", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--data-id", default="app-data")
    parser.add_argument("--adversarial", action="store_true", help="Probe the real HTML with stale/forged/truncated payload variants.")
    args = parser.parse_args()
    html = args.html.read_bytes()
    try:
        report = audit_payload(extract_payload(html, args.data_id))
        if args.adversarial:
            report["adversarial_controls"] = adversarial_controls(html, args.data_id)
    except Exception as error:
        report = {"verdict": "FAIL", "error": type(error).__name__ + ": " + str(error)}
    report["html"] = str(args.html)
    report["html_sha256"] = sha(html)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report if report["verdict"] != "PASS" else {"verdict": "PASS", "cases": len(report["cases"]), "html_sha256": report["html_sha256"]}, ensure_ascii=False, indent=2))
    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
