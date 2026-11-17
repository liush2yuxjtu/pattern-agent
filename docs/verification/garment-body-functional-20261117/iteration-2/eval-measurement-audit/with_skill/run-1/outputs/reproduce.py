#!/usr/bin/env python3
"""Recompute synthetic proxy sections; no external services. Usage: python outputs/reproduce.py"""
from pathlib import Path
import json, hashlib, sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parent.parent
IN=ROOT/'inputs'; OUT=Path(__file__).resolve().parent
TOL=1e-6
verts=[];faces=[]
for line in (IN/'body.obj').read_text().splitlines():
 p=line.split()
 if not p:continue
 if p[0]=='v':verts.append(list(map(float,p[1:4])))
 if p[0]=='f':
  ids=[int(x.split('/')[0])-1 for x in p[1:]]
  for i in range(1,len(ids)-1):faces.append([ids[0],ids[i],ids[i+1]])
v=np.array(verts);f=np.array(faces)
assert np.isfinite(v).all()
tri=v[f]
def cut(level):
 # Intersect each triangle against y=level; weld endpoints to 1e-6 mesh units.
 points={}; edges=set(); coplanar=0
 def key(p):
  k=tuple(np.rint(p/TOL).astype(np.int64));points.setdefault(k,p);return k
 for t in tri:
  d=t[:,1]-level
  if np.all(np.abs(d)<TOL):coplanar+=1;continue
  hits=[]
  for i,j in [(0,1),(1,2),(2,0)]:
   if abs(d[i])<TOL:hits.append(t[i])
   if d[i]*d[j]<0:hits.append(t[i]+d[i]/(d[i]-d[j])*(t[j]-t[i]))
  uniq={key(p) for p in hits}
  if len(uniq)==2:edges.add(tuple(sorted(uniq)))
 assert coplanar==0,'Coplanar triangle requires explicit boundary treatment'
 adjacency={}
 for a,b in edges:
  adjacency.setdefault(a,set()).add(b);adjacency.setdefault(b,set()).add(a)
 assert all(len(n)==2 for n in adjacency.values()),'Open or branched section'
 unseen=set(adjacency); loops=[]
 while unseen:
  start=min(unseen);order=[start];prev=None;cur=start
  while True:
   nxt=next(x for x in sorted(adjacency[cur]) if x!=prev)
   if nxt==start:break
   order.append(nxt);prev,cur=cur,nxt
   assert len(order)<=len(adjacency)
  unseen.difference_update(order)
  p=np.array([points[k] for k in order]);closed=np.vstack([p,p[0]])
  x,z=p[:,0],p[:,2]
  loops.append({'points':p,'perimeter':float(np.linalg.norm(np.diff(closed,axis=0),axis=1).sum()),'center_xz':p[:,[0,2]].mean(axis=0).tolist(),'area':float(abs(np.dot(x,np.roll(z,-1))-np.dot(z,np.roll(x,-1)))/2),'degree_two':True,'segments':len(p)})
 loops.sort(key=lambda l:l['center_xz'][0])
 # Select central contour by minimum distance of contour centroid from torso axis x=z=0.
 selected=min(range(len(loops)),key=lambda i:np.linalg.norm(loops[i]['center_xz']))
 return loops,selected
source=json.loads((IN/'source-evidence.json').read_text());sections=json.loads((IN/'sections.json').read_text())['sections']
results=[];measurement=[]
fig,axs=plt.subplots(1,3,figsize=(15,5.8))
for ax,s in zip(axs,sections):
 loops,chosen=cut(s['y']);sel=loops[chosen];p=sel['points']
 for i,l in enumerate(loops):
  q=np.vstack([l['points'],l['points'][0]])
  ax.plot(q[:,0],q[:,2],color='#126b41' if i==chosen else '#bb6a60',linewidth=2.4 if i==chosen else 1.3,label=('Selected torso' if i==chosen else 'Excluded disconnected loop')+f" ({l['perimeter']:.3f} cm)")
  ax.text(*l['center_xz'],str(i),ha='center')
 ax.set_aspect('equal');ax.set_xlabel('X (prior-scaled cm)');ax.set_ylabel('Z (prior-scaled cm)')
 ax.set_title(f"{s['name'].title()} | y={s['y']}\nTorso perimeter {sel['perimeter']:.4f} cm");ax.grid(alpha=.2);ax.legend(fontsize=7,loc='lower center')
 result={'name':s['name'],'plane_origin':[0,s['y'],0],'plane_normal':[0,1,0],'selected_component_index':chosen,'selection':'minimum centroid distance to central x=z=0 axis; inspected green contour is central torso','components':[{k:val for k,val in l.items() if k!='points'} for l in loops],'torso_axis_spans':np.ptp(p,axis=0).tolist(),'all_loop_perimeters_sum':sum(l['perimeter'] for l in loops)}
 results.append(result)
 measurement.append({'name':s['name']+'_circumference','value':sel['perimeter'],'unit':'cm','basis':'mesh_parameter','mesh_checked':True,'definition':f"Polygonal perimeter of central torso closed loop at y={s['y']} in supplied mesh",'evidence_status':'calculated synthetic proxy; not observed real-person dimensions','section':result['plane_origin'],'limitations':['Centimetres rely on supplied 170 cm height prior, without external calibration.','Anatomical section labels are supplied controls, not verified landmarks.','Polygonal discretization and section level affect perimeter; no statistical confidence interval.'],'uncertainty':{'endpoint_weld_tolerance_mesh_units':TOL,'statistical_interval':None,'scale_sensitivity':'All lengths scale linearly; a 1% assumed-scale change changes length by 1%.'}})
fig.suptitle('Actual triangle-plane intersections | Y vertical | synthetic proxy\nGreen: selected central torso; red: excluded arm loops; no real-person validation',fontsize=13)
fig.tight_layout(rect=(0,0,1,.88));fig.savefig(OUT/'section-evidence.png',dpi=170);plt.close(fig)
measurement += [
 {'name':'height','value':170,'unit':'cm','basis':'prior','mesh_checked':False,'definition':'Assumed stature used for proxy scale','evidence_status':'assumption','limitations':['No calibration object or known camera distance.','Mesh y span is separately recorded; prior is not an observed person measurement.']},
 {'name':'bust_point_distance','value':None,'unit':'cm','basis':'unavailable','mesh_checked':False,'definition':'Distance between semantic bust landmarks','evidence_status':'unknown','limitations':[source['bust_point_distance']['reason']]},
 {'name':'depth','value':None,'unit':'cm','basis':'unavailable','mesh_checked':False,'definition':'Observed physical depth claimed by original screenshot','evidence_status':'unknown; screenshot is illustrative','limitations':['25.3 cm observed claim withdrawn.','No calibrated physical depth, depth estimator or Z-buffer is supplied; generated side/back views add no observed dimensions.']}]
hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(IN.iterdir()) if p.is_file()}
output={'schema_version':1,'mode':'prior_avatar','subject':'synthetic controlled proxy only','up_axis':'y','mesh_units':'prior-scaled cm','scale_assumption':source['scale'],'evidence_status':'single synthetic front; side/back generated; geometry checks establish proxy dimensions only','mesh_sha256':hashes['body.obj'],'source_hashes':hashes,'software':{'python':sys.version.split()[0],'numpy':np.__version__,'matplotlib':matplotlib.__version__},'mesh_statistics':{'vertices':len(v),'triangles':len(f),'min_xyz':v.min(axis=0).tolist(),'max_xyz':v.max(axis=0).tolist(),'y_span':float(np.ptp(v[:,1]))},'method':{'intersection':'Triangle edge intersections with y plane, endpoint welding, undirected unique edges, degree-two graph traversal into closed loops','tolerance_mesh_units':TOL,'selection':'Central centroid nearest x=z=0; arm loops excluded; plot used for inspection','limitations':'No coplanar triangles encountered at requested cuts. Not an anatomical or physical validation.'},'measurements':measurement,'section_audit':results,'depth_caption':'ILLUSTRATIVE SYNTHETIC PROXY — no observed physical depth; 25.3 cm claim withdrawn'}
(OUT/'corrected-measurements.json').write_text(json.dumps(output,indent=2)+'\n')
im=Image.open(IN/'depth-claim.png').convert('RGB');draw=ImageDraw.Draw(im);draw.rectangle((0,590,im.width,im.height),fill='white')
font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',10)
for y,text in [(596,'ILLUSTRATIVE SYNTHETIC PROXY'),(610,'No observed physical depth; 25.3 cm claim withdrawn.'),(624,'Side design assumption; no calibrated depth evidence.')]:draw.text((7,y),text,fill='#9a2920',font=font)
im.save(OUT/'corrected-depth.png')
lines=['# Measurement audit','', 'All inputs are synthetic controls. Results describe the supplied proxy mesh, never real-person dimensions. A single synthetic front is supplied; generated side/back previews are not observed evidence.','', 'The original report summed disconnected loops and overstated evidence. Triangle-plane cuts were recomputed from body.obj. Coordinates are X left/right, Y vertical, Z front/back. Mesh units are prior-scaled centimetres under the supplied 170 cm stature assumption, without calibration.','', '| Section | Y plane | Selected torso cm | All loops cm (incorrect girth) | Loops |','|---|---:|---:|---:|---:|']
for r,m in zip(results,measurement):lines.append(f"| {r['name']} | {r['plane_origin'][1]} | {m['value']:.6f} | {r['all_loop_perimeters_sum']:.6f} | {len(r['components'])} |")
lines+=['','Each triangle edge crossing was linearly intersected. Endpoints were welded on a 1e-6 mesh-unit grid, duplicate segments removed, and degree-two adjacency graphs traversed into closed unbranched loops. No coplanar triangles occurred. The selected loop has the centroid nearest the central X=Z=0 axis. The plotted large central contour identifies the torso; small lateral contours are excluded arms. Loop closure alone does not establish anatomical validity.','',f"Mesh contains {len(v)} vertices and {len(f)} triangles; vertical span is {np.ptp(v[:,1]):.6f} prior-scaled cm. Height 170 cm remains a prior (not independently measured).",'', 'Bust-point distance stays null: no semantic landmarks or reliable multi-view observations exist. Observed physical depth stays null; the 25.3 cm claim is withdrawn. corrected-depth.png preserves the synthetic side drawing but replaces its caption. No depth estimator or Z-buffer was run.','', 'Uncertainty: units depend on the height assumption; all lengths change linearly with scale (1% scale change = 1% length change). Polygonal resolution, endpoint tolerance, section location, proxy design, garment ambiguity and missing calibration limit interpretation. There is no statistical basis for a confidence interval.','', 'Verification: executed NumPy triangle intersections and rendered all selected/excluded loops with Matplotlib. Source hashes, component perimeters, selection indexes, mesh bounds and software versions are saved in corrected-measurements.json. Further VTK cross-check and visual inspection are recorded in transcript.md.','', 'Reproduce with `python outputs/reproduce.py` from this run directory. Requires local NumPy, Matplotlib and Pillow; no paid or external service. Font: local DejaVu Sans.','', 'No blockers for this synthetic audit. Unknown physical/anatomical quantities remain unavailable.']
(OUT/'report.md').write_text('\n'.join(lines)+'\n')
print(json.dumps({'mesh_statistics':output['mesh_statistics'],'sections':[{ 'name':r['name'],'torso':measurement[i]['value'],'loops':len(r['components']),'selected':r['selected_component_index'],'all_loop_sum':r['all_loop_perimeters_sum']} for i,r in enumerate(results)]},indent=2))
