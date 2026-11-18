#!/usr/bin/env python3
"""Freeze anonymous visual bundles with a private assignment and byte bindings."""
import argparse, hashlib, json, re, shutil
from pathlib import Path

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def prepare(work, iteration, case_id):
    origin=next((work/f'iteration-{iteration}').glob(f'eval-{case_id}-*'))
    assignment=work/'protocol'/f'blind-map-i{iteration}.json'
    mapping=json.loads(assignment.read_text()) if assignment.exists() else {}
    key=f'case-{case_id}'
    if key not in mapping:
        import secrets
        configs=['with_skill','old_skill']
        if secrets.randbelow(2): configs.reverse()
        mapping[key]=dict(zip(['A','B'],configs));assignment.write_text(json.dumps(mapping,indent=2)+'\n')
    for label,config in mapping[key].items():
        run=origin/config/'run-1';output=run/'outputs';meta=json.loads((run/'eval_metadata.json').read_text())
        target=work/'blind'/f'iteration-{iteration}'/key/label
        if target.exists(): raise ValueError('Frozen bundle already exists: '+str(target))
        target.mkdir(parents=True);bindings={}
        names=['final-state.json','posed.obj','neutral.obj','camera.json','photo-render.png','measurements.json','views/front.png','views/side.png','views/back.png','views/joints.json']
        names += [str(p.relative_to(output)) for p in sorted((output/'images').glob('*.png'))]
        for name in names:
            p=output/name
            if not p.exists(): continue
            q=target/name;q.parent.mkdir(parents=True,exist_ok=True)
            if p.suffix=='.json':
                raw=p.read_text();raw=re.sub(r'skill-v[012]|with_skill|old_skill','anonymous',raw)
                raw=re.sub(r'/workspace/work/pattern-agent/work/commerce-skill-evals-20261118/[^"\n]*','anonymous-path',raw)
                q.write_text(raw)
            else: shutil.copyfile(p,q)
            bindings[name]={'review_sha256':sha(q),'source_sha256':sha(p)}
        inp=work/'inputs'/meta['input_case']
        for src,dst in [('original.jpg','input.jpg'),('source.json','source.json')]:
            shutil.copyfile(inp/src,target/dst)
            bindings[dst]={'review_sha256':sha(target/dst),'source_sha256':sha(inp/src)}
        (target/'review-binding.json').write_text(json.dumps(bindings,indent=2)+'\n')
    print('Frozen anonymous bundles:',key)
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--workspace',type=Path,required=True);a.add_argument('--iteration',type=int,required=True);a.add_argument('--case',type=int,required=True);n=a.parse_args();prepare(n.workspace,n.iteration,n.case)
