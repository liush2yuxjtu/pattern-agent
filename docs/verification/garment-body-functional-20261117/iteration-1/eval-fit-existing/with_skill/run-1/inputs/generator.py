#!/usr/bin/env python3
"""Synthetic control geometry. All lengths in prior-scaled centimetres; no anatomy claims."""
import argparse, json, math
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
CAMERA={'projection':'orthographic','width':384,'height':640,'horizontal_extent_cm':[-50,50],'vertical_extent_cm':[-4,180],'near_axis':'front +z; side +x; back -z','scale_assumption':'height prior 170 cm; synthetic controls'}
DEFAULT={'height':170.0,'chest':78.0,'waist':88.0,'hip':84.0,'depth_ratio':0.70}
def ellipse_radii(c, ratio):
    # Ramanujan ellipse perimeter, linear in radius
    unit=math.pi*(3*(1+ratio)-math.sqrt((3+ratio)*(1+3*ratio)))
    return c/unit,c/unit*ratio

def mesh(p):
    v=[]; f=[]; groups=[]
    def loft(name, rows, cx=0, cz=0):
        start=len(v); n=48
        for y,rx,rz in rows:
            for t in np.arange(n)*2*np.pi/n:
                v.append([cx+rx*np.cos(t),y,cz+rz*np.sin(t)])
        for j in range(len(rows)-1):
            for k in range(n):
                a=start+j*n+k;b=start+j*n+(k+1)%n;c=b+n;d=a+n
                f.extend([[a,b,c],[a,c,d]]);groups.extend([name,name])
        for row,reverse in [(0,True),(len(rows)-1,False)]:
            center=len(v);v.append([cx,rows[row][0],cz])
            for k in range(n):
                a=start+row*n+k;b=start+row*n+(k+1)%n
                f.append([center,b,a] if reverse else [center,a,b]);groups.append(name)
    ratio=p['depth_ratio']; cr=ellipse_radii(p['chest'],ratio);wr=ellipse_radii(p['waist'],ratio);hr=ellipse_radii(p['hip'],ratio)
    loft('torso',[(76,hr[0]*.8,hr[1]*.8),(88,*hr),(98,hr[0]*.95,hr[1]*.95),(109,*wr),(119,cr[0]*.94,cr[1]*.94),(128,*cr),(138,cr[0]*1.02,cr[1]*.85),(145,9,6),(149,5,4)])
    loft('head',[(148,4,4),(151,7,7),(159,8,8),(166,6,6),(170,.3,.3)])
    for sign in [-1,1]:
        loft('leg',[(0,4,6),(8,4,4),(39,5,5),(75,7,7),(85,7,7)],sign*8)
        loft('arm',[(80,3,3),(105,4,4),(128,5,5),(141,4,4)],sign*27)
    a=np.asarray(v);a*=p['height']/170
    return a,np.asarray(f),groups

def export_obj(path,v,f,groups):
    with open(path,'w') as o:
        o.write('# SYNTHETIC CONTROL; assumed centimetres from height prior\n')
        for xyz in v:o.write('v '+' '.join(f'{x:.6f}' for x in xyz)+'\n')
        prev=None
        for face,g in zip(f,groups):
            if g!=prev:o.write('g '+g+'\n');prev=g
            o.write('f '+' '.join(str(int(x)+1) for x in face)+'\n')

def render(v,f,out,view,mask=False):
    axis={'front':0,'side':2,'back':0}[view]
    xx=v[:,axis]*(-1 if view=='back' else 1)
    xy=np.column_stack(((xx+50)*384/100,(180-v[:,1])*640/184))
    img=Image.new('RGB',(384,640),'black' if mask else '#eef1f4');d=ImageDraw.Draw(img)
    dep=v[:,2] if view!='side' else v[:,0]
    for idx in np.argsort(dep[f].mean(axis=1)):
        face=f[idx];shade=160+int(50*(idx%7)/6)
        d.polygon([tuple(x) for x in xy[face]],fill='white' if mask else (shade,shade,shade))
    if not mask:d.text((10,10),'SYNTHETIC CONTROL / '+view.upper(),fill='#222222')
    img.save(out)

def run(params,out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    v,f,g=mesh(params);export_obj(out/'body.obj',v,f,g)
    for view in ['front','side','back']:
        render(v,f,out/f'{view}.png',view)
        render(v,f,out/f'{view}-mask.png',view,True)
    (out/'camera.json').write_text(json.dumps(CAMERA,indent=2)+'\n')
    (out/'params.json').write_text(json.dumps(params,indent=2)+'\n')
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--params',type=Path);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    run(json.loads(a.params.read_text()) if a.params else DEFAULT,a.out)
