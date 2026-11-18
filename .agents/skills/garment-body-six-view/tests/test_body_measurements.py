"""Independent geometry/target-confusion controls, using an explicit flat fixture."""
import copy
import csv
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SKILL = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('body_measurements', SKILL/'scripts/export_body_measurements.py')
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


def fixture(weight=0):
    # This 2x3 rectangle is a numeric test control, never a human specimen.
    corners = [[0, 0, 0], [2, 0, 0], [2, 3, 0], [0, 3, 0]]
    order = [2, 0, 3, 1]  # Real compact meshes require explicit index remapping.
    controls = []
    lengths = {'shoulders', 'upperArmLength', 'forearmLength', 'thighLength'}
    for key in module.KEYS:
        controls.append(dict(key=key, label=key, kind='standing height' if key == 'height'
                             else 'landmark distance' if key in lengths else 'circumference',
                             path=[] if key == 'height' else [0, 1] if key in lengths else [0, 1, 2, 3, 0],
                             incr=[], decr=[]))
    controls[0]['incr'] = [[2, 0, 1, 0], [3, 0, 1, 0]]
    controls[0]['decr'] = [[2, 0, -1, 0], [3, 0, -1, 0]]
    asset = dict(schema=1, unit='cm', vertices=sum(corners, []), bodyVertexIds=order,
                 indices=[0, 1, 2, 0, 2, 3], controls=controls)
    raw = json.dumps(asset).encode()
    state = dict(version=module.MODEL_VERSION, units='cm', asset=hashlib.sha256(raw).hexdigest(),
                 dimensions={key: 170 if key == 'height' else 90 for key in module.KEYS},
                 measuredNeutral={key: 999 for key in module.KEYS},
                 morphWeights=[weight] + [0] * 11, poseDegrees={})
    actual = copy.deepcopy(corners)
    actual[2][1] += weight
    actual[3][1] += weight
    compact = {original: i + 1 for i, original in enumerate(order)}
    lines = ['v ' + ' '.join(str(x) for x in actual[i]) for i in order]
    lines += ['f ' + ' '.join(str(compact[i]) for i in face) for face in [(0, 1, 2), (0, 2, 3)]]
    return state, raw, ('\n'.join(lines) + '\n').encode()


class BodyMeasurementTests(unittest.TestCase):
    def test_known_mesh_measurements_and_compact_mapping(self):
        state, asset, mesh = fixture()
        report = module.measure(state, asset, mesh)
        self.assertEqual(report['measured_values_cm']['height'], 3)
        self.assertEqual(report['measured_values_cm']['bust'], 10)
        self.assertEqual(report['measured_values_cm']['shoulders'], 2)
        bust = next(r for r in report['measurements'] if r['name'] == 'bust')
        self.assertEqual(bust['source_mesh_vertex_indices'], [1, 3, 0, 2, 1])
        self.assertEqual(bust['method'], 'closed_neutral_surface_tape_polyline')
        self.assertFalse(report['person_accuracy_verified'])
        self.assertTrue(report['geometry_verification']['neutral_mesh_checked'])

    def test_claimed_or_changed_targets_never_become_measured_values(self):
        state, asset, mesh = fixture()
        before = module.measure(state, asset, mesh)
        changed = copy.deepcopy(state)
        changed['dimensions'] = {key: 11 for key in module.KEYS}
        changed['measuredNeutral'] = {key: 12345 for key in module.KEYS}
        changed['maximumTargetErrorCm'] = -999
        after = module.measure(changed, asset, mesh)
        self.assertEqual(before['measured_values_cm'], after['measured_values_cm'])
        self.assertEqual(after['target_dimensions_cm']['height'], 11)
        height = after['measurements'][0]
        self.assertEqual(height['value_cm'], 3)
        self.assertEqual(height['input_target_delta_cm'], -8)
        del changed['measuredNeutral']
        self.assertEqual(module.measure(changed, asset, mesh)['measured_values_cm'], after['measured_values_cm'])

    def test_actual_changed_mesh_responds_while_targets_stay_fixed(self):
        state, asset, mesh = fixture(weight=1)
        report = module.measure(state, asset, mesh)
        self.assertEqual(report['measured_values_cm']['height'], 4)
        self.assertEqual(report['measured_values_cm']['bust'], 12)
        self.assertEqual(report['target_dimensions_cm']['height'], 170)

    def test_changed_or_posed_vertices_fail_even_when_topology_unchanged(self):
        state, asset, mesh = fixture()
        altered = mesh.replace(b'v 2 3 0', b'v 2 3 1')
        with self.assertRaisesRegex(ValueError, 'does not match'):
            module.measure(state, asset, altered)
        # Rigid 90-degree pose rotation does not become neutral standing height.
        points, faces = module.parse_obj(mesh)
        posed = '\n'.join('v '+str(-y)+' '+str(x)+' '+str(z) for x, y, z in points)
        posed += '\n'+'\n'.join('f '+' '.join(str(i+1) for i in f) for f in faces)+'\n'
        with self.assertRaisesRegex(ValueError, 'does not match'):
            module.measure(state, asset, posed.encode())

    def test_topology_rejects_missing_or_reversed_faces(self):
        state, asset, mesh = fixture()
        lines = mesh.decode().splitlines()
        for altered in ['\n'.join(lines[:-1]), '\n'.join(lines[:-1]+['f 2 3 1'])]:
            with self.assertRaisesRegex(ValueError, 'topology'):
                module.measure(state, asset, altered.encode())
        # Equivalent ordering/cyclic indexing does not trigger a false rejection.
        reordered = '\n'.join(lines[:4] + ['f 1 3 2', 'f 4 1 2'])
        self.assertEqual(module.measure(state, asset, reordered.encode())['measured_values_cm']['bust'], 10)

    def test_units_fingerprint_nonfinite_or_scaled_mesh_rejected(self):
        state, asset, mesh = fixture()
        for key, value in [('units', 'm'), ('asset', '0' * 64), ('morphWeights', [float('nan')]*12)]:
            altered = copy.deepcopy(state); altered[key] = value
            with self.assertRaises(ValueError): module.measure(altered, asset, mesh)
        with self.assertRaisesRegex(ValueError, 'finite'):
            module.measure(state, asset, mesh.replace(b'v 2 3 0', b'v nan 3 0'))
        with self.assertRaisesRegex(ValueError, 'does not match'):
            module.measure(state, asset, mesh.replace(b'v 2 3 0', b'v .02 .03 0'))

    def test_csv_reports_actual_values_and_posed_identity_scope(self):
        state, asset, mesh = fixture()
        report = module.measure(state, asset, mesh, posed_obj_bytes=b'identity only')
        csv_rows = list(csv.DictReader(io.StringIO(module.csv_text(report))))
        self.assertEqual(float(csv_rows[0]['value_cm']), 3)
        self.assertEqual(float(csv_rows[0]['body_parameter_target_cm']), 170)
        self.assertFalse(report['geometry_verification']['posed_geometry_checked'])
        self.assertEqual(report['model_fingerprints']['posed_mesh_sha256'], hashlib.sha256(b'identity only').hexdigest())

    def test_real_cli_rejects_bad_mesh_without_overwriting_previous_export(self):
        state, asset, mesh = fixture()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            (path/'state.json').write_text(json.dumps(state))
            (path/'asset.json').write_bytes(asset)
            (path/'neutral.obj').write_bytes(mesh.replace(b'v 2 3 0', b'v 2 3 1'))
            (path/'output.json').write_text('previous export')
            (path/'output.csv').write_text('previous csv')
            command = [sys.executable, str(SKILL/'scripts/export_body_measurements.py'),
                       '--state', str(path/'state.json'), '--asset-json', str(path/'asset.json'),
                       '--neutral-mesh', str(path/'neutral.obj'), '--out', str(path/'output.json'),
                       '--csv', str(path/'output.csv')]
            result = subprocess.run(command, text=True, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('does not match', result.stderr)
            self.assertEqual((path/'output.json').read_text(), 'previous export')
            self.assertEqual((path/'output.csv').read_text(), 'previous csv')


if __name__ == '__main__':
    unittest.main()
