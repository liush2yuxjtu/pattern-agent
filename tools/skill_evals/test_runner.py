import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import run as runner
from strict_runtime import decision,NativeTrialError


class TriggerPreparationTests(unittest.TestCase):
    def test_balanced_frozen_outer_split(self):
        cases=runner.load_cases(runner.SKILL/'evals/trigger-evals.json')
        self.assertEqual(len(cases),20)
        a,b=runner.split_cases(cases)
        self.assertEqual((len(a),len(b)),(12,8))
        self.assertEqual(sum(x['should_trigger'] for x in a),6)
        self.assertEqual(sum(x['should_trigger'] for x in b),4)
        self.assertFalse({x['query'] for x in a}&{x['query'] for x in b})
        self.assertEqual((a,b),runner.split_cases(cases))
    def test_duplicate_or_non_boolean_label_rejected(self):
        for cases in [[{'query':'a','should_trigger':1},{'query':'b','should_trigger':False}],
                      [{'query':'a','should_trigger':True},{'query':'a','should_trigger':False}]]:
            with tempfile.TemporaryDirectory() as directory:
                p=Path(directory)/'eval.json';p.write_text(json.dumps(cases))
                with self.assertRaises(ValueError):runner.load_cases(p)
    def test_preparation_does_not_invent_native_scores(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)
            value=runner.prepare(runner.SKILL,runner.SKILL/'evals/trigger-evals.json',p)
            self.assertEqual(value['status'],'PREPARED')
            self.assertIsNone(value['native_trigger_results'])
            self.assertNotIn('__EVAL_DATA_PLACEHOLDER__',(p/'review.html').read_text())
            self.assertEqual(len(json.loads((p/'final-holdout.json').read_text())),8)
    def test_missing_cli_is_blocked_not_nontrigger(self):
        with mock.patch.object(runner.shutil,'which',return_value=None):
            value=runner.doctor('fixture-model',probe=True)
        self.assertEqual(value['status'],'BLOCKED')
        self.assertIsNone(value['native_trigger_results'])
    def test_upstream_sources_match_pinned_hashes(self):
        self.assertEqual(runner.integrity(),'1780c5e5a552fd4d1c9d6a7b0cab26b0c2bef064')
    def test_claude_discovery_uses_canonical_skill(self):
        link=runner.ROOT/'.claude/skills/garment-body-six-view'
        self.assertTrue(link.is_symlink())
        self.assertEqual(link.resolve(),runner.SKILL)


class NativeEventFixtureTests(unittest.TestCase):
    def event(self,name,args):
        return {'type':'assistant','message':{'content':[{'type':'tool_use','name':name,'input':args}]}}
    def test_actual_skill_and_read_events(self):
        self.assertTrue(decision(self.event('Skill',{'skill':'body-alias'}),'body-alias'))
        self.assertTrue(decision(self.event('Read',{'file_path':'/x/body-alias.md'}),'body-alias'))
    def test_wrong_skill_is_not_a_trigger(self):
        self.assertFalse(decision(self.event('Skill',{'skill':'other'}),'body-alias'))
        self.assertFalse(decision(self.event('Bash',{'command':'echo skill'}),'body-alias'))
    def test_assistant_text_claim_is_not_a_trigger(self):
        self.assertIsNone(decision({'type':'assistant','message':{'content':[{'type':'text','text':'I used body-alias'}]}},'body-alias'))
    def test_error_result_is_not_a_negative(self):
        with self.assertRaises(NativeTrialError):decision({'type':'result','subtype':'error_during_execution','is_error':True},'x')
    def test_clean_final_without_tool_is_valid_negative(self):
        self.assertFalse(decision({'type':'result','subtype':'success','result':'done'},'x'))

if __name__=='__main__':unittest.main()
