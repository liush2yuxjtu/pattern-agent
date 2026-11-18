import copy
import gzip
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('fold_inspector',ROOT/'scripts/inspect.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

def control(name):
    return json.loads(gzip.decompress((ROOT/'fixtures'/f'{name}-basic.json.gz').read_bytes()))

def hinge(degrees):
    a=math.radians(degrees)
    return {'schema':'garment-body-wear-audit-input/2','garment':[{'partId':'sleeve-test',
      'vertices':[[0,0,0],[0,.02,0],[-.02,0,0],[.02*math.cos(a),0,.02*math.sin(a)]],
      'points2d':[{'x':0,'y':0},{'x':0,'y':20},{'x':-20,'y':0},{'x':20,'y':0}],
      'triangles':[[0,1,2],[1,0,3]],'boundary':[{'a':2,'b':0,'edge':'underarm-left'}]}]}

class InspectorTests(unittest.TestCase):
    def test_frozen_control_hashes(self):
        manifest=json.loads((ROOT/'fixtures/manifest.json').read_text())
        for item in manifest['controls'].values():
            data=(ROOT/'fixtures'/item['file']).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(),item['sha256'])
            self.assertEqual(hashlib.sha256(gzip.decompress(data)).hexdigest(),item['decompressedSha256'])

    def test_actual_before_is_rejected(self):
        r=module.inspect(control('before'))
        self.assertEqual((r['status'],r['sharpCount'],r['invalidCount']),('FAIL',161,0))
        self.assertAlmostEqual(r['peak']['angleDeg'],179.65791251667937,places=7)
        self.assertEqual([p['stats']['count']for p in r['parts']],[1957,1957])
        self.assertEqual([p['excludedCount']for p in r['parts']],[73,73])
        self.assertTrue(all(p['clusters']for p in r['parts']))

    def test_actual_after_has_zero_over_limit_edges(self):
        r=module.inspect(control('after'))
        self.assertEqual((r['status'],r['sharpCount'],r['invalidCount']),('PASS',0,0))
        self.assertAlmostEqual(r['peak']['angleDeg'],31.902069243381185,places=7)
        self.assertEqual([p['stats']['count']for p in r['parts']],[1956,1956])
        self.assertTrue(all(p['excludedCount']==73 for p in r['parts']))

    def test_visible_ridge_matches_same_material_edge(self):
        before=module.inspect(control('before'));after=module.inspect(control('after'))
        old=next(e for e in before['parts'][0]['edges']if e['id']=='sleeve-right:374:400')
        def same(e):
            key=lambda p:(round(p['x'],8),round(p['y'],8))
            return sorted(map(key,e['endpointsUv']))==sorted(map(key,old['endpointsUv']))
        candidates=[e for e in after['parts'][0]['edges']if same(e)]
        self.assertEqual(len(candidates),1)
        self.assertEqual(candidates[0]['id'],'sleeve-right:373:399')
        self.assertAlmostEqual(old['angleDeg'],117.4297761571478,places=7)
        self.assertAlmostEqual(candidates[0]['angleDeg'],6.620925165371011,places=7)

    def test_flat_and_right_angle(self):
        flat=module.inspect(hinge(0),exclusion_mm=0)
        bent=module.inspect(hinge(90),exclusion_mm=0)
        self.assertEqual(flat['status'],'PASS');self.assertEqual(flat['peak']['angleDeg'],0)
        self.assertEqual(bent['status'],'FAIL');self.assertAlmostEqual(bent['peak']['angleDeg'],90)

    def test_near_foldback_not_aliased_to_ten_degrees(self):
        result=module.inspect(hinge(170),exclusion_mm=0)
        self.assertEqual(result['status'],'FAIL');self.assertAlmostEqual(result['peak']['angleDeg'],170)

    def test_smooth_cylinder_is_not_a_sharp_ridge(self):
        n=36;radius=.12
        vertices=[[radius*math.cos(2*math.pi*i/n),y,radius*math.sin(2*math.pi*i/n)]for i in range(n+1)for y in[0,.1]]
        uv=[{'x':2*math.pi*radius*1000*i/n,'y':y}for i in range(n+1)for y in[0,100]]
        triangles=[]
        for i in range(n):
            a=2*i;b=a+2;triangles.extend([[a,b,a+1],[b,b+1,a+1]])
        d={'schema':'garment-body-wear-audit-input/2','garment':[{'partId':'sleeve-cylinder','vertices':vertices,'points2d':uv,'triangles':triangles,'boundary':[{'a':0,'b':1,'edge':'underarm-left'}]}]}
        result=module.inspect(d)
        self.assertEqual(result['status'],'PASS');self.assertAlmostEqual(result['peak']['angleDeg'],10,places=6)

    def test_rigid_transform_and_scale_invariance(self):
        d=control('after');reference=module.inspect(d)
        for panel in d['garment']:
            panel['vertices']=[[3*(-v[1])+.2,3*v[0]-.7,3*v[2]+1]for v in panel['vertices']]
        result=module.inspect(d)
        self.assertEqual(result['sharpCount'],reference['sharpCount'])
        self.assertAlmostEqual(result['peak']['angleDeg'],reference['peak']['angleDeg'],places=7)

    def test_renderer_normals_do_not_affect_geometry(self):
        d=hinge(90);expected=module.inspect(d,exclusion_mm=0)
        d['garment'][0]['normals']=[[0,0,1]]*4
        self.assertEqual(module.inspect(d,exclusion_mm=0)['peak']['angleDeg'],expected['peak']['angleDeg'])

    def test_excluded_strip_keeps_evidence(self):
        r=module.inspect(hinge(90),exclusion_mm=15)
        self.assertEqual(r['parts'][0]['excludedCount'],1)
        self.assertEqual(r['parts'][0]['edges'][0]['angleDeg'],90)
        self.assertEqual(r['status'],'INVALID') # Nothing eligible is not a pass.

    def test_winding_error_is_invalid(self):
        d=hinge(0);d['garment'][0]['triangles'][1].reverse()
        r=module.inspect(d,exclusion_mm=0)
        self.assertEqual(r['status'],'INVALID');self.assertEqual(r['parts'][0]['invalidEdges'][0]['reason'],'inconsistent-winding')

    def test_nonmanifold_is_invalid(self):
        d=hinge(0);d['garment'][0]['triangles'].append([0,1,3])
        self.assertEqual(module.inspect(d,exclusion_mm=0)['status'],'INVALID')

    def test_degenerate_face_is_invalid(self):
        d=hinge(0);d['garment'][0]['vertices'][2]=[0,.01,0]
        self.assertEqual(module.inspect(d,exclusion_mm=0)['status'],'INVALID')

    def test_missing_units_semantics_or_bad_coordinates_rejected(self):
        for field in ['schema','garment']:
            d=hinge(0);del d[field]
            with self.assertRaises((ValueError,KeyError)):module.inspect(d)
        d=hinge(0);d['garment'][0]['boundary']=[]
        with self.assertRaises(ValueError):module.inspect(d)
        d=hinge(0);d['garment'][0]['vertices'][0][0]=float('nan')
        with self.assertRaises(ValueError):module.inspect(d)

    def test_public_cli_outputs_real_report_trace_and_exit_codes(self):
        with tempfile.TemporaryDirectory()as tmp:
            folder=Path(tmp)
            for name,code in [('before',2),('after',0)]:
                report,trace=folder/(name+'.json'),folder/(name+'-trace.json')
                result=subprocess.run([sys.executable,str(ROOT/'scripts/inspect.py'),'--input',str(ROOT/'fixtures'/f'{name}-basic.json.gz'),'--out',str(report),'--trace',str(trace)],capture_output=True,text=True)
                self.assertEqual(result.returncode,code,result.stderr)
                r=json.loads(report.read_text());self.assertEqual(r['status'],'FAIL'if name=='before'else'PASS')
                t=json.loads(trace.read_text())['traceEvents'][0]
                self.assertEqual(t['args']['status'],r['status']);self.assertGreater(t['dur'],0)
                self.assertTrue(r['performance']['notSimulationHistory'])
            bad=folder/'bad.json';bad.write_text('{}')
            result=subprocess.run([sys.executable,str(ROOT/'scripts/inspect.py'),'--input',str(bad),'--out',str(folder/'invalid.json')],capture_output=True,text=True)
            self.assertEqual(result.returncode,3)

if __name__=='__main__':unittest.main(verbosity=2)
