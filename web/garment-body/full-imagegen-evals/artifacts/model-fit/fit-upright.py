#!/usr/bin/env python3
"""Actual calibrated MakeHuman FK/LBS fitting to immutable source + illustrative cues."""
import sys,json,copy,time,hashlib,argparse,os
from pathlib import Path
import numpy as np,cv2
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
from scipy.ndimage import map_coordinates
HERE=Path(__file__).resolve().parent; ROOT=next(p for p in HERE.parents if (p/'web/human-studio/assets/human.json').exists()); BASE=HERE; FIX=ROOT/'tools/human_fit/pose_guided'
sys.path.insert(0,str(FIX));from runtime import Runtime,sha
import render_mesh

def put(path,obj):Path(path).write_text(json.dumps(obj,indent=2,default=lambda x:x.tolist() if isinstance(x,np.ndarray) else x.item())+'\n')
def proj(p,c):
 q=np.asarray(p)@Rotation.from_euler('YXZ',c[3:],degrees=True).as_matrix().T
 return np.c_[500+(q[:,0]-c[1])*c[0],638-(q[:,1]-c[2])*c[0]]
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--steps',type=int,default=90);ap.add_argument('--resume');ap.add_argument('--frontal',action='store_true');ap.add_argument('--handflip',action='store_true');ap.add_argument('--handonly',action='store_true');ap.add_argument('--ik-length',action='store_true');ap.add_argument('--label',default='round-1');a=ap.parse_args();out=BASE/'iterations'/a.label;out.mkdir(parents=True,exist_ok=True)
 r=Runtime()
 try:
  baseline=json.load(open(BASE/'baseline/final-state.json'));bc=np.array(json.load(open(BASE/'baseline/camera.json'))['final']);source=copy.deepcopy(baseline);dims=copy.deepcopy(source['dimensions'])
  cue=json.load(open(BASE/'targets/pose-targets.json'));targets={p['id']:p for p in cue['points']};photo=cv2.imread(str(BASE/'reference/original-product.jpg'));ref=cv2.imread(str(BASE/'reference/reference-mask.png'),0);dt=cv2.distanceTransform((ref==0).astype('uint8'),cv2.DIST_L2,5)
  rest=r.shape(dims)['rest'];body=r.ids
  # Fixed actual mesh vertex IDs selected in neutral cm space; they deform with the skin.
  # Surface proxy heights are uncertain anatomical hypotheses, never measured joints.
  specs={'neckline_center':(0,141,8),'torso_midline':(0,123,12),'waist_midline':(0,105,10),'waist_image_left':(-12,105,6),'waist_image_right':(12,105,6),'shoulder_image_left':(-20,139,4),'shoulder_image_right':(20,139,4),'elbow_image_left':(-38,116,4),'elbow_image_right':(38,116,4)}
  surface={k:int(body[np.argmin(np.sum((rest[body]-xyz)**2,axis=1))]) for k,xyz in specs.items()}
  if a.ik_length:
   surface.pop('elbow_image_left');surface.pop('elbow_image_right')
  mapping={'eye_image_left':'eye.R','eye_image_right':'eye.L','shoulder_image_left':'upperarm01.R','shoulder_image_right':'upperarm01.L','elbow_image_left':'lowerarm01.R','elbow_image_right':'lowerarm01.L','wrist_image_left':'wrist.R','wrist_image_right':'wrist.L','hand_left_palm':'finger3-1.R','hand_right_palm':'finger3-1.L'}
  mapping={k:v for k,v in mapping.items() if k not in surface}
  ids=list(mapping)+['nose']+list(surface)
  # Lower uncertain garment marker weights, face/wrist strong; body-center cues explicitly present.
  scales={'eye_image_left':7,'eye_image_right':7,'nose':7,'shoulder_image_left':20,'shoulder_image_right':20,'elbow_image_left':15,'elbow_image_right':15,'wrist_image_left':8,'wrist_image_right':8,'neckline_center':22,'torso_midline':20,'waist_midline':15,'waist_image_left':23,'waist_image_right':23,'hand_left_palm':6,'hand_right_palm':6}
  if a.ik_length:scales['elbow_image_left']=5;scales['elbow_image_right']=7;scales['wrist_image_left']=5;scales['wrist_image_right']=5;scales['hand_left_palm']=18;scales['hand_right_palm']=18
  target=np.array([targets[k]['raw_xy'] for k in ids]);sigma=np.array([scales[k] for k in ids])
  keys=[(n,i) for n in ['root','spine05','spine03','spine01','neck01','head','shoulder01.L','shoulder01.R','upperarm01.L','upperarm01.R','lowerarm01.L','lowerarm01.R','wrist.L','wrist.R'] for i in range(3)]
  keys += [(f'finger{digit}-{seg}.{side}',i) for side in ['L','R'] for digit in [1,2] for seg in [1,2,3] for i in range(3)]
  if a.handonly:keys=[(n,i) for n,i in keys if n.startswith(('lowerarm','wrist','finger')) or n.startswith('upperarm')]
  if a.ik_length:keys=[(n,i) for n,i in keys if not n.startswith('finger')]
  p0=np.array([source['poseDegrees'][n][i] for n,i in keys]);p=p0.copy();c=bc.copy()
  if a.resume:
   old=Path(a.resume);source=json.load(open(old/'final-state.json'));dims=source['dimensions'];p=np.array([source['poseDegrees'][n][i] for n,i in keys]);c=np.array(json.load(open(old/'camera.json'))['final'])
  if a.ik_length:dims['upperArmLength']=28.;dims['forearmLength']=25.
  if a.handflip:p[keys.index(('lowerarm01.L',1))]=110
  if a.frontal:c=np.array([13.5,8,121,-12,0,-4.])
  def state(pp):
   s=copy.deepcopy(source);s['dimensions']=dims
   for (n,i),v in zip(keys,pp):s['poseDegrees'][n][i]=float(v)
   for side in ['L','R']:
    for digit in [3,4,5]:
     for seg,angle in [(1,75),(2,90),(3,65)]:s['poseDegrees'][f'finger{digit}-{seg}.{side}'][0]=angle
   return s
  def observed(e):return np.array([e['joints'][r.index[mapping[k]]] if k in mapping else e['posed'][201 if k=='nose' else surface[k]] for k in ids])
  # Envelope samples from actual torso/hip vertices: allfront/back contribute 2D containment, no scale shrinking.
  hiprings=[body[abs(rest[body,1]-height)<.7] for height in [100,95,90,85,80]]
  rows=[np.flatnonzero(row>0) for row in ref]
  ref_left=np.array([z[0] if len(z) else 0 for z in rows]);ref_right=np.array([z[-1] if len(z) else 999 for z in rows])
  handids={side:body[(np.isin(r.skin,[i for i,n in enumerate(r.names) if n.endswith('.'+side) and n.startswith(('finger','wrist'))])*r.weight).sum(1)[body]>.5] for side in ['L','R']}
  torsofront=body[(abs(rest[body,0])<22)&(rest[body,1]>95)&(rest[body,1]<140)&(rest[body,2]>0)]
  sample=body[(rest[body,1]>79)&(rest[body,1]<145)][::20]
  def residual(v,pp=None):
   pp=v[:-6] if pp is None else pp;cc=v[-6:];e=r.evaluate(state(pp));uv=proj(observed(e),cc);rr=list(((uv-target)/sigma[:,None]).ravel())
   q=proj(e['posed'][sample],cc);dist=map_coordinates(dt,[q[:,1],q[:,0]],order=1,mode='nearest');rr.extend((np.maximum(0,dist-3)/16/np.sqrt(len(sample))*40).tolist())
   j=e['joints'];tor=e['posed'][surface['torso_midline']];waist=e['posed'][surface['waist_midline']]
   for side in ['L','R']:
    w=j[r.index['wrist.'+side]];el=j[r.index['lowerarm01.'+side]];rr.extend([max(0,waist[2]+2-w[2])/3,(el[2]-3)/12]);rr.extend([max(0,w[2]-waist[2]-16)/6])
   for ring in hiprings:
    ringuv=proj(e['posed'][ring],cc);yy=float(ringuv[:,1].mean());left=float(np.interp(yy,np.arange(1276),ref_left));right=float(np.interp(yy,np.arange(1276),ref_right));center=(ringuv[:,0].min()+ringuv[:,0].max())/2;rr.append((center-(left+right)/2)/9)
   frontz=np.percentile(e['posed'][torsofront,2],95)
   for side in ['L','R']:
    handv=e['posed'][handids[side]];tv=e['posed'][torsofront];select=(tv[:,1]>handv[:,1].min()-1)&(tv[:,1]<handv[:,1].max()+1);fz=tv[select,2].max() if select.any() else frontz;rr.append(max(0,fz+.8-handv[:,2].min())/.3)
   for side in ['L','R']:
    for bone in ['wrist.','finger3-1.','finger3-2.','finger3-3.']:
     rr.append(max(0,frontz+2-j[r.index[bone+side],2])/1.5)
   pinches=[]
   for side,pinchxy in [('R',[275,780]),('L',[305,790])]:
    tips=[]
    for digit in [1,2]:
     b=r.bones[r.index[f'finger{digit}-3.{side}']];tips.append(e['posed'][r.data['joints'][b['tail']]].mean(0))
    pinches.append(np.mean(tips,axis=0))
    rr.extend(((tips[0]-tips[1])/(5 if a.ik_length else 1.5)).tolist());rr.extend(((proj(np.array(tips),cc).mean(0)-pinchxy)/(25 if a.ik_length else 7)).tolist())
    a1=j[r.index['finger2-1.'+side]]-j[r.index['wrist.'+side]];b1=j[r.index['finger5-1.'+side]]-j[r.index['wrist.'+side]];normal=np.cross(a1,b1);normal/=max(np.linalg.norm(normal),1e-6);desired=np.array([0,0,-1 if side=='L' else 1]);rr.extend(((normal-desired)/.35).tolist())
   rr.append(max(0,np.linalg.norm(pinches[0]-pinches[1])-7)/(4 if a.ik_length else 1.2))
   wl=j[r.index['wrist.L']];wr=j[r.index['wrist.R']];rr.extend([(wl[2]-wr[2])/4,max(0,np.linalg.norm(wl-wr)-28)/2])
   pelvis=j[r.index['root']];neck=j[r.index['neck01']]
   rr.extend([max(0,abs(neck[2]-pelvis[2])-8)/1.2,max(0,abs(neck[0]-pelvis[0])-15)/3])
   # Smooth distributed torso bend, realistic hinge, camera orientation regularization.
   for k,(n,i) in enumerate(keys):
    scale=18 if n.startswith('spine') else 30 if n.startswith(('neck','shoulder')) else 100
    rr.append(pp[k]/scale*.4)
   rr.extend([(cc[3]+10)/30*.5,cc[4]/15*.6,cc[5]/15*.2,(cc[0]-13.5)/2*.4])
   return np.array(rr)
  lo=[];hi=[]
  for n,i in keys:
   l,h=(-120,120)
   if n.startswith('spine'):l,h=(-8,8)
   if n=='root':l,h=((-2,2) if i<2 else (-22,22))
   if n.startswith('neck'):l,h=(-25,25)
   if n.startswith('shoulder'):l,h=(-12,12)
   if n.startswith('lowerarm') and i==0:l,h=(-5,135)
   if a.handonly and n.startswith('upperarm'):l,h=(source['poseDegrees'][n][i]-20,source['poseDegrees'][n][i]+20)
   if n.startswith('wrist'):l,h=((-90,90) if i==1 else (-40,40))
   if n.startswith('finger1'):l,h=((0,100) if i==0 else (-55,55))
   if n.startswith('finger2'):l,h=((0,110) if i==0 else (-12,12))
   lo.append(l);hi.append(h)
  clo=[11,-40,100,-35,-10,-18];chi=[16,40,145,35,10,18]
  if not a.frontal:clo=[10,-40,100,-65,-22,-18];chi=[17,40,145,55,22,18]
  if a.handonly:clo=(c-1e-8).tolist();chi=(c+1e-8).tolist()
  p=np.clip(p,np.array(lo)+1e-5,np.array(hi)-1e-5);c=np.clip(c,np.array(clo)+1e-12,np.array(chi)-1e-12);bounds=(np.r_[lo,clo],np.r_[hi,chi])
  history=[]
  def report(label,pp,cc):
   e=r.evaluate(state(pp));uv=proj(observed(e),cc);errors=np.linalg.norm(uv-target,axis=1);put(out/(label+'-cue-residual.json'),dict(camera=cc,points=[dict(id=k,target=target[i],projected=uv[i],residual_px=errors[i]) for i,k in enumerate(ids)]));m=np.zeros(ref.shape,'uint8');xy=proj(e['posed'],cc)
   for f in r.faces:cv2.fillConvexPoly(m,np.rint(xy[f]).astype('int32'),255)
   canvas=photo.copy();colored=photo.copy();colored[m>0]=colored[m>0]*.85+np.array([240,200,50])*.15;canvas=colored.astype('uint8');cv2.drawContours(canvas,cv2.findContours(m,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)[0],-1,(250,180,0),2);cv2.drawContours(canvas,cv2.findContours(ref,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)[0],-1,(40,150,240),1)
   for k,tar,pred in zip(ids,target,uv):
    t=tuple(np.rint(tar).astype(int));z=tuple(np.rint(pred).astype(int));cv2.arrowedLine(canvas,z,t,(50,30,240),2,tipLength=.15);cv2.circle(canvas,t,5,(30,220,40),2);cv2.circle(canvas,z,3,(250,180,0),-1)
   cv2.imwrite(str(out/(label+'-overlay.png')),canvas);cv2.imwrite(str(out/(label+'-mask.png')),m)
   return dict(cue_mean_px=float(errors.mean()),cue_worst_px=float(errors.max()),outside_fraction=float(((m>0)&(ref==0)).sum()/max((m>0).sum(),1)))
  put(out/'surface-proxies.json',dict(definition='Fixed nearest actual neutral body vertices; clothing-surface cue approximations, uncertainty reflected in loss',vertices={k:dict(vertex=v,neutral_cm=rest[v]) for k,v in surface.items()}))
  put(out/'initial-state.json',r.canonical_state(state(p))); put(out/'initial-camera.json',dict(final=c.tolist(),width=1000,height=1276)); print('baseline',report('baseline',p,c),flush=True)
  t=time.time();camfit=least_squares(lambda cc:residual(cc,p),c,bounds=(clo,chi),diff_step=.002,max_nfev=65);c=camfit.x;history.append(dict(stage='camera-only',camera=c,loss=float(np.sum(camfit.fun**2)),seconds=time.time()-t));print('camonly',report('camera-only',p,c),flush=True)
  t=time.time();fit=least_squares(residual,np.r_[p,c],bounds=bounds,diff_step=.003,max_nfev=a.steps,ftol=2e-5,xtol=2e-5);p=fit.x[:-6];c=fit.x[-6:];history.append(dict(stage='actual-pose-and-camera',nfev=fit.nfev,loss=float(np.sum(fit.fun**2)),seconds=time.time()-t,parameters=fit.x,keys=keys));print('final',report('final',p,c),flush=True)
  # Coordinate search genuine cm morphs/actual bone lengths, preserving bust/waist/hip priors.
  for cycle in range(0 if a.handflip or a.handonly else 1):
   trials=[]
   for key,step,low,high in [('shoulders',.6,35.5,38.5),('upperArmLength',.6,27.5,31),('forearmLength',.5,21.5,25)]:
    orig=dims[key];opts=[]
    for val in sorted(set([orig,round(max(low,orig-step),1),round(min(high,orig+step),1)])):
     dims[key]=val;loss=float(np.sum(residual(np.r_[p,c])**2)+.1*((val-baseline['dimensions'][key])/1.5)**2);opts.append((loss,val))
    dims[key]=min(opts)[1];trials.append(dict(key=key,candidates=opts,chosen=dims[key]))
   fit=least_squares(residual,np.r_[p,c],bounds=bounds,diff_step=.003,max_nfev=25,ftol=2e-5,xtol=2e-5);p=fit.x[:-6];c=fit.x[-6:];history.append(dict(stage='cm-bone-pose-camera',cycle=cycle,trials=trials,loss=float(np.sum(fit.fun**2)),dimensions=copy.deepcopy(dims)))
   print('cmcycle',cycle,dims,report('cm-'+str(cycle),p,c),flush=True)
  report('final',np.round(p,1),c)
  final=r.canonical_state(state(np.round(p,1)));final['limitations']=['Generic M170 assumed scale; no true person cm recovery from this one photo.','Image Gen cues are illustrative surface hypotheses, not detector truth.','Hidden side/back and depth are regularized hypotheses; no cloth physics/contact validation.'];put(out/'final-state.json',final);R=Rotation.from_euler('YXZ',c[3:],degrees=True).as_matrix();M=np.vstack((np.r_[c[0]*R[0],500-c[0]*c[1]],np.r_[-c[0]*R[1],638+c[0]*c[2]],[0,0,0,1]));put(out/'camera.json',dict(final=c,width=1000,height=1276,rotation_order='YXZ degrees',world_to_pixel_homogeneous=M));put(out/'history.json',history)
  e=r.evaluate(final);r.write_obj(out/'neutral.obj',e['shape']['rest']);r.write_obj(out/'posed.obj',e['posed']);camera=dict(width=600,height=900,depth_range_cm=[-100,100],views={v:dict(axis=axis,px_per_cm=4.8,center_cm=[0,85]) for v,axis in [('front','front'),('side','side'),('back','back'),('pose','front'),('depth','front')]});r.save(final,camera,out/'views');R=Rotation.from_euler('YXZ',c[3:],degrees=True).as_matrix();photo_cam=dict(width=1000,height=1276,depth_range_cm=[-100,100],views={'photo':dict(axis='front',px_per_cm=float(c[0]),center_cm=c[1:3].tolist())});v=e['posed']@R.T;mask,img,dep,z=render_mesh.raster(v,r.faces,photo_cam,'photo');cv2.imwrite(str(out/'photo-render.png'),img);cv2.imwrite(str(out/'photo-depth.png'),dep);cv2.imwrite(str(out/'photo-depth-valid.png'),np.isfinite(z).astype('uint8')*255);np.save(out/'photo-rawdepth.npy',z.astype('float32'))
  put(out/'provenance.json',dict(inputs={str(x.relative_to(ROOT)):sha(x) for x in [BASE/'reference/original-product.jpg',BASE/'reference/imagegen-pose.png',BASE/'targets/pose-targets.json',Path(__file__)]},state_sha256=sha(out/'final-state.json'),posed_mesh_sha256=sha(out/'posed.obj'),dimensions=final['dimensions'],measuredNeutral=final['measuredNeutral'],photo_camera_matrix=np.vstack((np.r_[c[0]*R[0],500-c[0]*c[1]],np.r_[-c[0]*R[1],638+c[0]*c[2]],[0,0,0,1]))))
 finally:r.close()
if __name__=='__main__':main()
