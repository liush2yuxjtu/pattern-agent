#!/usr/bin/env python3
"""Read-only consistency audit; refuses neutral measurements if input mesh differs."""
import csv,hashlib,json,platform,sys
from pathlib import Path
import numpy as np
BASE=Path(__file__).resolve().parents[5]
OUT=Path(__file__).resolve().parent
FILES={'state':BASE/'inputs/consistency-check/final-state.json','mesh':BASE/'inputs/consistency-check/neutral.obj','asset':BASE/'inputs/human.json','skill':BASE/'skill-old/SKILL.md','helper':BASE/'skill-old/scripts/inspect_human_state.py','runtime':BASE.parent.parent/'web/human-studio/body-engine.js','audit_code':Path(__file__).resolve()}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(n,d): (OUT/n).write_text(json.dumps(d,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
s=json.loads(FILES['state'].read_text());a=json.loads(FILES['asset'].read_text())
raw=FILES['mesh'].read_text().splitlines();v=np.array([[float(x) for x in l.split()[1:4]] for l in raw if l.startswith('v ')])
f=np.array([[int(x.split('/')[0])-1 for x in l.split()[1:]] for l in raw if l.startswith('f ')])
ids=np.array(a['bodyVertexIds']);rest=np.array(a['vertices'],dtype=float).reshape(-1,3)
for c,w in zip(a['controls'],s['morphWeights']):
 for i,x,y,z in c['incr' if w>=0 else 'decr']:rest[i]+=abs(w)*np.array([x,y,z])
rest[:,1]-=rest[ids,1].min()
remap={int(x):i for i,x in enumerate(ids)}
expected_faces=np.array([remap[int(x)] for x in a['indices']]).reshape(-1,3)
shape_ok=v.shape==rest[ids].shape;faces_ok=f.shape==expected_faces.shape and np.array_equal(f,expected_faces)
d=np.linalg.norm(v-rest[ids],axis=1) if shape_ok else None
asset_ok=sha(FILES['asset'])==s['asset']
tolerance=0.00001
neutral_ok=asset_ok and faces_ok and shape_ok and np.isfinite(v).all() and d.max()<=tolerance
mapped={int(x):v[i] for i,x in enumerate(ids)} if shape_ok else {}
def measure(points,c):
 if c['key']=='height':return float(np.ptp(np.array([points[int(i)] for i in ids])[:,1]))
 return sum(float(np.linalg.norm(points[int(j)]-points[int(i)])) for i,j in zip(c['path'],c['path'][1:]))
controls=s['dimensions'];reconstructed={c['key']:measure(rest,c) for c in a['controls']}
mesh_diagnostic={c['key']:measure(mapped,c) for c in a['controls']} if shape_ok and faces_ok else None
sources={k:{'path':str(p.relative_to(BASE)) if p.is_relative_to(BASE) else str(p),'sha256':sha(p)} for k,p in FILES.items()}
audit={'status':'verified_neutral' if neutral_ok else 'refused_neutral_export','sources':sources,'asset_fingerprint_matches_state':asset_ok,'units':'cm','coordinate_system':'X left/right, Y up, Z front/back','vertex_count':len(v),'triangle_count':len(f),'exact_face_index_mapping_matches_asset':faces_ok,'neutral_vertex_tolerance_cm':tolerance,'neutral_vertex_comparison':{'rms_distance_cm':float(np.sqrt(np.mean(d*d))),'max_distance_cm':float(d.max()),'vertices_above_tolerance':int(sum(d>tolerance))},'supplied_mesh_axis_spans_cm':np.ptp(v,axis=0).tolist(),'reconstructed_neutral_axis_spans_cm':np.ptp(rest[ids],axis=0).tolist(),'nonzero_pose_bones':{k:x for k,x in s['poseDegrees'].items() if any(x)},'reconstructed_neutral_measurements_cm':reconstructed,'reconstruction_minus_cached_cm':{k:reconstructed[k]-s['measuredNeutral'][k] for k in controls},'supplied_mesh_diagnostic_paths_cm':mesh_diagnostic,'diagnostic_caveat':'Input topology maps to resource, but vertex geometry is not reconstructed neutral. Mesh path values and Y span are diagnostics only; not valid neutral body dimensions or claimed posed-state correspondence.','python':platform.python_version(),'numpy':np.__version__,'tokens':None,'elapsed_time_seconds':None}
write('consistency-audit.json',audit)
rows=[]
for c in a['controls']:
 k=c['key'];method='standing_height' if k=='height' else ('landmark_distance' if len(c['path'])==2 else 'surface_tape_path')
 rows.append({'name':k,'value_cm':reconstructed[k] if neutral_ok else None,'unit':'cm','definition':method,'landmark_vertex_indices':c.get('path',[]),'basis':'mesh_parameter' if neutral_ok else 'unavailable','mesh_checked':True,'control_target_cm':controls[k],'difference_from_target_cm':reconstructed[k]-controls[k] if neutral_ok else None,'source_mesh_sha256':sources['mesh']['sha256'],'source_state_sha256':sources['state']['sha256'],'source_asset_sha256':sources['asset']['sha256'],'status':audit['status'],'reason':None if neutral_ok else 'Supplied mesh does not match neutral geometry reconstructed from supplied state/asset. Do not substitute cache or control targets.'})
write('measurements.json',{'status':audit['status'],'measurements':rows})
with (OUT/'measurements.csv').open('w',newline='') as handle:
 keys=[k for k in rows[0] if k!='landmark_vertex_indices'];writer=csv.DictWriter(handle,fieldnames=keys);writer.writeheader();writer.writerows({k:r[k] for k in keys} for r in rows)
print(json.dumps({'status':audit['status'],'mesh_rms_cm':audit['neutral_vertex_comparison']['rms_distance_cm'],'mesh_max_cm':audit['neutral_vertex_comparison']['max_distance_cm'],'topology_matches':faces_ok,'asset_matches':asset_ok,'dimensions_exported_as_null':sum(r['value_cm'] is None for r in rows)},indent=2))
