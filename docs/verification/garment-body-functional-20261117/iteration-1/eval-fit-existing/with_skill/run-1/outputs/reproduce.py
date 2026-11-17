#!/usr/bin/env python3
"""python reproduce.py [--inputs ../inputs]; uses only supplied masks, camera and initial controls."""
from pathlib import Path
import argparse, json, hashlib, time, platform
import numpy as np
import scipy, cv2
from scipy.optimize import differential_evolution, minimize
from PIL import Image, ImageDraw
import generator as gen
from verify_masks import compare, load_mask, overlay
P=Path(__file__).resolve().parent
ap=argparse.ArgumentParser();ap.add_argument('--inputs',type=Path,default=P.parent/'inputs');a=ap.parse_args();I=a.inputs
start=time.time()
def write(name,x): (P/name).write_text(json.dumps(x,indent=2)+'\n')
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
initial=json.loads((I/'initial-params.json').read_text());camera=json.loads((I/'camera.json').read_text());assert camera==gen.CAMERA
views=['front','side']; refs={v:load_mask(I/f'target-{v}-mask.png') for v in views}
for view in views:
    Image.open(I/f'target-{view}-mask.png').save(P/f'target-{view}-mask.png')
write('camera.json',camera);write('initial-params.json',initial)
keys=['chest','waist','hip','depth_ratio']; bounds=[(60,125),(50,115),(65,130),(.45,1.05)]
def params(x):return dict(height=170.,**dict(zip(keys,map(float,x))))
def raster(v,f,view):
    xx=v[:,0 if view=='front' else 2];xy=np.column_stack(((xx+50)*384/100,(180-v[:,1])*640/184))
    im=Image.new('L',(384,640));d=ImageDraw.Draw(im)
    for face in f:d.polygon([tuple(p) for p in xy[face]],fill=255)
    return np.asarray(im)>127
# Reuse the fixed non-torso component projection; torso triangles still rasterized from actual generated vertices.
v0,f0,g0=gen.mesh(initial);torso=np.asarray(g0)=='torso'
fixed={view:raster(v0,f0[~torso],view) for view in views}
def masks(p):
    v,f,g=gen.mesh(p)
    return {view:raster(v,f[torso],view)|fixed[view] for view in views}
def iou(a,b):return np.count_nonzero(a&b)/np.count_nonzero(a|b)
count=0;history=[];best=np.inf
initial_masks=masks(initial)
for view in views:Image.fromarray(initial_masks[view].astype('uint8')*255).save(P/f'initial-{view}-mask.png')
def objective(x):
    global count,best
    count+=1;m=masks(params(x));loss=sum(1-iou(refs[v],m[v]) for v in views)/2
    if loss<best:
        best=loss;history.append(dict(evaluation=count,loss=loss,params=params(x),iou={v:iou(refs[v],m[v]) for v in views}))
    return loss
opt=differential_evolution(objective,bounds,seed=481,popsize=7,maxiter=26,tol=.00015,polish=False,x0=[initial[k] for k in keys],workers=1)
local=minimize(objective,opt.x,method='Powell',bounds=bounds,options={'maxiter':7,'maxfev':650,'xtol':.001,'ftol':.00001})
x=local.x if local.fun<opt.fun else opt.x
# Preserve best actually tested parameters (raster plateaus can make a minimizer's last point worse).
best_record=min(history,key=lambda r:r['loss']);final=best_record['params'];write('params.json',final)
v,f,g=gen.mesh(final);gen.export_obj(P/'fitted.obj',v,f,g)
# Independently parse the written OBJ and use that quantized geometry for every final raster and preview.
verts=[];faces=[]
for line in (P/'fitted.obj').read_text().splitlines():
    s=line.split()
    if s and s[0]=='v':verts.append(list(map(float,s[1:4])))
    if s and s[0]=='f':faces.append([int(z.split('/')[0])-1 for z in s[1:]])
v=np.asarray(verts);f=np.asarray(faces);assert np.isfinite(v).all() and len(v)>0 and f.shape[1]==3
assert f.min()>=0 and f.max()<len(v) and abs(np.ptp(v[:,1])-170)<1e-6
metrics={'protocol':{'camera':camera,'threshold':'>127','contours':'OpenCV RETR_EXTERNAL / CHAIN_APPROX_NONE, exact Euclidean distance transform, concatenated bidirectional boundary samples; P95 over concatenation','reference_sha256':{view:sha(I/f'target-{view}-mask.png') for view in views},'mesh_sha256':sha(P/'fitted.obj'),'scale':'170 cm prior; synthetic proxy, not anatomical accuracy'},'initial':{},'final':{}}
for view in ['front','side','back']:
    gen.render(v,f,P/f'{view}.png',view)
    gen.render(v,f,P/f'final-{view}-mask.png',view,True)
    if view in views:
        actual=load_mask(P/f'final-{view}-mask.png')
        metrics['initial'][view]=compare(refs[view],initial_masks[view]);metrics['final'][view]=compare(refs[view],actual)
        cv2.imwrite(str(P/f'{view}-overlay.png'),overlay(np.full((640,384,3),245,np.uint8),refs[view],actual))
        cv2.imwrite(str(P/f'initial-{view}-overlay.png'),overlay(np.full((640,384,3),245,np.uint8),refs[view],initial_masks[view]))
write('metrics.json',metrics);write('optimization-history.json',{'bounds':dict(zip(keys,bounds)),'seed':481,'evaluations':count,'best_improvements':history,'de_message':str(opt.message),'local_message':str(local.message)})
# Topology audit counts edge multiplicities; disconnected capped components are an intentional generator property.
edges=np.sort(np.concatenate([f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]]),axis=1);_,multiplicity=np.unique(edges,axis=0,return_counts=True)
area=np.linalg.norm(np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]]),axis=1)/2
write('mesh-check.json',{'reopened_from':'fitted.obj','vertices':len(v),'triangles':len(f),'finite':bool(np.isfinite(v).all()),'axis_spans_cm':np.ptp(v,axis=0).tolist(),'boundary_edges':int(sum(multiplicity==1)),'nonmanifold_edges':int(sum(multiplicity>2)),'zero_area_triangles':int(sum(area<1e-10)),'coordinate_system':'generator native: X lateral, Y up, Z depth; frozen camera retained','disconnected_components':'6 capped lofts; intersections/overlap possible; no watertight anatomical union claim'})
write('run.json',{'python':platform.python_version(),'numpy':np.__version__,'scipy':scipy.__version__,'opencv':cv2.__version__,'optimization_duration_seconds':time.time()-start,'inputs':{p.name:sha(p) for p in [I/'generator.py',I/'camera.json',I/'initial-params.json',I/'target-front-mask.png',I/'target-side-mask.png']}})
rows='\n'.join(f"| {stage} | {view} | {metrics[stage][view]['iou']:.6f} | {metrics[stage][view]['dice']:.6f} | {metrics[stage][view]['mean_symmetric_contour_distance_px']:.4f} | {metrics[stage][view]['p95_symmetric_contour_distance_px']:.4f} |" for stage in ['initial','final'] for view in views)
report=f'''# Constrained synthetic proxy fit

Completed actual constrained parameter optimization using only the supplied front and side binary masks as target evidence. The 170 cm height is a fixed scale prior, not an observed human dimension. This is a synthetic simplified body proxy, not anatomical measurement or anatomical accuracy. No side or back photograph was observed or invented.

| Stage | View | IoU | Dice | Mean symmetric contour px | P95 px |
|---|---|---:|---:|---:|---:|
{rows}

All comparisons use the same 384×640 frozen orthographic camera from inputs/camera.json, full canvas, >127 foreground threshold and unchanged reference masks. The contour protocol uses external full boundary chains and concatenated bidirectional exact Euclidean pixel distances. IoU is silhouette agreement, not body-dimension accuracy. metrics.json records reference and exported mesh hashes. Green overlay marks agreement, pink reference-only and cyan model-only pixels.

Fitted controls: {json.dumps(final)}. Chest, waist and hip are generator ellipse circumference controls in prior-scaled cm; depth_ratio is dimensionless. These values are mesh parameters constrained by synthetic silhouettes, not observed anatomical truth. Global height stays exactly 170. The optimization bounds were chest 60–125, waist 50–115, hip 65–130 and depth_ratio 0.45–1.05. A seeded differential-evolution search followed by bounded Powell refinement evaluated {count} candidates. optimization-history.json records actual improving candidates and solver termination messages. The budget was bounded; no claim of unique or global optimality is made.

fitted.obj was independently reopened by an OBJ parser, validated for finite indexed triangle geometry and rendered for all final masks and previews. mesh-check.json records dimensions, edge counts and degenerate triangle count. The native generator coordinate system (X lateral, Y up, Z depth) is deliberately preserved to keep the camera frozen. It consists of six capped, disconnected lofts; overlap and intersections are possible. Previews use the generator's simple triangle shading, not a photorealistic anatomical render. The back preview is an unobserved projection of the fitted proxy, never held-out evidence.

Uncertainty: only two synthetic silhouette masks constrain the solution; surface details, concavities, asymmetry, anatomy and back appearance are not observed. The fixed head, limbs and posture come from the supplied generator. Discrete rasterization creates subpixel parameter ambiguity, and 170 cm scaling remains a prior. Final residuals can reflect raster quantization and the bounded search. No invented confidence interval, photograph or measurement is supplied.

Reproduce from this folder: `python reproduce.py --inputs ../inputs`. generator.py and verify_masks.py are local copies of the supplied generator and skill metric helper. Requires NumPy, SciPy, Pillow and OpenCV. All required deliverables use the requested names; additional target copies, initial overlays, audit and history files aid review. No external service or image generation was used.
'''
(P/'report.md').write_text(report)
print(json.dumps({'params':final,'initial':metrics['initial'],'final':metrics['final'],'evaluations':count,'seconds':time.time()-start},indent=2))
