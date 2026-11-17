import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('human_state', ROOT/'scripts/inspect_human_state.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class HumanStateTests(unittest.TestCase):
    def setUp(self):
        self.state = json.loads((ROOT/'tests/fixtures/human-model.json').read_text())

    def test_structure_only_never_claims_independent_match(self):
        report = module.audit(self.state)
        self.assertEqual(report['verdict'], 'STRUCTURE_ONLY')
        self.assertIsNone(report['dimensions_matched'])
        self.assertFalse(report['neutral_mesh_checked'])

    def test_require_match_requires_mesh(self):
        with self.assertRaisesRegex(ValueError, 'needs --asset-json'):
            module.audit(self.state, require_match=True)

    def test_rejects_units_and_incompatible_version(self):
        for key, value in [('units','m'), ('version','old-loft')]:
            bad = copy.deepcopy(self.state); bad[key] = value
            with self.assertRaises(ValueError): module.audit(bad)

    def test_rejects_missing_or_nonfinite_dimensions(self):
        for value in [float('nan'), float('inf'), True, -1]:
            bad = copy.deepcopy(self.state); bad['dimensions']['height'] = value
            with self.assertRaises(ValueError): module.audit(bad)
        del self.state['measuredNeutral']['bust']
        with self.assertRaises(ValueError): module.audit(self.state)

    def test_rejects_false_residual(self):
        self.state['maximumTargetErrorCm'] = 0.5
        with self.assertRaisesRegex(ValueError, 'False maximum'): module.audit(self.state)

    def test_rejects_asset_mismatch(self):
        with self.assertRaisesRegex(ValueError, 'fingerprint'): module.audit(self.state, b'{}')
        with self.assertRaisesRegex(ValueError, 'fingerprint'): module.audit(self.state, expected_asset='0'*64)

    def test_rejects_invalid_pose(self):
        for rotation in [[0,0], [181,0,0], [0,float('nan'),0], [0,.15,0]]:
            self.state['poseDegrees'] = {'lowerarm01.L':rotation}
            with self.assertRaises(ValueError): module.audit(self.state)

    def test_rejects_invalid_coefficients(self):
        self.state['morphWeights'][0] = 3
        with self.assertRaises(ValueError): module.audit(self.state)


if __name__ == '__main__': unittest.main()
