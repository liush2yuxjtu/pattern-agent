"""Analytic routing coupons and optional actual-frame arm-wear regressions.

No placement function or solver is imported. Default tests need only committed
body/OBJ/rig assets. Optional run31/run27 checks reopen actual recorded f32 XYZ;
their numerical wearing verdict never replaces body/self/physical acceptance.
"""
from __future__ import annotations

import argparse
import base64
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

import arm_wear_oracle as oracle

ROOT = Path(__file__).resolve().parents[3]


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _packed_body():
    path = ROOT / "tools/engine-cloth-lab/reference/assets/makehuman.json"
    raw = path.read_bytes()
    body = json.loads(raw)
    return {"source": str(path.relative_to(ROOT)), "source_sha256": _sha(raw),
            "positions": base64.b64encode(np.asarray(body["positions"], "<f4").tobytes()).decode(),
            "indices": base64.b64encode(np.asarray(body["triangles"], "<i4").tobytes()).decode()}


def prism_fixture(armhole_x=.13, cuff_x=.50, front_z=.23):
    """Analytic rectangular open sleeves: explicit planar faces, no retarget.

    The known canonical arm lies inside y in [1.0,1.4], z in [-.02,.23].
    Changing x=.13 to .23 moves the armhole past the shoulder, while retaining
    elbow/wrist enclosure. This is a topology coupon, not an anatomically fitted
    garment or accepted body-contact state.
    """
    positions, triangles, ids, panels = [], [], [], []
    certificate = {"patches": {}, "segments": {}}
    for side, sign in [("left", -1), ("right", 1)]:
        name, start = "sleeve." + side, len(positions)
        yz = np.array([[1., -.02], [1.4, -.02], [1.4, front_z], [1., front_z]])
        vertices = np.vstack([np.c_[np.full(4, sign * armhole_x), yz],
                              np.c_[np.full(4, sign * cuff_x), yz]])
        faces = []
        for j in range(4):
            k = (j + 1) % 4
            faces.extend([[j, k, k + 4], [j, k + 4, j + 4]])
        faces = np.asarray(faces, int)
        if sign < 0:
            faces = faces[:, ::-1]
        global_ids = list(range(start, start + len(vertices)))
        panels.append({"name": name, "start": start, "vertices": len(vertices),
                       "face_start": len(triangles), "faces": len(faces)})
        certificate["patches"][name] = {"local_faces": faces.tolist(), "global_vertices": global_ids}
        for suffix, indices in [("cap.front", [0, 1, 2]), ("cap.back", [2, 3, 0]), ("cuff", [4, 5, 6, 7])]:
            certificate["segments"][name + "." + suffix] = {"local_vertices": indices}
        positions.extend(vertices.tolist())
        triangles.extend((faces + start).tolist())
        ids.extend(global_ids)
    return {"positions": np.asarray(positions), "triangles": triangles, "global_ids": ids,
            "panels": panels, "source_sewing": certificate, "body": _packed_body()}


def _snapshot(data):
    return json.dumps(data, sort_keys=True, separators=(",", ":"), default=lambda value: np.asarray(value).tolist())


class ArmWearOracleContracts(unittest.TestCase):
    def test_analytic_full_enclosure_and_all_inputs_readonly(self):
        data = prism_fixture()
        before = _snapshot(data)
        result = oracle.check_arm_wear(data, data["positions"])
        self.assertEqual(_snapshot(data), before)
        self.assertTrue(result["both_arm_chains_enclosed"])
        self.assertTrue(result["both_arms_threaded"])
        for row in result["sleeves"]:
            self.assertEqual(row["arm_threading_status"], "FULL_CHAIN_ENCLOSED")
            self.assertEqual(row["arm_chain"]["inside_count"], 65)
            self.assertTrue(row["arm_chain"]["ray_solid_angle_agree"])
            self.assertFalse(row["actual_sleeve_bone_surface_hits"])
        self.assertEqual(result["physical_fit"], "NOT_RUN")
        self.assertEqual(result["body_contact_acceptance"], "NOT_RUN")
        self.assertEqual(result["cloth_self_acceptance"], "NOT_RUN")

    def test_one_armhole_entry_allows_shoulder_in_torso(self):
        data = prism_fixture(armhole_x=.23)
        result = oracle.check_arm_wear(data, data["positions"])
        self.assertFalse(result["both_arm_chains_enclosed"])
        self.assertTrue(result["both_arms_threaded"])
        for row in result["sleeves"]:
            self.assertEqual(row["arm_threading_status"], "THREADED_THROUGH_ARMHOLE")
            self.assertFalse(row["joint_checks"]["shoulder"]["inside_ray"])
            self.assertTrue(row["joint_checks"]["elbow"]["inside_ray"])
            self.assertTrue(row["joint_checks"]["wrist"]["inside_ray"])
            self.assertTrue(row["distal_elbow_to_wrist_chain_inside"])
            self.assertEqual(len(row["virtual_cap_bone_hits"]), 1)
            self.assertEqual(row["virtual_cap_bone_hits"][0]["opening"], "armhole")

    def test_empty_garment_with_disjoint_body_bounds_is_rejected(self):
        data = prism_fixture()
        moved = data["positions"] + [3., 0., 0.]
        body = np.frombuffer(base64.b64decode(data["body"]["positions"]), "<f4").reshape(-1, 3)
        # Exact finite negative: no body face can intersect disjoint AABBs.
        self.assertGreater(moved[:, 0].min(), body[:, 0].max())
        result = oracle.check_arm_wear(data, moved)
        self.assertFalse(result["both_arms_threaded"])
        for row in result["sleeves"]:
            self.assertEqual(row["arm_chain"]["inside_count"], 0)
            self.assertEqual(row["arm_threading_status"], "MISROUTED_OR_UNCOVERED")

    def test_wrist_exit_through_cuff_and_through_real_fabric_are_rejected(self):
        for fixture, opening in [(prism_fixture(cuff_x=.40), "cuff"), (prism_fixture(front_z=.12), "fabric")]:
            result = oracle.check_arm_wear(fixture, fixture["positions"])
            self.assertFalse(result["both_arms_threaded"])
            for row in result["sleeves"]:
                self.assertEqual(row["arm_threading_status"], "MISROUTED_OR_UNCOVERED")
                self.assertFalse(row["joint_checks"]["wrist"]["inside_ray"])
                if opening == "cuff":
                    self.assertTrue(any(hit["opening"] == "cuff" for hit in row["virtual_cap_bone_hits"]))
                else:
                    self.assertTrue(row["actual_sleeve_bone_surface_hits"])

    def test_wrong_opening_label_is_not_accepted_as_armhole_entry(self):
        data = prism_fixture(armhole_x=.23)
        segments = data["source_sewing"]["segments"]
        for name in ["sleeve.left", "sleeve.right"]:
            segments[name + ".cap.front"]["local_vertices"] = [4, 5, 6]
            segments[name + ".cap.back"]["local_vertices"] = [6, 7, 4]
            segments[name + ".cuff"]["local_vertices"] = [0, 1, 2, 3]
        result = oracle.check_arm_wear(data, data["positions"])
        self.assertFalse(result["both_arms_threaded"])
        for row in result["sleeves"]:
            self.assertEqual(row["arm_threading_status"], "MISROUTED_OR_UNCOVERED")
            self.assertEqual(row["virtual_cap_bone_hits"][0]["opening"], "cuff")

    def test_nonzero_aliases_and_unchecked_caps_are_inconclusive(self):
        data = prism_fixture()
        panel = data["panels"][-1]
        data["positions"] = np.vstack([data["positions"], data["positions"][panel["start"]] + [.0001, 0., 0.]])
        data["global_ids"].append(data["global_ids"][panel["start"]])
        data["source_sewing"]["patches"][panel["name"]]["global_vertices"].append(data["global_ids"][-1])
        panel["vertices"] += 1
        result = oracle.check_arm_wear(data, data["positions"])
        self.assertGreater(result["max_source_alias_gap_mm"], .09)
        self.assertFalse(result["both_arms_threaded"])
        self.assertTrue(all(row["arm_threading_status"] == "INCONCLUSIVE" for row in result["sleeves"]))
        data = prism_fixture()
        result = oracle.check_arm_wear(data, data["positions"], audit_virtual_caps=False)
        self.assertFalse(result["both_arms_threaded"])
        self.assertTrue(all(row["arm_threading_status"] == "INCONCLUSIVE" for row in result["sleeves"]))

    def test_wrong_cap_geometry_near_boundary_and_changed_recorded_faces_fail_closed(self):
        data = prism_fixture()
        for panel in data["panels"]:
            # Make the cuff boundary a bow tie, keeping its declared topology.
            a, b = panel["start"] + 5, panel["start"] + 6
            data["positions"][[a, b]] = data["positions"][[b, a]]
        result = oracle.check_arm_wear(data, data["positions"])
        self.assertFalse(result["both_arms_threaded"])
        self.assertTrue(all(row["arm_threading_status"] == "INCONCLUSIVE" for row in result["sleeves"]))
        data = prism_fixture(cuff_x=.431185)
        result = oracle.check_arm_wear(data, data["positions"])
        self.assertFalse(result["both_arms_threaded"])
        self.assertTrue(all(64 in row["arm_chain"]["near_boundary_indices"] for row in result["sleeves"]))
        data = prism_fixture()
        data["triangles"][0] = data["triangles"][1]
        result = oracle.check_arm_wear(data, data["positions"])
        self.assertFalse(result["both_arms_threaded"])
        self.assertIn("Recorded sleeve triangles differ", result["sleeves"][0]["error"])

    def test_raw_joint_recompute_ignores_saved_xyz_but_rejects_bad_provenance(self):
        data = prism_fixture()
        baseline = oracle.check_arm_wear(data, data["positions"])
        record = json.loads(oracle.PROXY_METADATA_FILE.read_text())
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "proxy-arm-joints.json"
            for side_joints in record["joint_coordinates"].values():
                for joint in side_joints.values():
                    joint["canonical_m"] = [999., 999., 999.]
            path.write_text(json.dumps(record))
            with patch.object(oracle, "PROXY_METADATA_FILE", path):
                independent = oracle.check_arm_wear(data, data["positions"])
                self.assertTrue(independent["both_arms_threaded"])
                for before, after in zip(baseline["sleeves"], independent["sleeves"]):
                    self.assertEqual(before["joint_checks"], after["joint_checks"])
                record["source_obj"]["sha256"] = "0" * 64
                path.write_text(json.dumps(record))
                with self.assertRaisesRegex(ValueError, "provenance"):
                    oracle.check_arm_wear(data, data["positions"])
        changed = deepcopy(data)
        points = np.frombuffer(base64.b64decode(changed["body"]["positions"]), "<f4").copy()
        points[0] += .0001
        changed["body"]["positions"] = base64.b64encode(points.tobytes()).decode()
        with self.assertRaisesRegex(ValueError, "stale source SHA"):
            oracle.check_arm_wear(changed, changed["positions"])


def actual_regressions(positive_run, negative_run):
    """Read actual recorded f32 frames; never synthesise a replacement frame."""
    positive_raw = (positive_run / "input.json").read_bytes()
    positive = json.loads(positive_raw)
    before = _snapshot(positive)
    results = []
    for phase, raw in [("input", None), ("preparation-final.bin", (positive_run / "preparation-final.bin").read_bytes())]:
        positions = np.asarray(positive["positions"]) if raw is None else np.frombuffer(raw, "<f4").astype(float).reshape(-1, 3)
        result = oracle.check_arm_wear(positive, positions)
        assert result["both_arms_threaded"], result
        if phase == "input":
            assert all(row["arm_chain"]["inside_count"] == 65 for row in result["sleeves"])
        else:
            assert all(row["arm_threading_status"] == "THREADED_THROUGH_ARMHOLE" for row in result["sleeves"])
            assert all(row["arm_chain"]["inside_count"] == 57 for row in result["sleeves"])
        results.append({"run": str(positive_run), "phase": phase, "expected": "THREADED",
                        "input_sha256": _sha(positive_raw), "positions_sha256": None if raw is None else _sha(raw), **result})
    moved = np.asarray(positive["positions"]) + [3., 0., 0.]
    body = np.frombuffer(base64.b64decode(positive["body"]["positions"]), "<f4").reshape(-1, 3)
    assert moved[:, 0].min() > body[:, 0].max()
    result = oracle.check_arm_wear(positive, moved)
    assert not result["both_arms_threaded"]
    assert all(row["arm_chain"]["inside_count"] == 0 for row in result["sleeves"])
    results.append({"run": str(positive_run), "phase": "SYNTHETIC NEGATIVE: entire garment +3m X",
                    "expected": "NOT_THREADED", "body_cloth_AABB_disjoint": True, **result})
    assert _snapshot(positive) == before
    negative_raw = (negative_run / "input.json").read_bytes()
    negative = json.loads(negative_raw)
    before = _snapshot(negative)
    recording = json.loads((negative_run / "trajectory.json").read_text())
    assert recording["input_sha256"] == _sha(negative_raw)
    for index, expected_counts in [(0, [22, 22]), (60, [15, 16])]:
        raw = base64.b64decode(recording["frames"][index]["positions"], validate=True)
        positions = np.frombuffer(raw, "<f4").astype(float).reshape(-1, 3)
        result = oracle.check_arm_wear(negative, positions)
        assert not result["both_arms_threaded"]
        assert [row["arm_chain"]["inside_count"] for row in result["sleeves"]] == expected_counts
        assert all(row["actual_sleeve_bone_surface_hits"] for row in result["sleeves"])
        results.append({"run": str(negative_run), "frame": index, "expected": "NOT_THREADED",
                        "input_sha256": _sha(negative_raw), "positions_sha256": _sha(raw), **result})
    assert _snapshot(negative) == before
    return {"contract_verdict": "PASS", "checks": results,
            "scope": "Actual recorded wearing-topology regressions plus explicit synthetic negative; not physical acceptance",
            "physical_fit": "NOT_RUN", "physical_acceptance": "NOT_RUN"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--positive-run", type=Path)
    parser.add_argument("--negative-run", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    outcome = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ArmWearOracleContracts))
    if not outcome.wasSuccessful():
        raise SystemExit(1)
    if args.positive_run or args.negative_run:
        if not all([args.positive_run, args.negative_run, args.output]):
            parser.error("Actual regressions require --positive-run, --negative-run and --output")
        report = actual_regressions(args.positive_run, args.negative_run)
        report["oracle_sha256"] = _sha(Path(oracle.__file__).read_bytes())
        report["test_sha256"] = _sha(Path(__file__).read_bytes())
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        print(json.dumps({"contract_verdict": report["contract_verdict"], "actual_checks": len(report["checks"]),
                          "physical_fit": report["physical_fit"]}))
