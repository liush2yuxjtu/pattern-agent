import sys,json,copy,time,hashlib
from pathlib import Path
import cv2,numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
ROOT=Path('/workspace/work/pattern-agent');OUT=Path(__file__).parent
sys.path.insert(0,str(ROOT/'tools/human_fit/pose_guided'));from runtime import Runtime,sha
import render_mesh
r=Runtime();initial=json.load(open(ROOT/'work/commerce-skill-evals-20261118/fixtures/neutral-state.json'));photo=cv2.imread(str(ROOT/'work/commerce-skill-evals-20261118/inputs/everlane-boatneck/original.jpg'));H,W=photo.shape[:2]
def save(p,d): (OUT/p).write_text(json.dumps(d,indent=2)+'\n')
# Register generated guide to unchanged photo with feature matches; coordinates are manually corrected anatomy, never detector truth.
g=cv2.imread(str(OUT/'reference/pose-guide.png'));orb=cv2.ORB_create(6000);a,da=orb.detectAndCompute(g,None);b,db=orb.detectAndCompute(photo,None);ms=cv2.BFMatcher(cv2.NORM_HAMMING).knnMatch(da,db,k=2);good=[x for x,y in ms if x.distance<.72*y.distance];pa=np.float32([a[m.queryIdx].pt for m in good]);pb=np.float32([b[m.trainIdx].pt for m in good]);M,inl=cv2.findHomography(pa,pb,cv2.RANSAC,5);err=np.linalg.norm(cv2.perspectiveTransform(pa[:,None],M)[:,0]-pb,axis=1);save('reference/registration.json',dict(method='ORB RANSAC homography; anatomy corrected manually on original',matrix=M.tolist(),matches=len(good),inliers=int(inl.sum()),inlier_mean_error_px=float(err[inl.ravel()>0].mean())))
# Original image manual inferred anatomical targets (clothing envelope is not a joint).
targets={'upperarm01.R':[785,1020],'upperarm01.L':[1630,1045],'lowerarm01.R':[675,1760],'lowerarm01.L':[1690,1785],'wrist.R':[647,2445],'wrist.L':[1730,2430],'neck01':[1210,920],'head':[1200,630],'upperleg01.R':[1010,2250],'upperleg01.L':[1450,2250]}
names=list(targets);target=np.array(list(targets.values()));weights=np.array([1,1,.8,.8,1,1,.5,.4,.25,.25]);save('reference/manual-joints.json',dict(basis='manual inferred under-clothing guidance after Image Gen registration',points=targets,limitations=['Shoulder joint lies medial to sleeve seam','Pelvis beneath clothing, low weight','Hidden lower legs have prior pose']))
# A native orthographic source camera, arbitrary yaw/pitch/roll.
def cammat(c):
 s,cx,cy,yaw,pitch,roll=c;R=Rotation.from_euler('YXZ',[yaw,pitch,roll],degrees=True).as_matrix();return R,np.array([s*R[0],-s*R[1],np.zeros(3)])
def project(v,c):
 R,_=cammat(c);q=v@R.T;return np.c_[(q[:,0]-c[1])*c[0]+W/2,H/2-(q[:,1]-c[2])*c[0]]
bones=['upperarm01.R','upperarm01.L','lowerarm01.R','lowerarm01.L','wrist.R','wrist.L','spine02','neck01','head']
# Starting pose is genuine shared neutral; fitting explores actual FK.
x0=np.r_[25.,0.,112.,0.,0.,0.,np.zeros(27)]
lo=np.r_[18,-12,95,-18,-12,-8,np.tile([-65,-65,-75],9)];hi=np.r_[35,12,135,18,12,8,np.tile([65,65,75],9)]
def stateof(x,base):
 st=copy.deepcopy(base)
 for i,n in enumerate(bones):st['poseDegrees'][n]=x[6+i*3:9+i*3].tolist()
 return st
def resid(x,base,reg=.10):
 e=r.evaluate(stateof(x,base),skin=False);xy=project(e['joints'][[r.index[n] for n in names]],x[:6]);return np.r_[((xy-target)*weights[:,None]/30).ravel(),x[6:]*reg/20,x[3:6]/20]
start=time.time();history=[]
sol=least_squares(resid,x0,args=(initial,),bounds=(lo,hi),max_nfev=130,diff_step=.001,ftol=1e-5)
x=sol.x;st=stateof(x,initial);history.append(dict(block='1 joint FK and camera',nfev=sol.nfev,loss=float(np.sum(resid(x,initial)**2)),parameters=x.tolist(),dimensions=st['dimensions']))
# 2: conditional bounded shape, with regularization toward generic prior. Limb lengths are allowed only a small conditional change.
keys=['shoulders','upperArmLength','forearmLength'];d0=np.array([initial['dimensions'][k] for k in keys])
def shape_res(d):
 b=copy.deepcopy(initial);b['dimensions'].update(dict(zip(keys,map(float,d))));return np.r_[resid(x,b), (d-d0)/1.5]
ds=least_squares(shape_res,d0,bounds=(d0-[2,2,2],d0+[2,2,2]),max_nfev=10,diff_step=.002);base=copy.deepcopy(initial);base['dimensions'].update(dict(zip(keys,map(float,ds.x))));sol2=least_squares(resid,x,args=(base,.13),bounds=(lo,hi),max_nfev=80,diff_step=.001,ftol=1e-5);x=sol2.x;st=stateof(x,base);history.append(dict(block='2 bounded lengths and final FK-camera refinement',nfev=sol2.nfev,loss=float(np.sum(resid(x,base,.13)**2)),parameters=x.tolist(),dimensions=st['dimensions'],shape_nfev=ds.nfev));save('parameter-block-history.json',dict(seconds=time.time()-start,blocks=history,initial=x0.tolist()))
st['poseDegrees']={k:[round(v,1) for v in a] for k,a in st['poseDegrees'].items()};st['dimensions']={k:round(v,1) for k,v in st['dimensions'].items()};final=r.canonical_state(st);save('final-state.json',final);save('initial-state.json',initial);e=r.evaluate(final);ei=r.evaluate(initial);r.write_obj(OUT/'neutral.obj',e['shape']['rest']);r.write_obj(OUT/'posed.obj',e['posed']);r.write_obj(OUT/'initial.obj',ei['posed'])
R,_=cammat(x[:6]);P=np.zeros((3,4));P[0,:3]=x[0]*R[0];P[0,3]=W/2-x[0]*x[1];P[1,:3]=-x[0]*R[1];P[1,3]=H/2+x[0]*x[2];P[2,3]=1
camera=dict(width=W,height=H,projection='oblique orthographic',units='cm',final=x[:6].tolist(),world_to_pixel_homogeneous=P.tolist(),depth_semantics='rotated world Z in cm, larger toward camera',depth_range_cm=[-60,60]);save('camera.json',camera);save('initial-camera.json',dict(camera,final=x0[:6].tolist()))
# actual raster uses rotated vertices, without resizing exported image.
rc=dict(width=W,height=H,views={'front':dict(axis='front',px_per_cm=float(x[0]),center_cm=x[1:3].tolist())},depth_range_cm=[-60,60])
def raster(e): return render_mesh.raster(e['posed']@R.T,r.faces,rc,'front')
m,img,dep,z=raster(e);mi,imi,_,_=raster(ei);cv2.imwrite(str(OUT/'photo-render.png'),img);cv2.imwrite(str(OUT/'final-mask.png'),m);cv2.imwrite(str(OUT/'initial-mask.png'),mi);cv2.imwrite(str(OUT/'initial-render.png'),imi);cv2.imwrite(str(OUT/'geometry-depth.png'),dep);np.save(OUT/'rawdepth.npy',z.astype('float32'));cv2.imwrite(str(OUT/'depth-valid.png'),np.isfinite(z).astype('uint8')*255)
# Preserve actual inferred silhouette using GrabCut at 640x800, then nearest-neighbor upscale. Clothing and hair included.
small=cv2.resize(photo,(640,800));gm=np.zeros((800,640),np.uint8);cv2.grabCut(small,gm,(145,15,345,785),None,None,5,cv2.GC_INIT_WITH_RECT);ref=np.isin(gm,[1,3]).astype('uint8')*255;cv2.imwrite(str(OUT/'reference/mask-640.png'),ref);ref=cv2.resize(ref,(W,H),interpolation=cv2.INTER_NEAREST);cv2.imwrite(str(OUT/'reference-mask.png'),ref)
def overlay(mask,path):
 out=photo.copy();a=ref>0;b=mask>0;colors=np.zeros_like(out);colors[a&b]=(70,210,70);colors[a&~b]=(180,70,220);colors[b&~a]=(220,220,30);active=a|b;out[active]=(out[active]*.63+colors[active]*.37).astype('uint8');cv2.imwrite(str(OUT/path),out)
overlay(m,'overlay.png');overlay(mi,'initial-overlay.png')
def metric(mask):
 a=ref>0;b=mask>0;ia=(a&b).sum();u=(a|b).sum();return dict(iou=float(ia/u),dice=float(2*ia/(a.sum()+b.sum())),model_outside_clothed_envelope=float((b&~a).sum()/b.sum()))
save('metrics.json',dict(reference_sha256=sha(OUT/'reference-mask.png'),resolution=[W,H],segmentation_working_resolution=[640,800],initial=metric(mi),final=metric(m),limitations='Hair/clothing mask versus bare anatomical model; not person measurement validation'))
rows=[]
for i,n in enumerate(r.names):
 p=project(e['joints'][[i]],x[:6])[0];inside=bool(0<=p[0]<W and 0<=p[1]<H);rows.append(dict(name=n,world_cm=e['joints'][i].tolist(),pixel=p.tolist(),inside_canvas=inside,occlusion='not classified'))
save('projected-joints.json',dict(joints=rows,pose_source='Actual FK from same 163-bone state'))
poseimg=img.copy()
for n in names:
 i=r.index[n];p=project(e['joints'][[i]],x[:6])[0];cv2.circle(poseimg,tuple(np.rint(p).astype(int)),10,(20,50,245),-1)
cv2.imwrite(str(OUT/'geometry-pose.png'),poseimg)
views=dict(width=640,height=900,views={v:dict(axis=v,px_per_cm=4.8,center_cm=[0,85]) for v in ['front','side','back']},depth_range_cm=[-60,60]);r.save(final,views,OUT/'views')
measurements=[]
for k,v in final['measuredNeutral'].items(): measurements.append(dict(name=k,value=v,unit='cm',basis='prior' if k not in keys else 'mesh_parameter',mesh_checked=True,definition='Neutral MakeHuman calibrated tape path or landmark',limitations='Conditional avatar; not photographed-person measurement'))
for k in ['bustPointSpacing','underBust','shoulderSlope','frontWaistLength','backWaistLength','crotchArc']:measurements.append(dict(name=k,value=None,unit='cm',basis='unavailable',mesh_checked=False))
save('measurements.json',dict(measurements=measurements,neutral_mesh_sha256=sha(OUT/'neutral.obj')))
(OUT/'measurements.csv').write_text('name,value,unit,basis\n'+'\n'.join(f"{a['name']},{a['value'] if a['value'] is not None else ''},{a['unit']},{a['basis']}" for a in measurements)+'\n')
save('input-provenance.json',dict(original_sha256=sha(ROOT/'work/commerce-skill-evals-20261118/inputs/everlane-boatneck/original.jpg'),asset_sha256=sha(r.asset),runtime_sha256=sha(ROOT/'tools/human_fit/pose_guided/runtime.py'),solver_sha256=sha(__file__),mode='prior_avatar',native_size=[W,H],timing_seconds=time.time()-start,tokens=None));r.close();print('OVERLAY',OUT/'overlay.png');print(json.dumps(history))
