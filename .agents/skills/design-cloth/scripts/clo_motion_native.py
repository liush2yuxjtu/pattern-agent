"""Run inside the CLO Python Script editor on an isolated Boat worker."""
import json
from pathlib import Path
import time
import traceback

import ApiTypes
import export_api
import import_api
import pattern_api
import utility_api


def write(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def first_file(returned):
    if isinstance(returned, (tuple, list)):
        for item in returned:
            path = first_file(item)
            if path:
                return path
    elif returned and Path(returned).is_file() and Path(returned).stat().st_size:
        return Path(returned)
    return None


def capture_views(result, folder, frame):
    maps = {}
    thumbnail = getattr(export_api, "ExportThumbnail3D", None)
    std_view = getattr(export_api, "ExportStdViewImage", None)
    if std_view:
        views = {}
        for name, view in (("front", 2), ("back", 8), ("side", 4)):
            image = first_file(std_view(view, str(folder / f"{name}.png"), 0, 960, 960, True))
            if image and image.is_relative_to(result):
                views[name] = image.relative_to(result).as_posix()
        if "front" in views:
            maps["appearance"] = {"frame": frame, "image": views["front"],
                                  "views": views, "source": "CLO native"}
    for name, suffix in (("stress", "Stress"), ("strain", "Strain")):
        setter = getattr(utility_api, f"Set{suffix}MapStatus", None)
        getter = getattr(utility_api, f"Get{suffix}MapStatus", None)
        if not thumbnail or not setter or not getter:
            continue
        try:
            setter(True)
            utility_api.Refresh3DWindow()
            if getter():
                image = first_file(thumbnail(str(folder / f"{name}.png")))
                if image and image.is_relative_to(result):
                    maps[name] = {"frame": frame, "image": image.relative_to(result).as_posix(),
                                  "source": "CLO native visual"}
        finally:
            setter(False)
    return maps


def raw_capture(root, result, request, receipt):
    required = (
        "GetStartAnimationFrame", "GetEndAnimationFrame", "SetCurrentAnimationFrame",
        "GetCurrentAnimationFrame", "SetAnimationRecording",
    )
    require(all(callable(getattr(utility_api, method, None)) for method in required),
            "此 CLO 版本缺少 Python 动作录制或时间轴 API")
    seed = str(root / "seed.zprj")
    if hasattr(import_api, "ImportZprj") and hasattr(ApiTypes, "ImportZPRJOption"):
        project_options = ApiTypes.ImportZPRJOption()
        project_options.bAppend = False
        project_options.bLoadGarment = True
        project_options.bLoadAvatar = True
        require(import_api.ImportZprj(seed, project_options), "CLO 未打开起始工程")
    else:
        require(import_api.ImportFile(seed), "CLO 未打开起始工程")
    count = pattern_api.GetPatternCount()
    pieces = [{"name": pattern_api.GetPatternPieceName(index),
               "area_mm2": pattern_api.GetPatternPieceArea(index),
               "seams": pattern_api.GetSeamlinePairGroupListInPattern(index)}
              for index in range(count)]
    receipt["project_readback"] = pieces
    checks = request["project_checks"]
    expected = checks.get("pieces_mm2", {})
    actual = {piece["name"]: piece["area_mm2"] for piece in pieces}
    tolerance = checks.get("area_tolerance_mm2", 0)
    receipt["project_checks_pass"] = (bool(expected) and set(expected) == set(actual)
        and all(abs(actual[name] - value) <= tolerance for name, value in expected.items())
        and all(piece["seams"] for piece in pieces))
    require(bool(pieces), "起始工程没有读取到裁片")

    receipt["stage"] = "project_readback"
    write(result / "receipt.json", receipt)
    motion = root / "motion.mtn"
    if motion.is_file():
        require(import_api.ImportFile(str(motion)), "CLO 未导入 MTN")
    else:
        options = ApiTypes.ImportExportOption()
        if hasattr(options, "bCreateAvatarJointAnimation"):
            options.bCreateAvatarJointAnimation = True
        elif hasattr(options, "bCreateAnimation"):
            options.bCreateAnimation = True
        else:
            raise RuntimeError("此 CLO 版本未提供 FBX 关节动画导入选项")
        options.bAdd = True
        options.bMoveGarment = True
        require(import_api.ImportFBX(str(root / "motion.fbx"), options), "CLO 未导入 FBX 动作")
    layer_range = (utility_api.GetAnimationLayerFrameRange(0)
                   if hasattr(utility_api, "GetAnimationLayerFrameRange") else
                   (utility_api.GetStartAnimationFrame(), utility_api.GetEndAnimationFrame()))
    first, last = map(round, layer_range)
    receipt["import_timeline"] = {"first": first, "last": last}
    expected_count = request["motion_checks"].get("source_frames")
    require(last > first and (expected_count is None or last - first + 1 == expected_count),
            f"CLO 原生时间轴 {first}–{last} 与动作帧数 {expected_count} 不一致")
    receipt["stage"] = "motion_imported"
    write(result / "receipt.json", receipt)
    utility_api.SetCurrentAnimationFrame(first)
    receipt["stage"] = "native_recording"
    write(result / "receipt.json", receipt)
    if hasattr(utility_api, "RunAnimationRecording"):
        utility_api.RunAnimationRecording(first, last)
    else:
        utility_api.SetAnimationRecording(True)
    deadline = time.monotonic() + request.get("native_record_timeout_seconds", 600)
    try:
        while round(utility_api.GetCurrentAnimationFrame()) < last:
            require(time.monotonic() < deadline, "CLO 原生录制超过时限或时间轴未推进")
            utility_api.Refresh3DWindow()
            time.sleep(0.1)
    finally:
        utility_api.SetAnimationRecording(False)

    project = first_file(export_api.ExportZPrj(str(result / "recorded.zprj")))
    require(project, "CLO 未保存录制工程")
    receipt["recording"] = {"project": project.name, "source_frames": last - first + 1,
                            "last_frame": last - first}
    fps = request["motion_checks"]["fps"]
    options = ApiTypes.ImportExportOption()
    options.bExportGarment = True
    options.bExportAvatar = False
    options.bThin = True
    options.bEmbedded = True
    options.bSingleObject = True
    options.bClothUnifiedUVCoordinates = False
    options.bUnifiedUVCoordinates = False
    options.scale = 0.001
    options.axisX, options.axisY, options.axisZ = 0, 1, 2
    for index in sorted({*request["frames"], last - first}):
        require(index <= last - first, f"抽查帧 {index} 超出 CLO 原生时间轴")
        utility_api.SetCurrentAnimationFrame(first + index)
        utility_api.Refresh3DWindow()
        require(round(utility_api.GetCurrentAnimationFrame()) == first + index,
                f"CLO 时间轴无法定位到 {index}")
        folder = result / f"native-{index:06}"
        folder.mkdir(exist_ok=True)
        mesh = first_file(export_api.ExportGLTF(str(folder / "cloth.gltf"), options, True))
        maps = capture_views(result, folder, index)
        receipt["frames"].append({"index": index, "seconds": index / fps, "maps": maps,
                                  "cloth_mesh": mesh.relative_to(result).as_posix() if mesh else None})
        write(result / "receipt.json", receipt)
    if hasattr(ApiTypes, "VideoExportOption"):
        video_options = ApiTypes.VideoExportOption()
        video_options.width = 1280
        video_options.height = 720
        video_options.fps = {24: 0, 25: 1, 30: 2, 60: 3}.get(fps, -1)
        video_options.startFrame = first
        video_options.endFrame = last
        video = first_file(export_api.ExportAnimationVideo(str(result / "native.avi"), video_options))
        if video:
            receipt["video"] = video.relative_to(result).as_posix()


def main(working_root, boat_id, clo_version):
    root = Path(working_root)
    result = root / "result"
    result.mkdir(exist_ok=True)
    request = json.loads((root / "request.json").read_text(encoding="utf-8"))
    receipt = {"engine": "CLO 3D", "boat_id": boat_id, "clo_version": clo_version,
               "fingerprint": request["fingerprint"], "frames": []}
    receipt["available_apis"] = {
        module.__name__: {name: getattr(module, name).__doc__ for name in dir(module)
                          if any(key in name.lower() for key in
                                 ("animation", "pressure", "stress", "strain", "snapshot", "view", "motion", "fbx"))}
        for module in (utility_api, export_api, import_api)
    }
    try:
        raw_capture(root, result, request, receipt)
    except Exception as error:
        receipt["reason"] = str(error)
        write(result / "native-error.json", traceback.format_exc())
    finally:
        write(result / "receipt.json", receipt)
        (result / "native.done").touch()
