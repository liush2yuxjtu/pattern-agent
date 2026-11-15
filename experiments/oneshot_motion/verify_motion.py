"""Independently audit saved moving meshes, preserving legacy routing separately.

This verifies every provided saved frame. It does not adjudicate nonplanar cap
ambiguity, prove continuous-time collision freedom, or approve physical fit.
"""
import argparse,hashlib,json,sys,time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'oneshot_control'))
import independent_oracle_v2 as oracle


def contained_samples(vertices,triangles,points):
    """Conservative slab AABBs prune proven exterior; winding decides the rest.

    A closed body's cross-section in a z slab lies inside the XY bounds of every
    boundary triangle intersecting that slab. Including entire triangles makes
    these boxes larger, never smaller. No possibly interior point is discarded.
    """
    points=np.asarray(points);faces=vertices[triangles];low=vertices.min(axis=0);high=vertices.max(axis=0)
    result=np.zeros(len(points),bool);possible=np.all((points>=low-1e-6)&(points<=high+1e-6),axis=1)
    zlow=faces[:,:,2].min(axis=1);zhigh=faces[:,:,2].max(axis=1)
    bins=np.floor((points[:,2]-low[2])/.02).astype(int)
    for index in np.unique(bins[possible]):
        ids=np.flatnonzero(possible&(bins==index));a=low[2]+index*.02;b=a+.02
        active=faces[(zlow<=b+1e-6)&(zhigh>=a-1e-6)]
        if not len(active):possible[ids]=False;continue
        minimum=active.min(axis=(0,1));maximum=active.max(axis=(0,1))
        possible[ids]&=np.all((points[ids,:2]>=minimum[:2]-1e-6)&(points[ids,:2]<=maximum[:2]+1e-6),axis=1)
    if possible.any():result[possible]=oracle.point_inside_mesh(vertices,triangles,points[possible])
    return result,int(possible.sum())


def audit_frame(task):
    path,old=task;started=time.monotonic()
    with np.load(path) as f:cv,ct,bv,bt=[f[k] for k in ('cloth_vertices','cloth_triangles','body_vertices','body_triangles')];frame=int(f['frame'])
    cloth=oracle.mesh_audit(cv,ct);body=oracle.mesh_audit(bv,bt)
    self_pairs=oracle.intersect_pairs(cv,ct);body_pairs=oracle.intersect_pairs(cv,ct,bv,bt);body_self=oracle.intersect_pairs(bv,bt)
    inside,winding_candidates=contained_samples(bv,bt,np.concatenate([cv,cv[ct].mean(axis=1)]))
    structure=(body['outward_closed_components'] and body['connected_components']==1 and cloth['connected_components']==1
               and cloth['boundary_cycles']==4 and all(cloth[k]==0 for k in ('nonmanifold_edges','boundary_branch_vertices','winding_conflicts','degenerate_triangles','duplicate_faces')))
    passed=bool(structure and not self_pairs and not body_pairs and not body_self and not inside.any())
    return {'frame':frame,'file':path.name,'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'cloth_self_pairs':self_pairs,'cloth_body_pairs':body_pairs,'body_self_pairs':body_self,'cloth_samples_inside_body':int(inside.sum()),'winding_candidate_samples':winding_candidates,
            'cloth_topology':cloth,'body_topology':body,'independent_saved_mesh_pass':passed,
            'legacy_self_count':old['self_intersection_pairs'],'legacy_arm_path_pass':old['arm_entry_pass'],
            'legacy_cloth_geometry_pass':old['cloth_sim_pass'],'seconds':time.monotonic()-started}


def main():
    p=argparse.ArgumentParser();p.add_argument('--frames',type=Path,required=True);p.add_argument('--legacy-report',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--workers',type=int,default=1)
    args=p.parse_args();args.out.parent.mkdir(parents=True,exist_ok=True)
    if args.workers<1:raise ValueError('workers must be positive')
    tests=oracle.analytic_tests();args.out.with_name(args.out.stem+'-analytic-first.json').write_text(json.dumps(tests,indent=2))
    legacy=json.loads(args.legacy_report.read_text());saved={int(x['frame']):x for x in legacy['frames']}
    paths=sorted(args.frames.glob('frame-*.npz'));rows=[]
    tasks=[(path,saved[int(path.stem.split('-')[-1])]) for path in paths]
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        for row in executor.map(audit_frame,tasks):
            rows.append(row)
            print(json.dumps({'frame':row['frame'],'self':len(row['cloth_self_pairs']),'body':len(row['cloth_body_pairs']),
                              'mesh_pass':row['independent_saved_mesh_pass'],'legacy_path':row['legacy_arm_path_pass']}),flush=True)
    assert [r['frame'] for r in rows]==list(range(1,len(rows)+1)),'Incomplete or duplicate frame coverage'
    summary={'frame_count':len(rows),'geometry_pass_frames':sum(r['independent_saved_mesh_pass'] for r in rows),
             'geometry_fail_frames':sum(not r['independent_saved_mesh_pass'] for r in rows),
             'self_intersection_frames':sum(bool(r['cloth_self_pairs']) for r in rows),
             'peak_self_pairs':max(len(r['cloth_self_pairs']) for r in rows),
             'cloth_body_intersection_frames':sum(bool(r['cloth_body_pairs']) for r in rows),
             'body_self_intersection_frames':sum(bool(r['body_self_pairs']) for r in rows),
             'cloth_inside_body_frames':sum(r['cloth_samples_inside_body']>0 for r in rows),
             'legacy_path_fail_frames':[r['frame'] for r in rows if not r['legacy_arm_path_pass']],
             'analytic_test_count':tests['test_count'],'oracle_sha256':hashlib.sha256(Path(oracle.__file__).read_bytes()).hexdigest(),
             'scope':'All saved integer meshes audited. Legacy path/cap flags are separate and may be cap-dependent; no complete wearing, continuous-time or fit PASS.'}
    report={'summary':summary,'frames':rows};args.out.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps(summary),flush=True)
    if summary['geometry_fail_frames']:raise SystemExit(2)


if __name__=='__main__':main()
