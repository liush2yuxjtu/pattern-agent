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
            target = folder / f"{name}.png"
            reported = std_view(view, str(target), 0, 960, 960, True)
            image = first_file(str(target)) or first_file(reported)
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
    motion = root / "motion.mtn"
    direct_avatar_verified = request["project_checks"].get("use_fbx_avatar") is True
    seed = str(root / "seed.zprj")
    if hasattr(import_api, "ImportZprj") and hasattr(ApiTypes, "ImportZPRJOption"):
        project_options = ApiTypes.ImportZPRJOption()
        project_options.bAppend = False
        project_options.bLoadGarment = True
        project_options.bLoadAvatar = motion.is_file() or not direct_avatar_verified
        require(import_api.ImportZprj(seed, project_options), "CLO 未打开起始工程")
    else:
        require(not direct_avatar_verified or motion.is_file(),
                "此版本不能无原人台读入 .zprj，直接 FBX 会加入第二个人台")
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
    expected_seams = checks.get("seam_group_count")
    get_seam_count = getattr(pattern_api, "GetSeamlinePairGroupCount", None)
    seam_groups = get_seam_count() if get_seam_count else None
    receipt["seam_group_count"] = seam_groups
    receipt["project_checks_pass"] = (bool(expected) and set(expected) == set(actual)
        and all(abs(actual[name] - value) <= tolerance for name, value in expected.items())
        and all(piece["seams"] for piece in pieces)
        and (expected_seams is None or seam_groups == expected_seams))
    require(bool(pieces), "起始工程没有读取到裁片")

    receipt["stage"] = "project_readback"
    write(result / "receipt.json", receipt)
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
        require(direct_avatar_verified,
                "需要同一尺码的已验证 FBX 人台，或用于原人台的 CLO MTN 动作")
        receipt["avatars_before_fbx"] = list(export_api.GetAvatarNameList())
        require(not receipt["avatars_before_fbx"], "仅载入服装的工程仍包含原人台")
        options.bAdd = True
        options.bAutoTranslate = False
        options.bMoveGarment = False
        options.scale = checks.get("fbx_scale", 1.0)
        if checks.get("fbx_blend_shapes"):
            require(hasattr(options, "bCreateAvatarBlendShapeAnimation"),
                    "此 CLO 版本未提供 FBX 形变动画导入选项")
            options.bCreateAvatarBlendShapeAnimation = True
        require(import_api.ImportFBX(str(root / "motion.fbx"), options), "CLO 未导入 FBX 动作")
        receipt["avatars_after_fbx"] = list(export_api.GetAvatarNameList())
        require(len(receipt["avatars_after_fbx"]) == 1, "FBX 导入后没有恰好一具匹配人台")
        utility_api.SetShowHideAvatar(True)
    layer_range = (utility_api.GetAnimationLayerFrameRange(0)
                   if hasattr(utility_api, "GetAnimationLayerFrameRange") else
                   (utility_api.GetStartAnimationFrame(), utility_api.GetEndAnimationFrame()))
    first, last = map(round, layer_range)
    receipt["import_timeline"] = {"first": first, "last": last}
    motion_checks = request["motion_checks"]
    warmup = motion_checks.get("warmup_frames", 0)
    expected_count = motion_checks.get("source_frames")
    action_start = first + warmup
    source_count = last - action_start + 1
    require(last > action_start and (expected_count is None or source_count == expected_count),
            f"CLO 原生时间轴 {action_start}–{last} 与动作帧数 {expected_count} 不一致")
    receipt["stage"] = "motion_imported"
    write(result / "receipt.json", receipt)
    utility_api.SetCurrentAnimationFrame(first)
    utility_api.SetStartAnimationFrame(first)
    utility_api.SetEndAnimationFrame(last)
    if "native_simulation_quality" in motion_checks:
        utility_api.SetSimulationQuality(*motion_checks["native_simulation_quality"])
        receipt["simulation_quality"] = utility_api.GetSimulationQuality()
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
    receipt["recording"] = {"project": project.name, "source_frames": source_count,
                            "last_frame": source_count - 1, "native_action_start": action_start,
                            "native_action_end": last}
    if hasattr(utility_api, "GetAnimationLayerFrameRange"):
        receipt["recording"]["native_layers"] = [utility_api.GetAnimationLayerFrameRange(i)
                                                 for i in range(2)]
    fps = motion_checks["fps"]
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
    for index in sorted({*request["frames"], source_count - 1}):
        require(index < source_count, f"抽查帧 {index} 超出 CLO 原生时间轴")
        move = getattr(utility_api, "MoveAnimationFrame", utility_api.SetCurrentAnimationFrame)
        native_frame = action_start + index
        move(native_frame)
        utility_api.Refresh3DWindow()
        require(round(utility_api.GetCurrentAnimationFrame()) == native_frame,
                f"CLO 时间轴无法定位到 {index}")
        folder = result / f"native-{index:06}"
        folder.mkdir(exist_ok=True)
        mesh = first_file(export_api.ExportGLTF(str(folder / "cloth.gltf"), options, True))
        maps = capture_views(result, folder, index)
        receipt["frames"].append({"index": index, "native_frame": native_frame,
                                  "seconds": index / fps, "maps": maps,
                                  "cloth_mesh": mesh.relative_to(result).as_posix() if mesh else None})
        write(result / "receipt.json", receipt)
    if hasattr(ApiTypes, "VideoExportOption"):
        video_options = ApiTypes.VideoExportOption()
        video_options.width = 1280
        video_options.height = 720
        video_options.fps = {24: 0, 25: 1, 30: 2, 60: 3}.get(fps, -1)
        video_options.startFrame = action_start
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
        receipt["stage"] = "captured"
    except Exception as error:
        receipt["reason"] = str(error)
        write(result / "native-error.json", traceback.format_exc())
    finally:
        write(result / "receipt.json", receipt)
        (result / "native.done").touch()
