import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('pipeline',Path(__file__).resolve().parents[1]/'run_pipeline.py')
pipeline=importlib.util.module_from_spec(spec);spec.loader.exec_module(pipeline)


class FullCoverageGate(unittest.TestCase):
    def rows(self):return [{'frame':i,'arm_entry_pass':True,'cloth_sim_pass':True} for i in [1,2,3]]
    def check(self,rows,negatives=None):
        return pipeline.summarize(rows,3,negatives or {'all_detected':True,'control_count':7})
    def test_pass_requires_all_frames(self):self.assertTrue(self.check(self.rows())['CLOTH_SIM_PASS'])
    def test_missing_middle_frame_fails(self):self.assertFalse(self.check(self.rows()[::2])['ARM_ENTRY_PASS'])
    def test_duplicate_frame_fails(self):self.assertFalse(self.check(self.rows()+[self.rows()[1]])['ARM_ENTRY_PASS'])
    def test_middle_arm_failure_fails(self):
        rows=self.rows();rows[1]['arm_entry_pass']=False
        self.assertFalse(self.check(rows)['ARM_ENTRY_PASS'])
    def test_middle_physics_failure_fails(self):
        rows=self.rows();rows[1]['cloth_sim_pass']=False
        result=self.check(rows);self.assertTrue(result['ARM_ENTRY_PASS']);self.assertFalse(result['CLOTH_SIM_PASS'])
    def test_missing_negatives_fails(self):self.assertFalse(self.check(self.rows(),{'all_detected':False})['ARM_ENTRY_PASS'])
    def test_empty_run_fails(self):self.assertFalse(self.check([])['CLOTH_SIM_PASS'])
    def test_no_physical_or_original_promotion(self):
        result=self.check(self.rows());self.assertIsNone(result['PHYSICAL_FIT_PASS'])
        self.assertEqual(result['physical_fit_status'],'NOT_RUN')
        self.assertTrue(result['original_project_status'].startswith('BLOCKED'))


if __name__=='__main__':unittest.main()
