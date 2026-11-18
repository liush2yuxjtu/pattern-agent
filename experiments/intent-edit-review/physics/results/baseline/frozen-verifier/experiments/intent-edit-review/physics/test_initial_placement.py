"""Local contracts plus optional actual-source initialisation readback.

The runtime observation reports body intrusion separately. A successful FEM
initialiser test is never a physical garment or collision acceptance result.
"""
from __future__ import annotations

import argparse
import base64
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

import numpy as np

from initial_placement import _fem_harmonic, improve_initial_placement

ROOT = Path(__file__).resolve().parents[3]


def square():
    points = np.array([[0., 0.], [1., 0.], [1., 1.], [0., 1.], [.17, .31]])
    faces = np.array([[0, 1, 4], [1, 2, 4], [2, 3, 4], [3, 0, 4]])
    return points, faces


class InitialPlacementContracts(unittest.TestCase):
    def test_uv_metric_affine_precision_on_nonuniform_mesh(self):
        points, faces = square()
        boundary = np.c_[points[:4], .3 * points[:4, 0] + .2 * points[:4, 1]]
        result = _fem_harmonic(points, faces, boundary)
        expected = np.r_[points[4], .3 * points[4, 0] + .2 * points[4, 1]]
        np.testing.assert_allclose(result[4], expected, atol=1e-14, rtol=0)
        # An unweighted four-neighbour graph would put this interior at (.5,.5),
        # so this coupon distinguishes the fixed bug rather than mirroring code.
        self.assertGreater(np.linalg.norm(result[4, :2] - [.5, .5]), .3)

    def test_fem_orientation_independence_and_exact_boundary(self):
        points, faces = square()
        values = np.c_[points[:4], np.zeros(4)]
        a = _fem_harmonic(points, faces, values)
        b = _fem_harmonic(points, faces[:, ::-1], values)
        np.testing.assert_allclose(a, b, atol=1e-14, rtol=0)
        self.assertEqual(a[:4].tobytes(), values.tobytes())

    def test_invalid_material_geometry_and_unanchored_component(self):
        with self.assertRaisesRegex(ValueError, "Degenerate"):
            _fem_harmonic([[0, 0], [1, 0], [2, 0]], [[0, 1, 2]], [[0, 0], [1, 0]])
        points = np.array([[0, 0], [1, 0], [0, 1], [3, 0], [4, 0], [3, 1]], float)
        with self.assertRaisesRegex(ValueError, "unanchored"):
            _fem_harmonic(points, [[0, 1, 2], [3, 4, 5]], [[0, 0, 0]])

    def _body_fixture(self):
        points, faces = square()
        boundary = np.c_[points[:4], .3 * points[:4, 0] + .2 * points[:4, 1]]
        body = np.vstack([boundary, [9, 9, 9]])
        band = np.array([[3., 4., 5.], [4., 4., 5.], [3., 5., 5.]])
        positions = np.vstack([body, body, band])
        certificate = {"patches": {
            "front": {"flat_points": (points * 1000).tolist(), "local_faces": faces.tolist(), "boundary_count": 4},
            "back": {"flat_points": (points * 1000).tolist(), "local_faces": faces.tolist(), "boundary_count": 4},
            "band": {"flat_points": [[0, 0], [1000, 0], [0, 1000]], "local_faces": [[0, 1, 2]], "boundary_count": 3},
        }, "segments": {}, "seams": [{"name": "synthetic-seam-kept"}]}
        panels = [{"name": "front", "start": 0, "vertices": 5},
                  {"name": "back", "start": 5, "vertices": 5},
                  {"name": "band", "start": 10, "vertices": 3}]
        ids = np.array([0, 1, 2, 3, 4, 0, 1, 2, 3, 5, 6, 7, 8])
        builder = SimpleNamespace(loops={}, segments={}, targets={})
        return certificate, positions, panels, ids, builder

    def test_aliases_band_and_all_source_inputs_retained(self):
        cert, positions, panels, ids, builder = self._body_fixture()
        before = deepcopy(cert), positions.copy(), deepcopy(panels), ids.copy()
        result, metadata = improve_initial_placement(
            cert, positions, panels, ids, builder, [0, 0, 0],
            {"scale": 1., "offset_m": 0., "arm_offset_m": 0.})
        expected = [.17, .31, .3 * .17 + .2 * .31]
        np.testing.assert_allclose(result[4], expected, atol=1e-14, rtol=0)
        np.testing.assert_allclose(result[9], expected, atol=1e-14, rtol=0)
        for a, b in [(0, 5), (1, 6), (2, 7), (3, 8)]:
            self.assertEqual(result[a].tobytes(), result[b].tobytes())
        self.assertEqual(result[10:].tobytes(), positions[10:].tobytes())
        self.assertEqual(cert, before[0]); self.assertEqual(panels, before[2])
        np.testing.assert_array_equal(positions, before[1]); np.testing.assert_array_equal(ids, before[3])
        self.assertTrue(metadata["fixed_boundary_coordinates_bit_exact"])
        self.assertEqual(metadata["max_seam_alias_gap_m"], 0)
        self.assertEqual(metadata["physical_acceptance"], "NOT_RUN")

    def test_inconsistent_input_alias_is_rejected(self):
        cert, positions, panels, ids, builder = self._body_fixture()
        positions[5, 0] += 1e-5
        with self.assertRaisesRegex(ValueError, "seam aliases"):
            improve_initial_placement(cert, positions, panels, ids, builder, [0, 0, 0],
                                      {"scale": 1, "offset_m": 0, "arm_offset_m": 0})

    def test_sleeve_uses_material_domain_then_tube_not_XYZ_collapse(self):
        points, faces = square()
        corners = np.c_[points[:4, 0], -np.pi + 2 * np.pi * points[:4, 1]]
        keys = [f"edge-{i}" for i in range(4)]
        segments = {}
        for i, key in enumerate(keys):
            a, b = corners[i], corners[(i + 1) % 4]
            segments[key] = {"domain": lambda q, a=a, b=b: a + np.asarray(q)[:, None] * (b - a)}
        def tube(u, theta):
            return np.c_[u, .1 * np.cos(theta), 1 + .1 * np.sin(theta)]
        builder = SimpleNamespace(loops={"sleeve.left": [(key, False) for key in keys]},
                                  segments=segments, targets={"tube.left": tube})
        cert = {"patches": {"sleeve.left": {"flat_points": (points * 1000).tolist(),
                "local_faces": faces.tolist(), "boundary_count": 4}},
                "segments": {key: {"parameter": [0., 1.]} for key in keys}, "seams": []}
        translation = np.array([0., .1, .2])
        native = tube(corners[:, 0], corners[:, 1])
        boundary = native[:, [0, 2, 1]] * [1, 1, -1] + translation
        boundary[:, 2] = boundary[:, 2] * 2 + .03
        initial = np.vstack([boundary, [9, 9, 9]])
        result, meta = improve_initial_placement(cert, initial,
            [{"name": "sleeve.left", "start": 0, "vertices": 5}], np.arange(5),
            builder, translation, {"scale": 2, "offset_m": .03, "arm_offset_m": 0})
        domain = np.array([points[4, 0], -np.pi + 2 * np.pi * points[4, 1]])
        expected = tube(domain[:1], domain[1:])[0][[0, 2, 1]] * [1, 1, -1] + translation
        expected[2] = expected[2] * 2 + .03
        np.testing.assert_allclose(result[4], expected, atol=1e-14, rtol=0)
        self.assertEqual(result[:4].tobytes(), initial[:4].tobytes())
        self.assertIn("(u,theta)", meta["panels"][0]["method"])


def observe_actual(input_path, dxf_path, output_path, reference=None):
    """One actual initial array: independent spectrum, self pairs and body sign."""
    import trimesh
    sys.path.insert(0, str(ROOT / "services/dxf-preview"))
    sys.path.insert(0, str(ROOT / "experiments/oneshot_control"))
    from converter.core import parse_dxf
    from prepare_experiment import PhysicsBuilder
    from independent_oracle_v2 import intersect_pairs
    raw = input_path.read_bytes(); data = json.loads(raw)
    dxf = dxf_path.read_bytes()
    if hashlib.sha256(dxf).hexdigest() != data["source_dxf_sha256"]:
        raise ValueError("Observation DXF does not match the actual experiment source")
    before = json.dumps(data, sort_keys=True, separators=(",", ":"))
    P, _ = parse_dxf(dxf)
    PhysicsBuilder.boundary_step_mm = data["config"]["数值条件"].get("边界采样间距_U", 5.)
    builder = PhysicsBuilder(P, spacing=data["config"]["数值条件"]["网格采样间距_U"])
    original = np.asarray(data["positions"], float)
    result, metadata = improve_initial_placement(
        data["source_sewing"], original, data["panels"], data["global_ids"], builder,
        data["initialization"]["translation_m"], data["initialization"]["depth_placement"])
    assert before == json.dumps(data, sort_keys=True, separators=(",", ":"))
    assert len(data["source_sewing"]["seams"]) == 15
    uv = np.asarray(data["uv"]); faces = np.asarray(data["triangles"], int)
    ids = np.asarray(data["global_ids"], int)
    _, first, inverse = np.unique(ids, return_index=True, return_inverse=True)
    material = uv[faces]
    inverse_dm = np.linalg.inv(np.stack([material[:, 1] - material[:, 0], material[:, 2] - material[:, 0]], axis=-1))
    def spectrum(points):
        spatial = points[faces]
        gradient = np.stack([spatial[:, 1] - spatial[:, 0], spatial[:, 2] - spatial[:, 0]], axis=-1) @ inverse_dm
        return np.linalg.svd(gradient, compute_uv=False)
    initial_sigma, actual_sigma = spectrum(original), spectrum(result)
    panel_rows = []
    for panel in data["panels"]:
        s = slice(panel["face_start"], panel["face_start"] + panel["faces"])
        a, b = initial_sigma[s], actual_sigma[s]
        panel_rows.append({"panel": panel["name"], "before_sigma_max": float(a[:, 0].max()),
                           "after_sigma_max": float(b[:, 0].max()), "before_sigma_min": float(a[:, 1].min()),
                           "after_sigma_min": float(b[:, 1].min())})
    body = data["body"]
    bv = np.frombuffer(base64.b64decode(body["positions"]), dtype="<f4").astype(float).reshape(-1, 3)
    bf = np.frombuffer(base64.b64decode(body["indices"]), dtype="<i4").reshape(-1, 3)
    body_mesh = trimesh.Trimesh(bv, bf, process=False)
    welded = result[first]
    inside = body_mesh.contains(welded)
    inside_distance = trimesh.proximity.closest_point(body_mesh, welded[inside])[1] if inside.any() else np.array([0.])
    self_pairs = intersect_pairs(welded, inverse[faces], epsilon_m=1e-6)
    pair_indices = np.asarray(data["seams"], int)
    seam_gap = float(np.linalg.norm(result[pair_indices[:, 0]] - result[pair_indices[:, 1]], axis=1).max())
    assert seam_gap == 0.
    reference_delta = None
    if reference:
        expected = np.load(reference)
        reference_delta = float(abs(expected - result).max())
        assert reference_delta < 2e-12, reference_delta
    report = {"contract_verdict": "PASS", "scope": "One actual initialisation seed; not a solver trajectory or fit test.",
              "input_sha256": hashlib.sha256(raw).hexdigest(), "initialisation": metadata,
              "input_data_unchanged": True, "source_sewing_pairs_retained": 15,
              "body_positions_and_topology_unchanged": True, "spectrum": panel_rows,
              "strict_self_pairs": len(self_pairs), "self_examples": self_pairs[:10],
              "body_inside_roots": int(inside.sum()), "max_inside_depth_mm": float(inside_distance.max() * 1000),
              "seam_gap_mm": seam_gap * 1000, "reference_max_delta_m": reference_delta,
              "ready_state_acceptance": "FAIL" if inside.any() or self_pairs else "NOT_RUN",
              "unverified": "Full triangle-body crossings, all physical steps, material calibration and physical fit."}
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    np.save(output_path.with_suffix(".positions.npy"), result)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path)
    parser.add_argument("--dxf", type=Path, default=ROOT / "patterns/fitted-tshirt/input.dxf")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--reference", type=Path)
    args = parser.parse_args()
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(InitialPlacementContracts)
    outcome = unittest.TextTestRunner(verbosity=2).run(suite)
    if not outcome.wasSuccessful():
        raise SystemExit(1)
    if args.input:
        if not args.output:
            parser.error("--output is required for an actual input observation")
        report = observe_actual(args.input, args.dxf, args.output, args.reference)
        print(json.dumps({k: report[k] for k in ["contract_verdict", "ready_state_acceptance", "strict_self_pairs", "body_inside_roots", "max_inside_depth_mm", "reference_max_delta_m"]}, ensure_ascii=False))
