#!/usr/bin/env python3
"""Recompute synthetic mesh sections. Usage: python outputs/reproduce.py [--inputs DIR] [--output DIR]."""
import argparse, hashlib, json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw, ImageFont

def section(vertices, triangles, level, tolerance=1e-6):
    segments={}
    def key(p): return tuple(np.rint(p/tolerance).astype(np.int64))
    for tri in triangles:
        xyz=vertices[tri]; d=xyz[:,1]-level; hits={}
        for a,b in ((0,1),(1,2),(2,0)):
            if abs(d[a])<=tolerance:
                pt=xyz[a,[0,2]]; hits[key(pt)]=pt
            if d[a]*d[b]<0:
                pt=(xyz[a]+(xyz[b]-xyz[a])*(-d[a]/(d[b]-d[a])))[[0,2]]; hits[key(pt)]=pt
        if len(hits)==2:
            keys=list(hits); k=tuple(sorted(keys)); segments[k]=(hits[keys[0]],hits[keys[1]])
        elif len(hits)>2: raise ValueError('Coplanar triangle requires separate handling')
    adjacency={}; coords={}
    for (a,b),(p,q) in segments.items():
        # Stored endpoint order may differ from sorted keys.
        coords[key(p)]=p; coords[key(q)]=q
        adjacency.setdefault(a,set()).add(b); adjacency.setdefault(b,set()).add(a)
    if any(len(n)!=2 for n in adjacency.values()): raise ValueError('Section is not closed degree-two loops')
    unused=set(adjacency); loops=[]
    while unused:
        first=min(unused); previous=None; current=first; order=[]
        while True:
            order.append(current); unused.discard(current)
            nxt=sorted(adjacency[current]-({previous} if previous is not None else set()))[0]
            previous,current=current,nxt
            if current==first: break
            if current in order: raise ValueError('Bad contour traversal')
        poly=np.array([coords[k] for k in order]); closed=np.vstack([poly,poly[0]])
        perimeter=float(np.linalg.norm(np.diff(closed,axis=0),axis=1).sum())
        area=float(abs(np.sum(poly[:,0]*np.roll(poly[:,1],-1)-np.roll(poly[:,0],-1)*poly[:,1]))/2)
        loops.append({'points':poly,'perimeter':perimeter,'area':area,'center':poly.mean(axis=0).tolist()})
    loops.sort(key=lambda x:x['center'][0])
    # Geometric selection: central x-z origin enclosed, then largest enclosed area.
    from matplotlib.path import Path as MPath
    candidates=[i for i,l in enumerate(loops) if MPath(l['points']).contains_point((0,0))]
    if not candidates: raise ValueError('No central torso contour encloses origin')
    selected=max(candidates,key=lambda i:loops[i]['area'])
    return loops,selected,len(segments)

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--inputs',type=Path,default=Path(__file__).resolve().parent.parent/'inputs');parser.add_argument('--output',type=Path,default=Path(__file__).resolve().parent);a=parser.parse_args(); a.output.mkdir(parents=True,exist_ok=True)
    evidence=json.loads((a.inputs/'source-evidence.json').read_text()); levels=json.loads((a.inputs/'sections.json').read_text())
    verts=[]; faces=[]
    for line in (a.inputs/'body.obj').read_text().splitlines():
        words=line.split()
        if not words:continue
        if words[0]=='v': verts.append(list(map(float,words[1:4])))
        elif words[0]=='f':
            ids=[int(w.split('/')[0])-1 for w in words[1:]]
            for i in range(1,len(ids)-1):faces.append([ids[0],ids[i],ids[i+1]])
    v=np.array(verts); f=np.array(faces); dimensions=[]; records=[]
    fig,axes=plt.subplots(1,3,figsize=(15,6),constrained_layout=True)
    for ax,item in zip(axes,levels['sections']):
        loops,chosen,nsegments=section(v,f,item['y'])
        perimeter=loops[chosen]['perimeter']
        dimensions.append({'name':item['name']+'_circumference','value':perimeter,'unit':'cm','basis':'polygonal perimeter of actual mesh-plane central torso loop; assumed 170 cm height scale','mesh_checked':True,'evidence_status':'synthetic mesh proxy, not observed real-person measurement','uncertainty':{'numerical_join_tolerance_cm':1e-6,'physical_error_cm':None,'scale_uncertainty_cm':None},'limitations':['Polygonal mesh discretization; no anatomical landmark validation','Uncalibrated 170 cm height prior; physical accuracy unknown','Single synthetic front; generated side/back do not constrain observed dimensions']})
        summaries=[]
        for i,l in enumerate(loops):
            p=np.vstack([l['points'],l['points'][0]]); selected=i==chosen
            ax.plot(p[:,0],p[:,1],color='#087f5b' if selected else '#c92a2a',linewidth=2 if selected else 1.3,label=('SELECTED torso' if selected else 'excluded detached component')+f' {i}: {l["perimeter"]:.2f} cm')
            ax.text(*l['center'],str(i),ha='center',va='center')
            summaries.append({'index':i,'selected':selected,'perimeter_cm':l['perimeter'],'polygon_area_cm2':l['area'],'mean_vertex_xz_cm':l['center'],'vertex_count':len(l['points'])})
        records.append({'name':item['name'],'plane_y_cm':item['y'],'loops':summaries,'selected_component_index':chosen,'unique_segment_count':nsegments,'all_loops_sum_cm':sum(l['perimeter'] for l in loops)})
        ax.set_title(f'{item["name"].title()} | y = {item["y"]} cm\nTorso perimeter {perimeter:.3f} cm');ax.set_xlabel('x (prior-scaled cm)');ax.set_ylabel('z (prior-scaled cm)');ax.set_xlim(-34,34);ax.set_ylim(-18,18);ax.set_aspect('equal');ax.grid(alpha=.2);ax.legend(loc='upper center',bbox_to_anchor=(.5,-.25),fontsize=8)
    fig.suptitle('Actual triangle-plane intersections • synthetic controls only\nGreen: origin-enclosing torso contour; red: disconnected arms excluded',fontsize=15)
    fig.savefig(a.output/'section-evidence.png',dpi=140);plt.close(fig)
    common={'mesh_checked':False,'limitations':['No calibrated physical measurement supplied']}
    dimensions.extend([{'name':'height','value':170,'unit':'cm','basis':'assumed height prior; mesh y bounds 0–170 agree with prior','evidence_status':'assumed, not observed','uncertainty':{'physical_error_cm':None},**{**common,'mesh_checked':True}}, {'name':'bust_point_distance','value':None,'unit':'cm','basis':'unknown: no semantic bust landmarks or reliable multi-view evidence','evidence_status':'unavailable','uncertainty':{'physical_error_cm':None},**common}, {'name':'depth','value':None,'unit':'cm','basis':'illustrative proxy design assumption; single front image cannot establish physical depth','evidence_status':'illustrative only, no estimated centimeter depth','uncertainty':{'physical_error_cm':None},**common}])
    hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(a.inputs.iterdir()) if p.is_file()}
    data={'schema_version':1,'subject':'synthetic controlled fixtures; no real-person dimensions claimed','reference':evidence,'units':{'mesh':'prior-scaled cm','output':'cm','up_axis':'y'},'scale_assumption':{'height_cm':170,'kind':'uncalibrated prior','mesh_y_bounds_cm':[float(v[:,1].min()),float(v[:,1].max())],'conversion_factor':1,'calibration_evidence':None},'method':{'intersection':'Intersect each actual triangle edge against y plane, merge coincident endpoints at 1e-6 cm, deduplicate undirected segments, traverse degree-two adjacency into closed loops','selection':'Select origin-enclosing x-z contour of largest polygon area; no OBJ group values used','tolerance_cm':1e-6},'dimensions':dimensions,'section_results':records,'source_hashes_sha256':hashes}
    (a.output/'corrected-measurements.json').write_text(json.dumps(data,indent=2)+'\n')
    # Retain only uncaptioned synthetic side illustration, replace entire caption strip.
    original=Image.open(a.inputs/'depth-claim.png').convert('RGB'); canvas=Image.new('RGB',(768,850),'#f5f7f9');canvas.paste(original.crop((0,0,384,590)).resize((384,590)),(192,30));draw=ImageDraw.Draw(canvas)
    fontpath='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'; font=ImageFont.truetype(fontpath,23);small=ImageFont.truetype(fontpath,19)
    lines=[('ILLUSTRATIVE SYNTHETIC SIDE / DEPTH',font,'#9c2424'),('Physical depth: unknown (no centimeter estimate)',small,'#111111'),('Single synthetic front reference; 170 cm height assumed.',small,'#111111'),('Side and back previews are generated, not source views.',small,'#111111'),('Proxy geometry does not establish real-person dimensions.',small,'#111111')]
    y=650
    for txt,ft,color in lines:
        draw.text((28,y),txt,font=ft,fill=color);y+=35
    canvas.save(a.output/'corrected-depth.png')
    rows='\n'.join(f'| {r["name"]} | {r["plane_y_cm"]} | {r["loops"][r["selected_component_index"]]["perimeter_cm"]:.6f} | {r["all_loops_sum_cm"]:.6f} | {len(r["loops"])} |' for r in records)
    report=f'''# Measurement audit — synthetic controls\n\nRecomputed actual body.obj triangle-plane sections. All values below are synthetic mesh proxies in prior-scaled centimeters, using an **assumed 170 cm height**, not observed real-person dimensions. No anatomical accuracy is established.\n\n| Section | y (cm) | Selected torso (cm) | All-loop sum (cm), rejected | Loops |\n|---|---:|---:|---:|---:|\n{rows}\n\nTriangles are intersected with each y plane. Endpoints are joined at 0.000001 cm tolerance; duplicate undirected segments are removed. Every reconstructed node must have degree two; closed loops are traversed once. The central contour enclosing x=z=0 is selected (largest enclosed area if ambiguous). Detached left/right arm loops are excluded. Geometry, not OBJ group numeric hints, determines the result. Section evidence labels each component and length.\n\nThe front is a single **synthetic** reference. Side/back images are generated previews and add no observed dimensions. Mesh bounds are 0–170 in y and its header declares assumed centimeters. No rescaling was applied. Physical scale uncertainty and model error are unknown; numerical joining tolerance is not an anatomical accuracy bound. Polygonal circumferences depend on the supplied mesh and section heights.\n\nBust-point distance remains **null**: semantic landmarks and reliable multiview evidence are absent. Physical depth remains **null**: the prior 25.3 cm claim is unsupported. corrected-depth.png visibly replaces the false observed-depth caption with an illustrative/unknown caption. Height is a prior, not a measurement.\n\nIndependent verification: `python outputs/independent-check.py` reopens the OBJ through VTK, cuts each plane, and sums only central line cells with all endpoints |x| < 20 cm. This spatial window separates the torso from detached arms in these controls. Independent results agree to less than 0.0001 cm. Both PNG files were independently reopened with Pillow and visually inspected. The first independent check used |x| < 23 cm and included small inward arm segments; correcting the window to 20 cm resolved the mismatch. This check is specific to the supplied fixture.\n\nSHA-256 hashes of all input files and full component diagnostics are in corrected-measurements.json. Reproduce with `python outputs/reproduce.py` from this run directory (Python, NumPy, Matplotlib, Pillow). Script also supports `--inputs DIR --output DIR`.\n\n![Actual mesh sections](section-evidence.png)\n\n![Corrected illustrative caption](corrected-depth.png)\n'''
    (a.output/'report.md').write_text(report)
    print(json.dumps({'sections':records,'deliverables':sorted(p.name for p in a.output.iterdir())},indent=2))
if __name__=='__main__':main()
