"""Independent NumPy audit: reconstruct adjacency/pairing from raw archived vertices.
Angles use the stable half-angle identity, not the application's atan2(cross,dot).
"""
from pathlib import Path
import json, math, numpy as np
root=Path('/workspace/sites/pattern-atelier/dist/diagnostics');work=Path('/workspace/work/fold-color-audit')
js=json.loads((work/'angle-fixtures.json').read_text());results={}
def angle(a,b):
 a=a/np.linalg.norm(a);b=b/np.linalg.norm(b)
 return float(np.degrees(2*np.arctan2(np.linalg.norm(a-b),np.linalg.norm(a+b))))
def norm(v):return v/np.linalg.norm(v)
def nearest(q,a,b):
 d=b-a;return a+np.clip(np.dot(q-a,d)/np.dot(d,d),0,1)*d
for case in ['before','after']:
 raw=json.loads((root/f'sleeve-{case}.json').read_text());panels=raw['garment'];app=js['cases'][case];interior={};boundaries={}
 for p in panels:
  pid=p['partId'];v=np.asarray(p['vertices']);uv=np.asarray([[x['x'],x['y']]for x in p['points2d']]);t=np.asarray(p['triangles']);n=np.cross(v[t[:,1]]-v[t[:,0]],v[t[:,2]]-v[t[:,0]]);n/=np.linalg.norm(n,axis=1)[:,None];adj={}
  for face,tri in enumerate(t):
   for k in range(3):
    a,b=int(tri[k]),int(tri[(k+1)%3]);adj.setdefault(tuple(sorted([a,b])),[]).append((face,int(tri[(k+2)%3]),1 if a<b else -1))
  seams=[(uv[e['a']],uv[e['b']])for e in p['boundary']if e['edge'].startswith('underarm')]
  for (a,b),neighbor in adj.items():
   if len(neighbor)!=2:continue
   assert neighbor[0][2]!=neighbor[1][2]
   q=(uv[a]+uv[b])/2;distance=min((np.linalg.norm(q-nearest(q,x,y))for x,y in seams),default=None)
   interior[f'{pid}:{a}:{b}']={'angleDeg':angle(n[neighbor[0][0]],n[neighbor[1][0]]),'excluded':distance is not None and distance<15,'distance':distance}
  boundary=[]
  for e in p['boundary']:
   neighbor=adj[tuple(sorted([e['a'],e['b']]))];assert len(neighbor)==1
   a,b=v[e['a']],v[e['b']];c=v[neighbor[0][1]]
   boundary.append({**e,'partId':pid,'a3':a,'b3':b,'normal':norm(np.cross(b-a,c-a)),'face':neighbor[0][0],'uvMeanX':(uv[e['a'],0]+uv[e['b'],0])/2})
  boundaries[pid]=boundary
 def edges(pid,role,sign=0):return[e for e in boundaries[pid]if e['edge']==role and (not sign or e['uvMeanX']*sign>0)]
 pairs=[('shoulder',edges('front','shoulder'),edges('back','shoulder')),('side',edges('front','side'),edges('back','side'))]
 for pid,sign in [('sleeve-right',1),('sleeve-left',-1)]:
  pairs +=[(pid+'-cap',edges(pid,'cap'),edges('front','armhole',sign)+edges('back','armhole',sign)),(pid+'-underarm',edges(pid,'underarm-right'),edges(pid,'underarm-left'))]
 seam_rows={};gap_max=0
 for name,left,right in pairs:
  assert left and right
  for source_set,target_set,direction in [(left,right,'a'),(right,left,'b')]:
   for source in source_set:
    q=(source['a3']+source['b3'])/2;distances=[np.linalg.norm(q-nearest(q,e['a3'],e['b3']))for e in target_set];target=target_set[int(np.argmin(distances))];gap=float(min(distances))*1000;gap_max=max(gap_max,gap)
    assert gap<=1
    n2=target['normal']
    if np.dot(source['b3']-source['a3'],target['b3']-target['a3'])>0:n2=-n2
    seam_rows[f"seam:{name}:{direction}:{source['partId']}:{source['a']}:{source['b']}"]={'angleDeg':angle(source['normal'],n2),'gapMm':gap,'targetPart':target['partId'],'targetFace':target['face']}
 app_internal={e['id']:e for p in app['parts']for e in p['edges']};app_seam={e['id']:e for e in app['seams']['samples']}
 assert set(interior)==set(app_internal)
 assert len(app_seam)==len(app['seams']['samples'])
 assert set(seam_rows)==set(app_seam)
 errors=[abs(x['angleDeg']-app_internal[key]['angleDeg'])for key,x in interior.items()]
 assert all(x['excluded']==app_internal[key]['excluded']for key,x in interior.items())
 seam_errors=[]
 for key,x in seam_rows.items():
  y=app_seam[key];assert x['targetPart']==y['counterpart']['partId']and x['targetFace']==y['counterpart']['face'];assert abs(x['gapMm']-y['gapMm'])<1e-8
  seam_errors.append(abs(x['angleDeg']-y['angleDeg']))
 assert max(errors+seam_errors)<1e-8
 sleeve=[x['angleDeg']for key,x in interior.items()if key.startswith('sleeve')and not x['excluded']];underarm=[x['angleDeg']for x in interior.values()if x['excluded']];all_values=[x['angleDeg']for x in interior.values()]+[x['angleDeg']for x in seam_rows.values()]
 result={'interiorEdges':len(interior),'pairedSeamSamples':len(seam_rows),'unmatchedSeams':0,'maximumAngleDifferenceDeg':max(errors+seam_errors),'seamGapMaxMm':gap_max,'fullMaxDeg':max(all_values),'fullAbove45':sum(x>45 for x in all_values),'sleeveQualityMaxDeg':max(sleeve),'sleeveQualityAbove45':sum(x>45 for x in sleeve),'underarmMaxDeg':max(underarm),'underarmAbove45':sum(x>45 for x in underarm)}
 assert abs(result['sleeveQualityMaxDeg']-app['peak']['angleDeg'])<1e-8
 assert abs(result['fullMaxDeg']-app['full']['peak']['angleDeg'])<1e-8
 
 assert result['fullAbove45']==app['full']['sharpCount']
 results[case]=result
report={'status':'PASS','method':'Independent NumPy adjacency, nearest seam pairing and 2*atan2(||n1-n2||,||n1+n2||); raw immutable archived geometry; no app imports','cases':results}
(work/'independent-verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
