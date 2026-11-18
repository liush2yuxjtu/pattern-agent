"""Independent artifact auditor for the seven-case intent-edit benchmark.

The audit deliberately does not import the generator, reconstruction reader or
case implementations. It reads raw CAD tags and computes its own measurements.
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path
import sys
import time

import yaml

REPO = Path(__file__).resolve().parents[2]
EXPECTED = {"01_sleeve_length", "02_body_length", "03_cuff_width", "04_front_neck"}
EXPECTED_NEGATIVE = {"05_uncalibrated_cm": "BLOCKED", "06_ambiguous_comfort": "BLOCKED", "07_invalid_cuff": "REJECTED"}
BASE_SPEC_SHA = "88a84e697273724cdb5b4a05116c00cd53b0cb75a4d7e6bdfa5d0b7fd34f181e"
BASE_DXF_SHA = "1f82b2c4ca094983657ce49fc73cf06aec24d3329a53dcc3472dd5ca2cee87f4"
TOL = 3e-6
GAP_ROUNDING_TOL = 5e-6


class AuditFailure(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise AuditFailure(message)


class UniqueLoader(yaml.SafeLoader):
    pass


def unique_mapping(loader, node, deep=False):
    result = {}
    for key, value in node.value:
        key = loader.construct_object(key, deep=deep)
        require(key not in result, f"重复YAML字段：{key}")
        result[key] = loader.construct_object(value, deep=deep)
    return result


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)


def number(value):
    require(not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value), "非有限或非数值几何")
    return float(value)


def point(value):
    return number(value["横"]), number(value["高"])


def close(actual, expected, name, tolerance=TOL):
    require(abs(actual - expected) <= tolerance, f"{name}：实测{actual:.9f}，要求{expected:.9f}")


def poly_length(points):
    return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(points, points[1:]))


def read_model(path):
    return yaml.load(Path(path).read_text(encoding="utf-8"), Loader=UniqueLoader)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def cad_pairs(raw):
    lines = raw.splitlines(keepends=True)
    require(len(lines) % 2 == 0, "DXF组码与值未成对")
    pairs = []
    for i in range(0, len(lines), 2):
        code = int(lines[i].rstrip(b"\r\n"))
        value = lines[i + 1].rstrip(b"\r\n").decode("gb18030")
        pairs.append((code, value))
    return lines, pairs


def read_cad(raw):
    _, pairs = cad_pairs(raw)
    records = []
    for index, (code, value) in enumerate(pairs):
        if code == 0:
            records.append({"kind": value.strip(), "tags": [], "index": index})
        elif records:
            records[-1]["tags"].append((code, value))

    def tag(record, code, default=None):
        return next((v for k, v in record["tags"] if k == code), default)

    def location(record, x=10, y=20):
        return number(float(tag(record, x))), number(float(tag(record, y)))

    result = []
    counts = Counter()
    vertices = 0
    i = 0
    while i < len(records):
        record = records[i]
        kind = record["kind"]
        if kind == "POLYLINE":
            points = []
            j = i + 1
            while j < len(records) and records[j]["kind"] == "VERTEX":
                points.append(location(records[j])); j += 1
            require(j < len(records) and records[j]["kind"] == "SEQEND", "多段线缺少SEQEND")
            result.append((kind, tuple(points), int(tag(record, 70, "0")) & 1))
            vertices += len(points); counts[kind] += 1
            i = j
        elif kind == "LINE":
            result.append((kind, (location(record), location(record, 11, 21)), 0)); counts[kind] += 1
        elif kind == "TEXT":
            result.append((kind, tag(record, 1, ""), location(record))); counts[kind] += 1
        i += 1
    require(dict(counts) == {"POLYLINE": 126, "LINE": 78, "TEXT": 27} or counts == Counter(POLYLINE=126, LINE=78, TEXT=27), "主实体数量改变")
    require(vertices == 1487, "折线顶点数改变")
    declared_units = next((pairs[j + 1][1].strip() for j, item in enumerate(pairs[:-1]) if item == (9, "$INSUNITS")), None)
    return result, {"entities": sum(counts.values()), "counts": dict(counts), "polyline_vertices": vertices, "raw_declared_INSUNITS": declared_units, "audit_coordinate_unit": "YAML U; physical scale uncalibrated"}


def canonical(rows):
    result = []
    for kind, a, b in rows:
        if kind == "TEXT":
            result.append((kind, a, tuple(round(v, 6) for v in b)))
        else:
            result.append((kind, tuple(tuple(round(v, 6) for v in p) for p in a), b))
    return Counter(result)


def model_rows(model):
    rows = []
    for part in model["完整二维几何"].values():
        origin = part["排版放置点"]
        def placed(p):
            return tuple(float(Decimal(str(origin[k])) + Decimal(str(p[k]))) for k in ("横", "高"))
        for line in part["线条"]:
            require(line["线型"] in ("直线", "折线"), "未知线型")
            points = tuple(placed(p) for p in line["点位"])
            for p in points:
                number(p[0]); number(p[1])
            require(len(points) >= 2, "线不足两个点")
            rows.append(("LINE" if line["线型"] == "直线" else "POLYLINE", points, int(line["闭合方式"] == "闭合")))
        for text in part["文字"]:
            rows.append(("TEXT", text["文字内容"], placed(text["位置"])))
    return rows


def curves(model, piece):
    lines = model["完整二维几何"][piece]["线条"]
    result = {line["名称"]: line for line in lines}
    require(len(result) == len(lines), "命名线重复")
    return result


def points_of(model, piece, name):
    return [point(p) for p in curves(model, piece)[name]["点位"]]


def measure_model(model):
    actual_ports = {}
    max_port_error = 0
    for piece, ports in model["裁片接口"].items():
        for name, port in ports.items():
            chains = []
            for member in port["组成"]:
                data = points_of(model, piece, member["线条"])
                require(member["方向"] in ("正向", "反向"), "接口方向无效")
                chains.append(data if member["方向"] == "正向" else data[::-1])
            measured = sum(poly_length(c) for c in chains)
            actual_ports[piece, name] = measured
            error = abs(measured - number(port["长度"]))
            max_port_error = max(max_port_error, error)
            close(measured, port["长度"], f"接口{piece}/{name}")
            require(chains[0][0] == point(port["起点"]) and chains[-1][-1] == point(port["终点"]), f"接口起止点{piece}/{name}")
            gaps = [math.dist(a[-1], b[0]) for a, b in zip(chains, chains[1:])]
            require(len(gaps) == len(port["段间间隙"]), "接口间隙数量")
            for i, (a, b) in enumerate(zip(gaps, port["段间间隙"])):
                close(a, b, f"接口间隙{piece}/{name}/{i}")
    projects = model["关键尺寸"]["项目"]
    measured_dimensions = {}
    def dimension(name, seen=()):
        require(name not in seen, "尺寸引用循环")
        if name in measured_dimensions:
            return measured_dimensions[name]
        value = projects[name]
        method = value["计算方式"]
        piece = value.get("裁片")
        if method == "线长相加":
            result = sum(poly_length(points_of(model, piece, n)) for n in value["线条"])
        elif method == "尺寸相加":
            result = sum(dimension(n, seen + (name,)) for n in value["尺寸项目"])
        elif method == "接口长相加":
            result = sum(actual_ports[p["裁片"], p["接口"]] for p in value["接口"])
        elif method in ("横向两点距离", "竖向两点距离"):
            ps = [point(model["完整二维几何"][piece]["定位点"][n]) for n in value["定位点"]]
            axis = 0 if method == "横向两点距离" else 1
            result = abs(ps[0][axis] - ps[1][axis])
        else:
            raise AuditFailure(f"未定义的尺寸度法{method}")
        require(value["单位"] == "U", "尺寸单位改变")
        close(result, number(value["数值"]), f"关键尺寸{name}")
        measured_dimensions[name] = result
        return result
    for name in projects:
        dimension(name)
    def edge(reference):
        return actual_ports[reference["裁片"], reference["接口"]]
    for name, relation in model["连接关系"].items():
        if "走缝长度差" in relation:
            close(edge(relation["连接一"]) - edge(relation["连接二"]), relation["走缝长度差"], f"连接差{name}")
        if name.endswith("袖装配"):
            a = sum(edge(r) for r in relation["衣身接口"])
            b = sum(edge(r) for r in relation["袖片接口"])
            close(a, relation["衣身袖窿总长"], f"袖窿汇总{name}")
            close(b, relation["袖山总长"], f"袖山汇总{name}")
            close(b - a, relation["总长差"], f"装袖总差{name}")
        if name == "领条与领口":
            a = sum(edge(r) for r in relation["衣身接口"])
            b = edge(relation["领条接口"])
            close(a, relation["衣身领圈总长"], "领圈汇总")
            close(b, relation["领条长边"], "领条汇总")
            close(b / a, relation["当前几何长度比"], "领条比")
    for relation in model["缝级关系图"]["缝级记录"]:
        a = sum(edge(r) for r in relation["边一"])
        current = relation["当前几何"]
        if isinstance(relation["边二"], list):
            b = sum(edge(r) for r in relation["边二"])
            if "衣身长度" in current:
                close(a, current["衣身长度"], "缝级衣身长度")
                close(b, current["领条长度"], "缝级领条长度")
                close(b / a, current["长度比"], "缝级配比")
            else:
                close(a - b, current["走缝长度差"], "缝级走缝差")
        else:
            close(a, current["衣身段长度"], "装袖衣身区段")
            require(current["已对应袖山段长度"] is None and current["已对应长度差"] is None, "未经确认的袖山映射被擅自填值")
    require(len(actual_ports) == 25 and len(projects) == 23, "尺寸或接口清单改变")
    calibration = model["原型与部件分层"]["配套标定"]
    for label, piece, name in [("前片左", "前片", "左袖窿"), ("前片右", "前片", "右袖窿"), ("后片左", "后片", "左袖窿"), ("后片右", "后片", "右袖窿")]:
        close(actual_ports[piece, name], calibration["当前衣身袖窿"][label], "配套袖窿")
    close(measured_dimensions["袖山总长"], calibration["当前袖山总长"]["数值"], "配套袖山")
    close(measured_dimensions["领圈总长"], calibration["当前领圈总长"]["数值"], "配套领圈")
    return {"ports": actual_ports, "dimensions": measured_dimensions, "max_interface_rounding_error_U": max_port_error}


def segment_intersection(a, b, c, d):
    def orient(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
    ab_c, ab_d, cd_a, cd_b = orient(a, b, c), orient(a, b, d), orient(c, d, a), orient(c, d, b)
    if ab_c * ab_d < -1e-14 and cd_a * cd_b < -1e-14:
        return True
    if all(abs(v) < 1e-10 for v in (ab_c, ab_d, cd_a, cd_b)):
        axis = 0 if abs(b[0] - a[0]) >= abs(b[1] - a[1]) else 1
        overlap = min(max(a[axis], b[axis]), max(c[axis], d[axis])) - max(min(a[axis], b[axis]), min(c[axis], d[axis]))
        return overlap >= -1e-10
    def on_segment(p, q, r):
        return min(p[0], q[0]) - 1e-10 <= r[0] <= max(p[0], q[0]) + 1e-10 and min(p[1], q[1]) - 1e-10 <= r[1] <= max(p[1], q[1]) + 1e-10
    if abs(ab_c) < 1e-10 and on_segment(a, b, c): return True
    if abs(ab_d) < 1e-10 and on_segment(a, b, d): return True
    if abs(cd_a) < 1e-10 and on_segment(c, d, a): return True
    if abs(cd_b) < 1e-10 and on_segment(c, d, b): return True
    return False


def contour_quality(model):
    result = {}
    for piece, part in model["完整二维几何"].items():
        for name, contour in part["轮廓"].items():
            chains, edges = [], []
            for member in contour["组成"]:
                ps = points_of(model, piece, member["线条"])
                if member["方向"] == "反向":
                    ps = ps[::-1]
                chains.append(ps)
                edges.extend((member["线条"], i, a, b) for i, (a, b) in enumerate(zip(ps, ps[1:])))
            gaps = [math.dist(a[-1], b[0]) for a, b in zip(chains, chains[1:] + chains[:1])]
            crosses, zeros = set(), set()
            for i, (line, k, a, b) in enumerate(edges):
                if math.dist(a, b) < 1e-9:
                    zeros.add((line, k)); continue
                for j in range(i + 1, len(edges)):
                    line2, k2, c, d = edges[j]
                    if j == i + 1 or (i == 0 and j == len(edges) - 1):
                        continue
                    if segment_intersection(a, b, c, d):
                        crosses.add((line, k, line2, k2))
            result[piece, name] = {"gaps": gaps, "crosses": crosses, "zeros": zeros}
    return result


def preserve_structure(base, current):
    for piece, old in base["完整二维几何"].items():
        new = current["完整二维几何"][piece]
        require(new["排版放置点"] == old["排版放置点"], "排版原点改变")
        require(list(new["定位点"]) == list(old["定位点"]), "定位点清单改变")
        require(len(new["线条"]) == len(old["线条"]), "线条清单改变")
        for a, b in zip(old["线条"], new["线条"]):
            for key in ("名称", "线型", "闭合方式"):
                require(a[key] == b[key], f"线条结构改变{piece}/{key}")
            require(len(a["点位"]) == len(b["点位"]), "线条点列长度改变")
        require([t["文字内容"] for t in old["文字"]] == [t["文字内容"] for t in new["文字"]], "文字内容或数量改变")
        vertices = {point(p) for line in new["线条"] for p in line["点位"]}
        require(all(point(p) in vertices for p in new["定位点"].values()), f"定位点脱离图形：{piece}")
    for key in ("材料选择", "工艺参数", "参考尺码表", "单位与坐标", "裁剪清单"):
        require(base[key] == current[key], f"未经允许改变生产/参考字段：{key}")


def intent_checks(case_id, base, current, before, after, requested=None):
    if requested is None:
        requested = {"01_sleeve_length": 20, "02_body_length": -15, "03_cuff_width": 10, "04_front_neck": 10}[case_id]
    frozen = {"01_sleeve_length": ["前片", "后片", "领条"], "02_body_length": ["袖片", "领条"], "03_cuff_width": ["前片", "后片", "领条"], "04_front_neck": ["后片", "袖片"]}[case_id]
    for piece in frozen:
        require(current["完整二维几何"][piece] == base["完整二维几何"][piece], f"未改裁片改变：{piece}")
    metrics = {}
    if case_id in ("01_sleeve_length", "03_cuff_width"):
        old = base["完整二维几何"]["袖片"]
        new = current["完整二维几何"]["袖片"]
        for name, line in curves(base, "袖片").items():
            if "袖山弧线" in name:
                require(line == curves(current, "袖片")[name], "袖山被改变")
        floor = min(p["高"] for k, p in old["定位点"].items() if "腋下点" in k)
        for a, b in zip(old["线条"], new["线条"]):
            for p, q in zip(a["点位"], b["点位"]):
                if p["高"] >= floor:
                    require(p == q, "腋下及以上几何改变")
        for name in ("袖片图面左侧腋下点", "袖片图面右侧腋下点"):
            require(old["定位点"][name] == new["定位点"][name], "腋下定位改变")
        if case_id == "01_sleeve_length":
            delta = after["dimensions"]["袖片纵线"] - before["dimensions"]["袖片纵线"]
            close(delta, requested, "袖片纵线增量")
            metrics["sleeve_length_delta_U"] = delta
            for name in ("袖口图面左端点", "袖口图面右端点", "袖口横线中间连接点"):
                a, b = old["定位点"][name], new["定位点"][name]
                close(b["横"], a["横"], "袖口横坐标保持")
                close(b["高"] - a["高"], -requested, "袖口纵向位移")
        else:
            for name, delta in [("袖口图面左端点", -requested / 2), ("袖口图面右端点", requested / 2)]:
                a, b = old["定位点"][name], new["定位点"][name]
                close(b["横"] - a["横"], delta, "袖口端点横移")
                close(b["高"], a["高"], "袖口高度保持")
            delta = after["ports"]["袖片", "袖口"] - before["ports"]["袖片", "袖口"]
            close(delta, requested, "展开袖口增量")
            metrics["cuff_width_delta_U"] = delta
    elif case_id == "02_body_length":
        for piece, dim in [("前片", "前中纵线"), ("后片", "后中纵线")]:
            old = base["完整二维几何"][piece]; new = current["完整二维几何"][piece]
            waist = next(line for line in old["线条"] if "腰部横线" in line["名称"])["点位"][0]["高"]
            delta = after["dimensions"][dim] - before["dimensions"][dim]
            close(delta, requested, piece + "中长变化")
            metrics[piece + "中长变化U"] = delta
            for a, b in zip(old["线条"], new["线条"]):
                for p, q in zip(a["点位"], b["点位"]):
                    close(q["横"], p["横"], "衣身横坐标保持")
                    require(min(0, -requested) - TOL <= q["高"] - p["高"] <= max(0, -requested) + TOL, "衣身出现超额或反向位移")
                    if p["高"] >= waist:
                        require(p == q, "腰部及以上改变")
                    if "下摆弧线" in a["名称"]:
                        close(q["高"] - p["高"], -requested, "下摆形状刚性平移")
    else:
        old = base["完整二维几何"]["前片"]; new = current["完整二维几何"]["前片"]
        for name, p in old["定位点"].items():
            if name != "前片领口中点":
                require(p == new["定位点"][name], f"前领之外定位点变化{name}")
        close(new["定位点"]["前片领口中点"]["高"] - old["定位点"]["前片领口中点"]["高"], -requested, "前领中加深")
        close(after["dimensions"]["前片领深"] - before["dimensions"]["前片领深"], requested, "前领深增量")
        close(after["dimensions"]["前片领宽"], before["dimensions"]["前片领宽"], "前领宽保持")
        for name, line in curves(base, "前片").items():
            if any(word in name for word in ("肩线", "袖窿弧线", "侧边", "下摆弧线", "胸部横线", "腰部横线")):
                require(line == curves(current, "前片")[name], f"前领修改影响衣身{name}")
        ratio_before = before["ports"]["领条", "接领长边"] / (before["ports"]["前片", "领圈"] + before["ports"]["后片", "领圈"])
        ratio_after = after["ports"]["领条", "接领长边"] / (after["ports"]["前片", "领圈"] + after["ports"]["后片", "领圈"])
        close(ratio_after, ratio_before, "候选领条几何比例", 1e-6)
        close(after["dimensions"]["领条展开宽"], before["dimensions"]["领条展开宽"], "领条宽度保持")
        for a, b in zip(base["完整二维几何"]["领条"]["线条"], current["完整二维几何"]["领条"]["线条"]):
            for p, q in zip(a["点位"], b["点位"]):
                close(p["高"], q["高"], "领条高度保持")
        metrics.update(front_neck_depth_delta_U=after["dimensions"]["前片领深"] - before["dimensions"]["前片领深"], candidate_ratio_before=ratio_before, candidate_ratio_after=ratio_after)
    return metrics


def pointer_parts(path):
    require(isinstance(path, str) and path.startswith("/") and path != "/", "不支持的JSON Pointer")
    return [s.replace("~1", "/").replace("~0", "~") for s in path[1:].split("/")]


def apply_spec_operations(document, operations, reverse=False):
    result = deepcopy(document)
    entries = list(reversed(operations)) if reverse else operations
    for operation in entries:
        op = operation["op"]
        old, value = operation.get("old"), operation.get("value")
        if reverse:
            op, old, value = {"add": "remove", "remove": "add", "replace": "replace"}[op], value, old
        parts = pointer_parts(operation["path"])
        parent = result
        for key in parts[:-1]:
            parent = parent[int(key)] if isinstance(parent, list) else parent[key]
        key = int(parts[-1]) if isinstance(parent, list) else parts[-1]
        if op == "add":
            if isinstance(parent, list):
                require(0 <= key <= len(parent), "列表添加下标非法"); parent.insert(key, deepcopy(value))
            else:
                require(key not in parent, "add覆盖已存在字段"); parent[key] = deepcopy(value)
        else:
            require(parent[key] == old, f"规格补丁旧值不匹配：{operation['path']}")
            if op == "replace":
                parent[key] = deepcopy(value)
            elif op == "remove":
                if isinstance(parent, list): parent.pop(key)
                else: del parent[key]
            else:
                raise AuditFailure("不支持的规格补丁操作")
    return result


def replay_spec(raw, patch):
    require(sha(raw) == patch["base_sha256"], "规格补丁基准摘要错误")
    return apply_spec_operations(yaml.load(raw.decode("utf-8"), Loader=UniqueLoader), patch["operations"])


def replay_dxf(raw, patch, reverse=False, target_raw=None):
    expected = patch.get("target_sha256", sha(target_raw) if target_raw is not None else None) if reverse else patch["base_sha256"]
    require(expected is not None and sha(raw) == expected, "DXF补丁基准摘要错误")
    lines, pairs = cad_pairs(raw)
    seen = set()
    for operation in patch["operations"]:
        index = operation["pair_index"]
        require(isinstance(index, int) and not isinstance(index, bool) and 0 <= index < len(pairs) and index not in seen, "DXF补丁索引非法或重复")
        seen.add(index)
        old, new = (operation["value"], operation["old"]) if reverse else (operation["old"], operation["value"])
        require(int(operation["code"]) in (10, 20, 11, 21), "本基准只允许坐标组码补丁")
        require(isinstance(new, str) and "\n" not in new and "\r" not in new, "DXF补丁值不得包含行分隔符")
        number(float(new))
        require(pairs[index] == (int(operation["code"]), old), "DXF补丁旧值或组码错误")
        body = lines[index * 2 + 1].rstrip(b"\r\n")
        ending = lines[index * 2 + 1][len(body):]
        lines[index * 2 + 1] = new.encode("gb18030") + ending
    return b"".join(lines)


def must_reject(action, name):
    try:
        action()
    except (AuditFailure, KeyError, IndexError, ValueError):
        return {"control": name, "verdict": "PASS"}
    raise AuditFailure("故障输入没有被拒绝：" + name)


def audit_case(case_dir, base, base_spec_raw, base_cad_raw, before, base_quality):
    start = time.perf_counter()
    case_id = case_dir.name
    require(case_id in EXPECTED, "未知正向案例目录：" + case_id)
    current = read_model(case_dir / "new-spec.yaml")
    raw = (case_dir / "output.dxf").read_bytes()
    rows, inventory = read_cad(raw)
    require(canonical(rows) == canonical(model_rows(current)), "真实DXF与新YAML几何/文字不一致")
    preserve_structure(base, current)
    after = measure_model(current)
    goals = intent_checks(case_id, base, current, before, after)
    quality = contour_quality(current)
    contour_report = []
    for key, q in quality.items():
        old = base_quality[key]
        require(q["crosses"].issubset(old["crosses"]), f"新增轮廓自交：{key}")
        require(q["zeros"].issubset(old["zeros"]), f"新增零长轮廓边：{key}")
        require(len(q["gaps"]) == len(old["gaps"]), "轮廓片段数量变化")
        for i, (a, b) in enumerate(zip(q["gaps"], old["gaps"])):
            require(a <= b + GAP_ROUNDING_TOL, f"新增或扩大轮廓缺口：{key}/{i} {b}->{a}")
        contour_report.append({"piece": key[0], "contour": key[1], "baseline_max_gap_U": max(old["gaps"]), "output_max_gap_U": max(q["gaps"]), "baseline_crossings": len(old["crosses"]), "output_crossings": len(q["crosses"]), "new_crossings": 0})
    spec_patch = json.loads((case_dir / "spec-diff.json").read_text())
    cad_patch = json.loads((case_dir / "geometry-patch.json").read_text())
    if "target_sha256" in spec_patch:
        require(spec_patch["target_sha256"] == sha((case_dir / "new-spec.yaml").read_bytes()), "规格目标摘要错误")
    if "target_sha256" in cad_patch:
        require(cad_patch["target_sha256"] == sha(raw), "DXF目标摘要错误")
    require(replay_spec(base_spec_raw, spec_patch) == current, "规格补丁重放结果不同")
    require(apply_spec_operations(current, spec_patch["operations"], reverse=True) == base, "规格补丁反向语义恢复失败")
    require(replay_dxf(base_cad_raw, cad_patch) == raw, "DXF补丁重放字节不同")
    require(replay_dxf(raw, cad_patch, reverse=True, target_raw=raw) == base_cad_raw, "DXF补丁反向字节恢复失败")
    controls = []
    bad = deepcopy(cad_patch); bad["base_sha256"] = "0" * 64
    controls.append(must_reject(lambda: replay_dxf(base_cad_raw, bad), "wrong_DXF_base_hash"))
    bad = deepcopy(cad_patch); require(bool(bad["operations"]), "未生成任何几何修改")
    bad["operations"][0]["old"] += "_fault"
    controls.append(must_reject(lambda: replay_dxf(base_cad_raw, bad), "wrong_DXF_old_value"))
    bad = deepcopy(spec_patch); bad["base_sha256"] = "0" * 64
    controls.append(must_reject(lambda: replay_spec(base_spec_raw, bad), "wrong_spec_base_hash"))
    bad = deepcopy(spec_patch)
    next(op for op in bad["operations"] if op["op"] != "add")["old"] = {"故障旧值": True}
    controls.append(must_reject(lambda: replay_spec(base_spec_raw, bad), "wrong_spec_old_value"))
    lines, pairs = cad_pairs(raw)
    index = next(i for i, (code, value) in enumerate(pairs) if code == 10)
    ending = lines[index * 2 + 1][len(lines[index * 2 + 1].rstrip(b"\r\n")):]
    lines[index * 2 + 1] = str(float(pairs[index][1]) + .137).encode() + ending
    faulty = b"".join(lines)
    controls.append(must_reject(lambda: require(canonical(read_cad(faulty)[0]) == canonical(model_rows(current)), "故障DXF与规格不同"), "faulty_output_geometry"))
    return {"case": case_id, "verdict": "PASS", "inventory": inventory, "independent_measurements": {"dimensions": after["dimensions"], "port_count": len(after["ports"]), "max_interface_rounding_error_U": after["max_interface_rounding_error_U"]}, "intent_metrics": goals, "contours": contour_report, "spec_patch_operations": len(spec_patch["operations"]), "geometry_patch_operations": len(cad_patch["operations"]), "patch_replay": "PASS", "spec_reverse_semantic_restore": "PASS", "DXF_reverse_byte_restore": "PASS", "fault_controls": controls, "audit_seconds": time.perf_counter() - start, "physical_fit": "NOT_RUN", "production_readiness": "BLOCKED"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--input-spec", type=Path, default=REPO / "patterns/fitted-tshirt/input-spec.yaml")
    parser.add_argument("--input-dxf", type=Path, default=REPO / "patterns/fitted-tshirt/input.dxf")
    parser.add_argument("--allow-partial", action="store_true", help="For local debugging only; full benchmark requires all four positive cases.")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    base_spec_raw, base_cad_raw = args.input_spec.read_bytes(), args.input_dxf.read_bytes()
    require(sha(base_spec_raw) == BASE_SPEC_SHA and sha(base_cad_raw) == BASE_DXF_SHA, "基准输入被修改或不是已提交的固定源对")
    base = read_model(args.input_spec)
    require(canonical(read_cad(base_cad_raw)[0]) == canonical(model_rows(base)), "基准DXF与输入规格不一致")
    before, base_quality = measure_model(base), contour_quality(base)
    results = []
    for spec in sorted(args.results.rglob("new-spec.yaml")):
        try:
            results.append(audit_case(spec.parent, base, base_spec_raw, base_cad_raw, before, base_quality))
        except Exception as error:
            results.append({"case": spec.parent.name, "verdict": "FAIL", "error": f"{type(error).__name__}: {error}"})
    discovered = {r["case"] for r in results}
    missing = sorted(EXPECTED - discovered)
    negatives = []
    for status_file in sorted(args.results.rglob("case-result.json")):
        value = json.loads(status_file.read_text())
        if value.get("status") in ("BLOCKED", "REJECTED"):
            clean = not any((status_file.parent / name).exists() for name in ("new-spec.yaml", "output.dxf"))
            reason = value.get("reason")
            case_id = status_file.parent.name
            expected_status = EXPECTED_NEGATIVE.get(case_id)
            negatives.append({"case": case_id, "verdict": "PASS" if clean and bool(reason) and value["status"] == expected_status else "FAIL", "status": value["status"], "reason": reason, "no_success_artifacts": clean})
    missing_negative = sorted(set(EXPECTED_NEGATIVE) - {r["case"] for r in negatives})
    passed = bool(results) and all(r["verdict"] == "PASS" for r in results) and all(r["verdict"] == "PASS" for r in negatives) and (args.allow_partial or (not missing and not missing_negative))
    report = {"verdict": "PASS" if passed else "FAIL", "scope": "Independent artifact/geometry intent benchmark; not production approval or physical fit.", "auditor_independence": "No imports of generator, case implementations or shared reconstruction/measurement helpers.", "baseline": {"spec_sha256": sha(base_spec_raw), "dxf_sha256": sha(base_cad_raw)}, "positive_cases": results, "negative_cases": negatives, "missing_positive_cases": missing, "missing_negative_cases": missing_negative, "partial_debug_mode": args.allow_partial, "suite_complete": not missing and not missing_negative, "gap_regression_rounding_tolerance_U": GAP_ROUNDING_TOL, "negative_case_requirement": "All three named rejection controls are required in a full benchmark; absence is FAIL.", "positive_pass_count": sum(r["verdict"] == "PASS" for r in results), "positive_total": len(results), "unit_interpretation": "Raw source and patched CAD have no declared $INSUNITS. Software loader defaults are not calibration. All measurements use YAML U.", "production_readiness": "BLOCKED", "physical_fit": "NOT_RUN"}
    (args.output / "independent-audit.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"verdict": report["verdict"], "positive_pass": report["positive_pass_count"], "positive_total": report["positive_total"], "missing": missing, "missing_negative": missing_negative, "negative_count": len(negatives), "failures": [r for r in results if r["verdict"] != "PASS"]}, ensure_ascii=False, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
