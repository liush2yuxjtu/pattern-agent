"""Run the frozen public legacy checker on actual case files inside Blender."""
import argparse,hashlib,importlib.util,json,sys
from pathlib import Path
import numpy as np


def main():
    p=argparse.ArgumentParser();p.add_argument('--cases',required=True);p.add_argument('--legacy',required=True)
    args=p.parse_args(sys.argv[sys.argv.index('--')+1:])
    legacy=Path(args.legacy).resolve();spec=importlib.util.spec_from_file_location('frozen_legacy',legacy)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    for folder in sorted(Path(args.cases).glob('*')):
        if not (folder/'arrays.npz').exists():continue
        arrays=dict(np.load(folder/'arrays.npz'));top=json.loads((folder/'topology.json').read_text())
        result=m.analyze_frame(arrays,top)
        result['verifier_sha256']=hashlib.sha256(legacy.read_bytes()).hexdigest()
        (folder/'legacy-result.json').write_text(json.dumps(result,indent=2))
        print(json.dumps({'case':folder.name,'arm_entry':result['arm_entry_pass'],
                          'cloth_geometry_flag':result['cloth_sim_pass'],'self_pairs':result.get('self_intersection_pairs'),
                          'body_pairs':result.get('cloth_body_intersection_pairs'),'errors':result.get('errors')}),flush=True)


if __name__=='__main__':main()
