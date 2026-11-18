"""A bounded, graphic-unit sleeve extension derived from the Chinese case intent.

The cuffs' low parallel-line band translates rigidly; the remaining lower sleeve
extends monotonically into a fixed underarm.  No physical-unit or workmanship
approval is inferred from the geometry.
"""
from __future__ import annotations

import math


CASE = {
    "id": "01_sleeve_length",
    "title": "袖片下段加长20U",
    "intent": (
        "仅把袖片袖口向下延伸20U。袖山、腋下及以上保持不变，"
        "从腋下到内圈袖口逐渐增加长度；袖口、折边、定位点、内部线和文字同步。"
        "前后衣身及领条全部保持。"
    ),
    "affected_pieces": ["袖片"],
    "preserve_pieces": ["前片", "后片", "领条"],
    "operation": "ADJUST_LENGTH",
    "parameters": {
        "extension": 20.0,
        "unit": "U",
        "direction": "图面高度负方向",
        "transition": "固定腋下至袖口近平行线带之间的单调三次平滑过渡",
        "bottom_band": "当前近袖口水平内部线以下整体平移，保留线带相对间距",
    },
}


def _curve(part: dict, name: str) -> dict:
    matches = [line for line in part["线条"] if line["名称"] == name]
    if len(matches) != 1:
        raise ValueError(f"袖长案例需要唯一命名线：{name}")
    return matches[0]


def _line_length(points: list[dict]) -> float:
    return sum(
        math.hypot(b["横"] - a["横"], b["高"] - a["高"])
        for a, b in zip(points, points[1:])
    )


def edit(model: dict, delta: float = 20.0) -> dict:
    """Edit only sleeve geometry, returning the anchors actually used.

    All points at/above the lower underarm stay exactly fixed.  The extension is
    a function of height alone, so duplicate endpoints continue to coincide and
    horizontal cuff/reference lines stay horizontal.  Clamping the translation
    below the low internal-line band avoids the -0.085601-U longitudinal-line
    overshoot and preserves the cuff-region offsets.
    """
    part = model["完整二维几何"]["袖片"]
    landmarks = part["定位点"]
    left_underarm = landmarks["袖片图面左侧腋下点"]
    right_underarm = landmarks["袖片图面右侧腋下点"]
    cuff_center = landmarks["袖口横线中间连接点"]
    fixed_height = min(left_underarm["高"], right_underarm["高"])
    cuff_height = cuff_center["高"]
    extension = delta
    if not math.isfinite(extension) or extension == 0:
        raise ValueError("袖长变化量须为有限非零数")
    if not fixed_height > cuff_height:
        raise ValueError("袖口必须位于腋下以下")

    near_cuff_lines = []
    for line in part["线条"]:
        if not line["名称"].startswith("袖片内部折线"):
            continue
        points = line["点位"]
        heights = [point["高"] for point in points]
        if (
            max(heights) - min(heights) <= 1e-6
            and cuff_height <= heights[0] < cuff_height + 0.1 * (fixed_height - cuff_height)
        ):
            near_cuff_lines.append(heights[0])
    if not near_cuff_lines:
        raise ValueError("未识别到本案例需要保持相对间距的近袖口水平内部线")
    rigid_band_top = max(near_cuff_lines)
    if not cuff_height <= rigid_band_top < fixed_height:
        raise ValueError("袖口刚性平移区与腋下固定区冲突")

    if fixed_height - rigid_band_top <= 1.5 * -extension:
        raise ValueError("袖长缩短量会造成过渡区翻折")

    longitudinal = _curve(part, "袖片纵向内部线")
    old_length = _line_length(longitudinal["点位"])
    old_cuff_height = cuff_height
    old_vertical_bottom = landmarks["袖纵向内部线下端"]["高"]
    seen: set[int] = set()
    changed_points = 0
    held_points = 0

    def move(point: dict) -> None:
        nonlocal changed_points, held_points
        # A caller may have retained YAML aliases or shared endpoint objects.
        if id(point) in seen:
            return
        seen.add(id(point))
        height = point["高"]
        if not math.isfinite(height) or not math.isfinite(point["横"]):
            raise ValueError("袖片存在非有限坐标")
        if height >= fixed_height:
            held_points += 1
            return
        if height <= rigid_band_top:
            shift = extension
        else:
            fraction = (height - rigid_band_top) / (fixed_height - rigid_band_top)
            smooth = fraction * fraction * (3.0 - 2.0 * fraction)
            shift = extension * (1.0 - smooth)
        value = round(height - shift, 6)
        if value != height:
            changed_points += 1
            point["高"] = value

    for line in part["线条"]:
        for point in line["点位"]:
            move(point)
    for point in landmarks.values():
        move(point)
    for text in part["文字"]:
        move(text["位置"])

    new_length = _line_length(longitudinal["点位"])
    actual_extension = new_length - old_length
    if not math.isclose(actual_extension, extension, abs_tol=1e-6, rel_tol=0):
        raise ValueError("当前几何不能满足袖纵向内部线准确加长目标")
    if not math.isclose(
        landmarks["袖口横线中间连接点"]["高"],
        old_cuff_height - extension,
        abs_tol=1e-6,
        rel_tol=0,
    ):
        raise ValueError("袖口下移未达到意图目标")
    return {
        "anchors": {
            "left_underarm_height": left_underarm["高"],
            "right_underarm_height": right_underarm["高"],
            "fixed_height": fixed_height,
            "rigid_cuff_band_top": rigid_band_top,
            "cuff_height_before": old_cuff_height,
            "cuff_height_after": landmarks["袖口横线中间连接点"]["高"],
            "vertical_line_bottom_before": old_vertical_bottom,
            "vertical_line_bottom_after": landmarks["袖纵向内部线下端"]["高"],
        },
        "measurements": {
            "sleeve_longitudinal_before": round(old_length, 6),
            "sleeve_longitudinal_after": round(new_length, 6),
            "actual_extension": round(actual_extension, 6),
            "unit": "U",
        },
        "changed_geometry_points": changed_points,
        "fixed_geometry_points": held_points,
        "explanation": (
            "以较低腋下为固定高度，袖口近平行内部线带按请求整体平移，"
            "中段采用单调平滑过渡；全部线条、定位点与文字位置使用同一高度变换。"
            "袖纵线略低于袖口的端点采用同量平移，避免微量超伸；"
            "图形单位U保持，生产工艺角色仍待确认。"
        ),
    }
