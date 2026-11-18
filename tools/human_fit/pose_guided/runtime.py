#!/usr/bin/env python3
"""Actual asset/source calibration, generic LBS/projection/rendering. No task solver.

One state supplies every view. No reference images or target parameters are read.
Euler rotations match Human Studio's restQuaternion * localXYZ convention.
"""
from pathlib import Path
import copy, hashlib, importlib.util, json, subprocess
import cv2
import numpy as np
from scipy.spatial.transform import Rotation

HERE=Path(__file__).resolve().parent
ROOT=next(p for p in HERE.parents if (p/'web/human-studio/assets/human.json').exists())

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def full_pose(data,pose):
    names={b['name'] for b in data['bones']}
    if set(pose)-names:raise ValueError('Unknown bones')
    result={name:[0.,0.,0.] for name in names}
    for name,values in pose.items():
        a=np.asarray(values,float)
        if a.shape!=(3,) or not np.isfinite(a).all() or (abs(a)>180).any():raise ValueError('Invalid angles')
        result[name]=list(map(float,a))
    return result

class Runtime:
    def __init__(self):
        self.asset=ROOT/'web/human-studio/assets/human.json'
        self.data=json.loads(self.asset.read_text());d=self.data
        self.base=np.asarray(d['vertices'],float).reshape(-1,3)
        self.ids=np.asarray(d['bodyVertexIds'],int);self.faces=np.asarray(d['indices'],int).reshape(-1,3)
        self.compact={int(v):i for i,v in enumerate(self.ids)}
        self.body_faces=np.asarray([[self.compact[int(v)] for v in row] for row in self.faces])
        self.bones=d['bones'];self.names=[b['name'] for b in self.bones];self.index={n:i for i,n in enumerate(self.names)}
        self.parent=[self.index.get(b['parent'],-1) for b in self.bones]
        self.order=[]
        def visit(i):
            if i in self.order:return
            if self.parent[i]>=0:visit(self.parent[i])
            self.order.append(i)
        for i in range(len(self.bones)):visit(i)
        self.skin=np.asarray(d['skinIndices']).reshape(-1,4)
        self.weight=np.asarray(d['skinWeights'],float).reshape(-1,4)
        self.weight/=self.weight.sum(1,keepdims=True)
        self.shape_cache={}
        self.worker=subprocess.Popen(['node',str(HERE/'calibrate-worker.mjs'),str(ROOT)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True,bufsize=1)

    def close(self):
        if self.worker.poll() is None:self.worker.stdin.close();self.worker.terminate();self.worker.wait(timeout=5)

    def shape(self,dimensions):
        key=json.dumps(dimensions,sort_keys=True)
        if key in self.shape_cache:return self.shape_cache[key]
        self.worker.stdin.write(json.dumps({'dimensions':dimensions})+'\n');self.worker.stdin.flush()
        fit=json.loads(self.worker.stdout.readline())
        if 'error' in fit:raise ValueError(fit['error'])
        v=self.base.copy()
        for c,w in zip(self.data['controls'],fit['weights']):
            rows=np.asarray(c['incr' if w>=0 else 'decr'],float)
            if len(rows):v[rows[:,0].astype(int)]+=rows[:,1:]*abs(w)
        v[:,1]-=v[self.ids,1].min()
        heads=np.array([v[self.data['joints'][b['head']]].mean(0) for b in self.bones])
        tails=np.array([v[self.data['joints'][b['tail']]].mean(0) for b in self.bones])
        frames=[]
        for head,tail in zip(heads,tails):
            y=tail-head;y/=max(np.linalg.norm(y),1e-12)
            if np.linalg.norm(y)<.5:y=np.array([0.,1.,0.])
            x=np.cross(y,[0,0,1])
            if np.linalg.norm(x)<1e-8:x=np.cross(y,[0,1,0])
            x/=np.linalg.norm(x);z=np.cross(x,y);frames.append(np.column_stack([x,y,z]))
        frames=np.array(frames)
        rest_rot=np.array([frames[p].T@frames[i] if p>=0 else frames[i] for i,p in enumerate(self.parent)])
        translations=np.array([frames[p].T@(heads[i]-heads[p]) if p>=0 else heads[i] for i,p in enumerate(self.parent)])
        result=dict(fit=fit,rest=v,heads=heads,frames=frames,rest_rot=rest_rot,translations=translations)
        self.shape_cache[key]=result
        return result

    def evaluate(self,state,skin=True):
        shape=self.shape(state['dimensions']);pose=full_pose(self.data,state.get('poseDegrees',{}))
        angles=np.array([pose[n] for n in self.names]);rot=shape['rest_rot']@Rotation.from_euler('XYZ',angles,degrees=True).as_matrix()
        g=np.zeros_like(rot);world=np.zeros_like(shape['heads'])
        for i in self.order:
            p=self.parent[i];g[i]=g[p]@rot[i] if p>=0 else rot[i]
            world[i]=world[p]+g[p]@shape['translations'][i] if p>=0 else shape['translations'][i]
        result=dict(shape=shape,joints=world,pose=pose)
        if skin:
            matrix=g@shape['frames'].transpose(0,2,1)
            offset=world-np.einsum('nij,nj->ni',matrix,shape['heads'])
            posed=np.zeros_like(shape['rest'])
            for k in range(4):
                posed+=self.weight[:,k,None]*(np.einsum('nij,nj->ni',matrix[self.skin[:,k]],shape['rest'])+offset[self.skin[:,k]])
            floor=posed[self.ids,1].min();posed[:,1]-=floor;world[:,1]-=floor
            result['posed']=posed;result['floor_cm']=float(floor)
        # For the fixed standing lower body in this fixture, floor is unchanged.
        return result

    def canonical_state(self,state):
        result=self.evaluate(state);fit=result['shape']['fit']
        return dict(version='makehuman-cm-rig-v1',asset=sha(self.asset),units='cm',dimensions=fit['dimensions'],morphWeights=fit['weights'],measuredNeutral=fit['measurements'],maximumTargetErrorCm=fit['maxError'],poseDegrees=result['pose'],measurementDefinition=self.data['measurementDefinition'],limitations=['Controlled synthetic anatomical fixture; not measurements of a real photographed person.'])

    @staticmethod
    def project(points,camera,view):
        p=np.asarray(points,float);c=camera['views'][view];axis=c['axis'];s=c['px_per_cm'];cx,cy=c['center_cm']
        horizontal=p[:,2] if axis=='side' else p[:,0]*(-1 if axis=='back' else 1)
        return np.column_stack([(horizontal-cx)*s+camera['width']/2,camera['height']/2-(p[:,1]-cy)*s])

    def mask(self,posed,camera,view):
        xy=self.project(posed,camera,view);out=np.zeros((camera['height'],camera['width']),np.uint8)
        for face in self.faces:cv2.fillConvexPoly(out,np.rint(xy[face]).astype(np.int32),255)
        return out

    def write_obj(self,path,vertices):
        p=Path(path);v=np.asarray(vertices)[self.ids];lines=['# Actual MakeHuman surface; centimetres; Y up']
        lines+=['v '+' '.join(format(float(x),'.11g') for x in row) for row in v]
        lines+=['f '+' '.join(str(int(i)+1) for i in row) for row in self.body_faces]
        p.write_text('\n'.join(lines)+'\n')

    def save(self,state,camera,out,views=None):
        out=Path(out);out.mkdir(parents=True,exist_ok=True);state=self.canonical_state(state);result=self.evaluate(state)
        (out/'state.json').write_text(json.dumps(state,indent=2)+'\n');(out/'camera.json').write_text(json.dumps(camera,indent=2)+'\n')
        self.write_obj(out/'neutral.obj',result['shape']['rest']);self.write_obj(out/'posed.obj',result['posed'])
        joints={'joints':[dict(name=n,parent=self.bones[i]['parent'],position=result['joints'][i].tolist()) for i,n in enumerate(self.names)]}
        (out/'joints.json').write_text(json.dumps(joints,indent=2)+'\n')
        spec=importlib.util.spec_from_file_location('generic_raster',HERE/'render_mesh.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        posehash=hashlib.sha256(json.dumps(state['poseDegrees'],sort_keys=True).encode()).hexdigest();meshhash=sha(out/'posed.obj');records={}
        for view in views or camera['views']:
            mask,img,dep,z=module.raster(result['posed'],self.faces,camera,view,joints)
            cv2.imwrite(str(out/(view+'.png')),dep if view=='depth' else img);cv2.imwrite(str(out/(view+'-mask.png')),mask)
            if view=='depth':np.save(out/'rawdepth.npy',z.astype('float32'));cv2.imwrite(str(out/'depth-valid.png'),np.isfinite(z).astype('uint8')*255)
            records[view]=dict(state_sha256=sha(out/'state.json'),pose_sha256=posehash,posed_mesh_sha256=meshhash,projected_joints=self.project(result['joints'],camera,view).tolist())
        (out/'view-provenance.json').write_text(json.dumps(records,indent=2)+'\n')
        return state
