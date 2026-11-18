"""Actual-source arm-placement contracts and independent initial-seed readback.

Local virtual caps below test whether the real arm is inside its sleeve. They
are never added to the physical mesh. Test success is not collision, readiness,
physical-trajectory or fit acceptance.
"""
from __future__ import annotations

import argparse
import base64
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import unittest

import numpy as np
import trimesh

from arm_placement import JOINT_FILE, retarget_sleeves
from initial_placement import improve_initial_placement

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "services/dxf-preview"))
sys.path.insert(0, str(ROOT / "experiments/oneshot_control"))
from converter.core import parse_dxf
from converter.sewn import build
from independent_oracle_v2 import intersect_pairs
from prepare_experiment import PhysicsBuilder, quality_triangulate


def body_arrays(body):
    if isinstance(body["positions"], str):
        points = np.frombuffer(base64.b64decode(body["positions"]), "<f4").astype(float).reshape(-1, 3)
        faces = np.frombuffer(base64.b64decode(body["indices"]), "<i4").reshape(-1, 3)
    else:
        points = np.asarray(body["positions"]).reshape(-1, 3)
        faces = np.asarray(body["triangles"], int).reshape(-1, 3)
    return points, faces


def actual_fixture():
    """Rebuild from committed DXF/body; no work-directory cache is required."""
    P, _ = parse_dxf((ROOT / "patterns/fitted-tshirt/input.dxf").read_bytes())
    PhysicsBuilder.boundary_step_mm = 5.
    welded, _, cert = build(P, spacing=20, builder_class=PhysicsBuilder,
                            triangulator=quality_triangulate)
    builder = PhysicsBuilder(P, spacing=20)
    body = json.loads((ROOT / "tools/engine-cloth-lab/reference/assets/makehuman.json").read_text())
    shoulder = cert["segments"]["front.shoulder.left"]["vertices"]
    translation = np.array([0., body["landmarks"]["shoulderY"] - welded[shoulder, 2].max(),
                            body["landmarks"]["neck"][2]])
    positions, uv, faces, ids, panels = [], [], [], [], []
    for name, patch in cert["patches"].items():
        index = np.asarray(patch["global_vertices"], int)
        material = np.asarray(patch["flat_points"]) / 1000
        origin = material.min(0)
        panels.append({"name": name, "start": len(positions), "vertices": len(index),
                       "face_start": len(faces), "faces": len(patch["local_faces"]),
                       "uv_origin_m": origin.tolist()})
        faces.extend((np.asarray(patch["local_faces"], int) + len(positions)).tolist())
        positions.extend((welded[index][:, [0, 2, 1]] * [1, 1, -1] + translation).tolist())
        uv.extend((material - origin).tolist())
        ids.extend(index.tolist())
    positions = np.asarray(positions)
    blend = np.clip((abs(positions[:, 0]) - .25) / .20, 0, 1)
    blend = blend * blend * (3 - 2 * blend)
    depth = {"scale": 2.2, "offset_m": .04, "arm_offset_m": .22}
    positions[:, 2] = positions[:, 2] * 2.2 + .04 + .22 * blend
    source = positions.copy()
    positions, _ = improve_initial_placement(cert, positions, panels, ids, builder, translation, depth)
    return {"positions": positions, "source_sewing": cert, "panels": panels,
            "global_ids": np.asarray(ids), "uv": np.asarray(uv), "triangles": np.asarray(faces),
            "body": body, "builder": builder, "initialization": {"translation_m": translation,
            "depth_placement": depth}, "source_reference_positions": source}


def run(data, body=None):
    init = data["initialization"]
    return retarget_sleeves(data["positions"], data["source_sewing"], data["panels"],
                            data["global_ids"], data["builder"], init["translation_m"],
                            init["depth_placement"], data["body"] if body is None else body)


def capped_sleeve(data, positions, panel):
    """Close actual mesh boundary cycles, without using production (u,theta)."""
    start, count = panel["start"], panel["vertices"]
    ids = np.asarray(data["global_ids"])[start:start + count]
    _, first, inverse = np.unique(ids, return_index=True, return_inverse=True)
    points = np.asarray(positions)[start:start + count][first].tolist()
    local_faces = inverse[np.asarray(data["source_sewing"]["patches"][panel["name"]]["local_faces"], int)]
    edge_uses = {}
    for face in local_faces:
        for k in range(3):
            a, b = int(face[k]), int(face[(k + 1) % 3])
            edge_uses.setdefault(tuple(sorted((a, b))), []).append((a, b))
    edges = [entries[0] for entries in edge_uses.values() if len(entries) == 1]
    adjacency = {}
    for a, b in edges:
        adjacency.setdefault(a, []).append(b)
        adjacency.setdefault(b, []).append(a)
    if any(len(neighbors) != 2 for neighbors in adjacency.values()):
        raise AssertionError("Sleeve has a branched/nonclosed physical boundary")
    remaining, components = set(adjacency), []
    while remaining:
        component, pending = set(), [next(iter(remaining))]
        while pending:
            item = pending.pop()
            if item in component:
                continue
            component.add(item)
            pending.extend(adjacency[item])
        remaining -= component
        components.append(component)
    if len(components) != 2:
        raise AssertionError("Actual sleeve does not have exactly an armhole and a cuff")
    closed_faces = local_faces.tolist()
    for component in components:
        center = np.asarray(points)[list(component)].mean(0)
        ci = len(points)
        points.append(center.tolist())
        closed_faces.extend([[ci, b, a] for a, b in edges if a in component])
    mesh = trimesh.Trimesh(np.asarray(points), np.asarray(closed_faces), process=False)
    if not mesh.is_watertight or not mesh.is_winding_consistent or mesh.volume <= 0:
        raise AssertionError("Virtual closure is not a consistent outward sleeve volume")
    return mesh


def diagnose(data, output):
    points = np.asarray(output)
    body = trimesh.Trimesh(*body_arrays(data["body"]), process=False)
    ids, faces, uv = (np.asarray(data[key]) for key in ["global_ids", "triangles", "uv"])
    _, first, inverse = np.unique(ids, return_index=True, return_inverse=True)
    self_pairs = intersect_pairs(points[first], inverse[faces], epsilon_m=1e-6)
    inside = body.contains(points[first])
    distance = trimesh.proximity.closest_point(body, points[first][inside])[1] if inside.any() else np.array([0.])
    material = uv[faces]
    inv_dm = np.linalg.inv(np.stack([material[:, 1] - material[:, 0], material[:, 2] - material[:, 0]], axis=-1))
    spatial = points[faces]
    sigma = np.linalg.svd(np.stack([spatial[:, 1] - spatial[:, 0], spatial[:, 2] - spatial[:, 0]], axis=-1) @ inv_dm,
                          compute_uv=False)
    joints = json.loads(JOINT_FILE.read_text())["joint_coordinates"]
    sleeves = []
    for panel in data["panels"]:
        if not panel["name"].startswith("sleeve."):
            continue
        side = "R" if panel["name"] == "sleeve.left" else "L"
        anatomical = np.array([joints[side][key]["canonical_m"] for key in ["shoulder", "elbow", "wrist"]])
        chain = np.vstack([np.linspace(anatomical[0], anatomical[1], 33),
                           np.linspace(anatomical[1], anatomical[2], 33)[1:]])
        old_mesh = capped_sleeve(data, data["positions"], panel)
        new_mesh = capped_sleeve(data, points, panel)
        fs = slice(panel["face_start"], panel["face_start"] + panel["faces"])
        sleeves.append({"panel": panel["name"], "anatomical_side": side,
                        "before_joint_inside": old_mesh.contains(anatomical).tolist(),
                        "after_joint_inside": new_mesh.contains(anatomical).tolist(),
                        "arm_chain_samples": len(chain), "actual_body_contains_samples": int(body.contains(chain).sum()),
                        "before_sleeve_contains_samples": int(old_mesh.contains(chain).sum()),
                        "after_sleeve_contains_samples": int(new_mesh.contains(chain).sum()),
                        "sigma_max": float(sigma[fs, 0].max()), "sigma_min": float(sigma[fs, 1].min()),
                        "local_virtual_caps_only": True})
    return {"sleeves": sleeves, "strict_self_pairs": len(self_pairs), "self_examples": self_pairs[:10],
            "body_inside_roots": int(inside.sum()), "max_inside_depth_mm": float(distance.max() * 1000),
            "ready_acceptance": "FAIL" if inside.any() or self_pairs else "NOT_RUN",
            "physical_acceptance": "NOT_RUN",
            "unverified": ["complete triangle/body crossings", "physical preparation and trajectory",
                           "material calibration", "physical fit"]}


class ArmPlacementContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = actual_fixture()
        cls.result, cls.metadata = run(cls.data)
        cls.observation = diagnose(cls.data, cls.result)

    def test_joint_derivation_from_exact_source_obj_and_canonical_ground(self):
        record = json.loads(JOINT_FILE.read_text())
        raw = (ROOT / record["source_obj"]["path"]).read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), record["source_obj"]["sha256"])
        verts = np.array([list(map(float, line.split()[1:4])) for line in raw.decode().splitlines()
                          if line.startswith("v ")])
        rig_raw = (ROOT / record["rig"]["path"]).read_bytes()
        self.assertEqual(hashlib.sha256(rig_raw).hexdigest(), record["rig"]["sha256"])
        rig = json.loads(rig_raw)
        self.assertEqual(len(verts), 19158)
        self.assertEqual(len(rig["bones"]), 163)
        self.assertEqual(record["source_obj"]["sha256"], self.data["body"]["source"]["sourceSHA256"])
        transform = record["transform"]
        for side, side_joints in record["joint_coordinates"].items():
            for name, joint in side_joints.items():
                helper_ids = joint["original_obj_vertex_ids"]
                self.assertEqual(helper_ids, rig["joints"][joint["helper_name"]])
                canonical = verts[helper_ids].mean(0) * transform["raw_obj_to_canonical_m_scale"]
                canonical += transform["raw_obj_to_canonical_translation_m"]
                np.testing.assert_allclose(canonical, joint["canonical_m"], atol=1e-14, rtol=0)
                if name == "shoulder":
                    landmark = "shoulderLeft" if side == "L" else "shoulderRight"
                    np.testing.assert_allclose(canonical, self.data["body"]["landmarks"][landmark], atol=2e-8, rtol=0)

    def test_exact_armhole_nonsleeve_alias_and_readonly_source_contract(self):
        data = self.data
        snapshot = lambda: json.dumps({key: value for key, value in data.items() if key != "builder"},
                                     sort_keys=True, separators=(",", ":"),
                                     default=lambda value: np.asarray(value).tolist())
        before = snapshot()
        result, metadata = run(data)
        self.assertEqual(snapshot(), before)
        self.assertEqual(len(data["source_sewing"]["seams"]), 15)
        self.assertEqual(len(result), 4387)
        self.assertEqual(len(data["triangles"]), 7186)
        for panel in data["panels"]:
            start, count = panel["start"], panel["vertices"]
            if panel["name"].startswith("sleeve."):
                segments = data["source_sewing"]["segments"]
                cap = set(segments[panel["name"] + ".cap.front"]["local_vertices"])
                cap |= set(segments[panel["name"] + ".cap.back"]["local_vertices"])
                cap = start + np.array(sorted(cap))
                self.assertEqual(result[cap].tobytes(), data["positions"][cap].tobytes())
            else:
                ss = slice(start, start + count)
                self.assertEqual(result[ss].tobytes(), data["positions"][ss].tobytes())
        for gid in np.unique(data["global_ids"]):
            group = np.flatnonzero(data["global_ids"] == gid)
            self.assertTrue(np.all(result[group] == result[group[0]]))
        self.assertEqual(metadata["max_seam_alias_gap_m"], 0.)
        self.assertTrue(metadata["does_not_replace_source_reference"])
        self.assertEqual(metadata["physical_acceptance"], "NOT_RUN")

    def test_independent_actual_arm_enclosure_and_no_self_acceptance_shortcut(self):
        for sleeve in self.observation["sleeves"]:
            self.assertEqual(sleeve["before_joint_inside"], [True, False, False])
            self.assertEqual(sleeve["after_joint_inside"], [True, True, True])
            self.assertEqual(sleeve["actual_body_contains_samples"], 65)
            self.assertLess(sleeve["before_sleeve_contains_samples"], 65)
            self.assertEqual(sleeve["after_sleeve_contains_samples"], 65)
            self.assertLess(sleeve["sigma_max"], 2.5)
            self.assertGreater(sleeve["sigma_min"], .10)
        self.assertEqual(self.observation["strict_self_pairs"], 0)
        # The initial seed remains intrusive: assertions deliberately preserve
        # that distinction rather than turning a topology fix into fit PASS.
        self.assertGreater(self.observation["body_inside_roots"], 0)
        self.assertEqual(self.observation["ready_acceptance"], "FAIL")
        self.assertEqual(self.observation["physical_acceptance"], "NOT_RUN")

    def test_packed_body_binding_and_stale_source_hash_rejection(self):
        record = json.loads(JOINT_FILE.read_text())["canonical_body"]
        p, f = body_arrays(self.data["body"])
        packed = {"positions": base64.b64encode(np.asarray(p, "<f4").tobytes()).decode(),
                  "indices": base64.b64encode(np.asarray(f, "<i4").tobytes()).decode(),
                  "source_sha256": record["sha256"]}
        result, _ = run(self.data, packed)
        np.testing.assert_array_equal(result, self.result)
        p[0, 0] += .0001
        packed["positions"] = base64.b64encode(np.asarray(p, "<f4").tobytes()).decode()
        with self.assertRaisesRegex(ValueError, "coordinates/topology"):
            run(self.data, packed)
        changed_body = deepcopy(self.data["body"])
        changed_body["triangles"][0], changed_body["triangles"][1] = changed_body["triangles"][1], changed_body["triangles"][0]
        with self.assertRaisesRegex(ValueError, "coordinates/topology"):
            run(self.data, changed_body)

    def test_inconsistent_source_seam_is_rejected(self):
        data = dict(self.data)
        data["positions"] = self.data["positions"].copy()
        ids = data["global_ids"]
        _, counts = np.unique(ids, return_counts=True)
        self.assertGreater(counts.max(), 1)
        group = next(np.flatnonzero(ids == gid) for gid in np.unique(ids) if np.count_nonzero(ids == gid) > 1)
        data["positions"][group[1], 0] += .0001
        with self.assertRaisesRegex(ValueError, "seam aliases"):
            run(data)


def observe_actual(input_path, output_path, reference=None):
    raw = input_path.read_bytes()
    data = json.loads(raw)
    before = json.dumps(data, sort_keys=True, separators=(",", ":"))
    source = (ROOT / "patterns/fitted-tshirt/input.dxf").read_bytes()
    if hashlib.sha256(source).hexdigest() != data["source_dxf_sha256"]:
        raise ValueError("Actual observation requires its exact baseline DXF")
    P, _ = parse_dxf(source)
    data["builder"] = PhysicsBuilder(P, spacing=20)
    output, metadata = run(data)
    observation = diagnose(data, output)
    del data["builder"]
    assert before == json.dumps(data, sort_keys=True, separators=(",", ":"))
    delta = None
    if reference:
        delta = float(abs(output - np.load(reference)).max())
        assert delta < 2e-12, delta
    report = {"contract_verdict": "PASS", "scope": "One actual initial XYZ array; not a physical frame",
              "input": str(input_path), "input_sha256": hashlib.sha256(raw).hexdigest(),
              "initialisation": metadata, "reference_max_delta_m": delta, **observation}
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    np.save(output_path.with_suffix(".positions.npy"), output)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--reference", type=Path)
    args = parser.parse_args()
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ArmPlacementContracts))
    if not result.wasSuccessful():
        raise SystemExit(1)
    if args.input:
        if not args.output:
            parser.error("--output required with --input")
        report = observe_actual(args.input, args.output, args.reference)
        print(json.dumps({key: report[key] for key in ["contract_verdict", "ready_acceptance", "strict_self_pairs",
              "body_inside_roots", "max_inside_depth_mm", "reference_max_delta_m"]}, ensure_ascii=False))
