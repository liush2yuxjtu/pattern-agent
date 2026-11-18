from pathlib import Path
from collections import Counter,defaultdict
import json, hashlib, time
import numpy as np


class RayGrid:
 def __init__(self,vertices,faces,direction,cell=.018):
  n=np.array(direction,float);n/=np.linalg.norm(n);helper=np.array([0.,0.,1.])if abs(n[2])<.9 else np.array([0.,1.,0.]);u=np.cross(n,helper);u/=np.linalg.norm(u);v=np.cross(n,u);self.basis=np.stack([u,v,n],axis=1);self.tri=vertices[faces]@self.basis;self.cell=cell;self.origin=self.tri[:,:,:2].min((0,1))-.0001;self.grid=defaultdict(list)
  boxes=np.stack([self.tri[:,:,:2].min(1),self.tri[:,:,:2].max(1)],axis=1)
  ij=np.floor((boxes-self.origin)/cell).astype(int)
  for i,((a,b),(c,d))in enumerate(ij):
   for x in range(a,c+1):
    for y in range(b,d+1):self.grid[x,y].append(i)
  self.grid={k:np.array(v,dtype=int)for k,v in self.grid.items()}
 def contains(self,points):
  result=np.zeros(len(points),bool);boundary=np.zeros(len(points),bool);rot=points@self.basis
  for j,p in enumerate(rot):
   cell=tuple(np.floor((p[:2]-self.origin)/self.cell).astype(int));ids=self.grid.get(cell)
   if ids is None:continue
   tri=self.tri[ids];a=tri[:,0];b=tri[:,1]-a;c=tri[:,2]-a;q=p-a;det=b[:,0]*c[:,1]-b[:,1]*c[:,0];good=np.abs(det)>1e-16
   u=np.divide(q[:,0]*c[:,1]-q[:,1]*c[:,0],det,out=np.zeros(len(det)),where=good);v=np.divide(b[:,0]*q[:,1]-b[:,1]*q[:,0],det,out=np.zeros(len(det)),where=good)
   hit=good&(u>=-1e-10)&(v>=-1e-10)&(u+v<=1+1e-10);z=a[:,2]+u*b[:,2]+v*c[:,2];boundary[j]=np.any(hit&(np.abs(z-p[2])<1e-7))
   zs=np.sort(z[hit&(z>p[2]+1e-7)]);count=0 if not len(zs)else 1+np.count_nonzero(np.diff(zs)>1e-7);result[j]=count%2==1
  return result,boundary

def nearest_surface(p,tri):
 a=tri[:,0];ab=tri[:,1]-a;ac=tri[:,2]-a;ap=p-a;d00=np.einsum('ij,ij->i',ab,ab);d01=np.einsum('ij,ij->i',ab,ac);d11=np.einsum('ij,ij->i',ac,ac);d20=np.einsum('ij,ij->i',ap,ab);d21=np.einsum('ij,ij->i',ap,ac);den=d00*d11-d01*d01
 u=np.divide(d11*d20-d01*d21,den,out=np.zeros(len(den)),where=np.abs(den)>1e-20);v=np.divide(d00*d21-d01*d20,den,out=np.zeros(len(den)),where=np.abs(den)>1e-20)
 closest=a+u[:,None]*ab+v[:,None]*ac;dist=np.sum((closest-p)**2,1);dist[(u<0)|(v<0)|(u+v>1)|(np.abs(den)<=1e-20)]=np.inf
 for i,j in [(0,1),(1,2),(2,0)]:
  start=tri[:,i];vec=tri[:,j]-start;length2=np.sum(vec*vec,1);t=np.clip(np.divide(np.sum((p-start)*vec,1),length2,out=np.zeros(len(length2)),where=length2>1e-20),0,1);q=start+t[:,None]*vec;dd=np.sum((q-p)**2,1);improve=dd<dist;closest[improve]=q[improve];dist[improve]=dd[improve]
 idx=int(np.argmin(dist));return float(np.sqrt(dist[idx])),closest[idx].tolist(),idx

def line_gaps(a,b):
 a=np.array(a);b=np.array(b)
 def maximum(p,poly):
  start=poly[:-1];vec=poly[1:]-start;length=np.sum(vec*vec,1);values=[]
  for x in p:
   t=np.clip(np.divide(np.sum((x-start)*vec,1),length,out=np.zeros(len(length)),where=length>1e-22),0,1);values.append(np.sqrt(np.min(np.sum((start+t[:,None]*vec-x)**2,1))))
  return float(max(values))*1000
 return max(maximum(a,b),maximum(b,a))

import sys
root=Path(sys.argv[1]if len(sys.argv)>1 else '/tmp/pattern-wear-audit')
def seamgaps(parts):
 def edge(i,r,sign=0):
  m=parts[i];p=np.array(m['vertices']);uv=m['points2d'];return np.array([[p[e['a']],p[e['b']]]for e in m['boundary']if e['edge']==r and(not sign or(uv[e['a']]['x']+uv[e['b']]['x'])*sign>0)])
 def gap(a,b):
  points=np.concatenate([a[:,0]*t+a[:,1]*(1-t)for t in[0,.125,.25,.375,.5,.625,.75,.875,1]]);start=b[:,0];vec=b[:,1]-start;l=np.sum(vec*vec,1);return max(np.linalg.norm(start+np.clip(np.sum((p-start)*vec,1)/l,0,1)[:,None]*vec-p,axis=1).min()for p in points)*1000
 def pair(a,b):return float(max(gap(a,b),gap(b,a)))
 out={r:pair(edge(0,r),edge(1,r))for r in ['shoulder','side']}
 for i,sign in[(2,1),(3,-1)]:out[str(i)+'-underarm']=pair(edge(i,'underarm-right'),edge(i,'underarm-left'));out[str(i)+'-cap']=pair(edge(i,'cap'),np.concatenate([edge(0,'armhole',sign),edge(1,'armhole',sign)]))
 return out
class TriangleGrid:
 def __init__(self,tri,cell=.025):
  self.tri=tri;self.cell=cell;self.grid=defaultdict(list);self.lo=tri.min(1);self.hi=tri.max(1)
  for i,(lo,hi)in enumerate(zip(np.floor(self.lo/cell).astype(int),np.floor(self.hi/cell).astype(int))):
   for x in range(lo[0],hi[0]+1):
    for y in range(lo[1],hi[1]+1):
     for z in range(lo[2],hi[2]+1):self.grid[x,y,z].append(i)
 def candidates(self,t):
  lo=t.min(0);hi=t.max(0);a=np.floor(lo/self.cell).astype(int);b=np.floor(hi/self.cell).astype(int);ids=set()
  for x in range(a[0],b[0]+1):
   for y in range(a[1],b[1]+1):
    for z in range(a[2],b[2]+1):ids.update(self.grid.get((x,y,z),[]))
  if not ids:return np.array([],int)
  ids=np.array(list(ids));return ids[np.all(self.lo[ids]<=hi+1e-10,1)&np.all(self.hi[ids]>=lo-1e-10,1)]
 def intersect(self,t):
  ids=self.candidates(t)
  if not len(ids):return []
  # Separating-axis theorem for two closed non-degenerate triangles.
  b=self.tri[ids];ae=np.roll(t,-1,axis=0)-t;be=np.roll(b,-1,axis=1)-b;an=np.cross(ae[0],ae[1]);bn=np.cross(be[:,0],be[:,1]);axes=[np.broadcast_to(an,(len(b),3)),bn]
  for x in ae:
   for j in range(3):axes.append(np.cross(np.broadcast_to(x,(len(b),3)),be[:,j]))
  # In-plane axes also cover the coplanar case.
  for x in ae:axes.append(np.broadcast_to(np.cross(an,x),(len(b),3)))
  for j in range(3):axes.append(np.cross(bn,be[:,j]))
  overlap=np.ones(len(b),bool)
  for axis in axes:
   length=np.linalg.norm(axis,axis=1);valid=length>1e-17;axis=np.divide(axis,length[:,None],out=np.zeros_like(axis),where=valid[:,None]);ap=np.einsum('ij,kj->ik',axis,t);bp=np.einsum('ij,ikj->ik',axis,b);overlap &=~valid|((ap.max(1)>=bp.min(1)-1e-9)&(bp.max(1)>=ap.min(1)-1e-9))
   if not overlap.any():break
  return ids[overlap].tolist()

def rayhits(tri,p,d):
 e1=tri[:,1]-tri[:,0];e2=tri[:,2]-tri[:,0];h=np.cross(np.broadcast_to(d,e2.shape),e2);det=np.einsum('ij,ij->i',e1,h);inv=np.divide(1.,det,out=np.zeros_like(det),where=np.abs(det)>1e-12);s=p-tri[:,0];u=np.einsum('ij,ij->i',s,h)*inv;q=np.cross(s,e1);v=q@d*inv;t=np.einsum('ij,ij->i',e2,q)*inv;return np.sort(t[(np.abs(det)>1e-12)&(u>=-1e-9)&(v>=-1e-9)&(u+v<=1+1e-9)&(t>1e-7)])

def wrapcheck(body,cloth,hem):
 # Fixed anatomical chest level and upper-arm axes, independent of solver contacts.
 y=hem/2000+(2.5-5.7)*1.75/(8.4913+8.1676);tests=[]
 for deg in np.arange(0,360,10):
  a=np.deg2rad(deg);p=np.array([0,y,-.04]);d=np.array([np.cos(a),0,np.sin(a)]);hb=rayhits(body,p,d);hc=rayhits(cloth,p,d);tests.append(len(hb)>0 and len(hc)>0 and hc[0]>hb[0]+.0005)
 return {'torsoDirections':len(tests),'torsoEnclosed':bool(all(tests))}
def openingcheck(data):
 def edges(i,role):
  m=data['garment'][i];p=np.array(m['vertices']);return np.array([[p[e['a']],p[e['b']]]for e in m['boundary']if e['edge']==role])
 def contains(segments,origin,u,v):
  q=(segments-np.array(origin))@np.array([u,v]).T;count=0
  for a,b in q:
   if(a[1]>0)!=(b[1]>0)and a[0]+(b[0]-a[0])*(-a[1])/(b[1]-a[1])>0:count+=1
  return count%2==1
 j=data['landmarks'];r={'neck':contains(np.concatenate([edges(0,'neck'),edges(1,'neck')]),j['neck'],[1,0,0],[0,0,1]),'hem':contains(np.concatenate([edges(0,'hem'),edges(1,'hem')]),[0,0,-.04],[1,0,0],[0,0,1])}
 for i,side in[(2,'l'),(3,'r')]:
  S=np.array(j[side+'-shoulder']);axis=np.array(j[side+'-elbow'])-S;axis/=np.linalg.norm(axis);u=np.cross(axis,[0,0,1]);u/=np.linalg.norm(u);r[side+'Cuff']=contains(edges(i,'hem'),S,u,np.cross(axis,u))
 return r

report={'schema':'garment-body-geometric-wear/2','status':'FAIL','scopeZh':'演示人体的静态几何穿着；非面料力学或个人合体认证','tolerances':{'bodyIntersectionM':1e-9,'seamGapMm':1},'methodsZh':['使用实际渲染人体顶点与求解后衣片，不读取示意映射坐标','独立 Python 三个斜射线方向对所有顶点、边中点、面中心作包含检查','空间网格宽相位与三角形分离轴检测，检查全部衣片与人体三角面交叉','指定配缝作双向点到线段距离采样，每段 9 点','领口、下摆和双袖口投影包含测试；腰部 36 个方向包围检查'],'limitsZh':['穿着通过仅限静态几何与当前演示人体','真实面料力学、压力与个人合体未校准','未作连续运动、自碰撞或制造工艺认证'],'variants':[]}
for key in(sys.argv[2:]or['basic','relaxed','cropped']):
 start=time.time();data=json.loads((root/(key+'.json')).read_text());bv=np.array(data['human']['vertices']);bf=np.array(data['human']['triangles'],int);bt=bv[bf];edges=Counter();direction=Counter()
 for face in bf:
  for a,b in zip(face,np.roll(face,-1)):edges[tuple(sorted([int(a),int(b)]))]+=1;direction[int(a),int(b)]+=1
 assert all(x==2 for x in edges.values())and all(direction[a,b]==direction[b,a]for a,b in edges)
 grids=[RayGrid(bv,bf,d)for d in[[.173,.291,1],[1,.241,.317],[.319,1,.127]]];tg=TriangleGrid(bt);parts=[];cloth=[]
 # Independent positive and negative controls.
 for g in grids:assert g.contains(np.array([[0.,.10,0.],[10.,10.,10.]]))[0].tolist()==[True,False]
 for m in data['garment']:
  v=np.array(m['vertices']);f=np.array(m['triangles'],int);tri=v[f];cloth.extend(tri);query=np.concatenate([v,tri.mean(1),(tri[:,0]+tri[:,1])/2,(tri[:,1]+tri[:,2])/2,(tri[:,2]+tri[:,0])/2]);votes=[];boundary=[]
  for g in grids:
   a,b=g.contains(query);votes.append(a);boundary.append(b)
  votes=np.array(votes);uncertain=np.any(votes,0)^np.all(votes,0);inside=np.all(votes,0);intersections=[]
  for i,t in enumerate(tri):
   hits=tg.intersect(t)
   if hits:intersections.append({'clothFace':i,'bodyFaces':hits})
  uv=np.array([[p['x'],p['y']]for p in m['points2d']])/1000;dm=np.stack([uv[f[:,1]]-uv[f[:,0]],uv[f[:,2]]-uv[f[:,0]]],2);ds=np.stack([tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]],2);strain=np.linalg.svd(ds@np.linalg.inv(dm),compute_uv=False)[:,0]-1
  row={'part':m['part'],'vertices':len(v),'triangles':len(f),'samplePoints':len(query),'insideSamples':int(inside.sum()),'insideVertices':int(inside[:len(v)].sum()),'ambiguousSamples':int(uncertain.sum()),'surfaceBoundarySamples':int(np.any(boundary,0).sum()),'intersectingTriangles':len(intersections),'maxPrincipalStrainPercent':float(strain.max()*100)};parts.append(row);print(key,row,flush=True)
  if intersections:(root/(key+'-intersections.json')).write_text(json.dumps(intersections))
 gaps=seamgaps(data['garment']);openings=openingcheck(data);wrap=wrapcheck(bt,np.array(cloth),data['hemMm']);good=all(p['insideSamples']==p['ambiguousSamples']==p['intersectingTriangles']==0 for p in parts)and max(gaps.values())<=1 and wrap['torsoEnclosed']and all(openings.values());row={'variant':key,'status':'PASS'if good else'FAIL','inputSha256':hashlib.sha256((root/(key+'.json')).read_bytes()).hexdigest(),'bodyClosedManifold':True,'parts':parts,'seamGapsMm':gaps,'enclosure':{**wrap,'openings':openings},'boundaryDeviationMm':data.get('boundaryDeviationMm'),'solver':data['solver'],'durationSeconds':round(time.time()-start,2)};report['variants'].append(row);(root/'wear-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(key,row['status'],gaps,wrap,flush=True)
report['status']='PASS'if all(v['status']=='PASS'for v in report['variants'])else'FAIL';(root/'wear-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print('OVERALL',report['status'],flush=True)

assert report['status']=='PASS','Geometric wear failed'
