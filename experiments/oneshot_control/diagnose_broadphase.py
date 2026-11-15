"""Trace independent collision disagreements through the frozen Blender checker.

This diagnostic calls legacy narrow and broad phases explicitly; it is not the
independent oracle and must never be presented as an independent algorithm.
"""
import argparse,hashlib,importlib.util,json,sys
from pathlib import Path
import numpy as np


def main():
    p=argparse.ArgumentParser();p.add_argument('--case',type=Path,required=True);p.add_argument('--legacy',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    args=p.parse_args(sys.argv[sys.argv.index('--')+1:])
    spec=importlib.util.spec_from_file_location('legacy_diagnostic',args.legacy);legacy=importlib.util.module_from_spec(spec);spec.loader.exec_module(legacy)
    with np.load(args.case/'arrays.npz') as f:v,t=f['cloth_vertices'],f['cloth_triangles']
    independent=json.loads((args.case/'independent-result.json').read_text())['garment_self_pairs']
    tree=legacy._bvh(v,t);candidates={tuple(sorted((int(i),int(j)))) for i,j in tree.overlap(tree)}
    legacy_pairs=legacy._intersection_pairs(v,t)
    rows=[]
    for i,j in independent:
        rows.append({'pair':[i,j],'bvh_candidate':(i,j) in candidates,
                     'legacy_narrow_phase_intersection':bool(legacy._tri_intersects(v[t[i]],v[t[j]])),
                     'a':v[t[i]].tolist(),'b':v[t[j]].tolist()})
    report={'legacy_sha256':hashlib.sha256(args.legacy.read_bytes()).hexdigest(),
            'input_npz_sha256':hashlib.sha256((args.case/'arrays.npz').read_bytes()).hexdigest(),
            'legacy_full_count':len(legacy_pairs),'independent_pair_count':len(independent),
            'independent_pairs_present_in_bvh':sum(r['bvh_candidate'] for r in rows),
            'independent_pairs_accepted_by_legacy_narrow_phase':sum(r['legacy_narrow_phase_intersection'] for r in rows),
            'pairs':rows,'scope':'Diagnostic of frozen legacy stages; independently produced pairs were inputs.'}
    args.out.write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='pairs'}),flush=True)


if __name__=='__main__':main()
