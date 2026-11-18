#!/usr/bin/env python3
"""Read-only consistency audit; refuses successful dimensions on geometry mismatch."""
import csv, hashlib, importlib.util, io, json, math, platform, subprocess, sys
from collections import Counter
from pathlib import Path
sys.dont_write_bytecode = True
ROOT=Path(__file__).resolve().parents[5]
OUT=Path(__file__).resolve().parent
SCRIPT=ROOT/'skill-new/scripts/export_body_measurements.py'
STATE=ROOT/'inputs/consistency-check/final-state.json'
ASSET=ROOT/'inputs/human.json'
MESH=ROOT/'inputs/consistency-check/neutral.obj'
spec=importlib.util.spec_from_file_location('exporter',SCRIPT)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
s=json.loads(STATE.read_bytes()); a=json.loads(ASSET.read_bytes())
v,f=m.parse_obj(MESH.read_bytes()); exp=m.reconstruct_neutral(a,s['morphWeights'])
ids=a['bodyVertexIds']; compact={x:i for i,x in enumerate(ids)}
ef=[tuple(compact[x] for x in a['indices'][i:i+3]) for i in range(0,len(a['indices']),3)]
errors=[math.dist(x,y) for x,y in zip(v,exp)]
ordered=sorted(errors)
bounds=lambda vv: {'min':[min(p[i] for p in vv) for i in range(3)],'max':[max(p[i] for p in vv) for i in range(3)]}
maxi=max(range(len(errors)),key=errors.__getitem__)
checks={
 'state_version':s.get('version'), 'state_units':s.get('units'),
 'asset_hash_matches_state':sha(ASSET)==s.get('asset'),
 'actual_vertices':len(v),'expected_vertices':len(exp),
 'actual_triangles':len(f),'expected_triangles':len(ef),
 'topology_and_winding_match':Counter(m.triangle_identity(list(x)) for x in f)==Counter(m.triangle_identity(list(x)) for x in ef),
 'all_coordinates_finite':all(math.isfinite(x) for p in v for x in p),
 'neutral_reconstruction_tolerance_cm':m.MESH_TOLERANCE_CM,
 'neutral_reconstruction_max_error_cm':max(errors),
 'neutral_reconstruction_rms_error_cm':math.sqrt(sum(x*x for x in errors)/len(errors)),
 'neutral_reconstruction_median_error_cm':ordered[len(ordered)//2],
 'vertices_exceeding_tolerance':sum(x>m.MESH_TOLERANCE_CM for x in errors),
 'actual_bounds_cm':bounds(v), 'reconstructed_neutral_bounds_cm':bounds(exp),
 'largest_difference':{'compact_index':maxi,'asset_vertex_id':ids[maxi], 'actual_cm':v[maxi], 'expected_neutral_cm':exp[maxi], 'distance_cm':errors[maxi]},
 'saved_pose_joint_count':len(s.get('poseDegrees',{})),
 'saved_nonzero_pose_joint_count':sum(any(abs(q)>0 for q in p) for p in s.get('poseDegrees',{}).values()),
 'pose_reconstruction_run':False,
}
cmd=[sys.executable,str(SCRIPT),'--state',str(STATE),'--asset-json',str(ASSET),'--neutral-mesh',str(MESH),'--out',str(OUT/'measurements.success.json'),'--csv',str(OUT/'measurements.success.csv')]
p=subprocess.run(cmd,text=True,capture_output=True)
(OUT/'exporter.stdout.txt').write_text(p.stdout)
(OUT/'exporter.stderr.txt').write_text(p.stderr)
checks['exporter_exit_code']=p.returncode
checks['neutral_correspondence_verified']=max(errors)<=m.MESH_TOLERANCE_CM
(OUT/'consistency-evidence.json').write_text(json.dumps(checks,indent=2)+'\n')
assert p.returncode!=0 and not checks['neutral_correspondence_verified'], 'Audit changed: review successful export path explicitly'
files=[STATE,ASSET,MESH,SCRIPT,Path(__file__),ROOT/'iteration-1/eval-3-consistency-check/with_skill/run-1/eval_metadata.json',ROOT/'skill-new/SKILL.md',ROOT/'skill-new/references/model-measurements.md',ROOT/'skill-new/references/tools-and-evidence.md',ROOT/'skill-new/references/human-studio.md']
fingerprints={str(x.relative_to(ROOT)):sha(x) for x in files}
(OUT/'source-hashes.json').write_text(json.dumps(fingerprints,indent=2)+'\n')
rows=[]
for c in a['controls']:
 key=c['key']; kind=c['kind']
 method='neutral_mesh_y_extent' if key=='height' else 'closed_neutral_surface_tape_polyline' if kind=='circumference' else 'neutral_surface_landmark_distance'
 definition='Y-axis standing neutral surface extent' if key=='height' else 'Declared closed surface tape polyline; not planar section circumference' if kind=='circumference' else 'Straight distance between declared surface landmarks; not bone length'
 rows.append({'name':key,'label':c['label'],'value_cm':None,'unit':'cm','basis':'unavailable_correspondence_rejected','status':'refused','method':method,'definition':definition,'source_vertices':c.get('path',[]),'body_parameter_target_cm':s.get('dimensions',{}).get(key),'input_target_delta_cm':None,'mesh_checked':True,'measurement_validated':False,'reason':'OBJ fails correspondence to independently reconstructed saved neutral geometry'})
report={'status':'refused','reason':'Neutral OBJ does not correspond to saved state/resource neutral geometry within 0.002 cm. No successful dimensions exported.','units':'cm','measurement_source':'unverified_input_mesh','measured_values_cm':{x['name']:None for x in rows},'target_dimensions_cm':s['dimensions'],'measurements':rows,'geometry_verification':checks,'model_fingerprints':{'state_sha256':sha(STATE),'asset_sha256':sha(ASSET),'neutral_mesh_sha256':sha(MESH)},'person_accuracy_verified':False,'limitations':['Filename neutral.obj does not establish neutral pose.','Pose skinning was not reconstructed; mismatch alone does not establish whether mesh is posed, otherwise changed, or scaled.','measuredNeutral cache is not used to obtain measurements.','Control targets are comparison-only; no delta is claimed without verified mesh correspondence.','No refit, pose edit, shape edit, rendering, or image generation was performed.']}
(OUT/'measurements.refused.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
with (OUT/'measurements.refused.csv').open('w',newline='') as h:
 fields=['name','label','value_cm','unit','basis','status','method','definition','body_parameter_target_cm','input_target_delta_cm','measurement_validated','reason']
 w=csv.DictWriter(h,fieldnames=fields);w.writeheader();w.writerows({k:r[k] for k in fields} for r in rows)
trace={'task':'consistency-check','runtime':platform.python_version(),'tokens':None,'elapsed_seconds':None,'commands':[cmd],'exporter_exit_code':p.returncode,'steps':['Read applicable AGENTS.md, task metadata, skill-new SKILL.md and its three referenced contracts.','Read bundled exporter source; executed exact exporter against supplied read-only inputs. Export rejected before success files.','Independently parsed actual OBJ; replayed saved morphWeights against matching human.json without fitting; checked complete topology and vertex correspondence.','Recorded rejection evidence and 12 null result rows with comparison targets separate.'],'inputs_unchanged':all(sha(x)==fingerprints[str(x.relative_to(ROOT))] for x in (STATE,ASSET,MESH)),'successful_dimensions_exported':False,'self_grade':None}
(OUT/'TRACE.json').write_text(json.dumps(trace,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(checks,indent=2))
