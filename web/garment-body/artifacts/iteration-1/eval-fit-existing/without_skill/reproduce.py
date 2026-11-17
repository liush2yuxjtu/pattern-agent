#!/usr/bin/env python3
"""Reproduce constrained two-mask synthetic fitting, mesh export, and evidence."""
import argparse, json, time, hashlib, shutil, sys
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.optimize import least_squares, differential_evolution, minimize
from scipy.ndimage import binary_erosion, distance_transform_edt
import generator as g

def read(path): return np.asarray(Image.open(path).convert('L'))>127

def contour(a): return a & ~binary_erosion(a)

def metrics(a,b):
    aa,bb=contour(a),contour(b)
    ds=np.concatenate([distance_transform_edt(~aa)[bb],distance_transform_edt(~bb)[aa]])
    inter=np.logical_and(a,b).sum()
    return dict(iou=float(inter/np.logical_or(a,b).sum()),dice=float(2*inter/(a.sum()+b.sum())),mean_symmetric_contour_distance_px=float(ds.mean()),p95_symmetric_contour_distance_px=float(np.percentile(ds,95)))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--inputs',type=Path,default=Path(__file__).resolve().parent.parent/'inputs');ap.add_argument('--out',type=Path,default=Path(__file__).resolve().parent);args=ap.parse_args()
    out=args.out;out.mkdir(exist_ok=True,parents=True)
    targets={v:read(args.inputs/f'target-{v}-mask.png') for v in ['front','side']}
    initial=json.loads((args.inputs/'initial-params.json').read_text())
    assert json.loads((args.inputs/'camera.json').read_text())==g.CAMERA
    def params(x): return dict(height=170.,chest=float(x[0]),waist=float(x[1]),hip=float(x[2]),depth_ratio=float(x[3]))
    # Use central torso row widths for a subpixel geometric initialization.
    ys=np.arange(145,352) # screen rows; y approximately 79..138 cm
    ys=ys[(180-ys*184/640>=88)&(180-ys*184/640<=137)]
    target_widths=[]
    for view in ['front','side']:
        widths=[]
        for y in ys:
            row=targets[view][y]; c=192
            left=c
            while left>0 and row[left-1]:left-=1
            right=c
            while right+1<384 and row[right+1]:right+=1
            widths.append((right-left+1)*100/384/2)
        target_widths.append(widths)
    def width_res(x):
        p=params(x);cr=g.ellipse_radii(p['chest'],p['depth_ratio']);wr=g.ellipse_radii(p['waist'],p['depth_ratio']);hr=g.ellipse_radii(p['hip'],p['depth_ratio'])
        heights=[88,98,109,119,128,138]
        radii=np.array([hr,np.array(hr)*.95,wr,np.array(cr)*.94,cr,[cr[0]*1.02,cr[1]*.85]])
        return np.concatenate([np.interp(180-ys*184/640,heights,radii[:,axis])-np.array(target_widths[axis]) for axis in range(2)])
    fit=least_squares(width_res,[initial[k] for k in ['chest','waist','hip','depth_ratio']],bounds=([40,40,40,.45],[160,160,160,1.05]))
    print('geometric_initialization',fit.x.tolist(),flush=True)
    calls=0
    def objective(x):
        nonlocal calls
        calls+=1;v,f,_=g.mesh(params(x));loss=0
        for view in ['front','side']:
            g.render(v,f,out/'_candidate.png',view,True);a=read(out/'_candidate.png');b=targets[view]
            loss+=1-(a&b).sum()/(a|b).sum()
        return loss
    half=np.array([4,4,4,.04]);lo=np.maximum(fit.x-half,[40,40,40,.45]);hi=np.minimum(fit.x+half,[160,160,160,1.05])
    result=differential_evolution(objective,list(zip(lo,hi)),seed=3107,popsize=7,maxiter=32,tol=1e-7,polish=False,x0=fit.x)
    polished=minimize(objective,result.x,method='Powell',bounds=list(zip(lo,hi)),options={'maxiter':10,'xtol':1e-5,'ftol':1e-8})
    x=polished.x if polished.fun<result.fun else result.x
    fitted=params(x);(out/'params.json').write_text(json.dumps(fitted,indent=2)+'\n')
    v,f,groups=g.mesh(fitted);g.export_obj(out/'fitted.obj',v,f,groups)
    # Independently parse the delivered OBJ. Every final evidence image uses these vertices/faces.
    vv=[];ff=[]
    for line in (out/'fitted.obj').read_text().splitlines():
        if line.startswith('v '):vv.append([float(i) for i in line.split()[1:]])
        elif line.startswith('f '):ff.append([int(i)-1 for i in line.split()[1:]])
    v=np.array(vv);f=np.array(ff)
    assert len(v)>0 and len(f)>0 and np.isfinite(v).all() and f.shape[1]==3 and f.min()>=0 and f.max()<len(v)
    assert abs(np.ptp(v[:,1])-170)<1e-6
    iv,iff,_=g.mesh(initial)
    allmetrics={'protocol':{'resolution':[384,640],'camera':g.CAMERA,'foreground':'grayscale > 127','contour':'foreground minus 3x3 cross binary erosion (SciPy default), outside background','distance':'pooled bidirectional contour nearest-neighbor Euclidean distances; mean and NumPy percentile 95; pixels','targets':{view:{'file':f'inputs/target-{view}-mask.png','sha256':hashlib.sha256((args.inputs/f'target-{view}-mask.png').read_bytes()).hexdigest()} for view in targets}},'initial':{},'final':{}}
    for view in ['front','side','back']:
        g.render(v,f,out/f'{view}.png',view)
        if view=='back':continue
        g.render(iv,iff,out/f'initial-{view}-mask.png',view,True)
        g.render(v,f,out/f'final-{view}-mask.png',view,True)
        a=read(out/f'final-{view}-mask.png');b=targets[view]
        for stage in ['initial','final']:allmetrics[stage][view]=metrics(read(out/f'{stage}-{view}-mask.png'),b)
        rgb=np.zeros((*a.shape,3),dtype=np.uint8);rgb[a&b]=[215,215,215];rgb[b&~a]=[0,210,220];rgb[a&~b]=[245,80,125]
        Image.fromarray(rgb).save(out/f'{view}-overlay.png')
    allmetrics['optimization']={'evaluations':calls,'seed':3107,'objective':'sum of front and side (1-IoU), equally weighted','bounds':{'circumferences_cm':[40,160],'depth_ratio':[.45,1.05],'height_cm':[170,170]},'initialization':fit.x.tolist(),'local_search_bounds':list(zip(lo.tolist(),hi.tolist())),'final_objective':float(min(result.fun,polished.fun))}
    allmetrics['mesh_verification']={'vertices':len(v),'triangles':len(f),'finite':True,'height_cm':float(np.ptp(v[:,1])),'bounds_cm':[v.min(axis=0).tolist(),v.max(axis=0).tolist()],'reopened_obj':True}
    (out/'metrics.json').write_text(json.dumps(allmetrics,indent=2)+'\n');(out/'camera.json').write_text(json.dumps(g.CAMERA,indent=2)+'\n')
    (out/'_candidate.png').unlink(missing_ok=True)
    print(json.dumps({'params':fitted,'metrics':allmetrics,'completed':time.time()},indent=2),flush=True)
if __name__=='__main__':main()
