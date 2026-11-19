"""Independent NumPy audit of the actual GPU read-back snapshot.
No imports from the production JS math, seam, collider or solver.
"""
import json, pathlib, hashlib, argparse, numpy as np
root=pathlib.Path(__file__).resolve().parents[1]; folder=root/'evidence'
parser=argparse.ArgumentParser();parser.add_argument('--snapshot',default='gpu-snapshot.json');parser.add_argument('--runtime-key',default='settled');parser.add_argument('--output',default='independent-report.json');args=parser.parse_args()
snapshot=json.loads((folder/args.snapshot).read_text());project=snapshot['project'];doc=project['document'];body=project['body']
p=np.asarray(snapshot['positions'],dtype=np.float64).reshape(-1,3);uv=np.asarray(doc['mesh']['restUV'])/1000;t=np.asarray(doc['mesh']['triangles']).reshape(-1,3)
bp=np.asarray(body['positions']);bp=bp.reshape(-1,3);bt=np.asarray(body['triangles']).reshape(-1,3)
dx=np.stack([uv[t[:,1]]-uv[t[:,0]],uv[t[:,2]]-uv[t[:,0]]],axis=-1)
ds=np.stack([p[t[:,1]]-p[t[:,0]],p[t[:,2]]-p[t[:,0]]],axis=-1)
F=ds@np.linalg.inv(dx);singular=np.linalg.svd(F,compute_uv=False);strain=np.max(np.abs(singular-1),axis=1)

def segment_hits(a,b,tri,eps=1e-9):
    """Vectorized strict transverse segment/triangle hits (no coplanar claim)."""
    tri=np.asarray(tri);direction=np.asarray(b)-np.asarray(a);e1=tri[...,1,:]-tri[...,0,:];e2=tri[...,2,:]-tri[...,0,:]
    h=np.cross(direction,e2);det=np.sum(e1*h,axis=-1);valid=np.abs(det)>1e-13
    inv=np.divide(1,det,out=np.zeros_like(det),where=valid);s=np.asarray(a)-tri[...,0,:];u=np.sum(s*h,axis=-1)*inv;q=np.cross(s,e1);v=np.sum(direction*q,axis=-1)*inv;at=np.sum(e2*q,axis=-1)*inv
    return valid&(u>eps)&(v>eps)&(u+v<1-eps)&(at>eps)&(at<1-eps)

def face_crossings(vertices,faces,other_vertices,other_faces,self_test=False,roots=None):
    tri=vertices[faces];other=other_vertices[other_faces];lo=other.min(axis=1);hi=other.max(axis=1);pairs=[];candidates=0
    for i,a in enumerate(tri):
        ids=np.flatnonzero(np.all(hi>=a.min(axis=0)-1e-10,axis=1)&np.all(lo<=a.max(axis=0)+1e-10,axis=1))
        if self_test:
            ids=ids[ids>i]
            if len(ids):
                # Only true vertex adjacency (including welded seam identity).
                x=roots[faces[i]];ys=roots[other_faces[ids]];ids=ids[~np.any(x[None,:,None]==ys[:,None,:],axis=(1,2))]
        candidates+=len(ids)
        if not len(ids):continue
        b=other[ids];hits=np.zeros(len(ids),dtype=bool)
        for e in range(3):
            hits|=segment_hits(a[e],a[(e+1)%3],b)
            hits|=segment_hits(b[:,e],b[:,(e+1)%3],a)
        for j in ids[hits]:pairs.append([int(i),int(j)])
    return {'strictCrossingPairs':len(pairs),'pairs':pairs[:80],'broadPhaseCandidates':candidates,'method':'All AABB-overlapping face pairs, strict segment/triangle tests in both directions; coplanar overlap/CCD excluded.'}

def ray_inside(points,verts,faces):
    tri=verts[faces];direction=np.array([1,.231764,.417398]);e1=tri[:,1]-tri[:,0];e2=tri[:,2]-tri[:,0];h=np.cross(direction,e2);det=np.sum(e1*h,axis=1);valid=np.abs(det)>1e-13;inv=np.divide(1,det,out=np.zeros_like(det),where=valid);inside=[]
    for point in points:
        s=point-tri[:,0];u=np.sum(s*h,axis=1)*inv;q=np.cross(s,e1);v=q@direction*inv;at=np.sum(e2*q,axis=1)*inv
        times=np.sort(at[valid&(u>=-1e-10)&(v>=-1e-10)&(u+v<=1+1e-10)&(at>1e-9)])
        count=0 if not len(times) else 1+int(np.sum(np.diff(times)>1e-8));inside.append(count%2==1)
    return np.array(inside)

# Controls for the independent tests, including a genuinely transverse crossing.
control_tri=np.array([[[0.,0.,0.],[1.,0.,0.],[0.,1.,0.]]]);assert segment_hits([.2,.2,-1],[.2,.2,1],control_tri)[0];assert not segment_hits([2,2,-1],[2,2,1],control_tri)[0]
assert not segment_hits([.2,.2,1],[.3,.2,1],control_tri)[0]
collapsed=np.linalg.svd(np.array([[1,0],[0,1e-9],[0,0]]),compute_uv=False);assert abs(collapsed[-1]-1e-9)<1e-20

parent=np.arange(len(p))
def find(i):
    while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
    return i
gaps=[]
for seam in doc['seams']:
    for a,b in seam['pairs']:gaps.append(np.linalg.norm(p[a]-p[b])*1000);parent[find(b)]=find(a)
roots=np.array([find(i) for i in range(len(p))])
print('Auditing body crossings...',flush=True);body_cross=face_crossings(p,t,bp,bt)
print('Auditing self crossings...',flush=True);self_cross=face_crossings(p,t,p,t,True,roots)
print('Auditing independent inside parity...',flush=True);inside=ray_inside(p,bp,bt)
runtime=json.loads((folder/'browser-report.json').read_text())[args.runtime_key]['metrics'];p95=float(np.quantile(strain,.95));maximum=float(strain.max())
report={
 'snapshotSha256':hashlib.sha256((folder/args.snapshot).read_bytes()).hexdigest(),
 'source':'Real browser hybrid GPU predictor + CPU XPBD corrected snapshot; independent NumPy SVD, ray parity and triangle intersections.',
 'principalStrain':{'p95':p95,'max':maximum,'matchesRuntime':abs(p95-runtime['strainP95'])<1e-8 and abs(maximum-runtime['strainMax'])<1e-8,'p95Limit':.1,'maxLimit':.25,'status':'PASS' if p95<=.1 and maximum<=.25 else 'FAIL'},
 'seams':{'maxGapMm':float(max(gaps)),'status':'PASS' if max(gaps)<=2 else 'FAIL'},
 'insideBodyVertices':int(inside.sum()),'bodyFaceCrossings':body_cross,'clothSelfCrossings':self_cross,
 'sampledBodyGeometryStatus':'PASS' if not inside.any() and not body_cross['strictCrossingPairs'] else 'FAIL',
 'selfIntersectionStatus':'PASS' if self_cross['strictCrossingPairs']==0 else 'FAIL',
 'controls':'Transverse hit, miss, outside-plane miss and extreme-collapse SVD passed.',
 'physicalFit':'NOT_RUN','continuousCollision':'NOT_RUN','coplanarOverlap':'NOT_RUN','materialCalibration':'NOT_RUN',
 'limits':'One saved settled frame. Does not certify all simulated steps, self-contact prevention, physical fabric stress or human fit.'}
(folder/args.output).write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k not in ['bodyFaceCrossings','clothSelfCrossings']},indent=2));print('body crossings',body_cross['strictCrossingPairs'],'self',self_cross['strictCrossingPairs'])
