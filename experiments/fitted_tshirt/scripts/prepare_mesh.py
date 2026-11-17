import json, math, argparse
parser=argparse.ArgumentParser()
parser.add_argument("--polylines",default="data/polylines.json")
parser.add_argument("--output",default="data/tshirt_mesh.json")
args=parser.parse_args()
from pathlib import Path
import numpy as np
from scipy.spatial import Delaunay
from matplotlib.path import Path as PolyPath
P=json.load(open(args.polylines))
def join(spec):
 out=[]
 for i,reverse in spec:
  q=P[i][::-1] if reverse else P[i]
  if out and np.linalg.norm(np.array(out[-1])-q[0])<.1:q=q[1:]
  out+=q
 return np.array(out)
def mappt(q,front):
 cx=2962.449951 if front else 1881.964264
 x=(q[0]-cx)/1000
 z=(q[1]+(11.22 if front else 0)+2866.23)/1000
 alpha=np.clip((z-1.35)/.15,0,1)
 half=np.interp(z,[1.01,1.20,1.337,1.55],[.213,.180,.2164,.2164])
 # The flat panel width supplies an approximate half circumference.
 rx=half*.735
 theta=np.clip(x/half,-1,1)*math.pi/2
 X=(1-alpha)*rx*math.sin(theta)+alpha*x
 depth=(1-alpha)*half*.47+alpha*.064
 Y=depth*math.cos(theta)
 if front:
  Y+=.018*math.exp(-((abs(X)-.065)/.065)**2-((z-1.385)/.065)**2)*max(0,math.cos(theta))
  Y+=.0015*math.sin((z-1.10)*125+X*24)*math.exp(-((z-1.16)/.09)**2)*(math.sin(theta)**2)
 Y=Y*(-1 if front else 1)
 return [X,Y,z]
def sample(q,n=64):
 d=np.r_[0,np.cumsum(np.linalg.norm(np.diff(q,axis=0),axis=1))]
 return np.array([np.interp(np.linspace(0,d[-1],n),d,q[:,j]) for j in range(q.shape[1])]).T
specs={'front':[(93,True),(94,False),(95,True),(96,False),(91,False),(109,True),(113,True),(112,False),(111,True),(110,False)],'back':[(51,True),(50,True),(49,True),(48,False),(47,False),(25,True),(26,True),(27,False),(28,False),(29,False),(30,True),(52,False)]}
result={'panels':{},'paths':{}}
for name,spec in specs.items():
 poly=join(spec); path=PolyPath(np.vstack([poly,poly[0]]));mi=poly.min(0);ma=poly.max(0)
 xx,yy=np.meshgrid(np.arange(mi[0],ma[0],5),np.arange(mi[1],ma[1],5));g=np.c_[xx.ravel(),yy.ravel()];g=g[path.contains_points(g)]
 points=np.vstack([poly,g]);points=np.unique(np.round(points,4),axis=0)
 tri=Delaunay(points).simplices
 keep=np.ones(len(tri),dtype=bool)
 for weights in [(1/3,1/3,1/3),(.5,.5,0),(.5,0,.5),(0,.5,.5)]:
  c=sum(points[tri[:,i]]*weights[i] for i in range(3));keep &= path.contains_points(c,radius=.05)
 tris=tri[keep]
 verts=[mappt(q,name=='front') for q in points]
 result['panels'][name]={'verts':verts,'faces':tris.tolist()}
 result['paths'][name+'_neck']=[mappt(q,name=='front') for q in sample(join([(93,False),(110,True)]) if name=='front' else join([(52,True),(30,False)]),100)]
 for side,indices in [('right',[(112,False)] if name=='front' else [(28,False)]),('left',[(95,False)] if name=='front' else [(50,False)])]:
  result['paths'][name+'_'+side+'_arm']=[mappt(q,name=='front') for q in sample(join(indices),45)]
 result['paths'][name+'_hem']=[mappt(q,name=='front') for q in sample(join([(91,False),(109,True)]) if name=='front' else join([(47,False),(25,True)]),100)]
 for side,ids in [('right',[(111,False)] if name=='front' else [(29,True)]),('left',[(94,False)] if name=='front' else [(51,True)])]:
  result['paths'][name+'_'+side+'_shoulder']=[mappt(q,name=='front') for q in sample(join(ids),24)]
for name in ['front','back']:
 for side in ['left','right']:
  ids=([(96,False)] if side=='left' else [(113,False)]) if name=='front' else ([(49,True),(48,False)] if side=='left' else [(27,True),(26,False)])
  result['paths'][name+'_'+side+'_side']=[mappt(q,name=='front') for q in sample(join(ids),100)]
# Sleeve dimensions are sampled from actual inner sleeve side boundaries.
y=np.linspace(-1529.4,-1982,60)
r=np.array(P[70]);l=np.array(P[73]);
def at(q,y):
 order=np.argsort(q[:,1]);return np.interp(y,q[order,1],q[order,0])
result['sleeve_widths']=(at(r,y)-at(l,y)).tolist()
Path(args.output).write_text(json.dumps(result))
print('triangles', {k:len(v['faces']) for k,v in result['panels'].items()})
