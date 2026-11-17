#!/usr/bin/env python3
"""Independent vectorized ray/triangle and world-to-pixel checks.

This imports neither the supplied rasterizer nor its output verifier.
"""
import argparse
import json
from pathlib import Path
import cv2
import numpy as np


def read_obj(path):
    vertices, faces = [], []
    for line in path.read_text().splitlines():
        fields=line.split()
        if not fields: continue
        if fields[0]=='v': vertices.append([float(x) for x in fields[1:4]])
        if fields[0]=='f':
            assert len(fields)==4, 'Expected source triangles'
            faces.append([int(x.split('/')[0])-1 for x in fields[1:]])
    return np.asarray(vertices),np.asarray(faces)


def coordinates(vertices, camera, view):
    spec=camera['views'][view]
    scale=spec['px_per_cm'];cx,cy=spec['center_cm']
    if spec['axis']=='side': horizontal,depth=vertices[:,2],vertices[:,0]
    elif spec['axis']=='back': horizontal,depth=-vertices[:,0],-vertices[:,2]
    elif spec['axis']=='front': horizontal,depth=vertices[:,0],vertices[:,2]
    else: raise ValueError('Unknown camera axis')
    return np.column_stack(((horizontal-cx)*scale+camera['width']/2,
                            (cy-vertices[:,1])*scale+camera['height']/2)),depth


def ray_hits(vertices, faces, camera, view, pixels):
    xy,depth=coordinates(vertices,camera,view)
    triangles=xy[faces]
    a,b,c=triangles[:,0],triangles[:,1],triangles[:,2]
    cross=lambda u,v:u[:,0]*v[:,1]-u[:,1]*v[:,0]
    ab,ac=b-a,c-a
    determinant=cross(ab,ac)
    nondegenerate=np.abs(determinant)>1e-10
    hits=[]
    for pixel in pixels:
        ap=np.asarray(pixel)-a
        with np.errstate(divide='ignore',invalid='ignore'):
            weight_b=cross(ap,ac)/determinant
            weight_c=cross(ab,ap)/determinant
            weight_a=1-weight_b-weight_c
        inside=nondegenerate&(weight_a>=-1e-7)&(weight_b>=-1e-7)&(weight_c>=-1e-7)
        values=(np.column_stack((weight_a,weight_b,weight_c))*depth[faces]).sum(axis=1)
        hits.append(float(np.max(values[inside])) if inside.any() else None)
    return hits


def audit(output):
    camera=json.loads((output/'camera.json').read_text())
    vertices,faces=read_obj(output/'final.obj')
    raw=np.load(output/'renders/depth.npy',allow_pickle=False)
    valid=cv2.imread(str(output/'renders/depth-valid.png'),cv2.IMREAD_GRAYSCALE)
    assert valid is not None and raw.shape==valid.shape==(camera['height'],camera['width'])
    assert raw.dtype.kind=='f' and set(np.unique(valid))<={0,255}
    assert np.array_equal(np.isfinite(raw),valid>0), 'Raw depth finite support differs from valid mask'
    yy,xx=np.where(valid>0)
    assert len(xx)>100, 'Empty/near-empty depth'
    indices=np.linspace(0,len(xx)-1,40,dtype=int)
    pixels=list(zip(xx[indices],yy[indices]))
    truth=ray_hits(vertices,faces,camera,'depth',pixels)
    assert all(v is not None for v in truth), 'Valid pixel has no triangle intersection'
    difference=float(np.max(np.abs(np.asarray(truth)-raw[yy[indices],xx[indices]])))
    assert difference<.001, 'Raw depth differs from independent triangle hits'
    joints=json.loads((output/'renders/pose-joints.json').read_text())
    rows=joints['joints'];assert len(rows)>=15
    actual=np.asarray([row['pixel'] for row in rows],float)
    world=np.asarray([row['world_cm'] for row in rows],float)
    projected,_=coordinates(world,camera,'pose')
    joint_error=float(np.max(np.abs(actual-projected)))
    assert joint_error<.001, 'Joint pixels do not follow saved camera'
    assert len({r['name'] for r in rows})==len(rows)
    assert all(type(r['visible']) is bool for r in rows)
    names={r['name'] for r in rows}
    assert len(joints['edges'])>=10 and all(a in names and b in names for a,b in joints['edges'])
    return dict(verdict='PASS',ray_count=len(pixels),max_depth_error_cm=difference,
                joint_count=len(rows),max_joint_projection_error_px=joint_error,
                independence='Own OBJ parser, vectorized cross-product intersections and camera projection; no renderer import',
                limits='Checks model-space geometric consistency, not detector accuracy or photographed people')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    try: result=audit(args.output)
    except Exception as exc: result=dict(verdict='FAIL',error=type(exc).__name__+': '+str(exc))
    (args.output/'independent-projection.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))
    raise SystemExit(0 if result['verdict']=='PASS' else 2)
