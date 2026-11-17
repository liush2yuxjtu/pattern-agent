"""袖口放宽的受限几何案例；所有距离均为尚未标定的图形单位U。"""
from __future__ import annotations

import math


CASE = {
    "id": "03_cuff_width",
    "title": "袖口展开宽增加10U",
    "intent": (
        "只把内圈袖口展开宽增加10U，左端外放5U、右端外放5U。"
        "腋下及以上保持不变，向袖口平顺增加横向放量；"
        "袖口、相关低位辅助线、定位点和文字同步，前后衣身与领条保持原样。"
    ),
    "affected_pieces": ["袖片"],
    "preserve_pieces": ["前片", "后片", "领条"],
    "operation": "ADJUST_CUFF",
    "parameters": {"展开宽增量": 10.0, "左右端点各放量": 5.0, "单位": "U"},
}


def _points(piece):
    """仅枚举当前裁片内实际坐标对象，不改接口或其他派生字段。"""
    seen = set()
    for curve in piece["线条"]:
        for point in curve["点位"]:
            if id(point) not in seen:
                seen.add(id(point))
                yield point
    for point in piece["定位点"].values():
        if id(point) not in seen:
            seen.add(id(point))
            yield point
    for text in piece["文字"]:
        point = text["位置"]
        if id(point) not in seen:
            seen.add(id(point))
            yield point


def edit(model):
    """就地修改袖片几何，保持y、袖纵线、上部及所有其他裁片不变。

    横向位移在左端、中线、右端连续插值，并在左右端之外保持端点位移。
    因此端点准确各移5U，中线仍为x=0，内部两段袖口不会因正负号分支
    产生缺口。竖向权重采用三次平滑过渡；低位辅助线带内采用同一放量，
    保持折边深度和相互位置。这里不认定任何未确认的工艺角色。
    """
    piece = model["完整二维几何"]["袖片"]
    landmarks = piece["定位点"]
    left = float(landmarks["袖口图面左端点"]["横"])
    right = float(landmarks["袖口图面右端点"]["横"])
    cuff_y = float(landmarks["袖口横线中间连接点"]["高"])
    middle = float(landmarks["袖口横线中间连接点"]["横"])
    axilla = min(
        float(landmarks["袖片图面左侧腋下点"]["高"]),
        float(landmarks["袖片图面右侧腋下点"]["高"]),
    )
    delta = float(CASE["parameters"]["展开宽增量"])
    values = (left, right, middle, cuff_y, axilla, delta)
    if not all(math.isfinite(value) for value in values):
        raise ValueError("袖口案例的坐标和增量必须为有限数值")
    if not left < middle < right or axilla <= cuff_y:
        raise ValueError("袖口左右端、中线或腋下锚点次序不合法")
    half_delta = delta / 2.0
    if middle - left + half_delta <= 0 or right - middle + half_delta <= 0:
        raise ValueError("袖口调整将导致一侧宽度非正，拒绝生成几何")

    # 当前基准在袖口上方15U和18.000031U处有水平低位辅助线。
    # 从几何识别这个局部带，不将“用途待核对”的线批准为生产折边线。
    horizontal_low_lines = []
    for curve in piece["线条"]:
        ys = [float(point["高"]) for point in curve["点位"]]
        if max(ys) - min(ys) <= 1e-6 and cuff_y <= ys[0] <= cuff_y + (axilla - cuff_y) * 0.1:
            horizontal_low_lines.append(ys[0])
    lower_band_top = max(horizontal_low_lines, default=cuff_y)
    if lower_band_top >= axilla:
        raise ValueError("袖口低位带与腋下锚点没有可用过渡区")

    def vertical_weight(y):
        if y >= axilla:
            return 0.0
        if y <= lower_band_top:
            return 1.0
        t = (axilla - y) / (axilla - lower_band_top)
        return t * t * (3.0 - 2.0 * t)

    def horizontal_weight(x):
        if x <= left:
            return -1.0
        if x >= right:
            return 1.0
        if x <= middle:
            return (x - middle) / (middle - left)
        return (x - middle) / (right - middle)

    changed = 0
    for point in _points(piece):
        x, y = float(point["横"]), float(point["高"])
        if not math.isfinite(x) or not math.isfinite(y):
            raise ValueError("袖片含非有限坐标")
        shift = half_delta * horizontal_weight(x) * vertical_weight(y)
        new_x = round(x + shift, 6)
        if new_x != x:
            point["横"] = new_x
            changed += 1
    after_left = landmarks["袖口图面左端点"]["横"]
    after_right = landmarks["袖口图面右端点"]["横"]
    return {
        "锚点": {
            "袖口左端改前横坐标": left,
            "袖口左端改后横坐标": after_left,
            "袖口右端改前横坐标": right,
            "袖口右端改后横坐标": after_right,
            "袖口宽改前": round(right - left, 6),
            "袖口宽改后": round(after_right - after_left, 6),
            "中间连接点横坐标": middle,
            "袖口高度": cuff_y,
            "全量放量带上界": lower_band_top,
            "不变区下界": axilla,
            "单位": "U",
        },
        "改变横坐标的点对象数": changed,
        "处理说明": (
            "左端、中间连接点和右端之间连续插值，边外采用饱和位移；"
            "低位带全量外放，到腋下采用smoothstep衰减。所有高度、中线及上部保持，"
            "相关辅助线与文字使用相同映射。该案例仅执行已声明U单位几何目标。"
        ),
    }
