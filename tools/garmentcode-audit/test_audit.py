"""Known geometry, actual archived output, and malformed file controls."""
import tempfile
from pathlib import Path
import unittest

import numpy as np
import audit


class AuditTests(unittest.TestCase):
    def test_archived_fault_is_not_a_false_positive(self):
        path = audit.ROOT / 'web/garmentcode-preview/demo/mesh_sim.obj'
        v, f = audit.read_obj(path, .01)
        expected = [[4572, 4773], [4574, 5291], [4773, 5291]]
        self.assertEqual(audit.oracle.intersect_pairs(v, f), expected)
        self.assertEqual(audit.cgal_pairs(v, f), expected)

    def test_containment_without_surface_crossing_fails(self):
        body_v, body_f = audit.oracle._cube()
        v = np.array([[0., 0., 0.], [.2, 0., 0.], [0., .2, 0.]])
        f = np.array([[0, 1, 2]])
        result = audit.audit_surface(v, f, body_v, body_f)
        self.assertEqual(result['body_face_pairs'], [])
        self.assertEqual(result['strict_inside_vertex_ids'], [0, 1, 2])
        self.assertEqual(result['collision_verdict'], 'FAIL')

    def test_disjoint_surface_is_accepted(self):
        body_v, body_f = audit.oracle._cube()
        v = np.array([[3., 0., 0.], [3., .2, 0.], [3., 0., .2]])
        result = audit.audit_surface(v, np.array([[0, 1, 2]]), body_v, body_f)
        self.assertEqual(result['collision_verdict'], 'PASS_DISCRETE_SURFACE')

    def test_invalid_body_never_gets_a_volume_pass(self):
        body_v, body_f = audit.oracle._cube()
        v = np.array([[3., 0., 0.], [3., .2, 0.], [3., 0., .2]])
        result = audit.audit_surface(v, np.array([[0, 1, 2]]), body_v, body_f, body_volume_valid=False)
        self.assertIsNone(result['strict_inside_vertex_ids'])
        self.assertEqual(result['interior_verdict'], 'UNKNOWN_INVALID_BODY')
        self.assertEqual(result['collision_verdict'], 'UNKNOWN_BODY_VOLUME')

    def test_cgal_controls(self):
        # Shared-edge fold is legal; an overlap beyond that edge is not.
        v = np.array([[0., 0., 0.], [1., 0., 0.], [0., 1., 0.], [0., 0., 1.]])
        self.assertEqual(audit.cgal_pairs(v, np.array([[0, 1, 2], [1, 0, 3]])), [])
        v[3] = [.2, .2, 0.]
        self.assertEqual(audit.cgal_pairs(v, np.array([[0, 1, 2], [1, 0, 3]])), [[0, 1]])

    def test_invalid_obj_rejected(self):
        for text in ('v nan 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n',
                     'v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 4\n',
                     'v 0 0 0\nv 1 0 0\nv 0 1 0\nf -1 2 3\n'):
            with self.subTest(text=text), tempfile.TemporaryDirectory() as folder:
                path = Path(folder) / 'bad.obj'
                path.write_text(text)
                with self.assertRaises(ValueError):
                    audit.read_obj(path, .01)

    def test_all_existing_analytic_controls(self):
        result = audit.oracle.analytic_tests()
        self.assertEqual(result['test_count'], 23)
        self.assertTrue(result['all_passed'])


if __name__ == '__main__':
    unittest.main()
