#!/usr/bin/env python3
"""Independent saved-weight FK/LBS replay. No calibration, solver, or image generation.
FK/frame/LBS formulas from repository generic tools/human_fit/pose_guided/runtime.py.
Run from repository root with this script; only writes next to this file.
"""
import csv, hashlib, importlib.util, json, math, platform, sys
from pathlib import Path
import numpy as np
OUT=Path(__file__).resolve().parent
ROOT=next(p for p in OUT.parents if (p/'AGENTS.md').exists())
BASE=ROOT/'work/model-size-skill-evals-20261118'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
paths={'state':BASE/'inputs/saved-model/final-state.json','asset':BASE/'inputs/human.json','neutral':BASE/'inputs/saved-model/neutral.obj','posed':BASE/'inputs/saved-model/posed.obj'}
before={k:sha(v) for k,v in paths.items()}
s=json.loads(paths['state'].read_text());d=json.loads(paths['asset'].read_text())
spec=importlib.util.spec_from_file_location('exporter',OUT/'export_body_measurements.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
# Execute exporter from actual OBJ; alter cached claims in memory to prove independence.
r=m.export_report(paths['state'],paths['asset'],paths['neutral'],paths['posed'])
fake=json.loads(paths['state'].read_text());fake['measuredNeutral']={k:-12345 for k in m.KEYS}
probe=m.measure(fake,paths['asset'].read_bytes(),paths['neutral'].read_bytes())
assert r['measured_values_cm']==probe['measured_values_cm']
v=np.asarray(d['vertices'],float).reshape(-1,3).copy(); ids=np.asarray(d['bodyVertexIds'],int)
for c,w in zip(d['controls'],s['morphWeights']):
    rows=np.asarray(c['incr' if w>=0 else 'decr'],float)
    if len(rows): v[rows[:,0].astype(int)]+=rows[:,1:]*abs(w)
v[:,1]-=v[ids,1].min()
bones=d['bones'];names=[b['name'] for b in bones]; lookup={n:i for i,n in enumerate(names)};parent=[lookup.get(b['parent'],-1) for b in bones]
assert set(s['poseDegrees'])==set(names), 'Incomplete or unknown pose joints'
heads=np.array([v[d['joints'][b['head']]].mean(0) for b in bones]);tails=np.array([v[d['joints'][b['tail']]].mean(0) for b in bones]);frames=[]
for h,t in zip(heads,tails):
    y=t-h;y/=max(np.linalg.norm(y),1e-12)
    if np.linalg.norm(y)<.5:y=np.array([0.,1.,0.])
    x=np.cross(y,[0,0,1])
    if np.linalg.norm(x)<1e-8:x=np.cross(y,[0,1,0])
    x/=np.linalg.norm(x);z=np.cross(x,y);frames.append(np.column_stack([x,y,z]))
frames=np.array(frames)
rest_rot=np.array([frames[p].T@frames[i] if p>=0 else frames[i] for i,p in enumerate(parent)])
translations=np.array([frames[p].T@(heads[i]-heads[p]) if p>=0 else heads[i] for i,p in enumerate(parent)])
def euler(angles):
    a=np.radians(np.asarray(angles,float));assert a.shape==(3,) and np.isfinite(a).all()
    x,y,z=a;cx,sx=math.cos(x),math.sin(x);cy,sy=math.cos(y),math.sin(y);cz,sz=math.cos(z),math.sin(z)
    return np.array([[1,0,0],[0,cx,-sx],[0,sx,cx]])@np.array([[cy,0,sy],[0,1,0],[-sy,0,cy]])@np.array([[cz,-sz,0],[sz,cz,0],[0,0,1]])
rot=rest_rot@np.array([euler(s['poseDegrees'][n]) for n in names]);order=[]
def visit(i):
    if i in order:return
    if parent[i]>=0:visit(parent[i])
    order.append(i)
for i in range(len(bones)):visit(i)
g=np.zeros_like(rot);world=np.zeros_like(heads)
for i in order:
    p=parent[i];g[i]=g[p]@rot[i] if p>=0 else rot[i];world[i]=world[p]+g[p]@translations[i] if p>=0 else translations[i]
mat=g@frames.transpose(0,2,1);off=world-np.einsum('nij,nj->ni',mat,heads)
skin=np.array(d['skinIndices']).reshape(-1,4);weights=np.array(d['skinWeights'],float).reshape(-1,4);weights/=weights.sum(1,keepdims=True)
posed=np.zeros_like(v)
for k in range(4):posed+=weights[:,k,None]*(np.einsum('nij,nj->ni',mat[skin[:,k]],v)+off[skin[:,k]])
posed[:,1]-=posed[ids,1].min()
actual,faces=m.parse_obj(paths['posed'].read_bytes());neutral,nfaces=m.parse_obj(paths['neutral'].read_bytes())
assert len(actual)==len(ids) and faces==nfaces, 'Posed topology differs from neutral'
errors=np.linalg.norm(np.array(actual)-posed[ids],axis=1);assert errors.max()<=.002, f'Posed replay mismatch: {errors.max()}'
after={k:sha(p) for k,p in paths.items()};assert before==after
proof={'status':'saved_geometry_correspondence_verified','units':'cm','neutral':r['geometry_verification'],'posed':{'vertices':len(actual),'triangles':len(faces),'same_indexed_topology_as_neutral':True,'saved_pose_joints':len(s['poseDegrees']),'replay':'saved morphWeights + intrinsic XYZ FK + normalized four-weight LBS + surface floor grounding','maximum_vertex_error_cm':float(errors.max()),'rms_vertex_error_cm':float(np.sqrt(np.mean(errors**2))),'tolerance_cm':.002},'cached_measuredNeutral_ignored':True,'inputs_before_sha256':before,'inputs_after_sha256':after,'inputs_unchanged':before==after,'source_sha256':{'bundled_exporter_copy':sha(OUT/'export_body_measurements.py'),'generic_runtime':sha(ROOT/'tools/human_fit/pose_guided/runtime.py'),'body_engine':sha(ROOT/'web/human-studio/body-engine.js')},'software':{'python':sys.version,'numpy':np.__version__,'platform':platform.platform()},'tokens':None,'elapsed_time_seconds':None}
(OUT/'geometry-verification.json').write_text(json.dumps(proof,indent=2)+'\n')
with (OUT/'target-comparison.csv').open('w',newline='') as f:
    writer=csv.writer(f);writer.writerow(['name','measured_value_cm','target_cm','measured_minus_target_cm','method'])
    for row in r['measurements']:writer.writerow([row['name'],row['value_cm'],row['body_parameter_target_cm'],row['input_target_delta_cm'],row['method']])
print(json.dumps({'neutral_max_error_cm':r['geometry_verification']['neutral_reconstruction_max_error_cm'],'posed_max_error_cm':float(errors.max()),'cached_claims_ignored':True,'inputs_unchanged':True}))
