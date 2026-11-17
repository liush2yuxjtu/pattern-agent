#!/usr/bin/env python3
"""Recompute synthetic proxy sections, render evidence, replace false depth caption.
Run: python outputs/reproduce.py --inputs inputs --out outputs
"""
import argparse, hashlib, json, platform
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from PIL import Image, ImageDraw, ImageFont

TOL=1e-6

def read_obj(path):
    vertices=[]; faces=[]
    for line in path.read_text().splitlines():
        a=line.split()
        if not a: continue
        if a[0]=='v': vertices.append(list(map(float,a[1:4])))
        if a[0]=='f':
            q=[int(x.split('/')[0])-1 for x in a[1:]]
            faces.extend([[q[0],q[i],q[i+1]] for i in range(1,len(q)-1)])
    return np.array(vertices), np.array(faces)

def cut(vertices,faces,y):
    nodes={}; coordinates=[]; edges=set()
    def node(p):
        key=tuple(np.rint(p/TOL).astype(np.int64))
        if key not in nodes: nodes[key]=len(coordinates); coordinates.append(p)
        return nodes[key]
    for tri in vertices[faces]:
        pts=[]
        for a,b in zip(tri,np.roll(tri,-1,axis=0)):
            da,db=a[1]-y,b[1]-y
            if abs(da)<=TOL: pts.append(a)
            if da*db < 0: pts.append(a+(b-a)*(-da)/(db-da))
        unique=[]
        for p in pts:
            if not any(np.linalg.norm(p-q)<TOL for q in unique): unique.append(p)
        if len(unique)==2:
            a,b=map(node,unique)
            if a!=b: edges.add(tuple(sorted((a,b))))
        elif len(unique)>2: raise ValueError('Coplanar triangle requires separate handling')
    adj={i:[] for i in range(len(coordinates))}
    for a,b in edges: adj[a].append(b); adj[b].append(a)
    if any(len(v)!=2 for v in adj.values()): raise ValueError('Section not closed unbranched loops')
    unseen=set(adj); loops=[]
    while unseen:
        start=min(unseen); order=[start]; prev=None; cur=start
        while True:
            nxt=next(n for n in adj[cur] if n!=prev)
            if nxt==start: break
            if nxt in order: raise ValueError('Unexpected topology')
            order.append(nxt); prev,cur=cur,nxt
        unseen.difference_update(order)
        p=np.array([coordinates[i] for i in order]); p=np.vstack([p,p[0]])
        loops.append({'points':p,'perimeter':float(np.linalg.norm(np.diff(p,axis=0),axis=1).sum()),'center':p[:-1].mean(axis=0)})
    return sorted(loops,key=lambda l:l['center'][0])

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--inputs',type=Path,default=Path(__file__).resolve().parent.parent/'inputs'); ap.add_argument('--out',type=Path,default=Path(__file__).resolve().parent); a=ap.parse_args(); a.out.mkdir(exist_ok=True,parents=True)
    src=json.loads((a.inputs/'source-evidence.json').read_text()); specs=json.loads((a.inputs/'sections.json').read_text())
    v,f=read_obj(a.inputs/'body.obj'); assert np.isfinite(v).all()
    hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(a.inputs.iterdir()) if p.is_file()}
    common=['Synthetic simplified body proxy; no anatomical accuracy established.','Single synthetic front only; generated side/back add no observed dimensions.','Centimetres inherit the assumed 170 cm height; no calibrated scale.','Landmark levels are fixture-defined, not verified anatomical landmarks.']
    dims=[{'name':'height','value':170,'unit':'cm','basis':'prior','mesh_checked':False,'definition':'Assumed scale height, not measured human stature','evidence_status':'assumed','limitations':common.copy()}]
    sections=[]
    for s in specs['sections']:
        loops=cut(v,f,s['y']); selected=min(range(len(loops)),key=lambda i:np.linalg.norm(loops[i]['center'][[0,2]]))
        p=loops[selected]['points']; val=loops[selected]['perimeter']
        sections.append((s,loops,selected))
        dims.append({'name':s['name']+'_circumference','value':val,'unit':'cm','basis':'mesh_parameter','mesh_checked':True,'definition':'Polygonal circumference of central torso at horizontal y='+str(s['y'])+' cm','evidence_status':'calculated_synthetic_proxy','plane_origin':[0,s['y'],0],'plane_normal':[0,1,0],'component_selection':'Closed loop whose vertex-mean XZ center is closest to central axis; inspect evidence; disconnected arms excluded.','selected_component_index_left_to_right':selected,'component_count':len(loops),'all_component_perimeters_cm':[l['perimeter'] for l in loops],'world_axis_spans_cm':np.ptp(p,axis=0).tolist(),'limitations':common.copy(),'uncertainty':{'statistical_interval':None,'section_join_tolerance_mesh_cm':TOL,'scale_sensitivity':'A different assumed height H scales all lengths by H/170. A 1% height change changes these girths by 1%.','unquantified':['polygon tessellation','chosen anatomical section level','body shape prior','single-view and camera ambiguity']}})
    for name,reason in [('bust_point_distance','No semantic bust landmarks or reliable multiview evidence supplied.'),('physical_depth','Illustrative side proxy is not a depth estimate or observed centimetre depth.')]:
        dims.append({'name':name,'value':None,'unit':'cm','basis':'unavailable','mesh_checked':False,'definition':reason,'evidence_status':'unknown','limitations':[reason]+common})
    result={'mode':'prior_avatar','synthetic_control':True,'anatomical_accuracy_verified':False,'source_evidence':src,'source_hashes_sha256':hashes,'mesh_sha256':hashes['body.obj'],'mesh_coordinates':{'up_axis':'y','left_right_axis':'x','front_back_axis':'z','units':'prior-scaled cm','scale_assumption':src['scale'],'mesh_vertical_extent_cm':float(np.ptp(v[:,1])),'additional_rescaling_applied':False},'method':{'intersection':'Actual OBJ triangles intersected with y=constant planes; edge crossing endpoints joined by quantized 3D coordinates; deduplicated undirected segments form degree-2 closed loops. Polygon perimeter sums only selected loop edge lengths.','tolerance_cm':TOL,'input_claims_trusted':False},'depth':{'kind':'illustrative','physical_depth_cm':None,'caption_replaced':True,'content':'Existing synthetic side proxy preview; not an inferred depth map.'},'dimensions':dims,'software':{'python':platform.python_version(),'numpy':np.__version__,'matplotlib':matplotlib.__version__}}
    (a.out/'corrected-measurements.json').write_text(json.dumps(result,indent=2)+'\n')
    fig=plt.figure(figsize=(15,9)); ax=fig.add_subplot(1,2,1,projection='3d')
    # Plot actual triangles; map mesh X,Z,Y to plotting X,Y,Z so vertical remains up.
    tri=v[f][:,:,[0,2,1]]
    ax.add_collection3d(Poly3DCollection(tri,facecolor='#bbc5cd',edgecolor='none',alpha=.25))
    colors=['#d25600','#007ab3','#832db3']
    for (s,loops,sel),col in zip(sections,colors):
        for i,l in enumerate(loops):
            p=l['points']; ax.plot(p[:,0],p[:,2],p[:,1],color=col if i==sel else '#777777',linewidth=2 if i==sel else 1)
    ax.set(xlim=(v[:,0].min(),v[:,0].max()),ylim=(v[:,2].min(),v[:,2].max()),zlim=(v[:,1].min(),v[:,1].max()),xlabel='X (prior cm)',ylabel='Z (prior cm)',zlabel='Y up (prior cm)',title='Actual OBJ triangle render + actual intersections')
    ax.set_box_aspect((np.ptp(v[:,0]),np.ptp(v[:,2]),np.ptp(v[:,1]))); ax.view_init(16,-70)
    grid=fig.add_gridspec(3,2)
    for j,((s,loops,sel),col) in enumerate(zip(sections,colors)):
        ax2=fig.add_subplot(grid[j,1])
        for i,l in enumerate(loops):
            p=l['points']; ax2.plot(p[:,0],p[:,2],color=col if i==sel else '#999999',linewidth=2,label=('SELECTED torso' if i==sel else 'excluded arm')+f": {l['perimeter']:.3f} cm")
        ax2.set_aspect('equal'); ax2.set(xlabel='X (prior cm)',ylabel='Z (prior cm)',title=f"{s['name'].upper()}: y={s['y']} cm; {len(loops)} closed loops"); ax2.legend(fontsize=8,loc='upper right'); ax2.grid(alpha=.2)
    fig.suptitle('SYNTHETIC PROXY SECTION AUDIT | 170 cm scale assumption | No real-person dimensions',fontsize=13)
    fig.tight_layout(rect=(0,.03,1,.96)); fig.savefig(a.out/'section-evidence.png',dpi=150); plt.close(fig)
    # Remove the entire old bottom caption, retaining only the illustrative preview.
    original=Image.open(a.inputs/'depth-claim.png').convert('RGB'); preview=original.crop((0,0,original.width,590))
    canvas=Image.new('RGB',(900,720),'#eef1f5'); canvas.paste(preview,((900-preview.width)//2,0)); d=ImageDraw.Draw(canvas)
    fontpath='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'; font=ImageFont.truetype(fontpath,18)
    for i,line in enumerate(['ILLUSTRATIVE SYNTHETIC SIDE PROXY','Not an estimated depth map. Physical depth: UNKNOWN.','No observed centimetre depth; 170 cm scale is assumed.','Single synthetic front; generated side/back do not add observations.']):
        d.text((24,605+i*25),line,font=font,fill='#972d16' if i==0 else '#172536')
    canvas.save(a.out/'corrected-depth.png')
    print(json.dumps({'measurements':[(d['name'],d['value']) for d in dims],'loop_counts':[len(q[1]) for q in sections],'files':['corrected-measurements.json','section-evidence.png','corrected-depth.png']},indent=2))
if __name__=='__main__': main()
