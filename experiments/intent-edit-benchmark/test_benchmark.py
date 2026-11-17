from pathlib import Path
from copy import deepcopy
import json
import subprocess
import sys
import tempfile
import unittest
import yaml
import engine

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[1]
INPUT=REPO/'patterns/fitted-tshirt'

class PublicBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='intent-benchmark-test-')
        cls.work=Path(cls.temp.name);cls.out=cls.work/'all'
        p=subprocess.run([sys.executable,str(ROOT/'run_benchmark.py'),'--output',str(cls.out)],capture_output=True,text=True)
        cls.run_log=p.stdout+p.stderr
        if p.returncode:raise AssertionError(cls.run_log)
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def test_four_actual_case_outputs(self):
        rows=json.loads((self.out/'generation-results.json').read_text())
        self.assertEqual(4,sum(r.get('generation')=='PASS' for r in rows))
        for r in rows[:4]:
            d=self.out/r['case'];self.assertTrue((d/'output.dxf').is_file());self.assertTrue((d/'new-spec.yaml').is_file())
    def test_deterministic_geometry_and_spec(self):
        second=self.work/'second'
        p=subprocess.run([sys.executable,str(ROOT/'run_benchmark.py'),'--output',str(second)],capture_output=True,text=True)
        self.assertEqual(0,p.returncode,p.stdout+p.stderr)
        for d in self.out.iterdir():
            if d.is_dir() and (d/'new-spec.yaml').exists():
                for name in ['new-spec.yaml','output.dxf','spec-diff.json','geometry-patch.json']:
                    self.assertEqual((d/name).read_bytes(),(second/d.name/name).read_bytes())
    def test_three_negative_cases_have_no_design_output(self):
        expected={'05_uncalibrated_cm':'BLOCKED','06_ambiguous_comfort':'BLOCKED','07_invalid_cuff':'REJECTED'}
        for cid,status in expected.items():
            d=self.out/cid;r=json.loads((d/'case-result.json').read_text())
            self.assertEqual(status,r['status']);self.assertFalse((d/'output.dxf').exists());self.assertFalse((d/'new-spec.yaml').exists())
    def test_actual_request_cli_preflight(self):
        for i,text in enumerate(['袖子加长2厘米','抬手更舒服','袖口展开宽减少1000U']):
            out=self.work/('request'+str(i))
            p=subprocess.run([sys.executable,str(ROOT/'run_benchmark.py'),'--intent',text,'--output',str(out)],capture_output=True,text=True)
            self.assertEqual(0,p.returncode,p.stdout+p.stderr)
            self.assertIn(json.loads((out/'case-result.json').read_text())['status'],['BLOCKED','REJECTED'])
            self.assertFalse((out/'output.dxf').exists())
    def test_existing_output_is_not_reused_for_blocked_request(self):
        out=self.work/'old';out.mkdir();(out/'output.dxf').write_bytes(b'previous result')
        p=subprocess.run([sys.executable,str(ROOT/'run_benchmark.py'),'--intent','袖子加长2厘米','--output',str(out)],capture_output=True,text=True)
        self.assertNotEqual(0,p.returncode);self.assertEqual(b'previous result',(out/'output.dxf').read_bytes());self.assertFalse((out/'case-result.json').exists())
    def test_supported_natural_language_intent_file(self):
        out=self.work/'intent-file'
        source=self.out/'01_sleeve_length'
        p=subprocess.run([sys.executable,str(ROOT/'run_benchmark.py'),'--intent-file',str(source/'intent.txt'),'--output',str(out)],capture_output=True,text=True)
        self.assertEqual(0,p.returncode,p.stdout+p.stderr)
        self.assertEqual((source/'output.dxf').read_bytes(),(out/'01_sleeve_length/output.dxf').read_bytes())
        self.assertEqual((source/'new-spec.yaml').read_bytes(),(out/'01_sleeve_length/new-spec.yaml').read_bytes())
    def test_production_inputs_and_calibration_not_invented(self):
        base=yaml.safe_load((INPUT/'input-spec.yaml').read_text())
        for d in self.out.iterdir():
            if not d.is_dir() or not (d/'new-spec.yaml').exists():continue
            new=yaml.safe_load((d/'new-spec.yaml').read_text())
            for key in ['工艺参数','材料选择','裁剪清单','参考尺码表','单位与坐标','交付状态']:
                self.assertEqual(base[key],new[key],key)
    def test_patch_cli_replay(self):
        d=self.out/'01_sleeve_length'
        for kind,base,patch,target in [('spec','input-spec.yaml','spec-diff.json','new-spec.yaml'),('dxf','input.dxf','geometry-patch.json','output.dxf')]:
            out=self.work/('replay-'+kind)
            p=subprocess.run([sys.executable,str(ROOT/'apply_patch.py'),kind,str(INPUT/base),str(d/patch),str(out)],capture_output=True,text=True)
            self.assertEqual(0,p.returncode,p.stdout+p.stderr);self.assertEqual((d/target).read_bytes(),out.read_bytes())
    def test_bad_base_and_old_values_leave_no_output(self):
        d=self.out/'01_sleeve_length'
        for kind,base,patch_name in [('spec','input-spec.yaml','spec-diff.json'),('dxf','input.dxf','geometry-patch.json')]:
            patch=json.loads((d/patch_name).read_text())
            for fault in ['base','old','target']:
                bad=deepcopy(patch)
                if fault=='base':bad['base_sha256']='0'*64
                elif fault=='target':bad['target_sha256']='0'*64
                else:
                    op=next(op for op in bad['operations'] if 'old' in op);op['old']='invalid old value'
                file=self.work/(kind+'-'+fault+'.json');file.write_text(json.dumps(bad,ensure_ascii=False))
                out=self.work/(kind+'-'+fault+'.output')
                p=subprocess.run([sys.executable,str(ROOT/'apply_patch.py'),kind,str(INPUT/base),str(file),str(out)],capture_output=True,text=True)
                self.assertNotEqual(0,p.returncode);self.assertFalse(out.exists())

if __name__=='__main__':unittest.main(verbosity=2)
