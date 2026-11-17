#!/usr/bin/env python3
"""Run pinned official aggregation, then remove unavailable resource metrics."""
import argparse
import datetime
import json
from pathlib import Path
import subprocess
import sys
import shutil
import tempfile

from build_functional_review import normalize_benchmark

HERE = Path(__file__).resolve().parent


def aggregate(workspace):
    runs = sorted(workspace.glob('eval-*/*/run-*'))
    if not runs:
        raise ValueError('No functional execution runs')
    for run in runs:
        grading = json.loads((run / 'grading.json').read_text())
        expectations = grading['expectations']
        if not expectations or any(type(e['passed']) is not bool or not e.get('evidence') for e in expectations):
            raise ValueError('Incomplete evidence-backed grading: ' + str(run))
        expected_count = len(json.loads((run / 'eval_metadata.json').read_text())['assertions'])
        if len(expectations) != expected_count:
            raise ValueError('Grading does not cover frozen assertions: ' + str(run))
        passed = sum(e['passed'] for e in expectations)
        summary = grading['summary']
        if (summary['passed'] != passed or summary['total'] != len(expectations)
                or summary['failed'] != len(expectations) - passed
                or abs(summary['pass_rate'] - passed / len(expectations)) > 1e-12):
            raise ValueError('Incorrect grading summary: ' + str(run))
    raw = workspace / 'benchmark-upstream-raw.json'
    # Pinned upstream arithmetic cannot accept null timing. Keep original null
    # observations intact and give it a grading-only temporary projection. Its
    # default zero metrics are placeholders, removed below before interpretation.
    with tempfile.TemporaryDirectory(prefix='anthropic-grading-only-') as directory:
        projection = Path(directory)
        for run in runs:
            target = projection / run.relative_to(workspace)
            target.mkdir(parents=True)
            for name in ['grading.json', 'eval_metadata.json']:
                shutil.copyfile(run / name, target / name)
        command = [sys.executable, '-m', 'scripts.aggregate_benchmark', str(projection),
                   '--skill-name', 'garment-body-six-view', '--output', str(raw)]
        result = subprocess.run(command, cwd=HERE / 'upstream', text=True, capture_output=True)
    (workspace / 'aggregate-upstream.log').write_text(result.stdout + result.stderr)
    if result.returncode:
        raise RuntimeError('Official aggregator failed; see aggregate-upstream.log')
    benchmark = json.loads(raw.read_text())
    if len(benchmark['runs']) != len(runs):
        raise ValueError('Official aggregation omitted an execution')
    for run in benchmark['runs']:
        # Completion notifications did not provide tokens. The official fallback
        # from character counts or zero is not a model-token observation.
        run['result'].update(tokens=None, time_seconds=None, tool_calls=None, errors=None)
    benchmark = normalize_benchmark(benchmark)
    for config, summary in benchmark['run_summary'].items():
        if config != 'delta':
            summary.pop('time_seconds', None)
            summary.pop('tokens', None)
    configs = [k for k in benchmark['run_summary'] if k != 'delta']
    if len(configs) == 2:
        a, b = [benchmark['run_summary'][k]['pass_rate']['mean'] for k in configs]
        benchmark['run_summary']['delta'] = {'pass_rate': f'{a-b:+.4f}'}
    metadata = benchmark['metadata']
    metadata.update(timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    executor_model='Inherited session subagent model; ID not exposed',
                    protocol='Executed synthetic-control functional tasks; not native Claude routing',
                    resource_metrics='Tokens unavailable. Raw executor wallclock scopes differ; no time/token comparison.')
    benchmark['native_trigger_results'] = None
    benchmark['notes'] = [
        'Actual OBJ/mask/browser/output executions, not plan-only or metadata routing judgments.',
        'Three controlled tasks, one execution per configuration/task; standard deviation is across tasks, not repeated-run reliability.',
        'Synthetic controls do not validate real human anatomy, cloth fit, or the full six-image generation workflow.',
        'Token notification metadata was unavailable. Executor wallclock scopes differed; raw timing is retained, comparative time/token metrics omitted.',
        'benchmark-upstream-raw.json preserves official aggregation, including fallback placeholders; only this normalized benchmark is used for interpretation.'
    ]
    analysis_path = workspace / 'analysis.json'
    if analysis_path.exists():
        notes = json.loads(analysis_path.read_text())
        if not isinstance(notes, list) or any(not isinstance(note, str) for note in notes):
            raise ValueError('Expected an analyst JSON array of notes')
        benchmark['notes'] += notes
    (workspace / 'benchmark.json').write_text(json.dumps(benchmark, ensure_ascii=False, indent=2))
    lines = ['# Functional benchmark', '', '| Configuration | Assertion pass rate (mean ± SD across cases) |', '| --- | --- |']
    for config in configs:
        stat = benchmark['run_summary'][config]['pass_rate']
        lines.append(f"| {config} | {stat['mean']:.4f} ± {stat['stddev']:.4f} |")
    lines += ['', *['- ' + note for note in benchmark['notes']]]
    (workspace / 'benchmark.md').write_text('\n'.join(lines) + '\n')
    return benchmark


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workspace', type=Path)
    args = parser.parse_args()
    result = aggregate(args.workspace.resolve())
    print(json.dumps(result['run_summary'], indent=2))
