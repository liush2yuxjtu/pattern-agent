"""Read transparent one-file assets without importing either generator."""
import json
from pathlib import Path
import numpy as np


def read_obj(path):
    vertices=[];polygons=[];metadata=None
    for line in Path(path).read_text().splitlines():
        if line.startswith('# ASSET_CONTRACT '):metadata=json.loads(line[len('# ASSET_CONTRACT '):])
        elif line.startswith('v '):vertices.append([float(x) for x in line.split()[1:4]])
        elif line.startswith('f '):polygons.append([int(x.split('/')[0])-1 for x in line.split()[1:]])
    if metadata is None:raise ValueError('Asset contract missing')
    triangles=[(p[0],p[i],p[i+1]) for p in polygons for i in range(1,len(p)-1)]
    return np.asarray(vertices,dtype=float),np.asarray(triangles,dtype=int),metadata,polygons


def pair(model,cloth):
    bv,bt,bm,_=read_obj(model);cv,ct,topology,_=read_obj(cloth)
    arrays={'body_vertices':bv,'body_triangles':bt,'cloth_vertices':cv,'cloth_triangles':ct,
            'path_L':np.asarray(bm['path_L'],dtype=float),'path_R':np.asarray(bm['path_R'],dtype=float)}
    topology['rest_vertices']=cv.tolist()
    return arrays,topology
