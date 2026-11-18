#!/usr/bin/env python3
"""Pinned Anthropic arithmetic, with measured scope and unknown resources preserved."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from build_functional_review import normalize_benchmark

HERE = Path(__file__).resolve().parent

def aggregate(iteration):
    runs = sorted(iteration.glob('eval-*/*/run-*'))
    if not runs: raise ValueError('No actual runs')
    records = {}
    for run in runs:
        grade=json.loads((run/'grading.json').read_text())
        meta=json.loads((run/'eval_metadata.json').read_text())
        ex=grade['expectations']; expected=meta['assertions']
        if [x['text'] for x in ex] != expected: raise ValueError('Frozen assertion mismatch '+str(run))
        if any(type(x['passed']) is not bool or not x.get('evidence') for x in ex):raise ValueError('Missing evidence '+str(run))
        passed=sum(x['passed'] for x in ex); s=grade['summary']
        if (s['passed'],s['failed'],s['total']) != (passed,len(ex)-passed,len(ex)) or abs(s['pass_rate']-passed/len(ex))>1e-10:raise ValueError('Wrong summary '+str(run))
        records[(meta['eval_id'],run.parent.name,int(run.name.split('-')[-1]))]=(grade,meta)
    for case in iteration.glob('eval-*'):
        configurations={p.name for p in case.iterdir() if p.is_dir() and list(p.glob('run-*/grading.json'))}
        if configurations!={'with_skill','old_skill'}:raise ValueError('Paired actual runs required '+str(case))
    raw=iteration/'benchmark-upstream-raw.json'
    # Do not mutate real grades. Null timing and proxy character counts must not
    # enter upstream arithmetic as model tokens or an invented zero duration.
    with tempfile.TemporaryDirectory(prefix='commerce-official-aggregate-') as directory:
        projection=Path(directory)
        for run in runs:
            target=projection/run.relative_to(iteration);target.mkdir(parents=True)
            grade=json.loads((run/'grading.json').read_text());grade.pop('timing',None);grade.pop('execution_metrics',None)
            (target/'grading.json').write_text(json.dumps(grade))
            shutil.copyfile(run/'eval_metadata.json',target/'eval_metadata.json')
        command=[sys.executable,'-m','scripts.aggregate_benchmark',str(projection),'--skill-name','garment-body-six-view','--output',str(raw.resolve())]
        result=subprocess.run(command,cwd=HERE/'upstream',text=True,capture_output=True)
    (iteration/'aggregate-upstream.log').write_text(result.stdout+result.stderr)
    if result.returncode:raise RuntimeError('Official aggregation failed; inspect aggregate-upstream.log')
    data=json.loads(raw.read_text())
    if len(data['runs'])!=len(runs):raise ValueError('An execution was omitted')
    split_counts={}
    for run in data['runs']:
        grade,meta=records[(run['eval_id'],run['configuration'],run['run_number'])]
        run['eval_name']=meta.get('eval_name',str(run['eval_id']))
        run['split']=meta.get('split','development')
        run['result'].update(time_seconds=None,tokens=None,tool_calls=None,errors=None,overall_verdict=grade.get('overall_verdict','NOT_RUN'))
        split_counts[run['split']]=split_counts.get(run['split'],0)+1
    data=normalize_benchmark(data)
    for name,summary in data['run_summary'].items():
        summary.pop('time_seconds',None);summary.pop('tokens',None)
    configs=[k for k in data['run_summary'] if k!='delta']
    a,b=(data['run_summary'][k]['pass_rate']['mean'] for k in configs)
    data['run_summary']['delta']={'pass_rate':f'{a-b:+.4f}'}
    data['metadata'].update(protocol='Real e-commerce image tasks, explicit isolated subagents with frozen old vs revised skill; not native Claude routing',
        resource_metrics='Executor completion token and duration telemetry unavailable; actual solver timings have a narrower scope and are not compared.',
        split_run_counts=split_counts)
    data['notes']=[
        'Actual executions of independent solvers and Image Gen calls on new retailer images, not replaying the same body as a claimed skill gain.',
        'One execution per configuration/case; standard deviation is across different tasks, not repeated-run reliability or statistical significance.',
        'Case A tests complete six-image generation plus a shared adjustable body; pose-only cases explicitly do not test fresh six-image quality.',
        'Source provenance, cm/FK reconstruction, same-state views, original-region fit, visible action, three-dimensional plausibility and measurement claims are separate criteria.',
        'Any critical failure vetoes overall acceptance; assertion pass fraction is not pose accuracy, real-person measurement accuracy or physical cloth contact.',
        'A held-out case is activated only after the revised skill is frozen; its result is reported separately and not used for development edits.',
        'Benchmark-upstream-raw.json preserves official arithmetic and its zero fallback placeholders; the displayed benchmark removes unknown token/time values.',
        'Native Claude triggering remains BLOCKED. No cost, speed or general real-person accuracy advantage is established.'
    ]
    if (iteration/'analysis.json').exists():data['notes']+=json.loads((iteration/'analysis.json').read_text())
    (iteration/'benchmark.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    lines=['# Commerce functional benchmark','','| Configuration | Assertion mean ± SD across cases |','| --- | --- |']
    for config in configs:
        stat=data['run_summary'][config]['pass_rate'];lines.append(f"| {config} | {stat['mean']:.4f} ± {stat['stddev']:.4f} |")
    (iteration/'benchmark.md').write_text('\n'.join(lines+['']+['- '+x for x in data['notes']])+'\n')
    return data

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('iteration',type=Path)
    result=aggregate(parser.parse_args().iteration.resolve());print(json.dumps(result['run_summary'],indent=2))
