#!/usr/bin/env python3
"""Rebuild the MakeHuman-specific high-waist arrangement. Verification deps only.

The contour is an actual torso/plane intersection; its two arcs are resampled
and projected 7 mm outside real triangles. No body geometry is modified.
"""
import json,numpy as np,trimesh,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
source=ROOT/'web/human-studio/assets/human.json';s=json.loads(source.read_text());v=np.array(s['vertices']).reshape(-1,3)/100;f=np.array(s['indices']).reshape(-1,3);used=np.unique(f);v[:,1]-=v[used,1].min();body=trimesh.Trimesh(v,f,process=False)
ids=next(c['path'] for c in s['controls'] if c['key']=='waist');natural=float(v[ids[:-1],1].mean());height=round((natural+.035)/.005)*.005
lines=trimesh.intersections.mesh_plane(body,[0,1,0],[0,height,0]);lines=lines[np.all(abs(lines[:,:,0])<.24,axis=1)]
p=np.unique(np.round(lines.reshape(-1,3),10),axis=0);center=(p.min(0)+p.max(0))/2;angles=np.arctan2(p[:,2]-center[2],p[:,0]-center[0]);p=p[np.argsort(angles)];p=np.roll(p,-int(np.argmax(p[:,0])),axis=0)
if p[1,2]<p[-1,2]:p=np.r_[p[:1],p[:0:-1]]
split=int(np.argmin(p[:,0]));halves=[p[:split+1],np.r_[p[split:],p[:1]]];rows=[]
for half in halves:
 ds=np.r_[0,np.cumsum(np.linalg.norm(np.diff(half,axis=0),axis=1))];targets=np.linspace(0,ds[-1],17);q=np.array([np.interp(targets,ds,half[:,c]) for c in range(3)]).T
 near,_,faces=body.nearest.on_surface(q);q=near+body.face_normals[faces]*.007;rows.append(q)
rows[1][0]=rows[0][-1];rows[1][-1]=rows[0][0]
hipids=next(c['path'] for c in s['controls'] if c['key']=='hips');h=v[hipids];hipcenter=(h.min(0)+h.max(0))/2
profile={'sourceBodySha256':hashlib.sha256(source.read_bytes()).hexdigest(),'sourceWaistVertexIds':ids,'sourceHipVertexIds':hipids,'placement':'high-waist, natural tape mean + 35 mm, rounded to 5 mm','bodyNaturalWaistMm':s['baseMeasurements']['waist']*10,'bodySectionGirthMm':float(np.linalg.norm(lines[:,1]-lines[:,0],axis=1).sum()*1000),'naturalWaistHeightM':natural,'sectionHeightM':height,'targetGapMm':7,'waistPanelsM':[q.tolist() for q in rows],'topsMm':[float(np.linalg.norm(np.diff(q,axis=0),axis=1).sum()*1000) for q in rows],'hemCenterM':[float(hipcenter[0]),float(hipcenter[2])],'waistHeightM':float(np.vstack(rows)[:,1].mean())}
(ROOT/'web/cloth-lab/src/avatar-fit.json').write_text(json.dumps(profile,indent=2)+'\n');print({k:v for k,v in profile.items() if not isinstance(v,list) or k in ['topsMm','hemCenterM']})
