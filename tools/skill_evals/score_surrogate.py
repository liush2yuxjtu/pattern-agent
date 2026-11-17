#!/usr/bin/env python3
"""Score explicit subagent routing decisions; never native trigger observations."""
import argparse
import json
from pathlib import Path


PROTOCOL = 'subagent_metadata_routing_surrogate'


def score(labels, observation):
    if observation.get('protocol') != PROTOCOL:
        raise ValueError('Expected explicitly labeled surrogate observations')
    expected = {}
    for row in labels:
        key = row['case_id']
        if key in expected or type(row['should_trigger']) is not bool:
            raise ValueError('Duplicate label ID or non-boolean label')
        expected[key] = row
    if not expected or {r['should_trigger'] for r in labels} != {True, False}:
        raise ValueError('Need nonempty positive and negative labels')
    actual = {}
    for row in observation['decisions']:
        key = row['case_id']
        if key in actual or type(row['trigger']) is not bool:
            raise ValueError('Duplicate decision ID or non-boolean decision')
        actual[key] = row
    if set(actual) != set(expected):
        raise ValueError('Decision IDs must match labels exactly')
    counts = dict(tp=0, tn=0, fp=0, fn=0)
    errors = []
    for key, row in expected.items():
        truth, prediction = row['should_trigger'], actual[key]['trigger']
        counts[('tp' if truth else 'tn') if truth == prediction else ('fn' if truth else 'fp')] += 1
        if truth != prediction:
            errors.append(dict(case_id=key, expected=truth, predicted=prediction,
                               reason=actual[key].get('reason', '')))
    return dict(protocol=PROTOCOL, scope='explicit metadata-routing judgments only; not native Skill/Read events',
                total=len(expected), correct=counts['tp'] + counts['tn'],
                confusion=counts, errors=errors, native_trigger_results=None)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--labels', type=Path, required=True)
    parser.add_argument('--observations', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = score(json.loads(args.labels.read_text()), json.loads(args.observations.read_text()))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
