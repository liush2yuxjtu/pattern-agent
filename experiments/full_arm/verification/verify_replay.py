"""Independently reload a portable Blender replay and compare measured arrays.

Run under Blender, without importing any garment generator or replay builder::

    blender -b --python-exit-code 2 --python verification/verify_replay.py -- \
      --blend evidence/full-005/replay/measured-replay.blend \
      --frames evidence/full-005/frames --out evidence/full-005/replay-audit.json

The verifier copies only the .blend into a newly created directory. Original NPZ
files are read explicitly for comparison; no NPZ/cache is placed next to the copy.
Every exported integer frame is compared, including all transition frames.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import sys
import tempfile
import time
from datetime import datetime, timezone

import bpy
import numpy as np


TOLERANCE_M = 1e-7
OBJECTS = (("MeasuredCloth", "cloth"), ("MeasuredFullBody", "body"))


def file_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def collect_frames(directory):
    files = {}
    for path in sorted(Path(directory).glob("frame-*.npz")):
        match = re.fullmatch(r"frame-(\d+)\.npz", path.name)
        if match is None:
            continue
        frame = int(match.group(1))
        if frame in files:
            raise ValueError(f"Duplicate measured frame {frame}")
        files[frame] = path
    if not files:
        raise ValueError("No measured NPZ frames found")
    if sorted(files) != list(range(1, max(files) + 1)):
        raise ValueError("NPZ frame coverage must be contiguous and start at 1")
    return files


def mesh_arrays(obj, depsgraph):
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        coords = np.empty((len(mesh.vertices), 3), dtype=np.float64)
        mesh.vertices.foreach_get("co", coords.ravel())
        world_matrix = np.asarray(evaluated.matrix_world, dtype=np.float64)
        coords = coords @ world_matrix[:3, :3].T + world_matrix[:3, 3]
        sizes = np.empty(len(mesh.polygons), dtype=np.int32)
        mesh.polygons.foreach_get("loop_total", sizes)
        if not np.all(sizes == 3):
            raise ValueError(f"{obj.name} contains non-triangle polygons")
        vertices = np.empty(len(mesh.loops), dtype=np.int32)
        mesh.loops.foreach_get("vertex_index", vertices)
        return coords, vertices.reshape((-1, 3))
    finally:
        evaluated.to_mesh_clear()


def shape_key_audit(obj, frame_count):
    keys = obj.data.shape_keys
    failures = []
    if keys is None:
        return {"pass": False, "failures": ["shape keys missing"]}
    expected = {f"MeasuredFrame_{frame:04d}" for frame in range(2, frame_count + 1)}
    actual = {key.name for key in keys.key_blocks[1:]}
    if actual != expected:
        failures.append("measured shape-key names do not cover every NPZ frame")
    if len(keys.key_blocks) != frame_count:
        failures.append("shape-key count differs from frame count including Basis")
    if not keys.use_relative:
        failures.append("replay does not use relative shape keys")
    if any(key.relative_key != keys.key_blocks[0] for key in keys.key_blocks[1:]):
        failures.append("a measured key is not relative to Basis")
    animation = keys.animation_data
    if frame_count > 1 and (animation is None or animation.action is None):
        failures.append("shape-key animation missing")
    if animation and animation.drivers:
        failures.append("shape-key driver dependency present")
    if animation and len(animation.nla_tracks):
        failures.append("unexpected shape-key NLA tracks present")
    return {
        "pass": not failures,
        "shape_key_count": len(keys.key_blocks),
        "expected_basis_and_measured_keys": frame_count,
        "missing_keys": sorted(expected - actual),
        "extra_keys": sorted(actual - expected),
        "failures": failures,
    }


def dependency_audit():
    """Read datablocks, modifiers and point caches rather than scene claims."""
    findings = []
    for library in bpy.data.libraries:
        findings.append({"type": "linked_library", "path": library.filepath})
    for cache in bpy.data.cache_files:
        findings.append({"type": "geometry_cache", "path": cache.filepath})
    for obj in bpy.data.objects:
        if obj.library:
            findings.append({"type": "linked_object", "object": obj.name})
        # Expected replay objects have only self-contained mesh/shape-key data.
        # Reject unexpected procedural or simulation modifiers rather than trying
        # to infer which hidden node/cache inputs may affect evaluated geometry.
        for modifier in obj.modifiers:
            findings.append({"type": "unexpected_modifier", "object": obj.name,
                             "modifier": modifier.name, "modifier_type": modifier.type})
        if obj.particle_systems:
            findings.append({"type": "particle_geometry", "object": obj.name})
        if obj.type == "VOLUME" and obj.data.filepath:
            findings.append({"type": "volume_file", "object": obj.name,
                             "path": obj.data.filepath})
        animation = obj.animation_data
        if animation and animation.drivers:
            findings.append({"type": "object_drivers", "object": obj.name})
    return {"pass": not findings, "external_or_procedural_geometry_findings": findings,
            "library_count": len(bpy.data.libraries),
            "geometry_cache_datablock_count": len(bpy.data.cache_files)}


def audit(args):
    started = time.monotonic()
    source = Path(args.blend).resolve(strict=True)
    frames_dir = Path(args.frames).resolve(strict=True)
    files = collect_frames(frames_dir)
    source_hash = file_sha256(source)
    report = {
        "schema_version": 1,
        "verifier": "independent Blender reload and full-array comparison",
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "blender_version": bpy.app.version_string,
        "source_blend": str(source),
        "source_blend_sha256": source_hash,
        "source_frames_directory": str(frames_dir),
        "tolerance_m": TOLERANCE_M,
        "comparison_space": "world coordinates",
        "frame_count": len(files),
        "all_exported_integer_frames_checked": True,
        "failures": [],
        "frames": [],
    }
    with tempfile.TemporaryDirectory(prefix="pattern-replay-independent-") as temporary:
        isolated = Path(temporary)
        copied = isolated / "measured-replay.blend"
        shutil.copyfile(source, copied)
        report["isolated_reload"] = {
            "copy_sha256": file_sha256(copied),
            "only_files_before_load": sorted(p.name for p in isolated.iterdir()),
            "different_directory_from_original": isolated != source.parent,
            "npz_files_copied": False,
            "external_caches_copied": False,
        }
        if report["isolated_reload"]["copy_sha256"] != source_hash:
            report["failures"].append("isolated .blend bytes differ from source")
        bpy.ops.wm.open_mainfile(filepath=str(copied), load_ui=False, use_scripts=False)
        scene = bpy.context.scene
        report["scene_frame_range"] = [scene.frame_start, scene.frame_end]
        if (scene.frame_start, scene.frame_end) != (1, len(files)):
            report["failures"].append("scene frame range differs from measured NPZ coverage")
        report["dependencies"] = dependency_audit()
        if not report["dependencies"]["pass"]:
            report["failures"].append("external/procedural geometry dependency detected")
        objects = {}
        report["shape_key_coverage"] = {}
        for object_name, prefix in OBJECTS:
            obj = bpy.data.objects.get(object_name)
            if obj is None or obj.type != "MESH":
                raise ValueError(f"Required measured mesh missing: {object_name}")
            objects[prefix] = obj
            shape_report = shape_key_audit(obj, len(files))
            report["shape_key_coverage"][object_name] = shape_report
            if not shape_report["pass"]:
                report["failures"].append(f"{object_name}: incomplete shape-key coverage")
        worst = {prefix: 0.0 for _, prefix in OBJECTS}
        baseline_faces = {}
        for frame, path in sorted(files.items()):
            scene.frame_set(frame)
            depsgraph = bpy.context.evaluated_depsgraph_get()
            frame_report = {"frame": frame, "npz_sha256": file_sha256(path), "pass": True}
            with np.load(path, allow_pickle=False) as measured:
                for object_name, prefix in OBJECTS:
                    expected = np.asarray(measured[prefix + "_vertices"], dtype=np.float64)
                    expected_faces = np.asarray(measured[prefix + "_triangles"], dtype=np.int32)
                    actual, actual_faces = mesh_arrays(objects[prefix], depsgraph)
                    finite = bool(np.isfinite(expected).all() and np.isfinite(actual).all())
                    same_size = actual.shape == expected.shape
                    max_delta = float(np.max(np.abs(actual - expected))) if same_size and finite else None
                    same_faces = bool(np.array_equal(actual_faces, expected_faces))
                    if prefix not in baseline_faces:
                        baseline_faces[prefix] = expected_faces.copy()
                    stable_faces = bool(np.array_equal(expected_faces, baseline_faces[prefix]))
                    keys = objects[prefix].data.shape_keys
                    active = [] if keys is None else [key.name for key in keys.key_blocks[1:]
                                                      if abs(key.value) > 1e-6]
                    expected_active = [] if frame == 1 else [f"MeasuredFrame_{frame:04d}"]
                    active_keys_correct = active == expected_active
                    if frame > 1 and keys and active_keys_correct:
                        active_keys_correct = abs(keys.key_blocks[expected_active[0]].value - 1.0) < 1e-6
                    passed = bool(finite and same_size and same_faces and stable_faces
                                  and active_keys_correct and max_delta is not None
                                  and max_delta <= TOLERANCE_M)
                    frame_report[prefix] = {
                        "pass": passed, "vertex_count": len(actual),
                        "triangle_count": len(actual_faces), "finite": finite,
                        "vertex_array_shape_matches": same_size,
                        "connectivity_matches_npz": same_faces,
                        "connectivity_constant_across_npz": stable_faces,
                        "shape_key_activation_correct": active_keys_correct,
                        "max_absolute_coordinate_delta_m": max_delta,
                    }
                    if max_delta is not None:
                        worst[prefix] = max(worst[prefix], max_delta)
                    frame_report["pass"] = frame_report["pass"] and passed
            report["frames"].append(frame_report)
            if not frame_report["pass"]:
                report["failures"].append(f"frame {frame}: measured replay comparison failed")
        report["worst_absolute_coordinate_delta_m"] = worst
        report["checked_frames"] = sorted(files)
        report["requested_checkpoints_included"] = [f for f in (1, 21, 81, 141, 221, 241) if f in files]
        report["isolated_reload"]["only_files_after_comparison"] = sorted(p.name for p in isolated.iterdir())
    report["source_blend_sha256_after"] = file_sha256(source)
    if report["source_blend_sha256_after"] != source_hash:
        report["failures"].append("original .blend changed during audit")
    report["elapsed_seconds"] = time.monotonic() - started
    report["status"] = "PASS" if not report["failures"] else "FAIL"
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blend", required=True, help="Measured replay .blend")
    parser.add_argument("--frames", required=True, help="Original measured NPZ frames directory")
    parser.add_argument("--out", required=True, help="Audit JSON file")
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    args = parser.parse_args(argv)
    try:
        report = audit(args)
    except Exception as exc:
        report = {"schema_version": 1, "status": "FAIL",
                  "failures": [f"{type(exc).__name__}: {exc}"],
                  "tolerance_m": TOLERANCE_M}
    destination = Path(args.out).resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"status": report["status"], "out": str(destination),
                      "frame_count": report.get("frame_count"),
                      "failures": report["failures"]}), flush=True)
    if report["status"] != "PASS":
        # Blender's --python-exit-code makes this nonzero for pipeline callers.
        raise RuntimeError("Independent portable replay verification failed")


if __name__ == "__main__":
    main()
