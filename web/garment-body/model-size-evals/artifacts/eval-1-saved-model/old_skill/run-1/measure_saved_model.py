#!/usr/bin/env python3
"""Reconstruct only for identity; obtain all delivered measurements from supplied OBJ."""
import csv, hashlib, json, math, platform, sys
from pathlib import Path
OUT=Path(__file__).resolve().parent
ROOT=next(p for p in OUT.parents if (p/'inputs/human.json').is_file())
REPO=ROOT.parent.parent

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(name,data): (OUT/name).write_text(json.dumps(data,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
asset=ROOT/'inputs/human.json'; statefile=ROOT/'inputs/saved-model/final-state.json'; mesh=ROOT/'inputs/saved-model/neutral.obj'
a=json.loads(asset.read_text()); s=json.loads(statefile.read_text())
inputs=[asset,statefile,mesh,ROOT/'inputs/saved-model/posed.obj']
before={str(p.relative_to(ROOT)):sha(p) for p in inputs}
vertices=[]; faces=[]
for line in mesh.read_text().splitlines():
 t=line.split()
 if t and t[0]=='v': vertices.append(tuple(map(float,t[1:4])))
 elif t and t[0]=='f':
  if len(t)!=4: raise ValueError('Expected triangulated OBJ')
  faces.extend(int(v.split('/')[0])-1 for v in t[1:])
assert vertices and all(math.isfinite(v) for xyz in vertices for v in xyz)
assert s['asset']==sha(asset) and s['version']=='makehuman-cm-rig-v1' and s['units']=='cm'
assert a['schema']==1 and a['unit']=='cm'
assert len(s['morphWeights'])==len(a['controls'])==12
assert set(s['poseDegrees'])=={b['name'] for b in a['bones']}, 'Complete pose map required'
ids=a['bodyVertexIds']; remap={original:compact for compact,original in enumerate(ids)}
assert len(vertices)==len(ids)
expected_faces=[remap[i] for i in a['indices']]
assert faces==expected_faces, 'OBJ topology/index order differs from resource'
rest=[list(map(float,a['vertices'][i:i+3])) for i in range(0,len(a['vertices']),3)]
for control,weight in zip(a['controls'],s['morphWeights']):
 for i,x,y,z in control['incr' if weight>=0 else 'decr']:
  for axis,delta in enumerate((x,y,z)): rest[i][axis]+=abs(weight)*delta
floor=min(rest[i][1] for i in ids)
for xyz in rest: xyz[1]-=floor
errors=[math.dist(vertices[j],rest[i]) for j,i in enumerate(ids)]
max_error=max(errors)
assert max_error<1e-7, f'Neutral OBJ does not match reconstructed state: {max_error} cm'
rows=[]
for c in a['controls']:
 key=c['key']; path=c['path']; objpath=[remap[i] for i in path]
 if key=='height':
  value=max(v[1] for v in vertices)-min(v[1] for v in vertices); method='standing_height'; definition='Neutral surface max(Y)-min(Y), all body surface vertices; Y up.'
 else:
  assert all(i in remap for i in path)
  value=sum(math.dist(vertices[x],vertices[y]) for x,y in zip(objpath,objpath[1:]))
  method='landmark_distance' if c['kind']=='landmark distance' else 'surface_tape_path'
  definition=('Straight Euclidean distance between resource-authored surface landmarks.' if method=='landmark_distance' else 'Sum of Euclidean edge lengths along resource-authored closed neutral surface tape path; not a planar section.')
  if method=='surface_tape_path': assert path[0]==path[-1]
 row=dict(name=key,label=c['label'],value=value,unit='cm',method=method,definition=definition,basis='mesh_parameter',mesh_checked=True,target_cm=s['dimensions'][key],difference_cm=value-s['dimensions'][key],cached_reported_cm=s['measuredNeutral'][key],difference_from_cache_cm=value-s['measuredNeutral'][key],asset_vertex_path=path,obj_vertex_path_1based=[i+1 for i in objpath],source='inputs/saved-model/neutral.obj',mesh_sha256=sha(mesh),state_sha256=sha(statefile),asset_sha256=sha(asset),limitations=['Model geometry, not a measurement of a photographed person.','Resource-authored tape/landmark definition; no claim of standardized anthropometry.'])
 rows.append(row)
identity=dict(status='verified',asset_fingerprint_matches=True,version=s['version'],units='cm',coordinates='X left-right, Y up, Z front-back',surface_vertices=len(vertices),triangles=len(faces)//3,face_index_order_matches=True,vertex_order='asset.bodyVertexIds compact order',reconstruction='asset vertices plus saved signed morph coefficients; subtract min surface Y; no fitting or target calibration',maximum_vertex_distance_cm=max_error,rms_vertex_distance_cm=math.sqrt(sum(e*e for e in errors)/len(errors)),tolerance_cm=1e-7,pose_map_complete=True,pose_bones=len(s['poseDegrees']),posed_geometry_validated=False,posed_geometry_note='Posed file preserved and hashed; no skinning audit needed for neutral dimension delivery.')
save('identity-check.json',identity)
save('measurements.json',dict(status='measured_from_verified_neutral_obj',unit='cm',model_version=s['version'],identity_check='identity-check.json',measurements=rows,maximum_absolute_target_difference_cm=max(abs(r['difference_cm']) for r in rows),tokens=None,time_seconds=None))
fields=['name','label','value','unit','method','definition','basis','mesh_checked','target_cm','difference_cm','cached_reported_cm','difference_from_cache_cm','mesh_sha256','state_sha256','asset_sha256','asset_vertex_path','obj_vertex_path_1based','source','limitations']
with (OUT/'measurements.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
 for row in rows: w.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,list) else v for k,v in row.items()})
save('target-comparison.json',{r['name']:{k:r[k] for k in ('value','unit','target_cm','difference_cm','cached_reported_cm','difference_from_cache_cm')} for r in rows})
assert before=={str(p.relative_to(ROOT)):sha(p) for p in inputs},'Input bytes changed during execution'
sources=[ROOT/'skill-old/SKILL.md',ROOT/'skill-old/references/human-studio.md',ROOT/'skill-old/references/tools-and-evidence.md',ROOT/'skill-old/references/geometry-evidence.md',ROOT/'skill-old/scripts/inspect_human_state.py',REPO/'web/human-studio/body-engine.js',Path(__file__)]
save('provenance.json',dict(input_sha256=before,sources_sha256={str(p):sha(p) for p in sources},python=sys.version,platform=platform.platform(),input_bytes_unchanged=True,dependencies='Python standard library only',tokens=None,time_seconds=None))
print(json.dumps({'measurements':len(rows),'maximum_vertex_distance_cm':max_error,'maximum_target_difference_cm':max(abs(r['difference_cm']) for r in rows)}))
