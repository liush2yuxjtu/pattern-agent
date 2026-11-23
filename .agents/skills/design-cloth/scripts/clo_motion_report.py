"""Render synchronized CLO evidence for visual and statistical review."""
import csv
import json
from html import escape
from pathlib import Path
import re
import subprocess
from tempfile import TemporaryDirectory


def executable():
    import shutil

    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        return ffmpeg
    from imageio_ffmpeg import get_ffmpeg_exe
    return get_ffmpeg_exe()


def video_duration(path):
    process = subprocess.run([executable(), "-hide_banner", "-i", str(path)],
                             capture_output=True, text=True)
    match = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", process.stderr)
    if not match or "Video:" not in process.stderr:
        raise ValueError(f"无法读取原生录制视频 {path.name}")
    h, m, s = map(float, match.groups())
    return h * 3600 + m * 60 + s


def write_csv(path, fields, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def card(folder, frame, request, reference, api):
    from PIL import Image, ImageDraw, ImageFont, ImageOps

    titles = {"pressure": "试身压力", "stress": "应力", "strain": "应变",
              "appearance": "试穿效果与设计稿", "fold": "褶皱折角"}
    number = frame["index"]
    maps = frame.get("maps", {})
    points = {key: api["evidence_path"](folder, panel.get("point_image"))
              for key, panel in maps.items() if panel.get("frame") == number and panel.get("point_image")}
    proof_height = 50 if any(points.values()) else 0
    sheet = Image.new("RGB", (1584, 1008 + proof_height), "#132028")
    draw = ImageDraw.Draw(sheet)
    fonts = ("/System/Library/Fonts/Hiragino Sans GB.ttc",
             "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")
    font_path = next((path for path in fonts if Path(path).exists()), "DejaVuSans.ttf")
    regular = ImageFont.truetype(font_path, 24)
    small = ImageFont.truetype(font_path, 18)
    source = frame.get("seconds")
    time = f"{source:.2f}s" if api["finite"](source) else "待补"
    native = frame.get("native_frame", number)
    draw.text((20, 15), f"{request['size']} / {request['label']} / 动作帧 {number} / CLO 帧 {native} / {time}",
              font=regular, fill="white")
    for index, (key, label) in enumerate(titles.items()):
        x, y = 20 + (index % 3) * 520, 62 + (index // 3) * (465 + proof_height)
        panel = maps.get(key, {})
        path = api["evidence_path"](folder, panel.get("image")) if panel.get("frame") == number else None
        draw.text((x, y), label, font=regular, fill="white")
        value = panel.get("value")
        source_label = panel.get("source") or "来源待核对"
        notes = f"{value:.3g} {panel.get('unit', '')}" if api["finite"](value) else "读数待补"
        images = [path]
        if key == "appearance":
            native_views = [api["evidence_path"](folder, panel.get("views", {}).get(view))
                            for view in ("back", "side")] if path else [None, None]
            images = [path, *native_views, reference if reference.is_file() else None]
            notes = "正面 / 背面 / 侧面 / 设计稿"
        columns = 2 if key == "appearance" else 1
        width = 500 // columns
        height = 385 // columns
        for slot, image in enumerate(images):
            left, top = x + (slot % columns) * width, y + 35 + (slot // columns) * height
            draw.rectangle((left, top, left + width - 8, top + height - 5), fill="#1f3039")
            try:
                if image is None:
                    raise FileNotFoundError()
                with Image.open(image) as picture:
                    tile = ImageOps.contain(picture.convert("RGB"), (width - 10, height - 8))
                    sheet.paste(tile, (left + (width - tile.width) // 2,
                                       top + (height - tile.height) // 2))
            except OSError:
                draw.text((left + 8, top + 8), "图像待补证", font=small, fill="#ffd5a4")
        caption = f"{notes} · {source_label}"
        point = points.get(key)
        if point:
            try:
                with Image.open(point) as picture:
                    proof = ImageOps.contain(picture.convert("RGB"), (186, 62))
                sheet.paste(proof, (x + 310, y + 422))
                label = "同帧应变增量" if key == "strain" else "同帧复读"
                caption = f"{label} {notes}\n{source_label}"
            except OSError:
                pass
        draw.multiline_text((x, y + 426), caption, font=small, fill="#cfdee2", spacing=3)
    path = folder / f"frame-{number:06}.jpg"
    sheet.save(path, quality=92)
    return path


def browser_video(source):
    target = source.parent / "review-clip.mp4"
    latest_input = max(source.stat().st_mtime_ns, Path(__file__).stat().st_mtime_ns)
    if target.is_file() and target.stat().st_mtime_ns >= latest_input:
        return target
    temporary = target.with_suffix(".tmp.mp4")
    subprocess.run([executable(), "-v", "error", "-y", "-i", str(source), "-an",
                    "-vf", "scale=1280:720:force_original_aspect_ratio=decrease,"
                    "pad=1280:720:(ow-iw)/2:(oh-ih)/2,format=yuv420p",
                    "-r", "30", "-c:v", "libx264", "-preset", "fast", "-movflags", "+faststart", str(temporary)],
                   capture_output=True, text=True, check=True)
    temporary.replace(target)
    return target


def join_videos(out, clips):
    published = {}
    for size, paths in clips.items():
        if not paths:
            continue
        with TemporaryDirectory(dir=out) as temporary:
            temporary = Path(temporary)
            segments = []
            for index, path in enumerate(paths):
                segment = temporary / f"{index:02}.mp4"
                segment.symlink_to(path.resolve())
                segments.append(segment)
            concat = temporary / "list.txt"
            concat.write_text("".join(f"file {path.name}\n" for path in segments), encoding="utf-8")
            video = out / f"CLO-{size}.mp4"
            combined = temporary / video.name
            subprocess.run([executable(), "-v", "error", "-y", "-f", "concat", "-safe", "1",
                            "-i", str(concat), "-c", "copy", "-movflags", "+faststart", str(combined)],
                           capture_output=True, text=True, check=True)
            if video_duration(combined) > 0:
                combined.replace(video)
                published[size] = video.name
    return published


def publish(out, cases, batch):
    api = vars(batch)
    rows, details, sections = [], [], []
    clips = {size: [] for size in batch.SIZES}
    review_record = out / "visual-review.json"
    decisions = json.loads(review_record.read_text(encoding="utf-8")) if review_record.is_file() else {}
    for folder, request, files in cases:
        result = batch.review(folder, request)
        missing_inputs = [key for key, checksum in request["files"].items() if checksum is None]
        missing = result["issues"] + [f"缺少输入 {key}" for key in missing_inputs]
        error = folder / "blocked.txt"
        if error.is_file():
            missing.append(error.read_text(encoding="utf-8").strip())
        row = {"尺码": request["size"], "动作": request["motion"], "名称": request["label"],
               "原生帧数": result.get("source_frames"), "抽查帧数": len(result["frames"]),
               "统计判定": "BLOCKED" if missing_inputs else result["status"],
               "目视判定": "待复核" if result["frames"] else "待取证",
               "VM": result.get("boat_id"), "CLO": result.get("clo_version")}
        decision = decisions.get(request["fingerprint"], {})
        if (result["frames"] and decision.get("status") in {"PASS", "FAIL"}
                and str(decision.get("notes", "")).strip()):
            row["目视判定"] = decision["status"]
        row["目视备注"] = decision.get("notes", "")
        row["指纹"] = request["fingerprint"]
        duration = None
        video = batch.evidence_path(folder, result.get("video"))
        if video:
            try:
                video = browser_video(video)
                duration = video_duration(video)
                if any(not batch.finite(frame.get("seconds")) or frame["seconds"] > duration + 0.1
                       for frame in result["frames"]):
                    raise ValueError("快照时间超出视频")
            except (ValueError, OSError, subprocess.CalledProcessError) as problem:
                missing.append(str(problem))
                row["统计判定"] = "BLOCKED"
                video = None
        if video:
            clips[request["size"]].append(video)
        cards = []
        for frame in batch.key_frames(result, request):
            relative = card(folder, frame, request, files["design"], api).relative_to(out)
            seconds = frame.get("seconds")
            cards.append((frame["index"], str(relative), seconds))
        images = {index: image for index, image, _ in cards}
        for frame in result["frames"]:
            index, seconds = frame["index"], frame.get("seconds")
            details.append({
                "尺码": request["size"], "动作": request["motion"], "CLO帧": index, "秒": seconds,
                "快照": images.get(index, ""),
                "视频": f"{video.relative_to(out)}#t={seconds:.3f}" if video and batch.finite(seconds) else "",
                **{key: batch.read_value(frame, key) for key in (*batch.UNITS, "crossings", "coverage")},
            })
        for key in (*batch.UNITS, "crossings", "coverage"):
            samples = [(batch.read_value(frame, key), frame["index"]) for frame in result["frames"]]
            valid = [(value, index) for value, index in samples if batch.finite(value)]
            value, index = max(valid, default=(None, None))
            row[key] = value
            row[key + "_frame"] = index
        row["快照"] = " | ".join(item[1] for item in cards)
        row["视频"] = str(video.relative_to(out)) if video else ""
        row["关键帧时间（秒）"] = " | ".join(f"{i}:{seconds:.3f}" for i, _, seconds in cards
                                             if batch.finite(seconds))
        row["问题"] = " | ".join(dict.fromkeys(missing))
        rows.append(row)
        title = escape(f"{row['尺码']} · {row['动作']} {row['名称']}")
        body = [f"<section><h2>{title}</h2><p>{escape(row['统计判定'])} · {escape(row['目视判定'])}</p>"]
        if missing:
            body.append(f"<p>{escape(row['问题'])}</p>")
        body.append('<div class="cards">')
        for index, image, seconds in cards:
            seek = (f'<a href="{escape(row["视频"])}#t={seconds:.3f}">视频定位 {seconds:.2f}s</a>'
                    if video and batch.finite(seconds) else "")
            body.append(f'<figure><a href="{escape(image)}"><img loading="lazy" src="{escape(image)}" '
                        f'alt="{title} CLO 帧 {index}"></a><figcaption>帧 {index} {seek}</figcaption></figure>')
        body.append("</div>")
        if video:
            body.append(f'<video controls preload="none" src="{escape(row["视频"])}"></video>')
        body.append("</section>")
        sections.append("".join(body))
    write_csv(out / "stats.csv", rows[0].keys(), rows)
    fields = ("尺码", "动作", "CLO帧", "秒", "快照", "视频", *batch.UNITS, "crossings", "coverage")
    write_csv(out / "frames.csv", fields, details)
    page = """<!doctype html><html lang="zh-CN"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>CLO 四尺码十动作复验</title><style>
body{font:16px system-ui;margin:24px auto;max-width:1140px;padding:0 16px;background:#111b22;color:#eef5f6}
a{color:#a5dfef} video,img{width:100%;display:block} video{max-width:720px}
figure{margin:0 0 20px}.cards{display:grid;gap:16px;grid-template-columns:repeat(auto-fit,minmax(min(100%,420px),1fr))}
section{padding:8px 0 20px;border-bottom:1px solid #476270}</style>
<h1>CLO 四尺码十动作复验</h1><p><a href="stats.csv">统计表</a> · <a href="frames.csv">关键帧索引</a></p>"""
    videos = join_videos(out, clips)
    overview = "<nav>" + " · ".join(f'<a href="{path}">{size} 码视频</a>'
                                       for size, path in videos.items()) + "</nav>"
    (out / "index.html").write_text(page + overview + "".join(sections) + "</html>\n", encoding="utf-8")
    return ("FAIL" if any("FAIL" in (row["统计判定"], row["目视判定"]) for row in rows)
            else "PASS" if all(row["统计判定"] == row["目视判定"] == "PASS" for row in rows)
            else "BLOCKED")
