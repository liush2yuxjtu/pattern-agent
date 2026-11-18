import unittest

import numpy as np

from fold_preview import measure_folds


class FoldGeometryTests(unittest.TestCase):
    def setUp(self):
        self.uv = np.array([[0., 0.], [1., 0.], [0., 1.], [0., -1.]])
        self.faces = np.array([[0, 1, 2], [1, 0, 3]])

    @staticmethod
    def hinge(degrees):
        radians = np.radians(degrees)
        return np.array([[0., 0., 0.], [1., 0., 0.], [0., 1., 0.],
                         [0., -np.cos(radians), np.sin(radians)]])

    def test_known_angles_and_face_winding(self):
        for degrees in (0, 30, 90, 180):
            for faces in (self.faces, np.array([[0, 1, 2], [0, 1, 3]])):
                with self.subTest(degrees=degrees, faces=faces.tolist()):
                    stats, geometry = measure_folds(self.hinge(degrees), self.uv, faces, 15)
                    self.assertEqual(stats["fold_interior_edge_count"], 1)
                    self.assertEqual(stats["fold_boundary_edge_count"], 4)
                    self.assertAlmostEqual(stats["fold_p95_deg"], degrees)
                    self.assertEqual(len(geometry[3]), int(degrees >= 15))

    def test_vertex_splits_match_only_when_both_position_and_uv_agree(self):
        xyz = self.hinge(90)
        xyz = np.vstack((xyz, xyz[:2]))
        uv = np.vstack((self.uv, self.uv[:2]))
        faces = np.array([[0, 1, 2], [5, 4, 3]])
        stats, _ = measure_folds(xyz, uv, faces, 15)
        self.assertEqual(stats["fold_interior_edge_count"], 1)
        uv[4:] += 10
        stats, _ = measure_folds(xyz, uv, faces, 15)
        self.assertEqual(stats["fold_interior_edge_count"], 0)
        self.assertIsNone(stats["fold_p95_deg"])
