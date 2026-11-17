"""Prototype source-bound sewn shell; dimensions in canonical millimetres."""
from __future__ import annotations
import json,math
from pathlib import Path
import numpy as np
from scipy.optimize import brentq,root
from scipy.spatial import Delaunay,cKDTree
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import spsolve
from scipy.sparse.csgraph import dijkstra

def tidy_q(q):
 q=np.sort(np.asarray(q));keep=np.r_[True,np.diff(q)>1e-5];q=q[keep];q[0]=0
 if 1-q[-1]<1e-5:q[-1]=1
 else:q=np.r_[q,1.]
 return q

def length(p):return float(np.linalg.norm(np.diff(p,axis=0),axis=1).sum())
def fractions(p):
 d=np.r_[0,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))];return d/d[-1]
def interp(p,t):
 d=fractions(p);return np.column_stack([np.interp(np.atleast_1d(t),d,p[:,k]) for k in range(p.shape[1])])
def join(P,spec):
 out=[]
 for i,rev in spec:
  q=P[i][::-1] if rev else P[i]
  if out and np.linalg.norm(out[-1]-q[0])<.05:q=q[1:]
  out.extend(q)
 return np.array(out,float)
def inside(points,poly):
 x,y=points.T;keep=np.zeros(len(points),bool);a=poly[-1]
 for b in poly:
  if abs(a[1]-b[1])>1e-10:keep^=((a[1]>y)!=(b[1]>y))&(x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0])
  a=b
 return keep

def patterns(P):
 E={};spec={};loops={}
 def edge(name,refs):spec[name]=refs;E[name]=join(P,refs)
 for name in ['front','back']:
  if name=='front':
   defs={'neck.left':[(93,True)],'neck.right':[(110,False)],'shoulder.left':[(94,False)],'shoulder.right':[(111,False)],'arm.left':[(95,True)],'arm.right':[(112,True)],'side.left':[(96,False)],'side.right':[(113,False)],'hem':[(91,False),(109,True)]}
  else:
   defs={'neck.left':[(52,True)],'neck.right':[(30,False)],'shoulder.left':[(51,True)],'shoulder.right':[(29,True)],'arm.left':[(50,True)],'arm.right':[(28,True)],'side.left':[(49,True),(48,False)],'side.right':[(27,True),(26,False)],'hem':[(47,False),(25,True)]}
  for key,refs in defs.items():edge(name+'.'+key,refs)
  order=[('neck.left',name=='back'),('shoulder.left',False),('arm.left',False),('side.left',False),('hem',False),('side.right',True),('arm.right',True),('shoulder.right',True),('neck.right',name=='back')]
  loops[name]=[(name+'.'+k,r) for k,r in order]
 edge('sleeve.cap.front',[(71,True)]);edge('sleeve.cap.back',[(72,False)])
 edge('sleeve.side.front',[(70,True)]);edge('sleeve.side.back',[(73,True)])
 edge('sleeve.cuff',[(68,True),(69,False)])
 loops['sleeve']=[('sleeve.cap.back',False),('sleeve.side.back',False),('sleeve.cuff',False),('sleeve.side.front',True),('sleeve.cap.front',True)]
 original={k:v.copy() for k,v in E.items()};snaps=[]
 # Remove sub-0.05mm drafting junction noise without hiding broken/open contours.
 for name,loop in loops.items():
  for (ka,ra),(kb,rb) in zip(loop,loop[1:]+loop[:1]):
   ia=0 if ra else -1;ib=-1 if rb else 0;a,b=E[ka][ia],E[kb][ib];gap=float(np.linalg.norm(a-b))
   if gap>.05:raise ValueError(f'OPEN_SOURCE_JUNCTION {name} {ka} {kb}: {gap}')
   mid=(a+b)/2;E[ka][ia]=mid;E[kb][ib]=mid
   if gap>1e-9:snaps.append({'edges':[ka,kb],'gap_mm':gap})
 def move_endpoint(key,index,delta):
  q=E[key];t=fractions(q);weights=(1-t)**2 if index==0 else t**2;E[key]=q+weights[:,None]*delta
 operations=[]
 for side in ['left','right']:
  key='front.shoulder.'+side;q=E[key];target=length(E['back.shoulder.'+side]);delta=(q[-1]-q[0])*(1-target/length(q))
  move_endpoint(key,0,delta);move_endpoint('front.neck.'+side,-1 if side=='left' else 0,delta)
  operations.append({'kind':'front_shoulder_length_match','side':side,'delta_mm':delta.tolist(),'target_mm':target})
  key='front.side.'+side;q=E[key].copy();weights=fractions(q)**2;target=length(E['back.side.'+side])+10+6
  shift=brentq(lambda dy:length(q+weights[:,None]*[0,dy])-target,-8,8)
  move_endpoint(key,-1,np.array([0,shift]));move_endpoint('front.hem',0 if side=='left' else -1,np.array([0,shift]))
  operations.append({'kind':'side_residual_after_documented_process','side':side,'dy_mm':shift,'front_ease_mm':6,'back_stretch_mm':10,'target_front_rest_mm':target})
 f,b=E['sleeve.cap.front'].copy(),E['sleeve.cap.back'].copy();total=length(f)+length(b)-length(E['front.arm.left'])-length(E['back.arm.left'])
 if not 0<=total<=15:raise ValueError('SLEEVE_EASE_OUTSIDE_KNIT_RANGE')
 targets=[length(E['front.arm.left'])+.4*total,length(E['back.arm.left'])+.6*total]
 wf=(1-fractions(f))**2;wb=(1-fractions(b))**2
 solved=root(lambda delta:[length(f+wf[:,None]*delta)-targets[0],length(b+wb[:,None]*delta)-targets[1]],[4.,0.])
 if not solved.success:raise ValueError('CAP_REBALANCE_FAILED')
 E['sleeve.cap.front']=f+wf[:,None]*solved.x;E['sleeve.cap.back']=b+wb[:,None]*solved.x
 operations.append({'kind':'sleeve_cap_ease_distribution','apex_delta_mm':solved.x.tolist(),'total_ease_mm':total,'front_ease_mm':.4*total,'back_ease_mm':.6*total,'reference':'repository sleeve rule: front 0.4/back 0.6; body armholes unchanged'})
 q=E['sleeve.side.back'].copy();w=fractions(q)**2;target=length(E['sleeve.side.front'])
 shift=brentq(lambda dy:length(q+w[:,None]*[0,dy])-target,-8,8)
 move_endpoint('sleeve.side.back',-1,np.array([0,shift]));move_endpoint('sleeve.cuff',0,np.array([0,shift]))
 operations.append({'kind':'sleeve_underarm_length_match','dy_mm':shift,'target_mm':target})
 max_shift=max(float(np.linalg.norm(E[k]-original[k],axis=1).max()) for k in original)
 if max_shift>8:raise ValueError('DERIVED_PATTERN_EDIT_OVER_8MM')
 return E,loops,{'original_edges':{k:v.tolist() for k,v in original.items()},'derived_edges':{k:v.tolist() for k,v in E.items()},'source_edge_refs':spec,'junction_snaps':snaps,'operations':operations,'max_vertex_edit_mm':max_shift}

class ParamCurve:
 def __init__(self,fn,n=4097):
  self.fn=fn;self.t=np.linspace(0,1,n);self.points=fn(self.t);self.s=np.r_[0,np.cumsum(np.linalg.norm(np.diff(self.points,axis=0),axis=1))];self.length=self.s[-1];self.s/=self.length
 def __call__(self,q):return self.fn(np.interp(np.asarray(q),self.s,self.t))

def ellipse_half(a,L):
 # Length of an elliptical half with orthogonal radii |a| and depth b.
 u=np.linspace(0,np.pi,4097)
 def perimeter(b):return np.trapezoid(np.sqrt((np.linalg.norm(a)*np.sin(u))**2+(b*np.cos(u))**2),u)
 return brentq(lambda b:perimeter(b)-L,.0001,.25)

class Builder:
 def __init__(self,P,spacing=5):
  self.P=P;self.E,self.loops,self.pattern=patterns(P);self.spacing=spacing;self.seams=[];self.openings=[];self.segments={};self.targets={};self.edge_names={};self.domains={};self._targets()
 def add(self,name,p,target,process=0.,window=(.1,.7),domain=None):
  p=np.asarray(p);L=length(p);a,b=np.array(window)*L
  def proc(s):return s+process*np.clip((s-a)/(b-a),0,1)
  def inv(q):return np.interp(np.asarray(q)*(L+process),[0,a,b+process,L+process],[0,a,b,L])/L
  knots=proc(fractions(p)*L)/(L+process);q=np.unique(np.r_[knots,np.linspace(0,1,max(3,int((L+process)/self.spacing)+2)),proc(np.array([a,b]))/(L+process)])
  q=tidy_q(q)
  self.segments[name]={'flat':p,'target':target,'process':process,'window':list(window),'q':q,'inverse':inv,'domain':domain,'rest_length_mm':L,'processed_length_mm':L+process}
 def bind(self,name,a,b):
  if abs(self.segments[a]['processed_length_mm']-self.segments[b]['processed_length_mm'])>.05:raise ValueError(f'FLAT_SEAM_LENGTH {name}')
  q=tidy_q(np.r_[self.segments[a]['q'],self.segments[b]['q']]);self.segments[a]['q']=q;self.segments[b]['q']=q;self.seams.append({'name':name,'a':a,'b':b})
 def _targets(self):
  E=self.E;neck_x=.087;neck_z=1.50;drop_shoulder=.020;shoulder_len=length(E['back.shoulder.left'])/1000;sx=neck_x+math.sqrt(shoulder_len**2-drop_shoulder**2);ux=.150;zu=1.315
  self.pose={'neck_half_width_m':neck_x,'shoulder_outer_x_m':sx,'underarm_x_m':ux,'underarm_z_m':zu,'neck_z_m':neck_z,'arm_pose':'A pose, curved axis; no body/fit claim'}
  side_L=(length(E['back.side.left'])+10)/1000
  def side_curve(h):return ParamCurve(lambda q:np.c_[ux-.022*np.sin(np.pi*q)**2,np.zeros(len(q)),zu-h*q])
  h=brentq(lambda h:side_curve(h).length-side_L,.25,.36);base_side=side_curve(h);hem_z=zu-h
  neck_curves={};arm_curves={}
  for front in [True,False]:
   body='front' if front else 'back';sign=-1 if front else 1;drop=.070 if front else .025
   half_len=length(E[body+'.neck.left'])/1000
   a=np.array([neck_x,0,0]);depth=ellipse_half(np.array([neck_x,0,0]),2*half_len)
   # Replace ellipse's second radius by the combined vertical/depth radius.
   depth=math.sqrt(max(depth**2-drop**2,.0001))
   def neck(q,dep=depth,drop=drop,sign=sign):
    phi=-np.pi/2+np.pi*q;return np.c_[neck_x*np.sin(phi),sign*dep*np.cos(phi),neck_z-drop*np.cos(phi)]
   full_neck=ParamCurve(neck);neck_curves[body]=full_neck
   for side in ['left','right']:
    signx=-1 if side=='left' else 1
    S=np.array([signx*sx,0,neck_z-drop_shoulder]);U=np.array([signx*ux,0,zu]);O=(S+U)/2;A=(S-U)/2;depth_arm=ellipse_half(A,length(E[body+'.arm.'+side])/1000)
    curve=ParamCurve(lambda q,O=O,A=A,d=depth_arm,sign=sign:O+np.cos(np.pi*q)[:,None]*A+np.c_[np.zeros(len(q)),sign*d*np.sin(np.pi*q),np.zeros(len(q))]);arm_curves[body+'.'+side]=curve
    target=lambda q,sg=signx:base_side(q)*[sg,1,1]
    self.add(body+'.side.'+side,E[body+'.side.'+side],target,process=-6 if front else 10,window=(.04,.22) if front else (.24,.75))
    target=lambda q,sg=signx:np.c_[sg*(neck_x+(sx-neck_x)*q),np.zeros(len(q)),neck_z-drop_shoulder*q]
    self.add(body+'.shoulder.'+side,E[body+'.shoulder.'+side],target)
    self.add(body+'.arm.'+side,E[body+'.arm.'+side],curve)
   if front:
    # Front neck source directions: centre -> left, right -> centre.
    self.add('front.neck.left',E['front.neck.left'],lambda q,c=full_neck:c(.5*(1-q)))
    self.add('front.neck.right',E['front.neck.right'],lambda q,c=full_neck:c(1-.5*q))
   else:
    self.add('back.neck.left',E['back.neck.left'],lambda q,c=full_neck:c(.5*q))
    self.add('back.neck.right',E['back.neck.right'],lambda q,c=full_neck:c(.5+.5*q))
   signy=sign;target=lambda q,sy=signy:np.c_[-ux*np.cos(np.pi*q),sy*.12*np.sin(np.pi*q),hem_z-.012*np.sin(np.pi*q)]
   self.add(body+'.hem',E[body+'.hem'],target);self.openings.append(body+'.hem')
  for side in ['left','right']:
   for family in ['side','shoulder']:self.bind(family+'.'+side,'front.'+family+'.'+side,'back.'+family+'.'+side)
   # Actual source sleeve cap is split front/back, with 40/60 declared local ease.
   sgn=-1 if side=='left' else 1;S=np.array([sgn*sx,0,neck_z-drop_shoulder]);U=np.array([sgn*ux,0,zu]);O=(S+U)/2;A=(S-U)/2;beta0=math.atan2(abs(A[0]),A[2]);beta_end=math.radians(58)
   n=4097;t=np.linspace(0,1,n);blend=np.minimum(1,t/.35);blend=blend*blend*(3-2*blend);beta=beta0+(beta_end-beta0)*blend
   direction=np.c_[sgn*np.cos(beta),np.zeros(n),-np.sin(beta)];spine=np.vstack([np.zeros(3),np.cumsum((direction[:-1]+direction[1:])/2/(n-1),axis=0)])
   y0=np.mean([E['sleeve.side.front'][0,1],E['sleeve.side.back'][0,1]]);y1=np.mean([E['sleeve.cuff'][0,1],E['sleeve.cuff'][-1,1]])
   def width_at(v):
    y=y0+(y1-y0)*v;values=[]
    for key in ['sleeve.side.back','sleeve.side.front']:
     p=E[key];order=np.argsort(p[:,1]);values.append(np.interp(y,p[order,1],p[order,0]))
    return np.asarray(values[1])-values[0]
   def tube(u,theta,L,sgn=sgn,O=O,A=A,spine=spine,beta=beta,t=t,side=side):
    u=np.atleast_1d(u);theta=np.broadcast_to(theta,u.shape);b=np.interp(u,t,beta);C=O+L*np.column_stack([np.interp(u,t,spine[:,j]) for j in range(3)]);D=np.c_[sgn*np.sin(b),np.zeros(len(u)),np.cos(b)]
    radius=width_at(u)/1000/(2*np.pi);mix=np.minimum(1,u/.18);mix=mix*mix*(3-2*mix)
    major=(1-mix)*np.linalg.norm(A)+mix*radius
    fdepth=abs(arm_curves['front.'+side](np.array([.5]))[0,1]);bdepth=abs(arm_curves['back.'+side](np.array([.5]))[0,1]);dep=np.where(np.sin(theta)>=0,fdepth,bdepth);minor=(1-mix)*dep+mix*radius
    return C+D*(major*np.cos(theta))[:,None]+np.c_[np.zeros(len(u)),-minor*np.sin(theta),np.zeros(len(u))]
   wanted=length(E['sleeve.side.front'])/1000
   arm_L=brentq(lambda L:length(tube(t,np.pi,L))-wanted,.35,.7)
   tube_fn=lambda u,theta,tube=tube,L=arm_L:tube(u,theta,L)
   under_curve=ParamCurve(lambda q,tf=tube_fn:tf(q,np.pi))
   self.targets['tube.'+side]=tube_fn
   # u is arc parameter of the tube centre; side-edge inverse uses actual underarm arc.
   domain_side=lambda q,c=under_curve:np.interp(q,c.s,c.t)
   for half in ['front','back']:
    key='sleeve.'+side+'.cap.'+half;src='sleeve.cap.'+half;c=arm_curves[half+'.'+side];ease=length(E[src])-length(E[half+'.arm.'+side])
    self.add(key,E[src],c,process=-ease,window=(.10,.70),domain=lambda q,c=c,half=half:np.c_[np.zeros(len(q)),(1 if half=='front' else -1)*np.pi*np.interp(q,c.s,c.t)])
    self.bind('armhole.'+side+'.'+half,key,half+'.arm.'+side)
    key='sleeve.'+side+'.side.'+half;self.add(key,E['sleeve.side.'+half],under_curve,domain=lambda q,half=half,fn=domain_side:np.c_[fn(q),np.full(len(q),np.pi if half=='front' else -np.pi)])
   self.bind('underarm.'+side,'sleeve.'+side+'.side.front','sleeve.'+side+'.side.back')
   cuffname='sleeve.'+side+'.cuff';self.add(cuffname,E['sleeve.cuff'],lambda q,tf=tube_fn:tf(np.ones(len(q)),-np.pi+2*np.pi*q),domain=lambda q:np.c_[np.ones(len(q)),-np.pi+2*np.pi*q]);self.openings.append(cuffname)
   self.loops['sleeve.'+side]=[(k.replace('sleeve.','sleeve.'+side+'.'),r) for k,r in self.loops['sleeve']]
  del self.loops['sleeve']
  # Outer surface of the folded 40mm strip; hidden inner layer is not a shell face.
  P=self.P;xs=[float(P[i][0,0]) for i in [0,10,11,8,1]];yb=float(P[0][0,1]);yt=float(P[9][0,1]);self.band_bottom=yb;self.band_fold=yt
  neck_order=['back.neck.left','back.neck.right','front.neck.right','front.neck.left'];self.band_x=xs
  def neck_at(x):
   ans=np.empty((len(np.atleast_1d(x)),3));x=np.atleast_1d(x)
   for i,key in enumerate(neck_order):
    mask=(x>=xs[i]-1e-6)&(x<=xs[i+1]+1e-6);q=np.clip((x[mask]-xs[i])/(xs[i+1]-xs[i]),0,1);ans[mask]=self.segments[key]['target'](q)
   return ans
  def band(x,v):
   p=neck_at(x);rad=p.copy();rad[:,2]=0;rad/=np.linalg.norm(rad,axis=1)[:,None];width=(yt-yb)/1000;offset=-rad*(width*.9);offset[:,2]=width*math.sqrt(1-.9**2);return p+offset*np.asarray(v)[:,None]
  self.targets['band']=band
  band_loop=[]
  for i,key in enumerate(neck_order):
   bandkey='band.'+key;flat=np.array([[xs[i],yb],[xs[i+1],yb]])
   self.add(bandkey,flat,self.segments[key]['target'],process=length(E[key])-(xs[i+1]-xs[i]),window=(0,1));self.bind('neck.'+key,bandkey,key);band_loop.append((bandkey,False))
  for side,x in [('left',xs[0]),('right',xs[-1])]:self.add('band.end.'+side,np.array([[x,yb],[x,yt]]),lambda q,x=x:band(np.full(len(q),x),q))
  self.bind('band.end','band.end.left','band.end.right')
  self.add('band.fold',np.array([[xs[0],yt],[xs[-1],yt]]),lambda q:band(xs[0]+q*(xs[-1]-xs[0]),np.ones(len(q))));self.openings.append('band.fold')
  self.loops['band']=band_loop+[('band.end.right',False),('band.fold',True),('band.end.left',True)]

def enforce_boundary(points,tri,boundary_count):
 # Insert missing genuine contour segments by convex diagonal flips. This
 # precedes polygon clipping; otherwise a missing constraint creates a hole.
 def cross(a,b,c):
  u=b-a;v=c-a;return u[0]*v[1]-u[1]*v[0]
 def crossing(a,b,c,d):return cross(a,b,c)*cross(a,b,d)<-1e-12 and cross(c,d,a)*cross(c,d,b)<-1e-12
 def table():
  result={}
  for i,face in enumerate(tri):
   for a,b in zip(face,np.roll(face,-1)):result.setdefault(tuple(sorted([int(a),int(b)])),[]).append(i)
  return result
 edges=table();constraints=[tuple(sorted([i,(i+1)%boundary_count])) for i in range(boundary_count)];missing=[e for e in constraints if e not in edges]
 for a,b in missing:
  visited=set()
  for iteration in range(200):
   if (a,b) in edges:break
   options=[]
   for (c,d),faces in edges.items():
    if len(faces)!=2 or {a,b}&{c,d} or not crossing(points[a],points[b],points[c],points[d]):continue
    i,j=faces;x=next(int(v) for v in tri[i] if v not in [c,d]);y=next(int(v) for v in tri[j] if v not in [c,d]);diagonal=tuple(sorted([x,y]))
    if diagonal in visited or not crossing(points[c],points[d],points[x],points[y]):continue
    options.append((crossing(points[a],points[b],points[x],points[y]),i,j,c,d,x,y))
   if not options:break
   _,i,j,c,d,x,y=min(options);visited.add(tuple(sorted([c,d])));tri[i]=[x,y,c];tri[j]=[y,x,d];edges=table()
 return tri

def triangulate(boundary,spacing):
 lo,hi=boundary.min(0),boundary.max(0);xx,yy=np.meshgrid(np.arange(lo[0],hi[0],spacing),np.arange(lo[1],hi[1],spacing));g=np.c_[xx.ravel(),yy.ravel()];g=g[inside(g,boundary)];near=np.zeros(len(g),bool)
 for a,b in zip(boundary,np.roll(boundary,-1,axis=0)):
  v=b-a;delta=g-a;u=(delta@v)/(v@v);distance=np.abs(delta[:,0]*v[1]-delta[:,1]*v[0])/np.linalg.norm(v);near|=(u>=0)&(u<=1)&(distance<1e-4)
 g=g[~near]
 points=np.vstack([boundary,g]);tri=Delaunay(points).simplices
 tri=enforce_boundary(points,tri,len(boundary))
 keep=inside(points[tri].mean(1),boundary)
 for w in [(.499,.499,.002),(.499,.002,.499),(.002,.499,.499)]:keep &= inside(np.einsum('nkd,k->nd',points[tri],w),boundary)
 tri=tri[keep]
 def orient(t):
  e=points[t[:,1]]-points[t[:,0]];g=points[t[:,2]]-points[t[:,0]];area=e[:,0]*g[:,1]-e[:,1]*g[:,0];t=t[np.abs(area)>1e-5];area=area[np.abs(area)>1e-5];t[area<0]=t[area<0,::-1];return t
 tri=orient(tri);nb=len(boundary);wanted={tuple(sorted([i,(i+1)%nb])) for i in range(nb)}
 # Qhull may omit collinear boundary Steiner points. Split the incident face
 # along every such actual source boundary point rather than leaving T junctions.
 for iteration in range(6):
  edges=np.sort(np.concatenate([tri[:,[0,1]],tri[:,[1,2]],tri[:,[2,0]]]),axis=1);unique,counts=np.unique(edges,axis=0,return_counts=True);actual={tuple(e) for e in unique[counts==1]}
  if actual==wanted:break
  changed=False
  for a,b in actual-wanted:
   if max(a,b)>=nb:continue
   chains=[list(range(a,b+1)),list(range(b,nb))+list(range(0,a+1))] if a<b else []
   for chain in chains:
    if len(chain)<3:continue
    aa,bb=points[chain[0]],points[chain[-1]];direction=bb-aa;delta=points[chain]-aa;cross=direction[0]*delta[:,1]-direction[1]*delta[:,0]
    if np.max(np.abs(cross))/np.linalg.norm(direction)>1e-5:continue
    incident=np.flatnonzero(np.any(tri==a,axis=1)&np.any(tri==b,axis=1))
    if len(incident)!=1:continue
    j=incident[0];c=next(x for x in tri[j] if x not in [a,b]);new=np.array([[x,y,c] for x,y in zip(chain[:-1],chain[1:])]);tri=np.vstack([np.delete(tri,j,axis=0),orient(new)]);changed=True;break
  if not changed:break
 edges=np.sort(np.concatenate([tri[:,[0,1]],tri[:,[1,2]],tri[:,[2,0]]]),axis=1);unique,counts=np.unique(edges,axis=0,return_counts=True);actual={tuple(e) for e in unique[counts==1]}
 if actual!=wanted:
  raise ValueError(f'BOUNDARY_CONFORMITY missing {len(wanted-actual)} extra {len(actual-wanted)}')
 return points,tri,unique

def harmonic(points,tri,edges,values):
 n=len(points);nb=len(values);a,b=edges.T;rows=np.r_[a,b];cols=np.r_[b,a];adj=coo_matrix((np.ones(len(rows)),(rows,cols)),shape=(n,n)).tocsr();degree=np.asarray(adj.sum(1)).ravel();ii=np.arange(nb,n);system=coo_matrix((degree[ii],(np.arange(len(ii)),np.arange(len(ii)))),shape=(len(ii),len(ii))).tocsr()-adj[ii][:,ii]
 result=np.empty((n,values.shape[1]));result[:nb]=values;result[nb:]=spsolve(system,adj[ii,:nb]@values)
 return result,adj

def build(P,spacing=5):
 B=Builder(P,spacing);segments=B.segments;patches={};allv=[];allf=[];offset=0;manifest={'pattern':B.pattern,'pose':B.pose,'seams':B.seams,'openings':B.openings,'patches':{},'segments':{}}
 for name,loop in B.loops.items():
  boundary=[];targets=[];domains=[];ids={}
  for key,rev in loop:
   s=segments[key];q=s['q'];flat=interp(s['flat'],s['inverse'](q));target=s['target'](q);domain=s['domain'](q) if s['domain'] else None
   if rev:flat=flat[::-1];target=target[::-1];domain=domain[::-1] if domain is not None else None
   start=len(boundary);local=np.r_[np.arange(start,start+len(q)-1),start+len(q)-1];ids[key]=local[::-1] if rev else local
   boundary.extend(flat[:-1]);targets.extend(target[:-1])
   if domain is not None:domains.extend(domain[:-1])
  boundary=np.array(boundary);nb=len(boundary)
  for key in ids:ids[key]%=nb
  
  try:points,tri,edges=triangulate(boundary,spacing)
  except ValueError as exc:raise ValueError(name+': '+str(exc)) from exc
  if name in ['front','back']:
   v,adj=harmonic(points,tri,edges,np.array(targets));edge_len=np.linalg.norm(points[edges[:,0]]-points[edges[:,1]],axis=1);a,b=edges.T;graph=coo_matrix((np.r_[edge_len,edge_len],(np.r_[a,b],np.r_[b,a])),shape=(len(points),len(points))).tocsr();dist=dijkstra(graph,indices=np.arange(nb),min_only=True,directed=False)
   depth=np.interp(v[:,2],[1,1.17,1.32,1.48],[.08,.065,.090,.025]);bulge=depth*(1-np.exp(-dist/35));v[:,1]+=(-1 if name=='front' else 1)*bulge;v[:nb]=targets
  elif name.startswith('sleeve.'):
   domain,_=harmonic(points,tri,edges,np.array(domains));v=B.targets['tube.'+name.split('.')[-1]](domain[:,0],domain[:,1]);v[:nb]=targets
  else:v=B.targets['band'](points[:,0],(points[:,1]-B.band_bottom)/(B.band_fold-B.band_bottom));v[:nb]=targets
  patches[name]={'vertices':v,'faces':tri+offset,'offset':offset,'segments':{k:(q+offset).tolist() for k,q in ids.items()}}
  manifest['patches'][name]={'face_start':len(allf),'face_count':len(tri),'vertex_offset_unwelded':offset,'flat_points':points,'local_faces':tri.copy(),'boundary_points':points[:nb].tolist(),'boundary_count':nb}
  allv.extend(v);allf.extend(tri+offset);offset+=len(v)
  for key,local in ids.items():
   s=segments[key];manifest['segments'][key]={'patch':name,'vertices_unwelded':(local+patches[name]['offset']).tolist(),'local_vertices':local.tolist(),'flat_points':interp(s['flat'],s['inverse'](s['q'])).tolist(),'parameter':s['q'].tolist(),'rest_length_mm':s['rest_length_mm'],'process_mm':s['process'],'process_window':s['window']}
 allv=np.array(allv);allf=np.array(allf,int);parents=np.arange(len(allv))
 def root(i):
  while parents[i]!=i:parents[i]=parents[parents[i]];i=parents[i]
  return i
 for seam in B.seams:
  aa=manifest['segments'][seam['a']]['vertices_unwelded'];bb=manifest['segments'][seam['b']]['vertices_unwelded'];assert len(aa)==len(bb)
  for a,b in zip(aa,bb):parents[root(b)]=root(a)
 roots=np.array([root(i) for i in range(len(allv))]);unique,index=np.unique(roots,return_inverse=True);v=allv[unique];f=index[allf]
 # Orient the welded surface by actual edge adjacency, without dropping faces.
 links={}
 for i,face in enumerate(f):
  for a,b in zip(face,np.roll(face,-1)):links.setdefault(tuple(sorted([int(a),int(b)])),[]).append((i,1 if a<b else -1))
 graph=[[] for _ in f]
 for incidences in links.values():
  if len(incidences)==2:
   (a,sa),(b,sb)=incidences;graph[a].append((b,-sa*sb));graph[b].append((a,-sa*sb))
 orientation=np.zeros(len(f),int);orientation[0]=1;stack=[0]
 while stack:
  a=stack.pop()
  for b,factor in graph[a]:
   want=orientation[a]*factor
   if orientation[b] and orientation[b]!=want:raise ValueError('NONORIENTABLE')
   if not orientation[b]:orientation[b]=want;stack.append(b)
 if np.any(orientation==0):raise ValueError('DISCONNECTED_AFTER_SEWING')
 f[orientation<0]=f[orientation<0,::-1]
 nf=manifest['patches']['front']['face_count'];norm=np.cross(v[f[:nf,1]]-v[f[:nf,0]],v[f[:nf,2]]-v[f[:nf,0]])
 if norm[:,1].sum()>0:f=f[:,::-1]
 for key,s in manifest['segments'].items():s['vertices']=index[s.pop('vertices_unwelded')].tolist()
 for value in manifest['patches'].values():
  off=value.pop('vertex_offset_unwelded');value['global_vertices']=index[np.arange(off,off+len(value['flat_points']))]
  local=value['local_faces'];start=value['face_start'];count=value['face_count'];reversed_faces=orientation[start:start+count]<0
  local[reversed_faces]=local[reversed_faces,::-1]
  if norm[:,1].sum()>0:local[:]=local[:,::-1]
 return v,f,manifest

