"""Post-protocol diagnostic: isolate observed coplanar self-overlap discrepancy.

This added experiment is explicitly exploratory, not one of the preregistered
controls. It freezes all mesh indices and shifts a roof vertex laterally in its
own plane; the roof remains above the actual arm surface.
"""
import argparse,json
from copy import deepcopy
from pathlib import Path
import numpy as np
from run_experiment import build_cases,write_json,command,summarize_case,HERE


def main():
    p=argparse.ArgumentParser();p.add_argument('--matrix',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    args=p.parse_args();source=args.matrix/'cases/new_pair';folder=args.out/'cases/coplanar_roof_overlap_only';folder.mkdir(parents=True,exist_ok=True)
    with np.load(source/'arrays.npz') as f:data=dict(f)
    v=data['cloth_vertices'];eligible=np.flatnonzero(np.isclose(v[:,2],1.53)&(v[:,0]>.30)&(v[:,0]<.48)&(v[:,1]>.07)&(v[:,1]<.14))
    index=eligible[np.argmin(np.linalg.norm(v[eligible]-[.39,.105,1.53],axis=1))];before=v[index].copy();v[index,1]=-.105
    np.savez_compressed(folder/'arrays.npz',**data)
    top=json.loads((source/'topology.json').read_text());write_json(folder/'topology.json',top)
    spec=json.loads((source/'case.json').read_text());spec.update(name=folder.name,expected_static_wearing=False,
        construction='Exploratory follow-up: move one roof vertex laterally within z=1.53 plane; arm mesh/paths unchanged.',
        phase='post_protocol_investigation',edited_vertex=int(index),before=before.tolist(),after=v[index].tolist())
    write_json(folder/'case.json',spec)
    command(['blender','-b','-t','1','--python-exit-code','2','--python',HERE/'legacy_runner.py','--','--cases',args.out/'cases','--legacy',HERE.parent/'full_arm/verification/geometry.py'],args.out/'legacy.log')
    row=summarize_case(folder);write_json(args.out/'result.json',row);print(json.dumps(row),flush=True)


if __name__=='__main__':main()
