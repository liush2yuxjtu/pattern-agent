"""前后衣身各缩短15U，保持腰线以上及整个低位下摆带。

只执行本案例明确的图形单位编辑；不改变材料、净裁角色或工艺批准值。
"""
from math import hypot, isfinite


CASE = {
    "id": "02_body_length",
    "title": "前后衣身各缩短15U",
    "intent": (
        "前后衣身各缩短15U。腰线及以上保持，下摆和关联折边整体上移15U并保持形状，"
        "腰至下摆带之间平顺过渡；内部线、定位点和文字同步。袖片与领条全部保持。"
    ),
    "affected_pieces": ["前片", "后片"],
    "preserve_pieces": ["袖片", "领条"],
    "operation": "ADJUST_LENGTH",
    "parameters": {
        "unit": "U",
        "delta_length_U": -15.0,
        "hem_translation_y_U": 15.0,
        "waist_and_above_locked": True,
        "hem_band_rigid": True,
        "transition": "三次smoothstep，过渡带两端位移斜率为零",
    },
}


def _points(part):
    """定位、线条和文字共享同一变换；重复对象只处理一次。"""
    seen = set()
    for point in [
        *part["定位点"].values(),
        *(p for line in part["线条"] for p in line["点位"]),
        *(text["位置"] for text in part["文字"]),
    ]:
        if id(point) not in seen:
            seen.add(id(point))
            yield point


def _length(points):
    return sum(hypot(b["横"] - a["横"], b["高"] - a["高"])
               for a, b in zip(points, points[1:]))


def _waist(part):
    points = [p for name, p in part["定位点"].items() if "腰" in name]
    if len(points) != 2 or abs(points[0]["高"] - points[1]["高"]) > 1e-6:
        raise ValueError("本案例需要同高的左右腰线定位点")
    return (points[0]["高"] + points[1]["高"]) / 2.0


def _hem_band(part, waist):
    """从本基准低位完整线条识别下摆/平行内部线带，不解释其生产角色。

    基准原点在内圈下摆中点。只取整条都位于下摆到腰线最低三分之一
    的已有曲线，故不会把跨越过渡带的侧边纳入刚性区。
    """
    hem_lines = [line for line in part["线条"] if "下摆弧线" in line["名称"]]
    if len(hem_lines) != 2:
        raise ValueError("本案例需要两段命名下摆弧线")
    low = min(p["高"] for line in hem_lines for p in line["点位"])
    limit = low + (waist - low) / 3.0
    band = [line for line in part["线条"]
            if max(p["高"] for p in line["点位"]) <= limit]
    if not band or any(line not in band for line in hem_lines):
        raise ValueError("无法完整识别下摆刚性带")
    return max(p["高"] for line in band for p in line["点位"]), band


def edit(model, delta_length: float = -15.0):
    """就地修改完整二维几何；接口长度等派生字段由公共主程序复算。"""
    if model["单位与坐标"]["坐标单位"] != "U":
        raise ValueError("本案例只接受已声明的U单位")
    delta = -delta_length
    if not isfinite(delta) or delta == 0:
        raise ValueError("衣长变化量须为有限非零数")
    anchors = {}
    for piece in CASE["affected_pieces"]:
        part = model["完整二维几何"][piece]
        waist = _waist(part)
        band_top, band_lines = _hem_band(part, waist)
        span = waist - band_top
        # smoothstep最大导数1.5；此条件保证竖向变换严格单调、不翻折。
        if span <= 1.5 * delta:
            raise ValueError("腰到下摆过渡空间不足，不能保持单调的平顺缩短")
        center_name = "前中纵向内部线" if piece == "前片" else "后中纵向内部线"
        center = next(line for line in part["线条"] if line["名称"] == center_name)
        before_length = _length(center["点位"])
        moved = 0
        for point in _points(part):
            y = point["高"]
            if not isfinite(y) or not isfinite(point["横"]):
                raise ValueError("非有限几何坐标")
            if y >= waist:
                continue
            if y <= band_top:
                offset = delta
            else:
                t = (waist - y) / span
                offset = delta * t * t * (3.0 - 2.0 * t)
            point["高"] = round(y + offset, 6)
            moved += point["高"] != y
        after_length = _length(center["点位"])
        if abs((before_length - after_length) - delta) > 1e-6:
            raise ValueError("中纵线缩短量未达到请求值")
        anchors[piece] = {
            "waist_y_U": round(waist, 6),
            "rigid_hem_band_top_y_U_before": round(band_top, 6),
            "rigid_hem_band_top_y_U_after": round(band_top + delta, 6),
            "rigid_hem_lines": [line["名称"] for line in band_lines],
            "center_line_length_U_before": round(before_length, 6),
            "center_line_length_U_after": round(after_length, 6),
            "center_line_length_delta_U": round(after_length - before_length, 6),
            "minimum_unrounded_vertical_derivative": 1.0 - 1.5 * delta / span,
            "moved_point_objects": moved,
        }
    return {
        "anchors": anchors,
        "explanation": (
            "腰线及以上位移为0；完整低位下摆带按请求整体平移；中间按三次smoothstep过渡。"
            "排版原点、所有横坐标、点数、名称、文字内容、袖片和领条不变。"
            "低位平行内部线只是几何候选，不据此批准其折边或缝份角色。"
        ),
    }
