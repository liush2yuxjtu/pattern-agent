"""Consumer CLI regressions for the installed GarmentCode skill.

Use GARMENTCODE_PYTHON for the isolated environment described by the skill.
These exercise real exports, input boundaries and units, not mocked solvers.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from verify_garmentcode_preview import read_glb

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / '.agents/skills/garmentcode-preview'
SCRIPT = SKILL / 'scripts/garment_preview.py'
PYTHON = os.environ.get('GARMENTCODE_PYTHON', sys.executable)


class SkillConsumerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out = Path(self.tmp.name)

    def run_cli(self, *args):
        return subprocess.run([PYTHON, str(SCRIPT), *map(str, args)],
                              capture_output=True, text=True, timeout=60)

    def test_existing_glb_needs_no_pattern_repo_or_body_and_keeps_meters(self):
        source = ROOT / 'web/garmentcode-preview/garment.glb'
        out = self.out / 'existing'
        run = self.run_cli('build', '--mode', 'existing', '--existing-mesh', source, '--out', out)
        self.assertEqual(run.returncode, 0, run.stderr)
        before, faces_before = read_glb(source.read_bytes())
        after, faces_after = read_glb((out / 'garment.glb').read_bytes())
        self.assertEqual(faces_before, faces_after)
        self.assertEqual(before, after)
        manifest = json.loads((out / 'manifest.json').read_text())
        self.assertEqual(manifest['input']['sha256'], hashlib.sha256(source.read_bytes()).hexdigest())
        self.assertFalse(manifest['simulation']['executed'])
        self.assertFalse(manifest['mesh_generated_this_run'])
        self.assertEqual(manifest['release']['physical_fit'], 'NOT_RUN')
        self.assertTrue((out / 'preview.html').is_file())

    def test_centimeter_obj_converts_to_meter_geometry(self):
        source = self.out / 'shirt.obj'
        source.write_text('v 0 0 0\nv 100 0 0\nv 0 100 0\nf 1 2 3\n')
        out = self.out / 'obj'
        run = self.run_cli('build', '--mode', 'existing', '--existing-mesh', source, '--out', out)
        self.assertEqual(run.returncode, 0, run.stderr)
        vertices, _ = read_glb((out / 'garment.glb').read_bytes())
        self.assertEqual(max(v[0] for v in vertices), 1.0)
        self.assertEqual(max(v[1] for v in vertices), 1.0)

    def test_explicit_millimeter_scale(self):
        source = self.out / 'shirt.obj'
        source.write_text('v 0 0 0\nv 1000 0 0\nv 0 1000 0\nf 1 2 3\n')
        out = self.out / 'mm'
        run = self.run_cli('build', '--mode', 'existing', '--existing-mesh', source,
                           '--existing-scale', '.001', '--out', out)
        self.assertEqual(run.returncode, 0, run.stderr)
        vertices, _ = read_glb((out / 'garment.glb').read_bytes())
        self.assertEqual(max(v[0] for v in vertices), 1.0)

    def test_existing_output_is_preserved(self):
        sentinel = self.out / 'keep.txt'
        sentinel.write_text('prior evidence')
        source = ROOT / 'web/garmentcode-preview/garment.glb'
        run = self.run_cli('build', '--mode', 'existing', '--existing-mesh', source, '--out', self.out)
        self.assertNotEqual(run.returncode, 0)
        self.assertEqual(sentinel.read_text(), 'prior evidence')
        self.assertEqual(list(self.out.iterdir()), [sentinel])

    def test_ambiguous_pattern_directory_does_not_choose_a_sample(self):
        data = (SKILL / 'assets/example-shirt_specification.json').read_bytes()
        for name in ['a_specification.json', 'b_specification.json']:
            (self.out / name).write_bytes(data)
        run = self.run_cli('inspect', '--pattern', self.out)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn('Expected one', run.stderr)

    def test_nonfinite_pattern_rejected_before_meshing(self):
        data = json.loads((SKILL / 'assets/example-shirt_specification.json').read_text())
        first = next(iter(data['pattern']['panels'].values()))
        first['vertices'][0][0] = float('nan')
        source = self.out / 'bad_specification.json'
        source.write_text(json.dumps(data))
        run = self.run_cli('inspect', '--pattern', source)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn('non-finite', run.stderr)


if __name__ == '__main__':
    unittest.main()
