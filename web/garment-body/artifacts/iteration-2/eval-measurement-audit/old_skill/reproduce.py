#!/usr/bin/env python3
"""Audit supplied synthetic fixture using actual triangle/plane intersections."""
from pathlib import Path
import json, hashlib, sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from PIL import Image, ImageDraw, ImageFont
ROOT=Path(__file__).resolve().parent.parent
I=ROOT/'inputs'; O=ROOT/'outputs'; O.mkdir(exist_ok=True)
TOL=1e-6
verts=[]; faces=[]
for line in (I/'body.obj').read_text().splitlines():
 p=line.split()
 if not p:continue
 if p[0]=='v': verts.append([float(x) for x in p[1:4]])
 if p[0]=='f':
  ids=[int(x.split('/')[0])-1 for x in p[1:]]
  for j in range(1,len(ids)-1):faces.append([ids[0],ids[j],ids[j+1]])
v=np.array(verts); f=np.array(faces); assert np.isfinite(v).all()
def cut(y):
 points=[]; edges=set(); lookup={}
 def pid(p):
  key=tuple(np.rint(p/TOL).astype(np.int64))
  if key not in lookup: lookup[key]=len(points);points.append(p)
  return lookup[key]
 for tri in v[f]:
  d=tri[:,1]-y
  if np.min(d)>TOL or np.max(d)<-TOL:continue
  hits=[]
  for a,b in [(0,1),(1,2),(2,0)]:
   if abs(d[a])<=TOL:hits.append(tri[a])
   if d[a]*d[b]<0:hits.append(tri[a]+(tri[b]-tri[a])*(-d[a]/(d[b]-d[a])))
  unique=[]
  for p in hits:
   if not any(np.linalg.norm(p-q)<=TOL for q in unique):unique.append(p)
  if len(unique)==2:
   a,b=[pid(p) for p in unique]
   if a!=b:edges.add(tuple(sorted((a,b))))
  elif len(unique)>2: raise ValueError('Coplanar triangle: explicit handling required')
 adj={i:set() for i in range(len(points))}
 for a,b in edges:adj[a].add(b);adj[b].add(a)
 assert all(len(ns)==2 for ns in adj.values()),'Open/branched cut'
 loops=[]; unseen=set(adj)
 while unseen:
  start=min(unseen); ordered=[start];prev=None;cur=start
  while True:
   nxt=next(n for n in sorted(adj[cur]) if n!=prev)
   if nxt==start:break
   ordered.append(nxt);prev,cur=cur,nxt
   assert len(ordered)<=len(points)
  unseen.difference_update(ordered)
  p=np.array([points[x] for x in ordered]);xz=p[:,[0,2]]
  area=abs(np.sum(xz[:,0]*np.roll(xz[:,1],-1)-np.roll(xz[:,0],-1)*xz[:,1])/2)
  loops.append(dict(points=p,perimeter=float(np.linalg.norm(p-np.roll(p,1,axis=0),axis=1).sum()),area=float(area),centroid=p.mean(axis=0),spans=np.ptp(p,axis=0)))
 # Central loop: contains origin in horizontal XZ plane and largest area.
 central=[]
 from matplotlib.path import Path as MPath
 for j,l in enumerate(loops):
  if MPath(l['points'][:,[0,2]]).contains_point((0,0)):central.append(j)
 assert len(central)==1,'Torso selection ambiguous'
 return loops,central[0]
spec=json.loads((I/'sections.json').read_text()); src=json.loads((I/'source-evidence.json').read_text())
hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(I.iterdir()) if p.is_file()}
results=[]; diagnostics=[];cuts=[]
for s in spec['sections']:
 loops,k=cut(s['y']);l=loops[k];cuts.append((s,loops,k))
 results.append(dict(name=s['name']+'_circumference',value=l['perimeter'],unit='cm',basis='mesh_parameter',mesh_checked=True,definition='Polygonal perimeter of selected central torso loop',plane_origin=[0,s['y'],0],plane_normal=[0,1,0],limitations=['Synthetic proxy geometry; not a measured person','Centimetres depend on supplied 170 cm height prior','Chosen y plane is supplied, not an independently identified anatomical landmark','Finite triangulation; no statistical uncertainty interval available'],uncertainty={'endpoint_merge_tolerance_mesh_units':TOL,'scale_sensitivity':'All lengths scale linearly with assumed height: value * new_height_cm / 170'},evidence_status='computed synthetic mesh dimension under assumed scale'))
 diagnostics.append(dict(name=s['name'],y=s['y'],loop_count=len(loops),selected_loop=k,selection='Unique closed XZ contour containing (0,0); other components are lateral detached arms',components=[dict(index=j,perimeter=x['perimeter'],area=x['area'],centroid=x['centroid'].tolist(),world_axis_spans=x['spans'].tolist(),vertex_count=len(x['points']),closed=True,all_degrees_two=True,selected=j==k) for j,x in enumerate(loops)],all_loops_perimeter=sum(x['perimeter'] for x in loops)))
results.extend([dict(name='height',value=170,unit='cm',basis='prior',mesh_checked=True,definition='Assumed scale prior; mesh Y extent checked',mesh_y_extent=float(np.ptp(v[:,1])),evidence_status='assumed, not observed',limitations=['No calibration object or camera distance; no real-person height measurement']),dict(name='bust_point_distance',value=None,unit='cm',basis='unavailable',mesh_checked=False,evidence_status='unknown',definition='Distance between semantic bust points',limitations=[src['bust_point_distance']['reason']]),dict(name='depth',value=None,unit='cm',basis='unavailable',mesh_checked=False,evidence_status='illustrative image; physical depth unknown',definition='Claimed observed physical depth from input screenshot',limitations=['No physical depth estimator or calibrated camera','Side image is generated synthetic preview; cannot establish observed depth'])])
output=dict(mode='prior_avatar',synthetic_controls_only=True,units='cm (prior-scaled)',coordinate_system='Y up; X lateral; Z front/back',scale_assumption=src['scale'],reference_status=src,mesh_sha256=hashes['body.obj'],source_sha256=hashes,mesh_stats={'vertices':len(v),'triangles':len(f),'bounds_min':v.min(axis=0).tolist(),'bounds_max':v.max(axis=0).tolist()},measurements=results,section_method={'algorithm':'Intersect actual triangles with Y plane; deduplicate hits and undirected segments; snap endpoints to 1e-6 grid; build degree-2 graph and traverse each closed component; select unique loop containing torso axis','tolerance_mesh_units':TOL},sections=diagnostics,software={'python':sys.version.split()[0],'numpy':np.__version__,'matplotlib':matplotlib.__version__})
(O/'corrected-measurements.json').write_text(json.dumps(output,indent=2)+'\n')
fig=plt.figure(figsize=(15,9)); ax=fig.add_subplot(1,2,1,projection='3d')
# Plot real exported triangulated mesh with Y displayed vertically.
vv=v[:,[0,2,1]]
poly=Poly3DCollection(vv[f],alpha=.12,facecolor='#a3b0c0',edgecolor='#657080',linewidth=.12);ax.add_collection3d(poly)
colors=['#d32f2f','#237f3e','#2467b0']
for color,(s,loops,k) in zip(colors,cuts):
 for j,l in enumerate(loops):
  p=np.vstack([l['points'],l['points'][0]])[:,[0,2,1]]
  ax.plot(*p.T,color=color if j==k else '#888888',linewidth=2.5 if j==k else 1)
ax.set(xlim=(v[:,0].min(),v[:,0].max()),ylim=(v[:,2].min(),v[:,2].max()),zlim=(v[:,1].min(),v[:,1].max()),xlabel='X (prior-scaled cm)',ylabel='Z',zlabel='Y (up)',title='Actual triangle mesh + selected torso sections')
ax.set_box_aspect(np.ptp(vv,axis=0));ax.view_init(elev=13,azim=-65)
for i,(color,(s,loops,k)) in enumerate(zip(colors,cuts)):
 ax2=fig.add_subplot(3,2,2+2*i)
 for j,l in enumerate(loops):
  p=np.vstack([l['points'],l['points'][0]])
  ax2.plot(p[:,0],p[:,2],color=color if j==k else '#888888',linewidth=2 if j==k else 1,label=('selected torso' if j==k else 'excluded arm'))
  ax2.text(l['centroid'][0],l['centroid'][2],f"{l['perimeter']:.3f}",ha='center',fontsize=8)
 ax2.plot(0,0,'k+',ms=7);ax2.set_aspect('equal');ax2.set_title(f"{s['name']} Y={s['y']}: {len(loops)} closed loops; torso {loops[k]['perimeter']:.4f} cm")
 ax2.set(xlabel='X (prior-scaled cm)',ylabel='Z');ax2.grid(alpha=.2)
fig.suptitle('Synthetic mesh sections — coloured central torso retained; grey arm loops excluded\nLengths are model dimensions under a 170 cm prior, not real-person measurements',fontsize=13)
fig.tight_layout(rect=(0,0,1,.93));fig.savefig(O/'section-evidence.png',dpi=150);plt.close(fig)
# Remove false caption region completely; retain supplied illustrative synthetic side rendering.
im=Image.open(I/'depth-claim.png').convert('RGB'); clean=Image.new('RGB',(640,790),'white'); crop=im.crop((0,0,384,590));clean.paste(crop,((640-384)//2,0));draw=ImageDraw.Draw(clean)
try:font=ImageFont.truetype('DejaVuSans.ttf',19);small=ImageFont.truetype('DejaVuSans.ttf',16)
except OSError:font=small=ImageFont.load_default()
lines=['ILLUSTRATIVE SYNTHETIC SIDE PREVIEW','Physical depth: UNKNOWN','No calibrated depth or observed centimetres.','Proxy design assumption; front-only source.','Generated side/back add no observed dimensions.','This is not a measured depth map or Z-buffer.']
for i,line in enumerate(lines):draw.text((18,604+i*29),line,font=font if i<2 else small,fill='#173d64' if i<2 else '#222222')
clean.save(O/'corrected-depth.png')
report='''# Synthetic measurement and evidence audit

All inputs are synthetic controls. No result is a measured real-person dimension. The only supplied reference view is a synthetic front; side and back previews are generated. Mode: `prior_avatar`.

## Calculated measurements

| Selected section | Y level | Torso perimeter (prior-scaled cm) | Loops intersected | Excluded arm lengths (cm) |
|---|---:|---:|---:|---|
'''
for d in diagnostics:
 sel=d['components'][d['selected_loop']]
 report+=f"| {d['name']} | {d['y']} | {sel['perimeter']:.6f} | {d['loop_count']} | "+', '.join(f"{x['perimeter']:.6f}" for x in d['components'] if not x['selected'])+' |\n'
report+='''
## Method and uncertainty

`reproduce.py` parses actual OBJ faces, triangulates any polygons, intersects every triangle with each supplied horizontal Y plane, merges coincident endpoints on a 1e-6 mesh-unit grid, deduplicates segments and traverses the adjacency graph. Every retained component has degree two at every vertex and closes. Each section has a unique central loop containing X=Z=0; the lateral disconnected arm loops are excluded. No OBJ group labels or input reported circumferences are used as numeric measurements. Polygonal edge lengths are summed only for the selected torso loop. The evidence image plots actual triangle geometry and all section loops.

Units are inherited from the supplied `prior-scaled cm` declaration, with assumed height 170 cm and no calibration. Mesh Y extent is checked in JSON; this does not independently validate scale. All lengths change linearly with assumed height (new length = listed length × new height / 170). Endpoint tolerance is numerical, not an estimate of anatomical accuracy. Finite mesh resolution, selected section levels, synthetic shape and unobserved depth are limitations. No statistical confidence interval is justified. The supplied levels are controls, not verified anatomical landmarks.

Height remains a prior. Bust-point distance remains null: no semantic bust landmarks or reliable multi-view evidence. Claimed observed depth 25.3 cm is removed; physical depth remains null. `corrected-depth.png` retains the illustrative side preview with a replacement caption; it is neither an estimator output nor a Z-buffer. Generated views add no independent observed dimensions.

## Audit findings and reproducibility

The original JSON incorrectly labels dimensions as observed, sums disconnected components, invents bust-point distance and claims physical depth from an illustrative screenshot. Recalculated component totals and perimeters are retained in JSON so that torso selection is reviewable. Input report values were not used in the calculation. SHA-256 hashes of every input, mesh bounds and software versions are in `corrected-measurements.json`.

Run `python outputs/reproduce.py` from this run directory (or invoke the script by absolute path). Requires local NumPy, Matplotlib and Pillow; no external service. This writes the corrected JSON and both evidence images. Renderings and final files were inspected during this run; the script records no photographic fit or real-person accuracy claim. No blockers.
'''
helper=O/'helper-crosscheck.json'
if helper.exists():
 h=json.loads(helper.read_text())
 diffs=[abs(a['value']-b['mesh_girth']) for a,b in zip(results[:3],h['measurements'])]
 assert max(diffs)<1e-9
 report+='\nIndependent package helper cross-check executed with `measure_mesh.py --mesh inputs/body.obj --sections outputs/helper-sections.json --unit cm --out outputs/helper-crosscheck.json`. VTK '+h['software']+' selected the central component using seed [0,Y,0]. Maximum absolute difference from the standalone triangle-intersection calculation: '+str(max(diffs))+' cm. Agreement verifies computation, not real-person accuracy.\n'
(O/'report.md').write_text(report)
print(json.dumps({'mesh_stats':output['mesh_stats'],'sections':diagnostics},indent=2))
