#!/usr/bin/env python3
"""Refine an anatomical body's camera/torso/hip pose against a photo envelope.

Actual FK/LBS only. The reference clothing silhouette is a containment constraint,
not a naked-body measurement. Fixed dimensions prevent shrink-to-pass fitting.
Case-specific pixels/regions are supplied as input files, never embedded here.
"""
import argparse,copy,json,sys,time
from pathlib import Path
import numpy as np,cv2
from scipy.optimize import least_squares
from scipy.ndimage import map_coordinates
from scipy.spatial.transform import Rotation
from runtime import Runtime,sha

def put(p,x):
 Path(p).write_text(json.dumps(x,indent=2,default=lambda z:z.tolist() if isinstance(z,np.ndarray) else float(z))+'\n')
def project(p,c,w,h):
 q=np.asarray(p)@Rotation.from_euler('YXZ',c[3:],degrees=True).as_matrix().T
 return np.c_[w/2+(q[:,0]-c[1])*c[0],h/2-(q[:,1]-c[2])*c[0]]
def metrics(r,e,c,ref,regions,protocol=None):
 h,w=ref.shape;uv=project(e['posed'],c,w,h);m=np.zeros(ref.shape,'uint8')
 for face in r.faces:cv2.fillConvexPoly(m,np.rint(uv[face]).astype('int32'),255)
 body=m>0;ct=body&~cv2.erode(body.astype('uint8'),np.ones((3,3),'uint8')).astype(bool);dt=cv2.distanceTransform((~ref).astype('uint8'),cv2.DIST_L2,5)
 result={'iou':float((body&ref).sum()/max((body|ref).sum(),1)),'outside':float((body&~ref).sum()/max(body.sum(),1)),'regions':{}}
 for name,(x0,y0,x1,y1) in regions.items():
  roi=np.zeros(ref.shape,bool);roi[y0:y1,x0:x1]=True;bc=body&roi;cc=ct&roi
  result['regions'][name]={'outside_fraction':float((bc&~ref).sum()/max(bc.sum(),1)),'exterior_contour_p95_px':float(np.percentile(dt[cc],95)) if cc.any() else None,'body_pixels':int(bc.sum())}
 result['scanlines']=[]
 for y in (protocol or {}).get('scanlines',[]):
  actual=np.flatnonzero(body[y]);target=np.flatnonzero(ref[y])
  if not len(actual) or not len(target):result['scanlines'].append({'y':y,'center_error_px':None,'width_ratio':None});continue
  result['scanlines'].append({'y':y,'center_error_px':float(abs((actual[0]+actual[-1]-target[0]-target[-1])/2)),'width_ratio':float((actual[-1]-actual[0])/max(target[-1]-target[0],1))})
 return result,m

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--state',type=Path,required=True);ap.add_argument('--camera',type=Path,required=True);ap.add_argument('--mask',type=Path,required=True);ap.add_argument('--photo',type=Path,required=True);ap.add_argument('--acceptance',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--steps',type=int,default=90);ap.add_argument('--camera-fit',action='store_true');ap.add_argument('--standing-prior',action='store_true');a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
 source=json.loads(a.state.read_text());c0=np.array(json.loads(a.camera.read_text())['final']);ref=cv2.imread(str(a.mask),0)>0;photo=cv2.imread(str(a.photo));h,w=ref.shape;protocol=json.loads(a.acceptance.read_text());regions=protocol['regions'];r=Runtime()
 try:
  if source.get('asset')!=sha(r.asset) or source.get('units')!='cm':raise ValueError('State must reference exact current centimetre asset')
  if photo is None or photo.shape[:2]!=ref.shape or not ref.any():raise ValueError('Photo and nonempty original mask must share native dimensions')
  if not np.isfinite(c0).all() or c0.shape!=(6,) or c0[0]<=0:raise ValueError('Camera parameters must be finite with positive pixel scale')
  e0=r.evaluate(source);rest=e0['shape']['rest'];body=r.ids;dt=cv2.distanceTransform((~ref).astype('uint8'),cv2.DIST_L2,5)
  # Heuristic anatomical sampling domains expressed relative to a170cm
  # template, not observed person dimensions. Round only the sampling-domain
  # scale to0.001cm to remove calibration solver noise; geometry is unchanged.
  neutral_height_cm=float(np.ptp(rest[body,1]));height_scale=round(neutral_height_cm,3)/170.0
  if not np.isfinite(height_scale) or height_scale<=0:raise ValueError('Neutral height must be positive')
  ids=body[(abs(rest[body,0])<30*height_scale)&(rest[body,1]>65*height_scale)&(rest[body,1]<142*height_scale)][::6]
  rings=[body[(abs(rest[body,0])<29*height_scale)&(abs(rest[body,1]-y)<.7*height_scale)] for y in np.arange(70,111,5)*height_scale]
  rows=[np.flatnonzero(row) for row in ref];left=np.array([q[0] if len(q) else 0 for q in rows]);right=np.array([q[-1] if len(q) else w-1 for q in rows])
  anchors=[r.index[n] for n in ['eye.L','eye.R','upperarm01.L','upperarm01.R','lowerarm01.L','lowerarm01.R','wrist.L','wrist.R']]
  anchor0=project(e0['joints'][anchors],c0,w,h)
  keys=[(n,k) for n in ['root','spine05','spine03','spine01','upperleg01.L','upperleg01.R'] for k in range(3)]
  if a.standing_prior:keys += [(n,k) for n in ['foot.L','foot.R'] for k in range(3)]
  soles=[body[(rest[body,0]*sign>0)&(rest[body,1]<1.0*height_scale)] for sign in [1,-1]]
  p0=np.array([source['poseDegrees'][n][k] for n,k in keys]);lo=[];hi=[]
  for (n,k),v in zip(keys,p0):
   d=15 if n.startswith('upperleg') else 8 if n=='root' else 7
   lo.append(max(-30,v-d));hi.append(min(30,v+d))
  def state(p):
   s=copy.deepcopy(source)
   for (n,k),v in zip(keys,p):s['poseDegrees'][n][k]=float(v)
   return s
  def residual(v):
   p=v[:len(keys)];c=v[len(keys):] if a.camera_fit else c0;e=r.evaluate(state(p));xy=project(e['posed'][ids],c,w,h)
   exterior=map_coordinates(dt,[xy[:,1],xy[:,0]],order=1,mode='nearest')
   rr=list(np.maximum(0,exterior-1)/4/np.sqrt(len(ids))*24)
   # Keep real visible upper-body anchors while changing pelvic/leg articulation.
   rr.extend(((project(e['joints'][anchors],c,w,h)-anchor0)/5).ravel())
   for ring in rings:
    xy=project(e['posed'][ring],c,w,h);yy=xy[:,1].mean();l=np.interp(yy,np.arange(h),left);ri=np.interp(yy,np.arange(h),right);actual=np.ptp(xy[:,0]);target=ri-l
    rr.extend([((xy[:,0].min()+xy[:,0].max())/2-(l+ri)/2)/10,max(0,.60*target-actual)/6,max(0,actual-1.02*target)/6])
   if a.standing_prior:
    for sole in soles:
     # Both unobserved feet use a disclosed flat-support prior, not image truth.
     yy=e['posed'][sole,1];rr.extend([yy.min()/.6,float(np.std(yy))/1.0])
   rr.extend(((p-p0)/np.array([16 if n.startswith('upperleg') else 20 for n,k in keys])).tolist())
   if a.camera_fit:rr.extend(((c-c0)/np.array([.3,1,1,3,2,2])).tolist())
   return np.array(rr)
  x0=np.r_[p0,c0] if a.camera_fit else p0
  if a.camera_fit:lo+=list(c0-np.array([.8,3,3,5,4,4]));hi+=list(c0+np.array([.8,3,3,5,4,4]))
  initial,mask0=metrics(r,e0,c0,ref,regions,protocol);put(a.out/'initial-metrics.json',initial);cv2.imwrite(str(a.out/'initial-mask.png'),mask0)
  t=time.time();fit=least_squares(residual,x0,bounds=(lo,hi),max_nfev=a.steps,diff_step=.001,ftol=1e-6,xtol=1e-6)
  p=np.round(fit.x[:len(keys)],1);c=fit.x[len(keys):] if a.camera_fit else c0;s=r.canonical_state(state(p));e=r.evaluate(s);result,mask=metrics(r,e,c,ref,regions,protocol)
  put(a.out/'final-state.json',s);R=Rotation.from_euler('YXZ',c[3:],degrees=True).as_matrix();M=np.vstack((np.r_[c[0]*R[0],w/2-c[0]*c[1]],np.r_[-c[0]*R[1],h/2+c[0]*c[2]],[0,0,0,1]));put(a.out/'camera.json',{'final':c,'width':w,'height':h,'world_to_pixel_homogeneous':M});r.write_obj(a.out/'neutral.obj',e['shape']['rest']);r.write_obj(a.out/'posed.obj',e['posed']);put(a.out/'metrics.json',result)
  put(a.out/'optimization.json',{'seconds':time.time()-t,'nfev':fit.nfev,'initial_loss':float(np.sum(residual(x0)**2)),'final_loss':float(np.sum(fit.fun**2)),'keys':keys,'initial':x0,'final':fit.x,'dimensions_fixed':True,'sampling_domain':{'basis':'heuristic anatomical regions normalized from170cm template; not observed body measurements','neutral_height_cm':neutral_height_cm,'height_scale':height_scale,'height_rounding_cm':.001,'body_sample_count':len(ids),'ring_counts':[len(z) for z in rings],'sole_counts':[len(z) for z in soles]},'source_sha256':{str(z):sha(z) for z in [a.state,a.camera,a.mask,a.photo,a.acceptance,Path(__file__)]}})
  cv2.imwrite(str(a.out/'final-mask.png'),mask);over=photo.astype(float)
  for zone,color in [((mask>0)&ref,[70,200,70]),((mask>0)&~ref,[220,200,60]),((mask==0)&ref,[190,60,210])]:over[zone]=.84*over[zone]+.16*np.array(color)
  over=over.astype('uint8');cv2.drawContours(over,cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)[0],-1,(255,200,0),2);cv2.imwrite(str(a.out/'overlay.png'),over)
  camera=dict(width=600,height=900,depth_range_cm=[-100,100],views={v:dict(axis=axis,px_per_cm=4.8,center_cm=[0,85]) for v,axis in [('front','front'),('side','side'),('back','back')]});r.save(s,camera,a.out/'views')
  print(json.dumps({'initial':initial,'final':result,'seconds':time.time()-t}),flush=True)
 finally:r.close()
if __name__=='__main__':main()
