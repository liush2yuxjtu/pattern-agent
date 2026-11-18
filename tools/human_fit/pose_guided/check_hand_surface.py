#!/usr/bin/env python3
"""Actual triangle intersections along anatomical anterior rays, not percentile collision claims."""
import argparse,json
from pathlib import Path
import numpy as np
from runtime import Runtime

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--candidate',required=True);a=ap.parse_args();folder=Path(a.candidate);r=Runtime()
 try:
  s=json.load(open(folder/'final-state.json'));e=r.evaluate(s);rest=e['shape']['rest'];posed=e['posed'];neutral=rest[r.faces]
  # Torso-only anatomical patch. Open at neck/waist; ray tests valid only when 2+ skin hits exist.
  faceids=np.all((abs(neutral[:,:,0])<22)&(neutral[:,:,1]>95)&(neutral[:,:,1]<140),axis=1);tri=posed[r.faces[faceids]];A,B,C=tri[:,0],tri[:,1],tri[:,2];den=(B[:,1]-C[:,1])*(A[:,0]-C[:,0])+(C[:,0]-B[:,0])*(A[:,1]-C[:,1]);valid=abs(den)>1e-9;A,B,C,den=A[valid],B[valid],C[valid],den[valid]
  results={};rows=[]
  for side in ['L','R']:
   boneids=[i for i,n in enumerate(r.names) if n.endswith('.'+side) and (n.startswith('finger') or n.startswith('wrist'))];weighted=np.isin(r.skin,boneids)*r.weight;ids=r.ids[weighted.sum(1)[r.ids]>.5];clearances=[];penetrations=[];covered=0
   for vid in ids:
    x,y,z=posed[vid];u=((B[:,1]-C[:,1])*(x-C[:,0])+(C[:,0]-B[:,0])*(y-C[:,1]))/den;v=((C[:,1]-A[:,1])*(x-C[:,0])+(A[:,0]-C[:,0])*(y-C[:,1]))/den;w=1-u-v;hit=(u>=0)&(v>=0)&(w>=0)
    depths=u[hit]*A[hit,2]+v[hit]*B[hit,2]+w[hit]*C[hit,2]
    if len(depths)<2:continue
    lo,hi=depths.min(),depths.max()
    if hi-lo<1:continue
    covered+=1;clear=z-hi;inside=lo+.05<z<hi-.05;clearances.append(clear)
    if inside:penetrations.append(min(z-lo,hi-z))
    rows.append(dict(side=side,vertex=int(vid),anatomical_front_clearance_cm=float(clear),inside_torso_ray_interval=bool(inside)))
   results[side]=dict(hand_vertices=int(len(ids)),rays_with_two_torso_surfaces=covered,inside_torso_count=len(penetrations),maximum_inside_depth_cm=float(max(penetrations,default=0)),minimum_front_clearance_cm=float(min(clearances)) if clearances else None,front_clearance_p05_cm=float(np.percentile(clearances,5)) if clearances else None)
  result=dict(method='For every >50%-hand-skinned actual vertex, intersect anatomical +Z ray against actual posed torso triangles; compare z with front/back intersections. No z percentile surrogate.',limitations=['Torso patch open at neck/waist, so only rays with >=2 separated skin intersections classified.','Checks skin-skin overlap only; no cloth mesh/contact simulation.','Positive anterior clearance is not proof of original-photo hand gesture.'],hands=results,per_vertex=rows);(folder/'hand-surface-check.json').write_text(json.dumps(result,indent=2));print(json.dumps(results))
 finally:r.close()
if __name__=='__main__':main()
