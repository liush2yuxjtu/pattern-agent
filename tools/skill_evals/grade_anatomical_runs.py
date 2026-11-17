#!/usr/bin/env python3
"""Run artifact graders, preserve raw evidence and emit Anthropic grading schema."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

HERE=Path(__file__).resolve().parent


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace',type=Path,required=True)
    parser.add_argument('--iteration',type=int,required=True)
    args=parser.parse_args();workspace=args.workspace.resolve()
    iteration=workspace/f'iteration-{args.iteration}'
    summaries=[]
    for run in sorted(iteration.glob('eval-*/*/run-*')):
        spec=json.loads((run/'eval_metadata.json').read_text());case=spec.get('grader_case',spec['eval_name'])
        if case=='state-audit':
            command=[sys.executable,str(HERE/'grade_anatomical_state.py'),'--workspace',str(workspace),'--run',str(run)]
            process=subprocess.run(command,text=True,capture_output=True)
            (run/'grader.log').write_text(process.stdout+process.stderr)
            if process.returncode:raise RuntimeError(str(run)+' audit grader crashed')
            grading=json.loads((run/'grading.json').read_text())
        else:
            command=[sys.executable,str(HERE/'anatomical_controls.py'),'grade','--case',case,'--output',str(run/'outputs')]
            if spec.get('fixture_override'):
                # Run metadata preserves the original absolute execution path;
                # regrading uses the extracted fixture in this workspace.
                command+=['--fixture',str(workspace/'fixtures'/Path(spec['fixture_override']).name)]
            process=subprocess.run(command,text=True,capture_output=True)
            (run/'grader.log').write_text(process.stdout+process.stderr)
            if process.returncode:raise RuntimeError(str(run)+' geometry grader crashed')
            raw=json.loads((run/'outputs/grading.json').read_text())
            (run/'raw-grading.json').write_text(json.dumps(raw,indent=2)+'\n')
            checks=[dict(text=x['text'],passed=x['passed'],evidence=json.dumps(x['evidence'])) for x in raw['checks']]
            if case=='pose-depth-evidence':
                process=subprocess.run([sys.executable,str(HERE/'grade_anatomical_projection.py'),'--output',str(run/'outputs')],text=True,capture_output=True)
                (run/'independent-projection.log').write_text(process.stdout+process.stderr)
                evidence=json.loads((run/'outputs/independent-projection.json').read_text())
                checks.append(dict(text=spec['assertions'][-1],passed=evidence['verdict']=='PASS',evidence=json.dumps(evidence)))
            passed=sum(x['passed'] for x in checks)
            grading=dict(expectations=checks,summary=dict(passed=passed,failed=len(checks)-passed,total=len(checks),pass_rate=passed/len(checks)))
            (run/'grading.json').write_text(json.dumps(grading,indent=2)+'\n')
        assert [x['text'] for x in grading['expectations']]==spec['assertions'], 'Frozen assertions mismatch'
        summary=dict(run=str(run.relative_to(workspace)),**grading['summary']);summaries.append(summary)
        print(json.dumps(summary),flush=True)
    (iteration/'grading-summary.json').write_text(json.dumps(summaries,indent=2)+'\n')


if __name__=='__main__':main()
