#!/usr/bin/env python3
"""Bounded synthetic-proxy fit; only supplied masks are target evidence.
Run: python outputs/reproduce.py --inputs inputs --out outputs
Dependencies: numpy scipy Pillow opencv-python. No service or hidden target data.
"""
import argparse, importlib.util, json, hashlib, time, sys
from pathlib import Path
from datetime import datetime, timezone
import numpy as np
import scipy
from scipy.optimize import differential_evolution, minimize
from PIL import Image, ImageDraw
import PIL, cv2

def read_obj(path):
    verts=[];faces=[];groups=[];group=''
    for line in path.read_text().splitlines():
        fields=line.split()
        if not fields:continue
        if fields[0]=='v':verts.append([float(x) for x in fields[1:4]])
        if fields[0]=='g':group=fields[1]
        if fields[0]=='f':faces.append([int(x.split('/')[0])-1 for x in fields[1:]]);groups.append(group)
    return np.array(verts), np.array(faces),groups

def metrics(a,b):
    boundaries=[]
    for m in [a,b]:
        cs,_=cv2.findContours(m.astype(np.uint8),cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_NONE)
        edge=np.zeros(m.shape,np.uint8);cv2.drawContours(edge,cs,-1,1,1);boundaries.append(edge)
    distances=[cv2.distanceTransform(1-e,cv2.DIST_L2,cv2.DIST_MASK_PRECISE) for e in boundaries]
    ds=np.r_[distances[0][boundaries[1]>0],distances[1][boundaries[0]>0]]
    inter=(a&b).sum()
    return dict(iou=float(inter/(a|b).sum()),dice=float(2*inter/(a.sum()+b.sum())),mean_symmetric_contour_distance_px=float(ds.mean()),p95_symmetric_contour_distance_px=float(np.percentile(ds,95)))

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--inputs',type=Path,default=Path(__file__).resolve().parent.parent/'inputs');parser.add_argument('--out',type=Path,default=Path(__file__).resolve().parent);args=parser.parse_args()
    start=time.perf_counter();started=datetime.now(timezone.utc).isoformat();inp=args.inputs.resolve();out=args.out.resolve();out.mkdir(parents=True,exist_ok=True)
    spec=importlib.util.spec_from_file_location('source_generator',inp/'generator.py');g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
    camera=json.loads((inp/'camera.json').read_text());assert camera==g.CAMERA
    initial=json.loads((inp/'initial-params.json').read_text());assert initial['height']==170
    refs={v:np.array(Image.open(inp/f'target-{v}-mask.png').convert('L'))>127 for v in ['front','side']}
    assert all(a.shape==(640,384) and a.any() for a in refs.values())
    keys=['chest','waist','hip','depth_ratio'];bounds=[(60.,125.),(50.,115.),(65.,130.),(.45,1.05)]
    history=[];calls=0
    def params(x):return dict(height=170.,**dict(zip(keys,map(float,x))))
    def quick_mask(p,view):
        # Exact projected outline of straight-centred, elliptic lofts. Final
        # evidence is independently rasterized from exported OBJ triangles.
        v,f,groups=g.mesh(p);axis=0 if view=='front' else 2
        im=Image.new('L',(384,640),0);draw=ImageDraw.Draw(im)
        # Source mesh has six capped lofts, each 48 vertices per ring.
        cursor=0
        for rows in [9,5,5,4,5,4]:
            rings=v[cursor:cursor+rows*48].reshape(rows,48,3)
            left=[((r[:,axis].min()+50)*3.84,(180-r[0,1])*640/184) for r in rings]
            right=[((r[:,axis].max()+50)*3.84,(180-r[0,1])*640/184) for r in rings]
            draw.polygon(left+right[::-1],fill=255);cursor+=rows*48+2
        return np.asarray(im)>127
    def objective(x):
        nonlocal calls
        calls+=1;p=params(x)
        loss=float(np.mean([np.count_nonzero(refs[v]^quick_mask(p,v))/np.count_nonzero(refs[v]|quick_mask(p,v)) for v in refs]))
        if not history or loss<history[-1]['loss']:
            history.append(dict(evaluation=calls,loss=loss,params=p))
        return loss
    result=differential_evolution(objective,bounds,seed=731,popsize=12,maxiter=85,tol=1e-7,polish=False,x0=[initial[k] for k in keys],updating='immediate')
    result2=minimize(objective,result.x,method='Powell',bounds=bounds,options={'xtol':1e-6,'ftol':1e-9,'maxiter':25})
    best=result2.x if result2.fun<result.fun else result.x;p=params(best)
    (out/'params.json').write_text(json.dumps(p,indent=2)+'\n');(out/'camera.json').write_text(json.dumps(camera,indent=2)+'\n')
    v,f,groups=g.mesh(p);g.export_obj(out/'fitted.obj',v,f,groups)
    # Reopen the actual exported OBJ, without regenerating vertices for evidence.
    actual,faces,actual_groups=read_obj(out/'fitted.obj');assert np.isfinite(actual).all();assert faces.min()>=0 and faces.max()<len(actual)
    edges=np.sort(np.concatenate([faces[:,[0,1]],faces[:,[1,2]],faces[:,[2,0]]]),axis=1);_,counts=np.unique(edges,axis=0,return_counts=True)
    topology=dict(vertices=len(actual),triangles=len(faces),boundary_edges=int((counts==1).sum()),nonmanifold_edges=int((counts>2).sum()),height_cm=float(np.ptp(actual[:,1])),connected_lofts=6,overlap_note='Disconnected capped component lofts; component intersections are source design, not a watertight anatomical body.')
    assert topology['boundary_edges']==0 and topology['nonmanifold_edges']==0 and topology['height_cm']==170
    final_metrics={};initial_metrics={}
    for view in ['front','side','back']:
        g.render(actual,faces,out/f'{view}.png',view)
        if view=='back':continue
        g.render(actual,faces,out/f'final-{view}-mask.png',view,True)
        vi,fi,gi=g.mesh(initial);g.render(vi,fi,out/f'initial-{view}-mask.png',view,True)
        # Reload persisted PNGs before evaluating.
        a=refs[view];b=np.array(Image.open(out/f'final-{view}-mask.png').convert('L'))>127;c=np.array(Image.open(out/f'initial-{view}-mask.png').convert('L'))>127
        final_metrics[view]=metrics(a,b);initial_metrics[view]=metrics(a,c)
        overlay=np.zeros((*a.shape,3),np.uint8);overlay[:]=[25,29,34];overlay[a&b]=[55,220,125];overlay[a&~b]=[255,65,145];overlay[~a&b]=[0,205,255];Image.fromarray(overlay).save(out/f'{view}-overlay.png')
    # Geometric circumference check on torso rings, using reopened OBJ edges.
    sections={}
    for name,row in [('hip',1),('waist',3),('chest',5)]:
        ring=actual[row*48:(row+1)*48];sections[name]={'height_y_cm':float(ring[0,1]),'polygon_perimeter_cm':float(np.linalg.norm(np.roll(ring,-1,axis=0)-ring,axis=1).sum()),'basis':'mesh_parameter','mesh_checked':True}
    sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
    provenance={x.name:sha(x) for x in [inp/'generator.py',inp/'camera.json',inp/'initial-params.json',inp/'target-front-mask.png',inp/'target-side-mask.png',out/'fitted.obj']}
    record=dict(initial=initial_metrics,final=final_metrics,protocol={'width_px':384,'height_px':640,'camera':camera,'threshold':127,'contours':'OpenCV RETR_EXTERNAL CHAIN_APPROX_NONE; pooled bidirectional nearest Euclidean contour pixel distances','full_canvas':True,'no_alignment_or_resizing':True,'final_source':'Reopened fitted.obj, source generator triangle rasterizer; metrics reloaded from persisted PNGs'},optimization={'method':'SciPy bounded differential_evolution then Powell','seed':731,'bounds':dict(zip(keys,bounds)),'height_fixed_cm':170,'evaluations':calls,'search_objective':'mean per-view symmetric-difference / union on projected loft outlines','best_search_loss':min(result.fun,result2.fun),'history':history,'termination':str(result.message),'powell_termination':str(result2.message)},mesh_checks=topology,sections=sections,sha256=provenance,versions={'python':sys.version,'numpy':np.__version__,'scipy':scipy.__version__,'pillow':PIL.__version__,'opencv':cv2.__version__})
    (out/'metrics.json').write_text(json.dumps(record,indent=2)+'\n')
    rows='\n'.join(f"| {view} | {initial_metrics[view]['iou']:.6f} → {final_metrics[view]['iou']:.6f} | {initial_metrics[view]['dice']:.6f} → {final_metrics[view]['dice']:.6f} | {initial_metrics[view]['mean_symmetric_contour_distance_px']:.3f} → {final_metrics[view]['mean_symmetric_contour_distance_px']:.3f} | {initial_metrics[view]['p95_symmetric_contour_distance_px']:.3f} → {final_metrics[view]['p95_symmetric_contour_distance_px']:.3f} |" for view in refs)
    report=f'''# Constrained synthetic proxy fitting

Executed bounded SciPy optimization using only the supplied front and side binary masks. This is controlled synthetic silhouette consistency, not anatomical ground truth or a person's body measurement. The supplied source geometry, pose and camera are preserved. No back reference photograph exists; back.png is an inferred rendering of the same proxy.

## Evidence and results

| View | IoU initial → final | Dice initial → final | Mean contour px initial → final | P95 contour px initial → final |
|---|---|---|---|---|
{rows}

Source masks were visually inspected before fitting. Height is frozen to the **assumed 170 cm prior**; bounds are recorded in metrics.json, with depth ratio constrained to [0.45, 1.05]. Circumference bounds are deliberately broad engineering priors, not population confidence intervals. Both views participate in fitting; neither is held out. No mask, camera, scale or source generator was modified. Native coordinates are X left/right, Y up, Z depth; these are preserved to avoid changing the existing model convention. Orthographic front views along +Z, side along +X and back along -Z; canvas is 384×640, horizontal [-50,50] cm, vertical [-4,180] cm.

The optimizer varies chest, waist, hip and depth_ratio with height=170 fixed. Search uses exact silhouette outlines of the supplied straight-centred loft construction; final masks and previews use the source generator triangle rasterizer on vertices independently reopened from fitted.obj. Metrics reopen actual saved PNGs and use the entire frozen canvas. OpenCV external contour points and exact Euclidean distance transforms produce pooled symmetric mean/P95 distances in pixels. Overlays: green overlap, pink reference-only, cyan model-only.

## Mesh and parameter interpretation

Final parameters: `{json.dumps(p)}`. Chest/waist/hip are ellipse-circumference controls in prior-scaled cm, not observed anatomy. Mesh-derived 48-edge torso-ring perimeters at native Y=128/109/88 cm are recorded under sections in metrics.json; small differences from parameter values follow polygon discretization and the ellipse formula. Source lofts include fixed head/limbs and have overlapping disconnected capped components. Reopened mesh has {len(actual)} finite vertices and {len(faces)} triangles; no boundary or nonmanifold edges, height 170 cm. This is a simplified synthetic proxy, not a production anatomical or physical fitting body.

## Uncertainty and limits

Two silhouettes constrain projected widths and depths under this fixed model; they do not determine arbitrary cross-section shapes, anatomical landmarks, clothing ease, tissue structure or an independently validated back surface. Side depth is inferred through the shared ellipse-ratio prior and observed synthetic side envelope. All cm values depend on assumed height; proportional changes in that prior scale all lengths. No statistical confidence interval or anatomical accuracy percentage is claimed. Pixel quantization permits multiple nearby parameters with the same raster silhouette. Remaining pixel discrepancies and each view's changes are preserved above. The weaker final view by IoU is {min(final_metrics,key=lambda x:final_metrics[x]['iou'])}; any tie is equivalent. No unseen back evidence or extra observed photograph was invented.

## Reproduce and inspect

From the run directory: `python outputs/reproduce.py --inputs inputs --out outputs`. Dependencies are NumPy, SciPy, Pillow and OpenCV, with versions and SHA-256 provenance in metrics.json. It writes all requested files in outputs/, plus camera.json. Source input files remain unchanged. Inspect front.png, side.png, back.png, both overlays and initial/final masks. Numerical and mesh checks were executed; image previews are actual mesh renders. No browser, model weights, external service, or image generation was used.
'''
    (out/'report.md').write_text(report)
    ended=datetime.now(timezone.utc).isoformat();duration=time.perf_counter()-start
    (out.parent/'timing.json').write_text(json.dumps({'scope':'reproduce.py execution: load inputs, bounded optimization, export, reopen and evaluate, generate artifacts/report; excludes skill reading and later reviewer image inspection','start':started,'end':ended,'total_duration_seconds':duration,'total_tokens':None,'metadata_not_available':True},indent=2)+'\n')
    print(json.dumps({'params':p,'initial':initial_metrics,'final':final_metrics,'mesh':topology,'duration_seconds':duration,'output':str(out)},indent=2))
if __name__=='__main__':main()
