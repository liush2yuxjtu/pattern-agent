#!/usr/bin/env python3
"""Capture statistics and native Style3D images from a garment or an animation."""
import argparse
import csv
import importlib.util
import json
import math
from pathlib import Path
import sys
import time

source = Path(__file__).with_name("style3d-audit.py")
spec = importlib.util.spec_from_file_location("style3d_audit", source)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)

VIEWS = ("Front", "Back", "Left", "Right", "Upward", "Downward")
MAPS = {
    "strain": ("GetClothStrainMap", "ratio"),
    "stress": ("GetClothStressMap", "kPa"),
    "cloth-pressure": ("GetClothPressureMap", "Pa"),
    "avatar-pressure": ("GetAvatarPressureMap", "Pa"),
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def scene(client):
    diagnostics = client.call("Simulation.GetDiagnostics")
    require(diagnostics["projectLoaded"] and not diagnostics["running"] and not diagnostics["recording"],
            "Open a project and stop simulation and animation recording before capture.")
    project = client.call("Project.GetGarmentInfo")
    pieces = client.call("Pattern.GetAllMainClothPieceIds")["clothPieceIds"]
    avatars = client.call("Avatar.GetAllIds")["avatarIds"]

    def entities(ids):
        return [{"id": identifier, "name": client.call("Entity.GetName", entityId=identifier)["name"]}
                for identifier in ids]

    all_pieces = client.call("Pattern.GetAllClothPieceIds")["clothPieceIds"]
    return {"project": project, "pieces": entities(pieces), "avatars": entities(avatars),
            "otherPieceIds": sorted(set(all_pieces) - set(pieces))}


def select(items, selectors, kind):
    if selectors is None:
        return items
    selected = []
    for key in selectors:
        matches = [entity for entity in items if key in (entity["id"], entity["name"])]
        require(len(matches) == 1, f"Select one {kind} for {key!r}; use a current ID if names repeat.")
        if matches[0] not in selected:
            selected.append(matches[0])
    return selected


def cropped_body(body, cloth):
    """Keep every body triangle whose box overlaps the cloth mesh box."""
    axes = tuple(zip(*cloth["positions"]))
    bounds = tuple((min(axis) - 2, max(axis) + 2) for axis in axes)
    result = {"valid": True, "error": "", "positions": [], "normals": [],
              "faces": [], "patternPositions": []}
    indices = {}
    for face in body["faces"]:
        points = [body["positions"][index] for index in face]
        if any(max(p[i] for p in points) < lo or min(p[i] for p in points) > hi
               for i, (lo, hi) in enumerate(bounds)):
            continue
        mapped = []
        for index in face:
            if index not in indices:
                indices[index] = len(result["positions"])
                result["positions"].append(body["positions"][index])
                result["normals"].append(body["normals"][index])
            mapped.append(indices[index])
        result["faces"].append(mapped)
    return result


def map_statistics(client, kind, entity_id, frame_dir, save_raw):
    method, unit = MAPS[kind]
    arg = "avatarId" if kind == "avatar-pressure" else "clothPieceId"
    result = client.call("Simulation." + method, **{arg: entity_id, "includeMesh": True})
    raw_file = audit.store_raw(frame_dir, f"{kind}-{entity_id}", result) if save_raw else None
    values = result.get("values")
    count = result.get("vertexCount")
    row = {key: result.get(key) for key in ("unit", "vertexCount", "actualValueCount",
                                            "meshFingerprint", "dataFingerprint", "source")}
    row["rawFile"] = raw_file
    valid = (result.get("valid") is True and result.get("status") == "ok"
             and result.get("unit") == unit and isinstance(values, list) and values
             and len(values) == count == result.get("actualValueCount")
             and all(type(v) in (float, int) and math.isfinite(v) for v in values))
    mesh = result.get("mesh") or {}
    valid = (valid and mesh.get("valid") is True and len(mesh.get("positions", [])) == count
             and bool(result.get("meshFingerprint")))
    if not valid:
        return dict(row, status="needs_review",
                    issue=result.get("error") or "Native map validity, units, sample counts or mesh did not match.")
    values = sorted(values)
    if kind == "avatar-pressure" and not any(values):
        return dict(row, status="needs_review", issue="All body pressure readings were zero; inspect native contact evidence.")
    return dict(row, status="captured", minimum=values[0], p95=values[math.floor(0.95 * (count - 1))],
                maximum=values[-1], nonzeroSamples=sum(value != 0 for value in values))


def mesh_snapshot(client, kind, entity_id):
    arg = "avatarId" if kind == "Avatar" else "clothPieceId"
    mesh = client.call(f"Mesh.Get{kind}Snapshot", **{arg: entity_id})["snapshot"]
    require(mesh.get("valid") and mesh["positions"] and mesh["faces"],
            f"{kind} {entity_id} has no usable mesh: {mesh.get('error', '')}")
    return mesh


def capture_images(client, folder, config):
    wanted = config.get("views", ["Front", "Back", "Left", "Right"])
    if not wanted:
        return []
    settings = client.call("Snapshot.GetProject3DImageConfig")["config"]
    settings.update({
        "outputDirectory": str(folder), "widthPixels": config.get("width", 920),
        "heightPixels": config.get("height", 1150), "viewSource": "Enum", "viewOrientations": wanted,
        "customViewFile": "", "fileType": "Png", "renderType": "Normal",
        "useAllColorways": True, "colorwayIds": [], "merge": False, "overwrite": False,
        "nameType": "CustomTextViewName", "customText": "fit", "punctuation": "UnderLine",
    })
    result = client.call("Snapshot.ExportImage3D", config=settings)
    require(result.get("exported"), "Native image export did not report success.")
    images = sorted(path for path in folder.iterdir() if path.suffix.lower() == ".png")
    valid = []
    for path in images:
        with path.open("rb") as stream:
            if stream.read(8) == b"\x89PNG\r\n\x1a\n":
                valid.append(path.name)
    require(len(valid) >= len(wanted), f"Expected images for {len(wanted)} views; found {len(valid)} readable PNG headers.")
    return valid


def capture(client, folder, frame, avatar, pieces, config):
    folder.mkdir()
    issues = []
    row = {"frame": frame, "directory": folder.name, "issues": issues, "pieces": [],
           "snapshots": [], "coverageReview": "pending"}
    maps = config.get("maps", ["strain"])
    save_raw = config.get("saveRaw", False)
    try:
        body = mesh_snapshot(client, "Avatar", avatar["id"])
        if save_raw:
            row["avatarMeshFile"] = audit.store_raw(folder, "avatar-mesh", body)
    except (audit.McpError, KeyError, ValueError) as error:
        body = None
        issues.append(str(error))

    def sample_map(kind, identifier):
        try:
            result = map_statistics(client, kind, identifier, folder, save_raw)
            if result["status"] != "captured":
                issues.append(f"{kind} {identifier}: {result['issue']}")
            return result
        except (audit.McpError, KeyError, ValueError) as error:
            issues.append(str(error))
            return {"status": "needs_review", "issue": str(error)}

    if "avatar-pressure" in maps:
        row["avatarPressure"] = sample_map("avatar-pressure", avatar["id"])
    for piece in pieces:
        identifier = piece["id"]
        evidence = {**piece, "crossings": {"status": "needs_review", "facePairs": None}, "maps": {}}
        row["pieces"].append(evidence)
        try:
            cloth = mesh_snapshot(client, "ClothPiece", identifier)
            evidence["vertexCount"], evidence["faceCount"] = len(cloth["positions"]), len(cloth["faces"])
            if save_raw:
                evidence["meshFile"] = audit.store_raw(folder, "cloth-" + identifier, cloth)
            if body is not None:
                cropped = cropped_body(body, cloth)
                crossing = (client.call("Mesh.QueryCrossings", meshA=cloth, meshB=cropped,
                                        maxResults=config.get("maxCrossings", 6000)) if cropped["faces"]
                            else {"facePairs": [], "truncated": False})
                evidence["crossings"] = {"status": "truncated" if crossing["truncated"] else "captured",
                                         "facePairs": len(crossing["facePairs"]),
                                         "truncated": crossing["truncated"], "avatarFacesTested": len(cropped["faces"])}
                if crossing["truncated"]:
                    issues.append(f"{identifier}: crossing count reached its reporting cap.")
                if save_raw:
                    evidence["crossings"]["rawFile"] = audit.store_raw(folder, "crossings-" + identifier, crossing)
        except (audit.McpError, KeyError, ValueError) as error:
            issues.append(f"{identifier}: {error}")
        for kind in maps:
            if kind != "avatar-pressure":
                evidence["maps"][kind] = sample_map(kind, identifier)
    try:
        row["snapshots"] = capture_images(client, folder, config)
    except (audit.McpError, OSError, KeyError, ValueError) as error:
        issues.append(f"Snapshots: {error}")
    return row


def record_motion(client, avatar, settings):
    require(not client.call("Avatar.GetCurrentAnimationIds", avatarId=avatar)["animationIds"],
            "Recording needs a working project without existing poses or animations on the selected avatar.")
    poses = client.call("Avatar.GetAvatarPoseResources", avatarId=avatar)["names"]
    require(all(item["name"] in poses for item in settings["poses"]),
            f"One or more pose names are unavailable. Available poses: {poses}")
    require(client.call("Avatar.GetAvatarVisible", avatarId=avatar)["visible"],
            "Make the selected avatar visible for the evidence images.")
    client.call("Application.SetEditorMode", mode="Animation", enabled=True)
    for index, item in enumerate(settings["poses"]):
        client.call("Animation.InsertAvatarCurrentPose", avatarId=avatar, index=index,
                    poseName=item["name"], unit=0, preSmoothTime=item.get("transitionSeconds", 0),
                    keepSmoothTime=item.get("holdSeconds", 0.2), nextSmoothTime=0,
                    isMoveToOriginPosition=False)
    client.call("Animation.SetCurrentTrackTime", time=0)
    started = client.call("Animation.StartRecording")
    recording_id = started["recordingId"]
    deadline = time.monotonic() + settings.get("timeoutSeconds", 300)
    try:
        while True:
            status = client.call("Animation.GetRecordingState", recordingId=recording_id)
            if not status["recording"]:
                require(status["status"] == "Stopped" and status["frameCount"] > 0,
                        f"Recording produced no verified timeline commit: {status}")
                return status
            if time.monotonic() >= deadline:
                stopped = client.call("Animation.StopRecording", recordingId=recording_id, save=False)
                raise ValueError(f"Recording timed out; stop requested, recording={stopped['recording']}.")
            time.sleep(1)
    except KeyboardInterrupt:
        stopped = client.call("Animation.StopRecording", recordingId=recording_id, save=False)
        raise ValueError(f"Recording interrupted; stop requested, recording={stopped['recording']}.") from None


def sampled_frames(config, first, last):
    explicit = config.get("frames")
    if explicit == "all":
        return range(first, last + 1)
    if explicit is not None:
        require(all(first <= value <= last for value in explicit),
                f"Frames must lie in the observed range {first}–{last}.")
        return sorted(set(explicit))
    count = config.get("samples", 5)
    return sorted({first + round((last - first) * i / (count - 1)) for i in range(count)})


def validate_config(config):
    require(isinstance(config, dict), "Configuration must be a JSON object.")
    mode = config.get("mode", "timeline")
    require(mode in ("current", "timeline", "record"), "mode must be current, timeline or record.")
    for key, allowed in (("views", VIEWS), ("maps", MAPS)):
        values = config.get(key, [])
        require(isinstance(values, list) and all(isinstance(v, str) and v in allowed for v in values)
                and len(values) == len(set(values)), f"Invalid or duplicate {key} values.")
    for key, minimum, maximum in (("width", 2, 16384), ("height", 2, 16384),
                                   ("samples", 2, 10000), ("maxCrossings", 1, 1000000)):
        if key in config:
            require(type(config[key]) is int and minimum <= config[key] <= maximum,
                    f"{key} must be an integer in [{minimum}, {maximum}].")
    pieces = config.get("pieces")
    require(pieces is None or isinstance(pieces, list) and pieces and
            all(isinstance(item, str) and item for item in pieces), "pieces must be a non-empty list of names or IDs.")
    frames = config.get("frames")
    require(frames is None or frames == "all" or isinstance(frames, list) and frames and
            all(type(i) is int and i >= 0 for i in frames), "frames must be 'all' or a non-empty list of frame indices.")
    for key in ("avatar", "expectedProject", "case"):
        require(config.get(key) is None or isinstance(config[key], str) and config[key], f"{key} must be a string.")
    require(type(config.get("saveRaw", False)) is bool, "saveRaw must be Boolean.")
    if "saveProject" in config:
        name = config["saveProject"]
        require(mode == "record" and isinstance(name, str) and name.endswith(".sproj")
                and "/" not in name and "\\" not in name,
                "saveProject requires record mode and a .sproj filename without a path.")
    if mode == "record":
        require(config.get("expectedProject"), "Recording requires the exact expectedProject name of a working copy.")
        record_settings = config.get("record")
        require(isinstance(record_settings, dict), "record mode needs a record object.")
        poses = record_settings.get("poses")
        require(isinstance(poses, list) and len(poses) >= 2, "Give at least two pose entries to record.")
        for item in poses:
            require(isinstance(item, dict) and isinstance(item.get("name"), str) and item["name"],
                    "Each pose needs an exact native name.")
            for key in ("transitionSeconds", "holdSeconds"):
                value = item.get(key, 0)
                require(type(value) in (int, float) and 0 <= value <= 1000, f"Invalid pose {key}.")
        limit = record_settings.get("timeoutSeconds", 300)
        require(type(limit) in (int, float) and 0 < limit <= 3600, "Invalid recording timeout.")
    return mode


def write_evidence(output, summary):
    crossings = [piece["crossings"] for frame in summary["frames"] for piece in frame["pieces"]]
    counts = [check["facePairs"] for check in crossings if check["facePairs"] is not None]
    summary["totals"] = {
        "sampledFrames": len(summary["frames"]),
        "pieceFrameChecks": len(crossings),
        "checksWithObservedCrossings": sum(count > 0 for count in counts),
        "checksWithMissingOrCappedCounts": sum(check["status"] != "captured" for check in crossings),
        "snapshots": sum(len(frame["snapshots"]) for frame in summary["frames"]),
    }
    with (output / "statistics.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["frame", "piece_id", "piece", "avatar_id", "crossing_status", "crossing_face_pairs",
                         "truncated", "avatar_faces_tested", "strain_status", "strain_p95", "strain_unit",
                         "stress_status", "stress_p95", "stress_unit", "snapshots"])
        for frame in summary["frames"]:
            for piece in frame["pieces"]:
                crossing = piece["crossings"]
                values = [piece["maps"].get(kind, {}) for kind in ("strain", "stress")]
                writer.writerow([frame["frame"], piece["id"], piece["name"], summary["avatar"]["id"],
                                 crossing["status"], crossing.get("facePairs"), crossing.get("truncated"),
                                 crossing.get("avatarFacesTested"),
                                 *[m.get(key) for m in values for key in ("status", "p95", "unit")],
                                 "|".join(f"{frame['directory']}/{name}" for name in frame["snapshots"])])
    temp = output / "summary.tmp"
    temp.write_text(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    temp.replace(output / "summary.json")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="new directory for statistics and snapshots")
    parser.add_argument("--config", type=Path, help="JSON configuration; defaults to sampling an existing timeline")
    parser.add_argument("--inspect", action="store_true", help="only list project, avatar, native poses and piece names")
    parser.add_argument("--endpoint", default="http://127.0.0.1:57281/mcp")
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8-sig")) if args.config else {}
    mode = "inspect" if args.inspect else validate_config(config)
    output = args.output.resolve()
    output.mkdir(parents=True)
    summary = {"schemaVersion": 1, "mode": mode, "case": config.get("case"), "frames": [],
               "issues": [], "metric": "noncoplanar_surface_triangle_pairs",
               "coverageReview": "pending", "wholeGarmentVerdict": "not_evaluated"}
    original_frame = None
    with (output / "requests.jsonl").open("x", encoding="utf-8") as journal:
        client = audit.Style3D(args.endpoint, journal, log_arguments=False)
        try:
            client.start()
            summary["software"] = client.tool("GetSoftwareInfo")
            initial = scene(client)
            summary["scene"] = initial
            expected = config.get("expectedProject")
            require(expected is None or expected == initial["project"]["garmentName"],
                    f"Expected open project {expected!r}; observed {initial['project']['garmentName']!r}.")
            if mode == "inspect":
                for avatar in initial["avatars"]:
                    avatar["poseNames"] = client.call("Avatar.GetAvatarPoseResources", avatarId=avatar["id"])["names"]
                summary["timelineEnd"] = client.call("Animation.GetEndTrackTime")["time"]
            else:
                wanted_avatar = config.get("avatar")
                avatars = select(initial["avatars"], [wanted_avatar] if wanted_avatar else None, "avatar")
                require(len(avatars) == 1, "Choose one avatar by exact entity name or ID.")
                avatar = summary["avatar"] = avatars[0]
                pieces = select(initial["pieces"], config.get("pieces"), "cloth piece")
                require(pieces, "No main cloth pieces are available to verify.")
                if config.get("views", VIEWS):
                    require(client.call("Avatar.GetAvatarVisible", avatarId=avatar["id"])["visible"],
                            "Make the selected avatar visible before taking evidence images.")
                if mode == "record":
                    summary["recording"] = record_motion(client, avatar["id"], config["record"])
                if mode == "timeline":
                    original_frame = client.call("Animation.GetCurrentTrackTime")["time"]
                if mode == "current":
                    frames = [None]
                else:
                    last = client.call("Animation.GetEndTrackTime")["time"]
                    require(last > 0, "No animation range is available; use current mode for a static fit.")
                    first = summary.get("recording", {}).get("firstFrame", 0)
                    last = min(last, summary.get("recording", {}).get("lastFrame", last))
                    frames = sampled_frames(config, first, last)
                    summary["timelineRange"] = [first, last]
                summary["selectedPieces"] = pieces
                summary["plannedFrameCount"] = len(frames)
                for frame in frames:
                    if frame is not None:
                        observed = client.call("Animation.SetCurrentTrackTime", time=frame)
                        require(observed.get("success") and observed.get("time") == frame,
                                f"Could not confirm timeline frame {frame}: {observed}")
                    folder = output / ("current" if frame is None else f"frame-{frame:06}")
                    row = capture(client, folder, frame, avatar, pieces, config)
                    summary["frames"].append(row)
                    summary["issues"].extend(f"{folder.name}: {issue}" for issue in row["issues"])
                    summary["captureStatus"] = "in_progress"
                    write_evidence(output, summary)
                require(scene(client) == initial, "Project identity or entity IDs changed during capture.")
                if "saveProject" in config:
                    saved = client.call("Project.Save", filePath=str(output / config["saveProject"]))
                    require(saved.get("saved") and (output / config["saveProject"]).is_file(),
                            "Recorded project could not be verified on disk.")
                    summary["recordedProject"] = config["saveProject"]
        except (audit.McpError, OSError, KeyError, TypeError, ValueError) as error:
            summary["issues"].append(str(error))
        except KeyboardInterrupt:
            summary["issues"].append("Capture interrupted.")
        finally:
            if original_frame is not None:
                try:
                    restored = client.call("Animation.SetCurrentTrackTime", time=original_frame)
                    require(restored.get("success") and restored.get("time") == original_frame,
                            "Native API did not confirm restoration of the initial timeline frame.")
                    summary["restoredTimelineFrame"] = original_frame
                except (audit.McpError, KeyError, ValueError) as error:
                    summary["issues"].append(f"Timeline restore: {error}")
            client.close()
            summary["captureStatus"] = "needs_review" if summary["issues"] else "captured"
            summary["requestCounts"] = dict(client.calls)
            write_evidence(output, summary)
    print(json.dumps({"captureStatus": summary["captureStatus"], "frames": len(summary["frames"]),
                      "summary": str(output / "summary.json"), "issues": summary["issues"][:5]},
                     ensure_ascii=False))
    return 2 if summary["issues"] else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError) as error:
        sys.exit(str(error))
