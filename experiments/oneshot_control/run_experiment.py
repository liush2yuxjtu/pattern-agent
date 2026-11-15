"""Public control experiment: two standalone assets, frozen legacy, independent oracle.

Run with Python (NumPy/SciPy installed), Blender on PATH. No cloth simulation is
claimed by this static method calibration. Existing assets are never overwritten.
"""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import numpy as np

from control_io import pair, read_obj
import independent_oracle_v2 as oracle

HERE=Path(__file__).resolve().parent


def write_json(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')


def command(args,log):
    with log.open('w') as stream:
        result=subprocess.run([str(x) for x in args],stdout=stream,stderr=subprocess.STDOUT)
    if result.returncode:
        raise RuntimeError(f'Command failed ({result.returncode}); see {log}')


def rectangular_route(path,side):
    """Independent analytic oracle, only for the protocol's rectangular sleeve.

    Intersect actual line segments with x=armhole and x=cuff planes; require
    one outward crossing through each rectangle, in order. Check the complete
    intervening polyline against the convex sleeve box, not just end points.
    This intentionally does not read legacy caps, fans, winding or triangle IDs.
    """
    path=np.asarray(path,float).copy();path[:,0]*=1 if side=='L' else -1
    hits=[]
    for plane in (.25,.53):
        current=[]
        for i,(a,b) in enumerate(zip(path[:-1],path[1:])):
            if abs(b[0]-a[0])<1e-12:continue
            u=(plane-a[0])/(b[0]-a[0])
            if 0<=u<1:
                p=a+u*(b-a)
                if -.14<p[1]<.14 and 1.27<p[2]<1.53:
                    current.append((i+u,1 if b[0]>a[0] else -1,p))
        hits.append(current)
    valid=(len(hits[0])==len(hits[1])==1 and hits[0][0][1]==hits[1][0][1]==1
           and hits[0][0][0]<hits[1][0][0])
    if valid:
        start,end=hits[0][0],hits[1][0]
        samples=np.asarray([start[2]]+[p for i,p in enumerate(path) if start[0]<i<end[0]]+[end[2]])
        valid=bool(np.all((samples[:,1]>-.14)&(samples[:,1]<.14)&(samples[:,2]>1.27)&(samples[:,2]<1.53)))
    return {'pass':bool(valid),'armhole_crossings':len(hits[0]),'cuff_crossings':len(hits[1]),
            'method':'analytic segment/rectangle intersections and convex-box containment'}


def sleeve_annotation_ok(triangles,topology):
    """Direct edge incidence comparison; no legacy implementation imported."""
    from collections import Counter
    answer={}
    for side in ('L','R'):
        faces=triangles[np.asarray(topology['sleeve_triangles'][side],int)]
        counts=Counter(tuple(sorted((int(a),int(b)))) for t in faces for a,b in zip(t,np.roll(t,-1)))
        boundary={e for e,c in counts.items() if c==1}
        marked=set()
        for kind in ('armholes','cuffs'):
            loop=topology[kind][side]
            marked.update(tuple(sorted((a,b))) for a,b in zip(loop,loop[1:]+loop[:1]))
        answer[side]=bool(boundary==marked and all(c<=2 for c in counts.values()))
    return answer


def build_cases(model,cloth,root,original_cloth=None):
    arrays,top=pair(model,cloth)
    for side in ('L','R'):
        path=arrays['path_'+side]
        arrays['claimed_internal_path_'+side]=(path[:-1]+path[1:])/2
    definitions=[]
    def save(name,expected,change=None,description='',canonical_rotation=None,canonical_scale=1.,canonical_offset=None,top_override=None):
        data={k:v.copy() for k,v in arrays.items()};metadata=deepcopy(top)
        if change:change(data,metadata)
        if top_override is not None:metadata=top_override
        folder=root/name;folder.mkdir(parents=True,exist_ok=True)
        np.savez_compressed(folder/'arrays.npz',**data);write_json(folder/'topology.json',metadata)
        spec={'name':name,'expected_static_wearing':expected,'construction':description,
              'inverse_rotation':(np.eye(3) if canonical_rotation is None else canonical_rotation).tolist(),
              'inverse_offset':(np.zeros(3) if canonical_offset is None else canonical_offset).tolist(),
              'inverse_scale':canonical_scale}
        write_json(folder/'case.json',spec);definitions.append(spec)
    save('new_pair',True,description='Two newly generated independent standalone assets, unmodified geometry.')
    ax=.37;az=.53
    rx=np.array([[1,0,0],[0,np.cos(ax),-np.sin(ax)],[0,np.sin(ax),np.cos(ax)]])
    rz=np.array([[np.cos(az),-np.sin(az),0],[np.sin(az),np.cos(az),0],[0,0,1]])
    rotation=rz@rx;offset=np.array([1.25,-.73,.4])
    def rigid(data,metadata):
        for key in data:
            if 'triangles' not in key:data[key]=data[key]@rotation.T+offset
        metadata['rest_vertices']=data['cloth_vertices'].tolist()
    save('rigid_transform_both_and_paths',True,rigid,'Same meshes and paths, translated and rotated together.',canonical_rotation=rotation,canonical_offset=offset)
    def scale(data,metadata):
        for key in data:
            if 'triangles' not in key:data[key]*=2
        metadata['rest_vertices']=data['cloth_vertices'].tolist()
    save('uniform_scale_both_and_paths',True,scale,'All positions and rest positions scaled by two.',canonical_scale=2.)
    def diagonal(data,metadata):
        _,_,_,polygons=read_obj(model)
        data['body_triangles']=np.array([t for q in polygons for t in [(q[0],q[1],q[3]),(q[1],q[2],q[3])]],int)
        old=data['cloth_triangles'];new=[]
        for a,b in zip(old[::2],old[1::2]):
            assert a[0]==b[0] and a[2]==b[1]
            q=[a[0],a[1],a[2],b[2]];new.extend([(q[0],q[1],q[3]),(q[1],q[2],q[3])])
        data['cloth_triangles']=np.array(new,int)
    save('opposite_quad_diagonal_tessellation',True,diagonal,'Same planar surfaces, every quad uses its opposite diagonal.')
    def wrong(data,metadata):data['path_L'],data['path_R']=data['path_R'].copy(),data['path_L'].copy()
    save('wrong_side_paths',False,wrong,'Declared left and right arm routes are exchanged.')
    def pierce(data,metadata):data['path_L'][3,1]=.35
    save('path_pierces_fabric',False,pierce,'Left route leaves sleeve box through fabric then returns.')
    def stop(data,metadata):
        data['path_L']=np.array([[.07,0,1.42],[.17,0,1.42],[.30,0,1.42],[.40,0,1.42]])
    save('path_stops_before_cuff',False,stop,'Left route ends at x=.40, before cuff x=.53.')
    def displaced(data,metadata):data['body_vertices']+=np.array([2.,0,0])
    save('body_displaced_but_stale_paths',False,displaced,'Actual complete closed human is translated 2m away; fake/stale internal paths stay inside garment.')
    def self_cross(data,metadata):
        v=data['cloth_vertices'];eligible=np.flatnonzero(np.isclose(v[:,2],1.53)&(v[:,0]>.30)&(v[:,0]<.48)&(v[:,1]>.07)&(v[:,1]<.14))
        selected=eligible[np.argmin(np.linalg.norm(v[eligible]-np.array([.39,.105,1.53]),axis=1))]
        v[selected,2]=1.20
    save('garment_self_intersection',False,self_cross,'One sleeve-roof vertex is pushed through the lower sleeve wall; topology and paths unchanged.')
    def penetration(data,metadata):
        v=data['cloth_vertices'];v[np.isclose(v[:,1],-.14),1]=-.03
    save('cloth_body_penetration',False,penetration,'Front garment surface moved inside the torso/arms.')
    if original_cloth:
        _,_,bad,_=read_obj(original_cloth);bad['rest_vertices']=arrays['cloth_vertices'].tolist()
        save('first_export_wrong_sleeve_labels',False,description='Original one-shot export had lower torso faces mislabeled as sleeve; geometry exactly unchanged.',top_override=bad)
    return definitions


def summarize_case(folder):
    spec=json.loads((folder/'case.json').read_text());top=json.loads((folder/'topology.json').read_text())
    with np.load(folder/'arrays.npz') as f:data=dict(f)
    result=oracle.audit_npz(folder/'arrays.npz')
    rotation=np.array(spec['inverse_rotation']);offset=np.array(spec['inverse_offset']);scale=spec['inverse_scale']
    routes={s:rectangular_route(((data['path_'+s]-offset)@rotation)/scale,s) for s in ('L','R')}
    annotations=sleeve_annotation_ok(data['cloth_triangles'],top)
    body=result['body_mesh'];cloth=result['garment_mesh']
    structure=(body['outward_closed_components'] and body['connected_components']==1 and cloth['connected_components']==1
               and cloth['boundary_cycles']==4 and all(cloth[k]==0 for k in ('nonmanifold_edges','boundary_branch_vertices','winding_conflicts','degenerate_triangles','duplicate_faces')))
    # Derive samples from the CURRENT route. Do not let a caller pair a false
    # route with an unrelated list of supposedly internal sample coordinates.
    # Every segment midpoint is internal in this control's explicit contract;
    # a general avatar with deliberate external path extensions needs explicit
    # internal segment ranges tied to its evaluated skeleton instead.
    derived_membership={}
    for side in ('L','R'):
        path=data['path_'+side];points=(path[:-1]+path[1:])/2
        winding=oracle.winding_numbers(data['body_vertices'],data['body_triangles'],points)
        mask=np.abs(winding)>.5000001
        derived_membership[side]={'sample_count':len(points),'inside_count':int(mask.sum()),
                                  'all_inside':bool(mask.all()),'winding_numbers':winding.tolist()}
    result['route_derived_body_membership']=derived_membership
    association=all(r['all_inside'] for r in derived_membership.values())
    clean=all(not result[k] for k in ('garment_self_pairs','body_self_pairs','garment_body_pairs'))
    # Vertex and triangle-centroid samples additionally catch complete containment.
    cv,ct=data['cloth_vertices'],data['cloth_triangles']
    samples=np.concatenate([cv,cv[ct].mean(axis=1)])
    inside=oracle.point_inside_mesh(data['body_vertices'],data['body_triangles'],samples)
    result['cloth_samples_inside_body_count']=int(inside.sum())
    strong=bool(structure and association and clean and not inside.any() and all(annotations.values()) and all(r['pass'] for r in routes.values()))
    result.update({'analytic_rectangular_routes':routes,'sleeve_annotation_valid':annotations,'body_path_association_pass':bool(association),
                   'static_wearing_pass':strong,'cloth_simulation':'NOT_RUN','physical_fit':'NOT_RUN'})
    write_json(folder/'independent-result.json',result)
    legacy=json.loads((folder/'legacy-result.json').read_text())
    row={'case':spec['name'],'expected_static_wearing':spec['expected_static_wearing'],
         'legacy_arm_entry':legacy['arm_entry_pass'],'legacy_cloth_geometry_flag':legacy['cloth_sim_pass'],
         'legacy_self_pairs':legacy.get('self_intersection_pairs'),'legacy_body_pairs':legacy.get('cloth_body_intersection_pairs'),
         'independent_self_pairs':len(result['garment_self_pairs']),'independent_body_pairs':len(result['garment_body_pairs']),
         'independent_body_path_association':bool(association),'independent_static_wearing':strong,
         'expectation_met':bool(strong==spec['expected_static_wearing']),
         'collision_counts_agree':bool(legacy.get('self_intersection_pairs')==len(result['garment_self_pairs']) and legacy.get('cloth_body_intersection_pairs')==len(result['garment_body_pairs'])),
         'description':spec['construction']}
    return row


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--model',type=Path);p.add_argument('--cloth',type=Path);p.add_argument('--original-cloth',type=Path)
    p.add_argument('--blender',default='blender');p.add_argument('--legacy',type=Path,default=HERE.parent/'full_arm/verification/geometry.py')
    args=p.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=True)
    if (out/'experiment.json').exists():raise FileExistsError('Use a fresh output directory')
    # Save independent analytic tests BEFORE running any legacy/control comparison.
    write_json(out/'analytic-first.json',{'source_sha256':hashlib.sha256(Path(oracle.__file__).read_bytes()).hexdigest(),'tests':oracle.analytic_tests()})
    model=args.model;cloth=args.cloth
    for kind,path in [('model',model),('cloth',cloth)]:
        if path is None:
            destination=out/(kind+'.blend')
            command([args.blender,'-b','-t','1','--python-exit-code','2','--python',HERE/('generate_'+kind+'.py'),'--','--out',destination],out/(kind+'-generation.log'))
            if kind=='model':model=destination.with_suffix('.obj')
            else:cloth=destination.with_suffix('.obj')
    cases=build_cases(model,cloth,out/'cases',args.original_cloth)
    command([args.blender,'-b','-t','1','--python-exit-code','2','--python',HERE/'legacy_runner.py','--','--cases',out/'cases','--legacy',args.legacy],out/'legacy.log')
    rows=[]
    for spec in cases:
        row=summarize_case(out/'cases'/spec['name']);rows.append(row);print(json.dumps(row),flush=True)
    report={'schema_version':1,'time_utc':datetime.now(timezone.utc).isoformat(),
            'protocol_sha256':hashlib.sha256((HERE/'protocol.json').read_bytes()).hexdigest(),
            'legacy_sha256':hashlib.sha256(args.legacy.read_bytes()).hexdigest(),
            'source_hashes':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(HERE.glob('*.py'))},
            'model_obj_sha256':hashlib.sha256(Path(model).read_bytes()).hexdigest(),
            'cloth_obj_sha256':hashlib.sha256(Path(cloth).read_bytes()).hexdigest(),
            'cases':rows,'all_independent_expectations_met':all(r['expectation_met'] for r in rows),
            'all_collision_counts_agree':all(r['collision_counts_agree'] for r in rows),
            'scope':'Static T-pose analytic calibration only. No new cloth simulation, donning, material or physical fit approval.',
            'known_legacy_contract_gap':'Routing assumes supplied paths really belong inside the body. A displaced body with stale paths is deliberately outside that narrow contract.',
            'cleanup':'Generated artifacts retained in caller-selected output directory; no service, spending or repository settings changed.'}
    write_json(out/'experiment.json',report)
    if not report['all_independent_expectations_met']:raise SystemExit('Control expectation failed; inspect evidence, do not tune a mesh to obtain PASS.')
    print(json.dumps({'output':str(out),'cases':len(rows),'independent_expectations':'PASS','collision_count_agreement':report['all_collision_counts_agree']}))


if __name__=='__main__':main()
