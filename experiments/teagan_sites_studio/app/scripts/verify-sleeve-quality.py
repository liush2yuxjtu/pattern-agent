"""Independent source-curve quadrature and geometric seam audit (no app imports)."""
from pathlib import Path
import json,sys,math
import numpy as np
from scipy.integrate import quad
root=Path(sys.argv[1]if len(sys.argv)>1 else'/tmp/pattern-wear-audit')
LIMITS={'upperCapPlaneP95Deg':30,'upperCapInwardTurnMaxDeg':45,'sleeveMirrorMaxMm':.5,'interiorFoldP95Deg':25,'interiorFoldMaxDeg':45}
def unit(a):
 n=np.linalg.norm(a);assert n>1e-12;return a/n
def summarize(a):
 a=np.sort(a);return{'count':len(a),'mean':float(a.mean()),'p95':float(a[math.ceil(len(a)*.95)-1]),'max':float(a[-1])}
def curves(part):
 start=None
 for op in part['seamOps']:
  if op['type']=='move':start=np.array([op['to']['x'],op['to']['y']]);continue
  if'to'not in op:continue
  end=np.array([op['to']['x'],op['to']['y']]);yield op,start,end;start=end
def apex(part):
 candidates=[]
 for op,a,d in curves(part):
  if op['edge']!='cap':continue
  candidates.extend([a,d])
  if op['type']=='curve':
   b=np.array([op['cp1']['x'],op['cp1']['y']]);c=np.array([op['cp2']['x'],op['cp2']['y']]);coef=[-a[1]+3*b[1]-3*c[1]+d[1],2*(a[1]-2*b[1]+c[1]),b[1]-a[1]]
   for r in np.roots(np.trim_zeros(coef,'f')):
    if abs(r.imag)<1e-10 and 0<r.real<1:
     t=r.real;u=1-t;candidates.append(u**3*a+3*u*u*t*b+3*u*t*t*c+t**3*d)
 return min(candidates,key=lambda p:p[1])
def length(part,role):
 total=0.
 for op,a,d in curves(part):
  if op['edge']!=role:continue
  if op['type']=='line':total+=np.linalg.norm(d-a);continue
  b=np.array([op['cp1']['x'],op['cp1']['y']]);c=np.array([op['cp2']['x'],op['cp2']['y']]);speed=lambda t:np.linalg.norm(3*(1-t)**2*(b-a)+6*(1-t)*t*(c-b)+3*t*t*(d-c));value,error=quad(speed,0,1,epsabs=1e-10,epsrel=1e-12,limit=100);assert error<1e-7;total+=value
 return float(total)
def source_check(parts):
 joins=[]
 for name in['front','back','sleeve']:
  previous=None
  for op,a,d in curves(parts[name]):
   if op['edge']not in['cap','armhole']:previous=None;continue
   pts=[a,np.array([op['cp1']['x'],op['cp1']['y']]),np.array([op['cp2']['x'],op['cp2']['y']]),d]if op['type']=='curve'else[a,d]
   start=next(p-a for p in pts[1:]if np.linalg.norm(p-a)>1e-9);end=next(d-p for p in reversed(pts[:-1])if np.linalg.norm(d-p)>1e-9)
   if previous and previous[0]['edge']==op['edge']:
    assert np.linalg.norm(previous[1]-a)<1e-8
    joins.append(float(np.degrees(np.arctan2(abs(previous[2][0]*start[1]-previous[2][1]*start[0]),np.dot(previous[2],start)))))
   previous=(op,d,end)
 arm=length(parts['front'],'armhole')+length(parts['back'],'armhole');cap=length(parts['sleeve'],'cap');return{'armholeLengthMm':arm,'capLengthMm':cap,'capEaseMm':cap-arm,'maxJoinAngleDeg':max(joins)}
def mesh_boundaries(m):
 v=np.array(m['vertices']);uv=np.array([[p['x'],p['y']]for p in m['points2d']]);adj={}
 for t in m['triangles']:
  for k in range(3):adj.setdefault(tuple(sorted([t[k],t[(k+1)%3]])),[]).append(t[(k+2)%3])
 out=[]
 for e in m['boundary']:
  ids=adj[tuple(sorted([e['a'],e['b']]))];assert len(ids)==1;a=v[e['a']];b=v[e['b']];c=v[ids[0]];axis=unit(b-a);mid=(a+b)/2;inward=c-mid-axis*np.dot(c-mid,axis);out.append({**e,'a3':a,'b3':b,'normal':unit(np.cross(b-a,c-a)),'inward':unit(inward),'uvA':uv[e['a']],'uvB':uv[e['b']]})
 return out

def interior_quality(m):
 v=np.array(m['vertices']);uv=np.array([[p['x'],p['y']]for p in m['points2d']]);f=np.array(m['triangles']);n=np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]]);n/=np.linalg.norm(n,axis=1)[:,None];edges={}
 for i,t in enumerate(f):
  for a,b in zip(t,np.roll(t,-1)):edges.setdefault(tuple(sorted([int(a),int(b)])),[]).append(i)
 seams=[(uv[e['a']],uv[e['b']])for e in m['boundary']if e['edge'].startswith('underarm')];values=[];excluded=0
 for(a,b),faces in edges.items():
  if len(faces)!=2:continue
  mid=(uv[a]+uv[b])/2;dist=[]
  for p,q in seams:
   u=q-p;t=np.clip(np.dot(mid-p,u)/np.dot(u,u),0,1);dist.append(np.linalg.norm(mid-p-t*u))
  if min(dist)<15:excluded+=1;continue
  values.append(np.degrees(np.arccos(np.clip(n[faces[0]]@n[faces[1]],-1,1))))
 return{**summarize(values),'excludedNearUnderarmEdges':excluded,'underarmExclusionMm':15}

def check(data):
 panels=data['garment'];parts=data['patternParts'];peak=apex(parts['sleeve']);edges=[mesh_boundaries(m)for m in panels];sides=[]
 for i,sign in[(2,1),(3,-1)]:
  caps=[]
  for e in edges[i]:
   if e['edge']!='cap':continue
   reverse=e['uvA'][0]<e['uvB'][0];a,b=(e['uvB'],e['uvA'])if reverse else(e['uvA'],e['uvB']);caps.append({**e,'reverse':reverse,'start':a,'end':b,'length':np.linalg.norm(b-a)})
  caps.sort(key=lambda e:-e['start'][0]-e['end'][0]);j=0;start=0.;samples=[]
  for s in np.arange(2.5,sum(e['length']for e in caps),5.):
   while j<len(caps)-1 and s>start+caps[j]['length']:start+=caps[j]['length'];j+=1
   e=caps[j];t=(s-start)/e['length'];uv=e['start']*(1-t)+e['end']*t
   if uv[1]>peak[1]*.65:continue
   t=1-t if e['reverse']else t;p=e['a3']*(1-t)+e['b3']*t;arms=[a for a in edges[0 if uv[0]>=peak[0]else 1]if a['edge']=='armhole'and(a['uvA'][0]+a['uvB'][0])*sign>0];dist=[]
   for a in arms:
    vec=a['b3']-a['a3'];u=np.clip(np.dot(p-a['a3'],vec)/np.dot(vec,vec),0,1);dist.append(np.linalg.norm(p-a['a3']-u*vec))
   a=arms[int(np.argmin(dist))];plane=np.degrees(np.arccos(np.clip(abs(np.dot(e['normal'],a['normal'])),-1,1)));turn=180-np.degrees(np.arccos(np.clip(np.dot(e['inward'],a['inward']),-1,1)));samples.append([plane,turn])
  q=np.array(samples);assert len(q)>=10;sides.append({'part':panels[i].get('part',panels[i].get('partId')),'planeAngleDeg':summarize(q[:,0]),'inwardTurnDeg':summarize(q[:,1]),'interiorFoldDeg':interior_quality(panels[i])})
 right=np.array(panels[2]['vertices']);left=np.array(panels[3]['vertices']);mirror=float(np.linalg.norm(right*np.array([-1,1,1])-left,axis=1).max()*1000)
 good=mirror<=LIMITS['sleeveMirrorMaxMm']and all(x['planeAngleDeg']['p95']<=LIMITS['upperCapPlaneP95Deg']and x['inwardTurnDeg']['max']<=LIMITS['upperCapInwardTurnMaxDeg']and x['interiorFoldDeg']['p95']<=LIMITS['interiorFoldP95Deg']and x['interiorFoldDeg']['max']<=LIMITS['interiorFoldMaxDeg']for x in sides)
 source=source_check(parts)
 runtime=data.get('sleeveQuality');error=0.
 if runtime:
  error=max(abs(runtime['sleeveMirrorMaxMm']-mirror),*(abs(a[k][stat]-b[k][stat])for a,b in zip(sides,runtime['sides'])for k in['planeAngleDeg','inwardTurnDeg','interiorFoldDeg']for stat in['mean','p95','max']));assert error<1e-7,error
 return{'status':'PASS'if good else'FAIL','sides':sides,'sleeveMirrorMaxMm':mirror,'source':source,'maxRuntimeDifference':error}
# Opposing coplanar co-normals are smooth; same-plane inward folding must fail.
assert 180-np.degrees(np.arccos(-1))==0
assert 180-np.degrees(np.arccos(1))>LIMITS['upperCapInwardTurnMaxDeg']
results=[]
for key in(sys.argv[2:]or['basic','relaxed','cropped']):
 data=json.loads((root/(key+'.json')).read_text());r=check(data);r['variant']=key;assert r['status']=='PASS',r;assert r['source']['maxJoinAngleDeg']<=.1
 if data.get('sleeveRefinement'):assert abs(r['source']['capEaseMm'])<=.01
 results.append(r);print(key,r['status'],'upper p95',[round(x['planeAngleDeg']['p95'],3)for x in r['sides']],'mirror mm',r['sleeveMirrorMaxMm'],flush=True)
negative=None
if(root/'legacy-basic.json').exists():
 data=json.loads((root/'legacy-basic.json').read_text());negative=check(data);assert negative['status']=='FAIL';assert data['previousWearStatus']=='PASS';print('PASS: former wear-PASS / sharp-sleeve geometry is rejected',flush=True)
report={'schema':'independent-sleeve-surface-quality/1','status':'PASS','limits':LIMITS,'meaningZh':'本次无结构装袖三维预览平顺性目标，非工业合体标准','methodsZh':['独立NumPy按源弧长每5mm采样最高35%袖山','使用真实相邻三角面法平面与向内余切方向；不使用渲染平滑法线','左右袖同源顶点镜像距离','SciPy自适应积分复核零吃势配缝与曲线切向连续'],'variants':results,'negativeControl':negative}
(root/'sleeve-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
p=root/'wear-report.json'
if p.exists():
 w=json.loads(p.read_text());w['sleeveSurfaceQuality']=report;w['status']='PASS'if w['status']=='PASS'and report['status']=='PASS'else'FAIL';p.write_text(json.dumps(w,ensure_ascii=False,indent=2)+'\n')
print('PASS: independent sleeve surface, mirror and source-curve verification')
