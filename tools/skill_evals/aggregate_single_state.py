#!/usr/bin/env python3
"""Use pinned official aggregation with this mixed dataset's explicit scope."""
import argparse
import json
from pathlib import Path
from aggregate_functional import aggregate


def run(workspace):
    result = aggregate(workspace)
    result['metadata']['protocol'] = 'Six explicitly injected subagent executions: controlled single-state fit, actual editor, and original-photo fit; not native Claude routing'
    result['metadata']['resource_metrics'] = 'Completion token/duration metadata unavailable; no cost or speed comparison.'
    result['notes'] = [
        'Three cases, one execution per configuration/case. Standard deviation is across heterogeneous tasks, not repeated-run reliability.',
        'Both configurations receive the same existing anatomical model and generic cm/FK/LBS runtime. The runtime is evaluation infrastructure, not an optimizer bundled in the skill.',
        'Case1 is controlled anatomical reconstruction; case2 is an actual editor workflow; case3 uses the original e-commerce photo. No new Image Gen call was made.',
        'Same-state body/pose consistency and actual joint optimization are functional claims; passing them is not perfect photograph matching, true-person measurement accuracy, or physical garment contact.',
        'Different camera protocols and self-declared objective scales in the photo runs prevent treating their raw loss delta as a causal skill-quality gain.',
        'Missing token/duration metadata remains null. Native Claude trigger testing remains BLOCKED.',
        'benchmark-upstream-raw.json retains unmodified official aggregation output; this adapter only corrects context and removes unavailable resource placeholders.',
    ]
    analysis = workspace/'analysis.json'
    if analysis.exists():
        notes = json.loads(analysis.read_text())
        if not isinstance(notes, list) or any(not isinstance(note, str) for note in notes):
            raise ValueError('Analysis must be an array of notes')
        result['notes'] += notes
    (workspace/'benchmark.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    lines = ['# Single-state functional benchmark', '', '| Configuration | Mean ± SD across cases |', '| --- | --- |']
    for config, values in result['run_summary'].items():
        if config != 'delta':
            stat = values['pass_rate']
            lines.append(f"| {config} | {stat['mean']:.4f} ± {stat['stddev']:.4f} |")
    lines += ['', *['- '+note for note in result['notes']]]
    (workspace/'benchmark.md').write_text('\n'.join(lines)+'\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workspace', type=Path)
    result = run(parser.parse_args().workspace.resolve())
    print(json.dumps(result['run_summary'], indent=2))
