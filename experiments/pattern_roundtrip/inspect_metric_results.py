"""Audit final saved meshes with the frozen independent v2 geometry predicates.

Cut panels remain topologically separate; sewing springs do not weld vertices.
Counts refer to proper surface intersections, not a closed-garment volume claim.
"""
import argparse,hashlib,json,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'oneshot_control'))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'oneshot_motion'))
import independent_oracle_v2 as oracle
from verify_motion import contained_samples


def main():
    p=argparse.ArgumentParser();p.add_argument('--runs',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    tests=oracle.analytic_tests();assert tests['all_passed'];rows=[];body_self=None
    for case in ['baseline','atlas_rigid','left_sleeve_90']:
        root=a.runs/case;files=sorted((root/'frames').glob('*.npz'));last=files[-1]
        with np.load(last) as f:cv,ct,bv,bt=[f[k] for k in ('cloth_vertices','cloth_triangles','body_vertices','body_triangles')]
        if body_self is None:body_self=oracle.intersect_pairs(bv,bt)
        own=oracle.intersect_pairs(cv,ct);cross=oracle.intersect_pairs(cv,ct,bv,bt)
        inside,n=contained_samples(bv,bt,np.concatenate([cv,cv[ct].mean(axis=1)]))
        report=json.loads((root/'drape-report.json').read_text())
        rows.append({'case':case,'final_frame':int(last.stem[6:]),'source_sha256':hashlib.sha256(last.read_bytes()).hexdigest(),
                     'cloth_topology':oracle.mesh_audit(cv,ct),'cloth_self_pairs':own,'cloth_body_pairs':cross,
                     'body_self_pairs':body_self,'cloth_samples_inside_body':int(inside.sum()),'winding_candidate_samples':n,
                     'max_sewing_gap_all_saved_frames_mm':max(x['sewing_max_gap_mm'] for x in report['frames']),
                     'final_sewing_gap_mm':report['frames'][-1]['sewing_max_gap_mm']})
    result={'analytic_tests':tests,'oracle_sha256':hashlib.sha256(Path(oracle.__file__).read_bytes()).hexdigest(),'rows':rows,
            'coverage':'Only final saved mesh of each diagnostic run; no continuous-time or complete motion certificate.',
            'armhole_fit':'UNKNOWN','physical_fit':'NOT_RUN','causal_control_failure_prevents_pattern_fit_inference':True}
    a.out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'analytic_tests':tests['test_count'],'rows':[{k:r[k] for k in ('case','final_frame','cloth_samples_inside_body','final_sewing_gap_mm')}|{'self_pairs':len(r['cloth_self_pairs']),'body_pairs':len(r['cloth_body_pairs'])} for r in rows]}))


if __name__=='__main__':main()
