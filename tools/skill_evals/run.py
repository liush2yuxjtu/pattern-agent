#!/usr/bin/env python3
"""Prepare/review native trigger evals; run only with a working authenticated Claude CLI."""
import argparse
import hashlib
import html
import json
import os
import random
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
UPSTREAM=HERE/'upstream'
SKILL=ROOT/'.agents/skills/garment-body-six-view'


def load_cases(path):
    cases=json.loads(Path(path).read_text())
    if not isinstance(cases,list) or not cases:
        raise ValueError('Expected nonempty official [{query,should_trigger}] dataset')
    seen=set()
    for case in cases:
        if set(case)!= {'query','should_trigger'} or not isinstance(case['query'],str) or not case['query'].strip() or type(case['should_trigger']) is not bool:
            raise ValueError('Each case needs a nonempty query and exact boolean should_trigger')
        if case['query'] in seen:raise ValueError('Duplicate query')
        seen.add(case['query'])
    if not any(c['should_trigger'] for c in cases) or all(c['should_trigger'] for c in cases):
        raise ValueError('Both positive and nearby negative cases are required')
    return cases


def split_cases(cases):
    rng=random.Random(42);dev=[];holdout=[]
    for label in [True,False]:
        group=[c for c in cases if c['should_trigger'] is label];rng.shuffle(group)
        n=max(1,int(len(group)*.4));holdout+=group[:n];dev+=group[n:]
    return dev,holdout


def integrity():
    provenance=json.loads((UPSTREAM/'provenance.json').read_text())
    for entry in provenance['files']:
        actual=hashlib.sha256((UPSTREAM/entry['path']).read_bytes()).hexdigest()
        if actual!=entry['sha256']:raise ValueError('Pinned upstream file changed: '+entry['path'])
    return provenance['commit']


def prepare(skill,eval_set,out):
    commit=integrity();cases=load_cases(eval_set);dev,holdout=split_cases(cases)
    out.mkdir(parents=True,exist_ok=True)
    (out/'development.json').write_text(json.dumps(dev,ensure_ascii=False,indent=2))
    (out/'final-holdout.json').write_text(json.dumps(holdout,ensure_ascii=False,indent=2))
    text=(skill/'SKILL.md').read_text();description=re.search(r'^description: (.+)$',text,re.M).group(1)
    try:description=json.loads(description)
    except ValueError:pass
    review=(UPSTREAM/'assets/eval_review.html').read_text()
    for marker,value in [('__EVAL_DATA_PLACEHOLDER__',json.dumps(cases,ensure_ascii=False).replace('<','\\u003c')),('__SKILL_NAME_PLACEHOLDER__',html.escape(skill.name)),('__SKILL_DESCRIPTION_PLACEHOLDER__',html.escape(description))]:
        review=review.replace(marker,value)
    (out/'review.html').write_text(review)
    record={'status':'PREPARED','native_trigger_results':None,'upstream_commit':commit,
            'skill_sha256':hashlib.sha256((skill/'SKILL.md').read_bytes()).hexdigest(),
            'dataset_sha256':hashlib.sha256(Path(eval_set).read_bytes()).hexdigest(),
            'cases':len(cases),'development_cases':len(dev),'final_holdout_cases':len(holdout),
            'protocol':'Outer 60/40 development/final-holdout; official loop internally splits development 2/3 train,1/3 validation. Only final evaluation sees outer holdout.',
            'review_required':'Review labels in review.html before real optimization; no dataset or model score has been inferred from preparation.'}
    (out/'preparation.json').write_text(json.dumps(record,indent=2));return record


def doctor(model=None,probe=False):
    cli=shutil.which('claude')
    record={'status':'BLOCKED','claude_cli_available':bool(cli),'model':model,'native_trigger_results':None}
    if not cli:
        record['reason']='claude CLI is not installed; native trigger evaluation did not run'
        return record
    try:
        version=subprocess.run([cli,'--version'],capture_output=True,text=True,timeout=15)
        if version.returncode:
            record['reason']='claude --version failed';return record
        record['claude_version']=version.stdout.strip()[:120]
        if not probe:
            record.update(status='READY_FOR_AUTH_PROBE',reason='Authentication/model access not tested')
            return record
        cmd=[cli,'-p','Reply exactly SKILL_EVAL_READY. Do not use tools.','--output-format','json']
        if model:cmd+=['--model',model]
        result=subprocess.run(cmd,capture_output=True,text=True,timeout=60,
                              env={k:v for k,v in os.environ.items() if k!='CLAUDECODE'})
        if result.returncode:
            record['reason']='Authenticated/model probe failed; stderr omitted to avoid leaking credentials';return record
        payload=json.loads(result.stdout)
        if payload.get('is_error') or payload.get('subtype') not in [None,'success'] or 'SKILL_EVAL_READY' not in str(payload.get('result','')):
            record['reason']='Authenticated/model probe did not return expected successful result';return record
        record.update(status='PASS',reason='Native CLI/auth/model probe passed; trigger trials still not run')
    except (OSError,ValueError,subprocess.TimeoutExpired) as exc:
        record['reason']='Native CLI probe failed: '+type(exc).__name__
    return record


def optimize(args):
    record=prepare(args.skill,args.eval_set,args.out)
    readiness=doctor(args.model,probe=True)
    (args.out/'readiness.json').write_text(json.dumps(readiness,indent=2))
    if readiness['status']!='PASS':print(json.dumps(readiness,ensure_ascii=False,indent=2));return 3
    project=args.out/'isolated-project';project.mkdir(exist_ok=True);(project/'.claude').mkdir(exist_ok=True)
    target=args.out/'candidate-skill'
    if target.exists():raise ValueError('Use a fresh --out; candidate-skill already exists')
    shutil.copytree(args.skill,target,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    env=dict(os.environ);env['PYTHONPATH']=str(UPSTREAM)+os.pathsep+str(HERE)
    env['PATTERN_SKILL_TRIAL_DIR']=str(args.out/'trials')
    command=[sys.executable,str(HERE/'native_entry.py'),'--eval-set',str(args.out/'development.json'),
        '--skill-path',str(target),'--model',args.model,'--max-iterations',str(args.max_iterations),
        '--runs-per-query','3','--holdout',str(1/3),'--num-workers','2','--timeout','60','--verbose',
        '--results-dir',str(args.out/'native-results'),'--report',str(args.out/'native-report.html')]
    with (args.out/'stdout.log').open('w') as stdout,(args.out/'stderr.log').open('w') as stderr:
        run=subprocess.run(command,cwd=project,env=env,stdout=stdout,stderr=stderr)
    found=list((args.out/'native-results').glob('*/results.json'))
    if run.returncode or not found:
        status={'status':'BLOCKED','reason':'Native runner failed; inspect local logs/trials','native_trigger_results':None}
        (args.out/'status.json').write_text(json.dumps(status,indent=2));print(json.dumps(status));return 3
    result=json.loads(sorted(found)[-1].read_text())
    # Write the selected candidate locally; do not overwrite the installed skill before review.
    content=(target/'SKILL.md').read_text();content=re.sub(r'^description: .+$',lambda _: 'description: '+json.dumps(result['best_description'],ensure_ascii=False),content,count=1,flags=re.M)
    (target/'SKILL.md').write_text(content)
    sys.path.insert(0,str(UPSTREAM));sys.path.insert(0,str(HERE))
    from strict_runtime import install
    install()
    from scripts.run_loop import run_eval
    os.environ['PATTERN_SKILL_TRIAL_DIR']=str(args.out/'final-trials')
    # Original and selected descriptions are both measured only now on untouched final cases.
    holdout=load_cases(args.out/'final-holdout.json');final={}
    try:
        for name,description in [('baseline',result['original_description']),('selected',result['best_description'])]:
            final[name]=run_eval(holdout,args.skill.name,description,2,60,project,3,.5,args.model)
    except RuntimeError as exc:
        status={'status':'BLOCKED','reason':str(exc),'native_trigger_results':None,'installed_skill_changed':False}
        (args.out/'status.json').write_text(json.dumps(status,indent=2));print(json.dumps(status));return 3
    (args.out/'final-holdout-results.json').write_text(json.dumps(final,ensure_ascii=False,indent=2))
    status={'status':'PASS','scope':'native trigger routing only; task execution/physical accuracy not evaluated','native_trigger_results':'final-holdout-results.json','candidate_skill':'candidate-skill','installed_skill_changed':False}
    (args.out/'status.json').write_text(json.dumps(status,indent=2));print(json.dumps(status));return 0


def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    for name in ['prepare','doctor','optimize']:
        p=sub.add_parser(name);p.add_argument('--out',type=Path,required=True)
        if name!='doctor':
            p.add_argument('--skill',type=Path,default=SKILL);p.add_argument('--eval-set',type=Path,default=SKILL/'evals/trigger-evals.json')
        if name!='prepare':p.add_argument('--model',required=name=='optimize');p.add_argument('--probe',action='store_true')
        if name=='optimize':p.add_argument('--max-iterations',type=int,default=5,choices=range(1,6))
    args=parser.parse_args();args.out=args.out.resolve();args.out.mkdir(parents=True,exist_ok=True)
    if hasattr(args,'skill'):args.skill=args.skill.resolve();args.eval_set=args.eval_set.resolve()
    if args.command=='prepare':print(json.dumps(prepare(args.skill,args.eval_set,args.out),indent=2));return 0
    if args.command=='doctor':
        value=doctor(args.model,args.probe);(args.out/'readiness.json').write_text(json.dumps(value,indent=2));print(json.dumps(value,indent=2));return 3 if value['status']=='BLOCKED' else 0
    return optimize(args)

if __name__=='__main__':
    try:sys.exit(main())
    except (OSError,ValueError,RuntimeError) as exc:
        print('BLOCKED: '+str(exc),file=sys.stderr);sys.exit(3)
