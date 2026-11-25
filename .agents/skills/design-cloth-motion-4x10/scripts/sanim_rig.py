"""Style3D V4 forward kinematics used for motion retargeting."""
from math import cos, sin
from zipfile import ZipFile
import json

def mv(m,v):
    return tuple(sum(a*b for a,b in zip(row,v)) for row in m)

def mm(a,b):
    return tuple(tuple(sum(x*y for x,y in zip(row,col)) for col in zip(*b)) for row in a)

def transpose(m):
    return tuple(zip(*m))

def axes(angles):
    x, y, z = angles
    rx = ((1,0,0),(0,cos(x),-sin(x)),(0,sin(x),cos(x)))
    ry = ((cos(y),0,sin(y)),(0,1,0),(-sin(y),0,cos(y)))
    rz = ((cos(z),-sin(z),0),(sin(z),cos(z),0),(0,0,1))
    return mm(rz,mm(ry,rx))


def rig(path):
    with ZipFile(path) as archive:
        data = json.loads(archive.read('avatar.json'))
    by_id = {obj['_id']:obj for group in data['_objectsArrays'] for obj in group}
    avatar = next(obj for obj in by_id.values() if 'skeleton' in obj and 'avatarSizes' in obj)
    return [by_id[i] for i in by_id[avatar['skeleton']]['bones']]

def fk(bones, frames, inv_post=True):
    parents = {child:i for i,bone in enumerate(bones) for child in bone['sons']}
    points, transforms = [], []
    for i,(bone,frame) in enumerate(zip(bones,frames)):
        pivot = bone['pivot']
        post = axes(pivot['postRotation'])
        if inv_post:
            post = transpose(post)
        rot = mm(mm(axes(pivot['preRotation']),axes(frame['rotate'])),post)
        pos = tuple(frame['translate'])
        if i in parents:
            parent = parents[i]
            pos = tuple(a+b for a,b in zip(points[parent],mv(transforms[parent],pos)))
            rot = mm(transforms[parent],rot)
        points.append(pos)
        transforms.append(rot)
    return points,transforms
