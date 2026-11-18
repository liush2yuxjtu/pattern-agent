"""Front-neck deepening with an explicitly scoped geometric band dependency.

This case edits existing polyline vertices.  It does not infer a production seam
allowance, ribbing ratio, physical unit calibration or a missing spline history.
"""
from __future__ import annotations

from copy import deepcopy
import math


CASE = {
    "id": "04_front_neck",
    "title": "前领加深并联动候选领条",
    "intent": (
        "前领中点向下加深10U，领宽、领肩点、肩袖与其他衣身保持；"
        "内外前领圈相关线和领中标记同步。领条长度保持基准现状的候选几何长度比，"
        "展开宽40U不变。后片与袖片全部保持；候选比值不批准为生产配比。"
    ),
    "affected_pieces": ["前片", "领条"],
    "preserve_pieces": ["后片", "袖片"],
    "operation": "ADJUST_NECKLINE",
    "parameters": {
        "front_depth_delta": 10.0,
        "unit": "U",
        "band_dependency": "保持基准现状的候选几何长度比",
        "production_ratio_approval": "不变，仍待确认",
    },
}


def _line(piece, name):
    matches = [curve for curve in piece["线条"] if curve["名称"] == name]
    if len(matches) != 1:
        raise ValueError(f"线条缺失或重名：{name}")
    return matches[0]


def _length(curve):
    points = curve["点位"]
    return math.fsum(
        math.hypot(b["横"] - a["横"], b["高"] - a["高"])
        for a, b in zip(points, points[1:])
    )


def _neck_length(piece, prefix):
    return math.fsum(
        _length(_line(piece, prefix + "图面" + side + "领口"))
        for side in ["左", "右"]
    )


def _band_length(piece):
    return math.fsum(
        _length(_line(piece, "领条接领长边候选第" + n + "段"))
        for n in ["1", "2"]
    )


def _deepen_curve(curve, center_x, delta):
    """Zero displacement at the shoulder end and full displacement at center.

    A quadratic weight in the existing x-coordinate preserves all x values and
    gives zero weight slope at center.  Each nested contour uses its own shoulder
    endpoint so both inner and outer shoulder/neck endpoints stay fixed.
    """
    points = curve["点位"]
    endpoint = max(points, key=lambda point: abs(point["横"] - center_x))
    span = abs(endpoint["横"] - center_x)
    if not span > 0:
        raise ValueError("领口曲线横向跨度必须为正")
    for point in points:
        t = abs(point["横"] - center_x) / span
        weight = max(0.0, 1.0 - t * t)
        point["高"] = round(point["高"] - delta * weight, 6)


def edit(model, delta: float = 10.0):
    if model["单位与坐标"]["坐标单位"] != "U":
        raise ValueError("本案例只使用图形单位U，不推定毫米换算")
    if not math.isfinite(delta) or delta <= 0:
        raise ValueError("前领加深量必须是有限正数")
    geometry = model["完整二维几何"]
    front = geometry["前片"]
    back = geometry["后片"]
    band = geometry["领条"]
    landmark = front["定位点"]["前片领口中点"]
    center_before = deepcopy(landmark)
    front_before = _neck_length(front, "前片")
    back_length = _neck_length(back, "后片")
    band_before = _band_length(band)
    ratio_before = band_before / (front_before + back_length)

    center_line = _line(front, "前中纵向内部线")
    center_indices = [
        i for i, point in enumerate(center_line["点位"])
        if point == center_before
    ]
    if len(center_indices) != 1:
        raise ValueError("前中内部线必须恰好有一个端点对应前领中点")
    center_index = center_indices[0]
    if center_index not in (0, len(center_line["点位"]) - 1):
        raise ValueError("前领中点不是前中内部线端点")
    neighbor_index = 1 if center_index == 0 else center_index - 1
    neighbor = center_line["点位"][neighbor_index]
    if neighbor["高"] >= center_before["高"] - delta:
        raise ValueError("加深量越过前中内部线相邻点，需另定内部线联动策略")

    changed_names = [
        "前片图面左领口", "前片图面右领口",
        "前片外侧轮廓第6段", "前片外侧轮廓第7段",
    ]
    for name in changed_names:
        _deepen_curve(_line(front, name), center_before["横"], delta)

    # These two actual source marks cross the inner and outer neck center.
    # Moving the complete marks retains their 10U length and alignment.
    for name in [
        "前片短线或内部直线第1条（用途待核对）",
        "前片短线或内部直线第5条（用途待核对）",
    ]:
        for point in _line(front, name)["点位"]:
            point["高"] = round(point["高"] - delta, 6)
        changed_names.append(name)
    center_line["点位"][center_index]["高"] = round(center_before["高"] - delta, 6)
    changed_names.append("前中纵向内部线")
    landmark["高"] = round(center_before["高"] - delta, 6)

    front_after = _neck_length(front, "前片")
    target_band = (front_after + back_length) * ratio_before
    scale = target_band / band_before
    anchor_x = band["定位点"]["领条内圈左下角"]["横"]

    def move_band_point(point):
        point["横"] = round(anchor_x + (point["横"] - anchor_x) * scale, 6)

    # A single affine map includes both contours, all notches/internal lines,
    # landmarks and annotation positions. All y coordinates stay identical.
    for curve in band["线条"]:
        for point in curve["点位"]:
            move_band_point(point)
    for point in band["定位点"].values():
        move_band_point(point)
    for annotation in band["文字"]:
        move_band_point(annotation["位置"])
    band_after = _band_length(band)
    ratio_after = band_after / (front_after + back_length)
    if abs(ratio_after - ratio_before) > 1e-6:
        raise ValueError("六位小数输出后未保持约定的候选几何长度比")

    return {
        "anchors": {
            "front_neck_center_before": center_before,
            "front_neck_center_after": deepcopy(landmark),
            "front_neck_depth_delta_U": delta,
            "front_neck_length_before_U": front_before,
            "front_neck_length_after_U": front_after,
            "back_neck_length_U": back_length,
            "band_length_before_U": band_before,
            "band_length_after_U": band_after,
            "band_target_length_U": target_band,
            "band_horizontal_scale": scale,
            "band_vertical_width_U": 40.0,
            "observed_geometric_ratio_before": ratio_before,
            "observed_geometric_ratio_after": ratio_after,
            "ratio_absolute_error": abs(ratio_after - ratio_before),
        },
        "changed_front_line_names": changed_names,
        "changed_front_landmarks": ["前片领口中点"],
        "method": (
            "内外左右前领曲线分别按归一横向距离的二次权重下移，领肩端点固定；"
            "前中内部线上端和两条领中标记同步。领条全体使用同一个横向仿射映射，"
            "所有纵向坐标、排版原点、文字内容不变。"
        ),
        "limitations": [
            "只保持当前候选领条与领圈的几何长度比，不批准生产缩比。",
            "没有推定净裁角色、缝份、面料弹性或毫米比例。",
            "前中内部线只移动领中端点；若加深量越过相邻点则拒绝此有限策略。",
        ],
    }
