#!/usr/bin/env python3
"""Run actual compiled-engine controls locally and preserve command/source bindings."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def sha(raw):return hashlib.sha256(raw).hexdigest()
def parse_report(stdout):
    try:return json.loads(stdout)
    except json.JSONDecodeError:return json.loads(stdout.strip().splitlines()[-1])

def run(directory,output,body_fixture=None):
    directory=directory.resolve();output=output.resolve();output.mkdir(parents=True,exist_ok=True)
    wasm=directory/'solver.wasm';source=directory/'input.json'
    data=json.loads(source.read_bytes())
    for name,digest in data['source_hashes'].items():
        if name.endswith('.c') and sha((ROOT/name).read_bytes())!=digest:
            raise ValueError('Compiled C fragment no longer matches prepared source: '+name)
    commands=[
        ('kernel',[sys.executable,str(HERE/'test_physics_kernel.py'),str(directory),'--output',str(output/'kernel-raw.json')]),
        ('implicit',[sys.executable,str(HERE/'test_implicit_membrane.py'),'--wasm',str(wasm),'--input',str(source)]),
        ('hinges',['node',str(HERE/'test_hinges.mjs'),str(wasm)]),
        ('self-contact',['node',str(HERE/'test_mesh_contact.mjs')]),
        ('swept-edge',['node',str(HERE/'test_swept_edge.mjs')]),
        ('swept-vertex',['node',str(HERE/'test_swept_vertex.mjs')]),
        ('typed-contact',['node',str(HERE/'test_contact.mjs')]),
        ('swept-bounds',['node',str(HERE/'test_swept_bounds.mjs')]),
        ('self-step-guard',['node',str(HERE/'test_self_step_guard.mjs')]),
    ]
    if data.get('solver_features',{}).get('body_feature_contacts'):
        if body_fixture is None:raise ValueError('Feature-contact controls need the explicit saved negative fixture run')
        body_fixture=body_fixture.resolve()
        commands.append(('body-feature',[sys.executable,str(HERE/'test_body_feature_contact.py'),
            '--wasm',str(wasm),'--input',str(body_fixture/'input.json'),'--trajectory',str(body_fixture/'trajectory.json')]))
    sources={str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in sorted(HERE.iterdir())
             if p.suffix in ['.py','.mjs','.c','.yaml','.css','.html']}
    results={};failures=[]
    for name,command in commands:
        result=subprocess.run(command,capture_output=True,text=True,cwd=ROOT)
        (output/f'{name}.stdout.log').write_text(result.stdout);(output/f'{name}.stderr.log').write_text(result.stderr)
        try:report=parse_report(result.stdout)
        except Exception:report={'verdict':'FAIL','reason':'No valid final control report'}
        passed=result.returncode==0 and report.get('verdict')=='PASS'
        row={'verdict':'PASS' if passed else 'FAIL','command':command,'exit_code':result.returncode,
             'wasm_sha256':sha(wasm.read_bytes()),'input_sha256':sha(source.read_bytes()),'report':report}
        (output/f'{name}.json').write_text(json.dumps(row,ensure_ascii=False,indent=2)+'\n')
        results[name]=row['verdict']
        if not passed:failures.append(name)
        print(json.dumps({'control':name,'verdict':row['verdict']}),flush=True)
    manifest={'verdict':'FAIL' if failures else 'PASS','wasm_sha256':sha(wasm.read_bytes()),
              'compiled_source_sha256':sha((directory/'solver-capacity.c').read_bytes()),'input_sha256':sha(source.read_bytes()),
              'source_hashes':sources,'results':results,'failures':failures,
              'scope':'Engine arithmetic and mechanism controls; this does not replace case-specific geometry, full trajectory or browser verification.'}
    (output/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    return not failures

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('directory',type=Path);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--body-fixture',type=Path)
    a=p.parse_args();raise SystemExit(0 if run(a.directory,a.output,a.body_fixture) else 1)
