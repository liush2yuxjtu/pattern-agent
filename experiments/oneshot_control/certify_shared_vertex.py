"""Independent LP witness that an incident triangle pair crosses beyond contact."""
import argparse,hashlib,importlib.util,json
from pathlib import Path
import numpy as np
from scipy.optimize import linprog
p=argparse.ArgumentParser();p.add_argument('--npz',required=True,type=Path);p.add_argument('--pair',required=True,nargs=2,type=int);p.add_argument('--out',required=True,type=Path);p.add_argument('--oracle',type=Path,default=Path(__file__).with_name('independent_oracle_v2.py'));a=p.parse_args()
spec=importlib.util.spec_from_file_location('incident_oracle_v2_witness',a.oracle);oracle=importlib.util.module_from_spec(spec);spec.loader.exec_module(oracle)
with np.load(a.npz) as data:v=data['cloth_vertices'];t=data['cloth_triangles']
i,j=a.pair;A=v[t[i]];B=v[t[j]];shared=sorted(set(map(int,t[i]))&set(map(int,t[j])));nA=np.cross(A[1]-A[0],A[2]-A[0]);nB=np.cross(B[1]-B[0],B[2]-B[0]);axis=np.cross(nA,nB);axis/=np.linalg.norm(axis)
eq=np.zeros((5,6));eq[:3,:3]=A.T;eq[:3,3:]=-B.T;eq[3,:3]=1;eq[4,3:]=1;rhs=np.array([0,0,0,1,1]);solutions=[]
for sign in [-1,1]:
 c=np.concatenate([sign*(A@axis),np.zeros(3)]);r=linprog(c,A_eq=eq,b_eq=rhs,bounds=[(0,None)]*6,method='highs',options={'primal_feasibility_tolerance':1e-9,'dual_feasibility_tolerance':1e-9})
 if not r.success:raise RuntimeError(r.message)
 point=r.x[:3]@A;solutions.append(dict(point=point.tolist(),barycentric_a=r.x[:3].tolist(),barycentric_b=r.x[3:].tolist(),reconstruction_error_m=float(np.linalg.norm(point-r.x[3:]@B))))
pa=np.array(solutions[0]['point']);pb=np.array(solutions[1]['point']);mid=(pa+pb)/2;midA=(np.array(solutions[0]['barycentric_a'])+solutions[1]['barycentric_a'])/2;midB=(np.array(solutions[0]['barycentric_b'])+solutions[1]['barycentric_b'])/2
# This two-triangle local reindexing preserves the shared vertex identity.
ids=sorted(set(map(int,t[i]))|set(map(int,t[j])));mapping={old:new for new,old in enumerate(ids)};local=np.array([[mapping[int(k)] for k in row] for row in t[[i,j]]]);detected=oracle.intersect_pairs(v[ids],local)==[[0,1]]
report=dict(oracle_source_sha256=hashlib.sha256(a.oracle.read_bytes()).hexdigest(),input_sha256=hashlib.sha256(a.npz.read_bytes()).hexdigest(),pair=[i,j],vertex_indices=[t[i].tolist(),t[j].tolist()],triangles_m=[A.tolist(),B.tolist()],shared_vertex_ids=shared,shared_vertex_positions_m=v[shared].tolist(),independent_v2_detects_local_incident_pair=detected,intersection_segment_endpoints=solutions,intersection_segment_length_mm=float(np.linalg.norm(pa-pb)*1000),maximum_distance_beyond_shared_vertex_mm=float(max(np.linalg.norm(point-v[s])*1000 for point in [pa,pb] for s in shared)),interior_midpoint_m=mid.tolist(),midpoint_barycentric_a=midA.tolist(),midpoint_barycentric_b=midB.tolist(),midpoint_strictly_inside_both=bool(np.all(midA>1e-10) and np.all(midB>1e-10)),method='LP equality of independent barycentric combinations, optimized in both directions along triangle-plane intersection line.',limits='Numerical corroboration of a shared-vertex crossing, not formal proof or cloth physics.')
a.out.write_text(json.dumps(report,indent=2,allow_nan=False));print(json.dumps({k:v for k,v in report.items() if k not in ['triangles_m','intersection_segment_endpoints']}))
