#!/usr/bin/env python3
"""Generic triangle rasterizer. No fitting, target state, or task answers.
Usage: python render_mesh.py --mesh final.obj --camera camera.json --out renders
Source coordinates centimetres, Y up. Orthographic cameras never auto-fit.
"""
import argparse,json
from pathlib import Path
import cv2
import numpy as np

def obj(path):
    v=[];f=[]
    for line in Path(path).read_text().splitlines():
        t=line.split()
        if not t:continue
        if t[0]=='v':v.append(list(map(float,t[1:4])))
        if t[0]=='f':
            ids=[int(x.split('/')[0])-1 for x in t[1:]]
            for i in range(1,len(ids)-1):f.append([ids[0],ids[i],ids[i+1]])
    v=np.asarray(v,float);f=np.asarray(f,int)
    if v.ndim!=2 or v.shape[1]!=3 or f.ndim!=2 or f.shape[1]!=3 or not np.isfinite(v).all() or f.min()<0 or f.max()>=len(v):raise ValueError('Invalid mesh')
    return v,f

def raster(v,f,camera,view,joints=None):
    c=camera['views'][view];w,h=camera['width'],camera['height'];s=c['px_per_cm'];cx,cy=c['center_cm']
    axis=c['axis'];horizontal=v[:,2] if axis=='side' else v[:,0]*(-1 if axis=='back' else 1)
    depth=v[:,0] if axis=='side' else v[:,2]*(-1 if axis=='back' else 1)
    xy=np.column_stack(((horizontal-cx)*s+w/2,h/2-(v[:,1]-cy)*s))
    mask=np.zeros((h,w),np.uint8);z=np.full((h,w),-np.inf);shade=np.zeros((h,w),float)
    for face in f:
        p=xy[face];cv2.fillConvexPoly(mask,np.rint(p).astype(np.int32),255)
        x0,y0=np.maximum(np.floor(p.min(0)).astype(int),0);x1,y1=np.minimum(np.ceil(p.max(0)).astype(int),[w-1,h-1])
        if x1<x0 or y1<y0:continue
        a,b,c=p;den=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
        if abs(den)<1e-10:continue
        yy,xx=np.mgrid[y0:y1+1,x0:x1+1];u=((b[1]-c[1])*(xx-c[0])+(c[0]-b[0])*(yy-c[1]))/den;vv=((c[1]-a[1])*(xx-c[0])+(a[0]-c[0])*(yy-c[1]))/den;ww=1-u-vv
        d=u*depth[face[0]]+vv*depth[face[1]]+ww*depth[face[2]];region=z[y0:y1+1,x0:x1+1];hit=(u>=-1e-7)&(vv>=-1e-7)&(ww>=-1e-7)&(d>region)
        region[hit]=d[hit];n=np.cross(v[face[1]]-v[face[0]],v[face[2]]-v[face[0]]);n/=max(np.linalg.norm(n),1e-12);light=.42+.58*abs(float(n@np.array([.3,.4,.866])))
        shade[y0:y1+1,x0:x1+1][hit]=light
    visible=np.isfinite(z);img=np.full((h,w,3),242,np.uint8);img[mask>0]=[120,117,110];img[visible]=np.clip(shade[visible,None]*np.array([213,204,186]),0,255).astype(np.uint8)
    lo,hi=camera['depth_range_cm'];dep=np.zeros((h,w),np.uint8);dep[visible]=np.clip(1+253*(z[visible]-lo)/(hi-lo),1,254).astype(np.uint8)
    if view=='pose' and joints:
        points={}
        for joint in joints['joints']:
            a=np.asarray(joint['position'],float);xx=a[2] if axis=='side' else a[0]*(-1 if axis=='back' else 1)
            points[joint['name']]=(int(round((xx-cx)*s+w/2)),int(round(h/2-(a[1]-cy)*s)))
        selected={'root','pelvis','spine01','spine02','spine03','neck01','neck02','neck03','head','clavicle.L','clavicle.R','upperarm01.L','upperarm01.R','lowerarm01.L','lowerarm01.R','wrist.L','wrist.R','upperleg01.L','upperleg01.R','lowerleg01.L','lowerleg01.R','foot.L','foot.R'}
        for joint in joints['joints']:
            name=joint['name'];parent=joint.get('parent')
            if name in selected and parent in points:
                cv2.line(img,points[name],points[parent],(30,80,245),2,cv2.LINE_8)
                cv2.circle(img,points[name],3,(30,235,255),-1,cv2.LINE_8)
    return mask,img,dep,z

def render(mesh,camera,out,joints=None):
    v,f=obj(mesh);out=Path(out);out.mkdir(parents=True,exist_ok=True)
    for view in camera['views']:
        m,im,d,z=raster(v,f,camera,view,joints);cv2.imwrite(str(out/(view+'.png')),d if view=='depth' else im);cv2.imwrite(str(out/(view+'-mask.png')),m)
        if view=='depth':
            np.save(out/'rawdepth.npy',z.astype(np.float32));np.save(out/'depth.npy',z.astype(np.float32));cv2.imwrite(str(out/'depth-valid.png'),np.isfinite(z).astype(np.uint8)*255)
        if view=='pose' and joints:
            c=camera['views'][view];w,h=camera['width'],camera['height'];scale=c['px_per_cm'];cx,cy=c['center_cm'];axis=c['axis'];rows=[];edges=[];names={j['name'] for j in joints['joints']}
            for j in joints['joints']:
                p=j['position'];horizontal=p[2] if axis=='side' else p[0]*(-1 if axis=='back' else 1);u=(horizontal-cx)*scale+w/2;vv=h/2-(p[1]-cy)*scale
                rows.append({'name':j['name'],'world_cm':p,'pixel':[u,vv],'visible':bool(0<=u<w and 0<=vv<h)})
                if j.get('parent') in names:edges.append([j['parent'],j['name']])
            (out/'pose-joints.json').write_text(json.dumps({'joints':rows,'edges':edges,'visible_definition':'inside canvas; not an occlusion classification'},indent=2)+'\n')
    return v,f
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--mesh',required=True);p.add_argument('--camera',required=True);p.add_argument('--out',required=True);p.add_argument('--joints');a=p.parse_args();render(a.mesh,json.loads(Path(a.camera).read_text()),a.out,json.loads(Path(a.joints).read_text()) if a.joints else None)
