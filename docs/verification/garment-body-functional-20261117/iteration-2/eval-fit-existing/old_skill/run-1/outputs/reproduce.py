#!/usr/bin/env python3
"""Fit supplied synthetic masks. Run: python outputs/reproduce.py [--inputs inputs] [--out outputs]."""
import argparse, json, time, hashlib, platform
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import cv2
import scipy
from scipy.optimize import differential_evolution, minimize
from PIL import Image, ImageDraw
import PIL
import generator as gen
from verify_masks import compare, overlay, load_mask

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def raster(v,f,view):
    xx=v[:,0 if view=='front' else 2]
    xy=np.column_stack(((xx+50)*384/100,(180-v[:,1])*640/184))
    img=Image.new('L',(384,640));draw=ImageDraw.Draw(img)
    for face in f: draw.polygon([tuple(p) for p in xy[face]],fill=255)
    return np.asarray(img)>127

def reread(path):
    v=[];f=[]
    for line in path.read_text().splitlines():
        if line.startswith('v '):v.append(list(map(float,line.split()[1:])))
        elif line.startswith('f '):f.append([int(s.split('/')[0])-1 for s in line.split()[1:]])
    return np.asarray(v),np.asarray(f)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--inputs',type=Path,default=Path(__file__).resolve().parent.parent/'inputs');ap.add_argument('--out',type=Path,default=Path(__file__).resolve().parent);a=ap.parse_args()
    start=datetime.now(timezone.utc);tick=time.perf_counter();a.out.mkdir(parents=True,exist_ok=True)
    camera=json.loads((a.inputs/'camera.json').read_text());assert camera==gen.CAMERA,'Camera mismatch: refusing to change frozen projection'
    initial=json.loads((a.inputs/'initial-params.json').read_text());assert initial['height']==170
    views=['front','side'];refs={s:load_mask(a.inputs/f'target-{s}-mask.png') for s in views}
    for x in refs.values():assert x.shape==(640,384) and x.any()
    keys=['chest','waist','hip','depth_ratio'];bounds=[(60,120),(50,110),(65,130),(.45,1.05)]
    history=[]
    def params(x):return dict(height=170.0,**dict(zip(keys,map(float,x))))
    def objective(x):
        v,f,_=gen.mesh(params(x));loss=0.
        for s in views:
            b=raster(v,f,s);r=refs[s];loss+=np.count_nonzero(b^r)/np.count_nonzero(b|r)
        return loss/2
    v,f,g=gen.mesh(initial)
    for s in views:Image.fromarray(raster(v,f,s).astype('uint8')*255).save(a.out/f'initial-{s}-mask.png')
    def callback(x,convergence):
        row=dict(iteration=len(history)+1,loss=objective(x),params=params(x));history.append(row)
        if len(history)%5==0:print('iteration',len(history),'loss',row['loss'],flush=True)
    result=differential_evolution(objective,bounds,x0=[initial[k] for k in keys],seed=2468,popsize=7,maxiter=42,tol=.00001,polish=False,callback=callback,workers=1)
    refined=minimize(objective,result.x,method='Powell',bounds=bounds,options={'maxiter':10,'xtol':.0001,'ftol':.00001})
    best=refined.x if refined.fun<result.fun else result.x
    p=params(best);assert all(lo<=p[k]<=hi for k,(lo,hi) in zip(keys,bounds))
    (a.out/'params.json').write_text(json.dumps(p,indent=2)+'\n');v,f,g=gen.mesh(p);gen.export_obj(a.out/'fitted.obj',v,f,g)
    # Independent file reopening: only parsed exported vertices/faces feed final evaluation and previews.
    rv,rf=reread(a.out/'fitted.obj');assert np.isfinite(rv).all() and rf.min()>=0 and rf.max()<len(rv)
    assert abs(np.ptp(rv[:,1])-170)<1e-6
    metrics={'initial':{},'final':{},'protocol':{'resolution_px':[384,640],'camera':camera,'threshold':'>127','contours':'external contours, all components, one-pixel boundary; pooled bidirectional Euclidean distances','target_evidence':'only supplied synthetic front/side binary masks','scale':'170 cm assumed height; no observed anatomical scale'}}
    for s in ['front','side','back']:gen.render(rv,rf,a.out/f'{s}.png',s)
    for s in views:
        gen.render(rv,rf,a.out/f'final-{s}-mask.png',s,True)
        first=load_mask(a.out/f'initial-{s}-mask.png');last=load_mask(a.out/f'final-{s}-mask.png')
        metrics['initial'][s]=compare(refs[s],first);metrics['final'][s]=compare(refs[s],last)
        assert np.array_equal(last,raster(rv,rf,s)), 'Independent union raster mismatch'
        cv2.imwrite(str(a.out/f'{s}-overlay.png'),overlay(np.full((640,384,3),35,np.uint8),refs[s],last))
    edges=np.sort(np.concatenate((rf[:,[0,1]],rf[:,[1,2]],rf[:,[2,0]])),axis=1);_,counts=np.unique(edges,axis=0,return_counts=True)
    normals=np.cross(rv[rf[:,1]]-rv[rf[:,0]],rv[rf[:,2]]-rv[rf[:,0]])
    validation={'vertices':len(rv),'triangles':len(rf),'finite_vertices':bool(np.isfinite(rv).all()),'height_cm_prior':float(np.ptp(rv[:,1])),'boundary_edges':int(sum(counts==1)),'nonmanifold_edges':int(sum(counts>2)),'zero_area_triangles':int(sum(np.linalg.norm(normals,axis=1)<1e-10)),'max_obj_vertex_rounding_error_cm':float(abs(rv-v).max()),'connected_components_expected':6,'mesh_limitation':'Disconnected capped torso, head, two legs and two arms; not an anatomical or watertight union body.'}
    (a.out/'metrics.json').write_text(json.dumps(metrics,indent=2)+'\n')
    (a.out/'validation.json').write_text(json.dumps(validation,indent=2)+'\n')
    (a.out/'optimization-history.json').write_text(json.dumps({'rounds':history,'optimizer':'scipy differential_evolution seed=2468 then bounded Powell','bounds':dict(zip(keys,bounds)),'initial_params':initial,'initial_loss':float(np.mean([1-metrics['initial'][s]['iou'] for s in views])),'final_loss':float(np.mean([1-metrics['final'][s]['iou'] for s in views])),'nfev_de':int(result.nfev),'nfev_powell':int(refined.nfev)},indent=2)+'\n')
    (a.out/'camera.json').write_text(json.dumps(camera,indent=2)+'\n')
    provenance={'mode':'observed_fit on synthetic controls only','coordinates':'fixture convention X left/right, Y up, Z depth (source retained, rather than converting axes)','hashes':{p.name:sha(p) for p in [a.inputs/'generator.py',a.inputs/'camera.json',a.inputs/'initial-params.json',a.inputs/'target-front-mask.png',a.inputs/'target-side-mask.png',a.out/'fitted.obj']},'versions':{'python':platform.python_version(),'numpy':np.__version__,'scipy':scipy.__version__,'opencv':cv2.__version__,'pillow':PIL.__version__}}
    (a.out/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
    lines=['# Synthetic proxy fit evidence','', 'Executed a constrained four-parameter fit to the two supplied binary target masks. No photographs, target parameters, or back evidence were used. This is a synthetic proxy consistency test; it does not recover a real person or establish anatomical accuracy.','', 'The source generator is retained verbatim. Its coordinates are X lateral, Y up, Z depth. Camera is the supplied fixed orthographic 384×640 projection with horizontal extent [-50,50] cm and vertical extent [-4,180] cm. Height is fixed at the assumed 170 cm. No translation, camera adjustment, pose, head, or limb optimization was performed.','', 'Bounds (cm under the prior): chest 60–120, waist 50–110, hip 65–130; depth_ratio 0.45–1.05. All scales remain positive. Additional bounds are broad proxy regularization, not observed anatomy. Objective is mean front/side (1−IoU); deterministic differential evolution followed by bounded Powell. The finite budget and raster plateaus mean the solution is not guaranteed unique or globally optimal.','', '| View | Initial IoU | Final IoU | Initial Dice | Final Dice | Initial mean/P95 px | Final mean/P95 px |','|---|---:|---:|---:|---:|---:|---:|']
    for s in views:
        q=metrics['initial'][s];r=metrics['final'][s];lines.append(f"| {s} | {q['iou']:.6f} | {r['iou']:.6f} | {q['dice']:.6f} | {r['dice']:.6f} | {q['mean_symmetric_contour_distance_px']:.3f}/{q['p95_symmetric_contour_distance_px']:.3f} | {r['mean_symmetric_contour_distance_px']:.3f}/{r['p95_symmetric_contour_distance_px']:.3f} |")
    lines+=['',f'Final parameters: `{json.dumps(p)}`. These are mesh parameters inferred from synthetic silhouette evidence conditional on the source model and height prior. Circumference labels use the generator’s Ramanujan ellipse approximation; no anatomical measurement claim or unsupported confidence interval is made.','', 'Final masks and all previews were rendered from vertices/faces independently reopened from fitted.obj, then all PNG masks were reopened for scoring. Initial and final metrics use identical targets, full canvas, thresholds and external-contour protocol. See validation.json for actual topology checks. The proxy consists of disconnected capped components and lacks anatomical detail.','', 'Overlay legend: green overlap, pink target-only, cyan model-only. Front/side/back PNGs are actual mesh previews; back is a symmetry-driven model prediction with no observed back target. No held-out view exists. Neither IoU nor contour distance is a percentage of body measurement accuracy. Pixel quantization and shared generator assumptions limit identifiability; unmodeled anatomy, asymmetric depth, pose and perspective remain unconstrained.','',f"Weakest final view by IoU: {min(views,key=lambda s:metrics['final'][s]['iou'])}. All target masks and camera hashes are in provenance.json. Reproduce from run directory with `python outputs/reproduce.py`; the script carries the source generator and metric helper alongside it. No external services are needed."]
    (a.out/'report.md').write_text('\n'.join(lines)+'\n')
    end=datetime.now(timezone.utc);duration=time.perf_counter()-tick
    (a.out.parent/'timing.json').write_text(json.dumps({'scope':'Actual reproduce.py optimization, export, independent OBJ/mask reopening, validation, metrics and report; excludes prior task/skill reading and later visual review','start':start.isoformat(),'end':end.isoformat(),'total_duration_seconds':duration,'total_tokens':None,'metadata_not_available':True},indent=2)+'\n')
    print(json.dumps({'params':p,'metrics':metrics,'validation':validation,'duration_seconds':duration},indent=2),flush=True)
if __name__=='__main__':main()
