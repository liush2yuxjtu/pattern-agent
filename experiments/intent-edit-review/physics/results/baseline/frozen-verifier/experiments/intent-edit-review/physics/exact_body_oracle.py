"""Exact f64 minimum over all body faces; no proximity normal tie-breaking."""
import numpy as np
import trimesh

def closest_body(mesh,points):
    points=np.asarray(points,dtype=float);q=[];d=[];f=[]
    for start in range(0,len(points),16):
        a,b,c=trimesh.proximity.closest_point_naive(mesh,points[start:start+16])
        q.append(a);d.append(b);f.append(c)
    return np.vstack(q),np.concatenate(d),np.concatenate(f)
