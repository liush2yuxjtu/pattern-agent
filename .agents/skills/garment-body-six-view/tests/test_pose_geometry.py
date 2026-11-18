import copy
import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('poseaudit',Path(__file__).resolve().parents[1]/'scripts/audit_pose_geometry.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class PoseAuditTests(unittest.TestCase):
    def fixture(self):
        p={'root':[0,0,0],'spine01':[0,35,0],'neck01':[0,50,0],'upperleg01.L':[10,0,0],'upperleg01.R':[-10,0,0]}
        for side,x in [('L',20),('R',-20)]:p.update({f'upperarm01.{side}':[x,40,0],f'lowerarm01.{side}':[x,15,0],f'wrist.{side}':[x,-5,0]})
        rows=[{'name':n,'position':v,'parent':'spine01' if n=='neck01' else 'root' if n!='root' else None} for n,v in p.items()]
        return {'joints':rows},{'units':'cm','poseDegrees':{'root':[0,0,0]}}
    def test_known_straight_geometry(self):
        j,s=self.fixture();a=module.audit(j,s,'standing-relaxed');self.assertAlmostEqual(a['torso_lean_deg'],0);self.assertAlmostEqual(a['arms']['L']['elbow_flexion_deg'],0);self.assertEqual(a['review_flags'],[]);self.assertEqual(a['acceptance'],'NOT_ASSESSED')
    def test_arch_and_non_editor_step(self):
        j,s=self.fixture();next(x for x in j['joints'] if x['name']=='neck01')['position']=[0,35,-35];s['poseDegrees']['root'][0]=.04;a=module.audit(j,s,'standing-relaxed');self.assertAlmostEqual(a['torso_lean_deg'],45);self.assertGreaterEqual(len(a['review_flags']),2)
    def test_yaw_invariance_of_posterior_pocket_warning(self):
        j,s=self.fixture();next(x for x in j['joints'] if x['name']=='wrist.L')['position']=[20,0,-10];a=module.audit(j,s,'front-pocket');rot=copy.deepcopy(j)
        for row in rot['joints']:x,y,z=row['position'];row['position']=[z,y,-x]
        b=module.audit(rot,s,'front-pocket');self.assertEqual(a['review_flags'],b['review_flags']);self.assertAlmostEqual(a['arms']['L']['wrist_anterior_from_pelvis_cm'],-10)
    def test_invalid_geometry_rejected(self):
        j,s=self.fixture();j['joints'][0]['position'][0]=float('nan')
        with self.assertRaises(ValueError):module.audit(j,s)
    def test_only_observed_pocket_side_gets_its_prior(self):
        j,s=self.fixture();next(x for x in j['joints'] if x['name']=='wrist.R')['position']=[-20,0,-10]
        self.assertEqual(module.audit(j,s,'front-pocket',('L',))['review_flags'],[])

if __name__=='__main__':unittest.main()
