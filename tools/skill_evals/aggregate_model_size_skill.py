#!/usr/bin/env python3
"""Aggregate independent measurement-branch grades with pinned Anthropic code."""
import argparse, json, datetime, subprocess, sys, tempfile
from pathlib import Path
from build_functional_review import normalize_benchmark
HERE=Path(__file__).resolve().parent

def run(workspace):
    runs=sorted(workspace.glob('eval-*/*/run-*'))
    for run in runs:
        meta=json.loads((run/'eval_metadata.json').read_text())
        assert len(meta['assertions'])=={1:7,2:7,3:5}[meta['eval_id']]
    # The official script cannot dereference null timing/execution_metrics. A
    # temporary grading-only projection omits these unavailable resource keys;
    # original grading bytes and null observations remain untouched.
    with tempfile.TemporaryDirectory(prefix='anthropic-model-size-grading-only-') as directory:
        projection=Path(directory)
        for run in runs:
            grading=json.loads((run/'grading.json').read_text());expectations=grading['expectations'];summary=grading['summary'];passed=sum(e['passed'] for e in expectations)
            assert all(type(e['passed']) is bool and e.get('evidence') for e in expectations)
            assert summary==dict(passed=passed,failed=len(expectations)-passed,total=len(expectations),pass_rate=passed/len(expectations))
            target=projection/run.relative_to(workspace);target.mkdir(parents=True)
            # Only expectations and their checked summary are supplied upstream.
            (target/'grading.json').write_text(json.dumps(dict(expectations=expectations,summary=summary)))
            (target/'eval_metadata.json').write_bytes((run/'eval_metadata.json').read_bytes())
        command=[sys.executable,'-m','scripts.aggregate_benchmark',str(projection),'--skill-name','Model size measurement branch','--output',str(workspace/'benchmark-upstream-raw.json')]
        completed=subprocess.run(command,cwd=HERE/'upstream',text=True,capture_output=True)
    (workspace/'aggregate-upstream.log').write_text(completed.stdout+completed.stderr)
    if completed.returncode:raise RuntimeError('Pinned official aggregator failed; see aggregate-upstream.log')
    result=json.loads((workspace/'benchmark-upstream-raw.json').read_text());assert len(result['runs'])==len(runs)==6
    for item in result['runs']:item['result'].update(tokens=None,time_seconds=None,tool_calls=None,errors=None)
    result=normalize_benchmark(result)
    for config,summary in result['run_summary'].items():
        summary.pop('time_seconds',None);summary.pop('tokens',None)
    result['metadata']['timestamp']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    result['native_trigger_results']=None
    result['metadata'].update(skill_name='Model size measurement branch',skill_path='work/model-size-skill-evals-20261118/skill-new (with_skill); work/model-size-skill-evals-20261118/skill-old (old_skill)',executor_model='Explicit Codex subagent; model telemetry unavailable',analyzer_model='Explicit independent subagent; model telemetry unavailable',protocol='Fresh paired isolated subagent measurement-only executions; not native Claude triggering',resource_metrics='No completion token or duration telemetry; unknown values remain null.')
    result['notes']=[
        'Three measurement-only cases × updated/frozen-old skill, six actual independent executions. Same prompt and inputs within each pair; N=1 per case/configuration.',
        'Saved-model and residual-cache require 12 actual mesh measurements. Consistency-check requires rejection of a mesh that does not correspond to saved neutral morph geometry; correct rejection is not successful model matching.',
        'Residual-cache waist target 108 cm differs from actual mesh tape 99.0830995146 cm. Cached measuredNeutral claims are never treated as measured geometry.',
        'Native Claude routing BLOCKED. Image Gen NOT_REQUESTED; no new Image Gen call. Person accuracy, fitting, garment generation and cloth physics are outside this branch.',
        'Time and token telemetry are unavailable (null). Official raw aggregation fallback zeros are preserved for provenance but never interpreted as observations.',
        'Standard deviation is across heterogeneous cases, not repeated-run reliability; these paired N=1 runs establish no statistical advantage.'
    ]
    if (workspace/'analysis.json').exists():
        analysis=json.loads((workspace/'analysis.json').read_text());assert isinstance(analysis,list) and all(isinstance(n,str) for n in analysis);result['notes']+=analysis
    (workspace/'benchmark.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    lines=['# Measurement-branch benchmark','','| Configuration | Assertion pass rate mean ± SD across cases |','| --- | --- |']
    for key,value in result['run_summary'].items():
        if key!='delta':
            stat=value['pass_rate'];lines.append(f"| {key} | {stat['mean']:.4f} ± {stat['stddev']:.4f} |")
    (workspace/'benchmark.md').write_text('\n'.join(lines+['']+['- '+n for n in result['notes']])+'\n')
    return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('workspace',type=Path);print(json.dumps(run(p.parse_args().workspace.resolve())['run_summary'],indent=2))
