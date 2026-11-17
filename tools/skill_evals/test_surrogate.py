"""Negative controls for reporting explicit routing decisions without inflation."""
import unittest
from score_surrogate import PROTOCOL, score


class SurrogateScoreTests(unittest.TestCase):
    labels = [dict(case_id='a', should_trigger=True), dict(case_id='b', should_trigger=False)]

    def observation(self, rows):
        return dict(protocol=PROTOCOL, decisions=rows)

    def test_confusion_and_native_boundary(self):
        result = score(self.labels, self.observation([dict(case_id='a', trigger=False), dict(case_id='b', trigger=True)]))
        self.assertEqual(result['correct'], 0)
        self.assertEqual(result['confusion'], dict(tp=0, tn=0, fp=1, fn=1))
        self.assertIsNone(result['native_trigger_results'])

    def test_missing_duplicate_and_unknown_decisions_rejected(self):
        for rows in [[dict(case_id='a', trigger=True)], [dict(case_id='a', trigger=True)] * 2,
                     [dict(case_id='a', trigger=True), dict(case_id='x', trigger=False)]]:
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                score(self.labels, self.observation(rows))

    def test_string_boolean_and_unlabeled_protocol_rejected(self):
        with self.assertRaises(ValueError):
            score(self.labels, self.observation([dict(case_id='a', trigger='true'), dict(case_id='b', trigger=False)]))
        with self.assertRaises(ValueError):
            score(self.labels, dict(protocol='native', decisions=[]))


if __name__ == '__main__':
    unittest.main()
