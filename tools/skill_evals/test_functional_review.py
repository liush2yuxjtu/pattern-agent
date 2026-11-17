"""Regression controls for static review safety and honest resource reporting."""
import json
from pathlib import Path
import re
import tempfile
import unittest

from build_functional_review import build, normalize_benchmark


class FunctionalReviewTests(unittest.TestCase):
    def test_safe_embedded_html_and_static_feedback(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for config in ['old_skill', 'with_skill']:
                run = root / 'eval-1' / config / 'run-1'
                (run / 'outputs').mkdir(parents=True)
                (run / 'eval_metadata.json').write_text(json.dumps({'eval_id': 1, 'prompt': 'synthetic fixture'}))
                (run / 'outputs' / 'viewer.html').write_text('</script><script>window.bad=true</script>')
            document, record = build(root)
            self.assertEqual(record['runs'], 2)
            payload = re.search(r'const EMBEDDED_DATA = (.+);', document).group(1)
            self.assertNotIn('<', payload)
            self.assertIn('</script>', json.loads(payload)['runs'][0]['outputs'][0]['content'])
            self.assertIn('with_skill', json.loads(payload)['runs'][0]['id'])
            self.assertNotIn('/api/feedback', document)
            self.assertIn('anchor.download = "feedback.json"', document)

    def test_unknown_token_totals_are_not_zero_measurements(self):
        data = {'runs': [dict(eval_id=1, configuration=c, run_number=1, result={'tokens': None})
                         for c in ['old_skill', 'with_skill']],
                'run_summary': {c: {'tokens': {'mean': 0}} for c in ['old_skill', 'with_skill']},
                'metadata': {'runs_per_configuration': 99}}
        result = normalize_benchmark(data)
        self.assertEqual(result['metadata']['runs_per_configuration'], 1)
        self.assertEqual(result['runs'][0]['configuration'], 'with_skill')
        self.assertIsNone(result['runs'][0]['result']['tokens'])
        self.assertNotIn('tokens', result['run_summary']['with_skill'])


if __name__ == '__main__':
    unittest.main()
