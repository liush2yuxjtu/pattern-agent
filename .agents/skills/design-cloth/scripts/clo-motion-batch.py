#!/usr/bin/env python3
"""Run isolated Boat CLO cases and build a key-frame review bundle."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
import hashlib
from functools import lru_cache
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
from threading import Lock
from tempfile import TemporaryDirectory

SIZES = ("S", "M", "L", "XL")
MOTIONS = tuple(f"{number:02}" for number in range(1, 11))
MAPS = ("pressure", "stress", "strain", "appearance", "fold")
UNITS = {"pressure": "kPa", "stress": "kPa", "strain": "%", "fold": "deg"}
HERE = Path(__file__).resolve().parent


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def save(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


@lru_cache(maxsize=None)
def digest(path):
    with path.open("rb") as stream:
        checksum = hashlib.sha256()
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            checksum.update(chunk)
    return checksum.hexdigest()


def run(*args, timeout=120, check=True):
    return subprocess.run(args, capture_output=True, text=True, check=check, timeout=timeout)


def boat(*args, timeout=120):
    response = run("boat", "--no-update", "--json", *args, timeout=timeout)
    return json.loads(response.stdout)


def finite(number):
    return type(number) in (float, int) and math.isfinite(number)


def read_config(path):
    config = load(path)
    if set(config["sizes"]) != set(SIZES) or set(config["motions"]) != set(MOTIONS):
        raise ValueError("配置必须包含 S、M、L、XL 和 01–10 共十项动作")
    if set(config["thresholds"]) != {*UNITS, "crossings", "coverage"}:
        raise ValueError("配置必须声明全部定量阈值")
    if not all(finite(value) and value >= 0 for value in config["thresholds"].values()):
        raise ValueError("定量阈值必须是有限非负数")
    if not config["revision"]:
        raise ValueError("需要样衣版次")
    for motion in config["motions"].values():
        frames = motion["frames"]
        if (not frames or frames[0] != 0 or sorted(set(frames)) != frames
                or any(type(frame) is not int or frame < 0 for frame in frames)):
            raise ValueError("抽查帧必须是从 0 开始的有序唯一整数")
    return config


def inputs(config, root, size, motion):
    size_config, motion_config = config["sizes"][size], config["motions"][motion]
    paths = {key: (root / value).resolve() for key, value in {
        "project": size_config["project"], "design": size_config["design"],
        "fbx": motion_config["fbx"], "sanim": motion_config["sanim"],
        **({"mtn": motion_config["mtn"]} if motion_config.get("mtn") else {}),
    }.items()}
    files = {key: digest(path) if path.is_file() else None for key, path in paths.items()}
    request = {
        "size": size, "motion": motion, "revision": config["revision"],
        "label": motion_config["label"], "frames": motion_config["frames"],
        "thresholds": config["thresholds"], "files": files,
        "worker_code": {name: digest(HERE / name) for name in ("clo_motion_native.py", "clo-motion-guest.sh")},
        "clo_version": config["boat"]["clo_version"],
        "native_record_timeout_seconds": config["boat"]["timeout_seconds"] - 30, "project_checks": size_config["checks"],
        "motion_checks": motion_config["checks"],
    }
    request["fingerprint"] = hashlib.sha256(
        json.dumps(request, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()
    return request, paths


def evidence_path(folder, relative):
    if not isinstance(relative, str) or not relative:
        return None
    candidate = (folder / relative).resolve()
    return candidate if candidate.is_relative_to(folder.resolve()) and candidate.is_file() else None


def decodable_image(path):
    if not path:
        return False
    try:
        from PIL import Image
        with Image.open(path) as image:
            image.load()
    except OSError:
        return False
    return True


def review(folder, request):
    receipt = folder / "receipt.json"
    if not receipt.is_file():
        return {"status": "BLOCKED", "issues": ["无原生 CLO 录制证据"], "frames": []}
    try:
        data = load(receipt)
    except (ValueError, OSError):
        return {"status": "BLOCKED", "issues": ["原生证据清单不可读取"], "frames": []}
    if (data.get("fingerprint") != request["fingerprint"]
            or data.get("engine") != "CLO 3D" or not data.get("boat_id")
            or not data.get("clo_version")):
        return {"status": "BLOCKED", "issues": ["证据与当前工程、帧或原生 CLO 环境不符"], "frames": []}

    if data.get("status") == "BLOCKED":
        return {"status": "BLOCKED", "issues": [str(data.get("reason", "原生取证阻塞"))], "frames": []}

    issues, failures = ([data["reason"]] if data.get("reason") else []), []
    video = evidence_path(folder, data.get("video"))
    recording = data.get("recording", {})
    count = recording.get("source_frames")
    frames = data.get("frames", [])
    actual = [frame.get("index") for frame in frames]
    if (not video or not evidence_path(folder, recording.get("project"))
            or type(count) is not int or count < 2 or recording.get("last_frame") != count - 1
            or recording.get("cloth_geometry_changed") is not True):
        issues.append("布料轨不完整或未见网格变化")
    if (not actual or any(type(index) is not int or index < 0 for index in actual)
            or actual != sorted(set(actual)) or not set(request["frames"]).issubset(actual)
            or type(count) is not int or actual[-1] != count - 1):
        issues.append("缺少规定抽查帧或末帧")
    if data.get("project_checks_pass") is not True or data.get("motion_checks_pass") is not True:
        issues.append("原生工程或动作读回尚未通过")
    for frame in frames:
        index = frame.get("index")
        if not finite(frame.get("seconds")) or frame["seconds"] < 0:
            issues.append(f"{index} 帧无有效视频时间")
        for key in MAPS:
            panel = frame.get("maps", {}).get(key, {})
            if panel.get("frame") != index or not decodable_image(evidence_path(folder, panel.get("image"))):
                issues.append(f"{index} 帧缺少或错配 {key} 图")
                continue
            if key == "appearance" and any(not decodable_image(evidence_path(folder, panel.get("views", {}).get(view)))
                                           for view in ("back", "side")):
                issues.append(f"{index} 帧缺少试穿背面或侧面")
            if key in UNITS:
                value = panel.get("value")
                expected_source = "CLO mesh dihedral" if key == "fold" else "CLO native"
                if panel.get("source") != expected_source or panel.get("unit") != UNITS[key] or not finite(value):
                    issues.append(f"{index} 帧缺少有效 {key} 读数")
                elif value > request["thresholds"][key]:
                    failures.append(f"{index} 帧 {key}={value} {UNITS[key]}")
        for key in ("crossings", "coverage"):
            value = frame.get(key)
            if not finite(value) or value < 0:
                issues.append(f"{index} 帧缺少 {key} 读数")
            elif value > request["thresholds"][key]:
                failures.append(f"{index} 帧 {key}={value}")
    status = "FAIL" if failures else "BLOCKED" if issues else "PASS"
    return {"status": status, "issues": issues + failures, "missing": bool(issues),
            "frames": frames, "video": data.get("video"), "source_frames": count,
            "boat_id": data["boat_id"], "clo_version": data["clo_version"]}


def key_frames(result, request):
    frames = result["frames"]
    if not frames:
        return []
    selected = set(request["frames"]) | {frames[-1]["index"]}
    for key in (*UNITS, "crossings", "coverage"):
        measured = [(read_value(frame, key), frame["index"]) for frame in frames]
        valid = [(value, index) for value, index in measured if finite(value)]
        if valid:
            selected.add(max(valid)[1])
            selected.update(index for value, index in valid if value > request["thresholds"][key])
    return [frame for frame in frames if frame["index"] in selected]


def read_value(frame, key):
    return frame.get("maps", {}).get(key, {}).get("value") if key in UNITS else frame.get(key)


def copy_boat(source, target):
    run("boat", "--no-update", "scp", str(source), str(target), timeout=900)


def run_case(worker, folder, request, paths, native_timeout):
    # Upload only declared inputs. Each worker handles one project at a time.
    work = f"/tmp/clo-motion-{request['fingerprint'][:20]}"
    with TemporaryDirectory() as staging:
        staging = Path(staging)
        save(staging / "request.json", request)
        payload = staging / "inputs.tar"
        with tarfile.open(payload, "w") as archive:
            archive.add(staging / "request.json", arcname="request.json")
            for key, name in (("project", "seed.zprj"), ("design", "design.png"),
                              ("fbx", "motion.fbx"), ("mtn", "motion.mtn")):
                if key in paths:
                    archive.add(paths[key], arcname=name)
            for script in ("clo-motion-guest.sh", "clo_motion_native.py"):
                archive.add(HERE / script, arcname=script)
        copy_boat(payload, f"{worker}:{work}.tar")
        command = (
            f'mkdir -p {work} && cd {work} && tar -xf {work}.tar '
            f'&& rm -f result/native.done && CLO_CASE_TIMEOUT={native_timeout - 5} '
            f'bash clo-motion-guest.sh {worker} {request["clo_version"]} '
            '&& tar -czf evidence.tgz -C result .'
        )
        response = boat("exec", worker, "--timeout", str(native_timeout), command, timeout=native_timeout + 90)
        if response.get("exitCode") != 0:
            raise RuntimeError((response.get("stderr") or response.get("stdout") or "CLO worker failed")[-500:])
        bundle = staging / "evidence.tgz"
        copy_boat(f"{worker}:{work}/evidence.tgz", bundle)
        with tarfile.open(bundle) as archive:
            for member in archive.getmembers():
                resolved = (folder / member.name).resolve()
                if not resolved.is_relative_to(folder.resolve()) or not (member.isfile() or member.isdir()):
                    raise ValueError("invalid worker archive member")
            for member in archive.getmembers():
                target = folder / member.name
                if member.isdir():
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with archive.extractfile(member) as source, target.open("wb") as destination:
                        shutil.copyfileobj(source, destination)
        receipt = load(folder / "receipt.json")
        if receipt.get("boat_id") != worker or receipt.get("fingerprint") != request["fingerprint"]:
            (folder / "receipt.json").unlink()
            raise ValueError("CLO receipt does not belong to this worker and input")
        from clo_motion_geometry import add_folds
        add_folds(folder, receipt, evidence_path)
        save(folder / "receipt.json", receipt)


def dispatch(cases, config, requested):
    machinery = config["boat"]
    workers = list(dict.fromkeys(machinery["workers"]))
    if any(not worker.startswith("bx_") or not worker[3:].isalnum() for worker in workers):
        raise ValueError("invalid Boat IDs")
    if not all(part.isdecimal() for part in machinery["clo_version"].split(".")):
        raise ValueError("invalid CLO version")
    pending = [(folder, request, paths) for folder, request, paths in cases
               if all(request["files"].values()) and (review(folder, request)["status"] == "BLOCKED"
                                                    or review(folder, request).get("missing"))]
    if not pending or not workers:
        return
    # Only already-prepared workers are eligible. Re-read live Boat state
    # rather than dispatching a stopped fork or counting it as a CLO seat.
    response = boat("list")
    inventory = response if isinstance(response, list) else response.get("sandboxes", [])
    ready = {item["id"] for item in inventory if item.get("state") in {"ready", "idle", "running"}}
    workers = [worker for worker in workers if worker in ready]
    if not workers:
        return
    concurrent_seats = machinery["concurrent_seats"]
    limit = min(len(pending), len(workers), concurrent_seats,
                len(workers) if requested == "auto" else int(requested))
    if limit < 1:
        return
    work_items = iter(pending)
    queue_lock = Lock()

    def consume(worker):
        while True:
            with queue_lock:
                task = next(work_items, None)
            if task is None:
                return
            folder, request, paths = task
            try:
                run_case(worker, folder, request, paths, machinery["timeout_seconds"])
                (folder / "blocked.txt").unlink(missing_ok=True)
            except (OSError, subprocess.SubprocessError, ValueError, RuntimeError) as error:
                (folder / "blocked.txt").write_text(str(error) + "\n", encoding="utf-8")

    with ThreadPoolExecutor(max_workers=limit) as executor:
        list(executor.map(consume, workers[:limit]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--jobs", default="auto")
    parser.add_argument("--review-only", action="store_true")
    args = parser.parse_args()
    if args.jobs != "auto" and (not args.jobs.isdecimal() or int(args.jobs) < 1):
        parser.error("--jobs must be auto or a positive integer")
    config = read_config(args.config)
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    from clo_motion_report import publish
    cases = []
    for size in SIZES:
        for motion in MOTIONS:
            request, paths = inputs(config, args.config.resolve().parent, size, motion)
            folder = out / "cases" / size / motion / request["fingerprint"]
            folder.mkdir(parents=True, exist_ok=True)
            cases.append((folder, request, paths))
    if not args.review_only:
        dispatch(cases, config, args.jobs)
    verdict = publish(out, cases, sys.modules[__name__])
    print(f"{out / 'index.html'} | {out / 'stats.csv'} | {verdict}")
    return 0 if verdict == "PASS" else 2


if __name__ == "__main__":
    sys.exit(main())
