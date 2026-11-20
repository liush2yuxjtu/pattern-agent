#!/usr/bin/env python3
"""Exercise gate decisions with synthetic records. No record is a human approval."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, main


SPEC = spec_from_file_location('zero_gate_runner', Path(__file__).with_name('run-zero-draft-gates.py'))
GATE = module_from_spec(SPEC)
SPEC.loader.exec_module(GATE)


class FinalGateTest(TestCase):
    def setUp(self):
        self.gates = [{'id': f'G{i}', 'passed': True} for i in range(1, 8)]
        self.subject = {'fingerprint': 'synthetic-test-only'}
        self.record = {'fingerprint': self.subject['fingerprint'], 'reviewer': 'TEST ONLY',
                       'review_date': '2026-11-20', 'decision': 'approve', 'scale_x_mm': 100.0,
                       'scale_y_mm': 99.8, 'actual_size_printed': True,
                       **dict.fromkeys(GATE.MARKS, True)}

    def verdict(self, record):
        return GATE.decide(self.gates, self.subject, record)[0]

    def test_fewer_than_five(self):
        self.gates = self.gates[:4]
        self.assertEqual(self.verdict(self.record), 'DIGITAL_FAILED')

    def test_exactly_five_distinct_plus_human(self):
        self.gates = self.gates[:5]
        self.assertEqual(self.verdict(self.record), 'APPROVED')

    def test_five_passes_do_not_override_other_failure(self):
        self.gates[-1]['passed'] = False
        self.assertEqual(self.verdict(self.record), 'DIGITAL_FAILED')

    def test_duplicate_gate_does_not_count_twice(self):
        self.gates[1]['id'] = self.gates[0]['id']
        self.assertEqual(self.verdict(self.record), 'DIGITAL_FAILED')

    def test_absent_human_always_pending(self):
        self.assertEqual(self.verdict(None), 'AWAITING_HUMAN')

    def test_explicit_human_rejection(self):
        self.assertEqual(self.verdict(dict(self.record, decision='reject')), 'HUMAN_REJECTED')

    def test_revised_file_invalidates_past_approval(self):
        with TemporaryDirectory() as folder:
            trial = Path(folder)
            (trial/'outputs/revision').mkdir(parents=True)
            (trial/'revision.json').write_text('{}')
            for name in ['pattern.dxf', 'full.pdf', 'a4.pdf']:
                (trial/'outputs/revision'/name).write_text(name)
            previous = GATE.fingerprint(trial)
            (trial/'outputs/revision/a4.pdf').write_text('synthetic-change')
            current = GATE.fingerprint(trial)
            self.assertNotEqual(current['fingerprint'], previous['fingerprint'])
            self.assertEqual(GATE.decide(self.gates, current, dict(self.record, fingerprint=previous['fingerprint']))[0],
                             'HUMAN_EVIDENCE_INVALID')

    def test_digital_scale_does_not_replace_physical_scale(self):
        for values in [{'scale_x_mm': 98}, {'scale_y_mm': None}, {'actual_size_printed': False}, {'scale_y_mm': float('nan')}]:
            with self.subTest(values=values):
                self.assertEqual(self.verdict(dict(self.record, **values)), 'HUMAN_EVIDENCE_INVALID')

    def test_each_explicit_human_check_is_required(self):
        for check in [*GATE.MARKS, 'review_date', 'reviewer', 'decision']:
            with self.subTest(check=check):
                record = {key: val for key, val in self.record.items() if key != check}
                self.assertEqual(self.verdict(record), 'HUMAN_EVIDENCE_INVALID')

    def test_complete_same_version_human_decision(self):
        self.assertEqual(self.verdict(self.record), 'APPROVED')


if __name__ == '__main__':
    main()
