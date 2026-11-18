from pathlib import Path
import sys,json,hashlib,time,copy,shutil
import numpy as np,cv2
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
ROOT=Path('/workspace/work/pattern-agent');sys.path.insert(0,str(ROOT/'tools/human_fit/pose_guided'))
from runtime import Runtime,sha
from render_mesh import raster
OUT=Path(__file__).resolve().parent;BASE=ROOT/'work/commerce-skill-evals-20261118';start=time.time()
def save(n,v): (OUT/n).write_text(json.dumps(v,indent=2)+'\n')
photo=cv2.imread(str(BASE/'inputs/everlane-blue-shirt/original.jpg'));h,w=photo.shape[:2];small=cv2.resize(photo,(600,750));save('input-provenance.json',{'source':json.loads((BASE/'inputs/everlane-blue-shirt/source.json').read_text()),'raw_sha256':sha(BASE/'inputs/everlane-blue-shirt/original.jpg'),'native_size':[w,h],'prior_sha256':sha(BASE/'fixtures/neutral-state.json'),'skill_sha256':sha(BASE/'skill-v0/SKILL.md'),'runtime_sha256':sha(ROOT/'tools/human_fit/pose_guided/runtime.py'),'token_telemetry':None})
# Actual raw-photo foreground segmentation, frozen before fitting.
mask=np.full((750,600),cv2.GC_BGD,np.uint8);mask[12:736,205:418]=cv2.GC_PR_FGD;mask[75:710,265:345]=cv2.GC_FGD
bg=np.zeros((1,65));fg=np.zeros((1,65));cv2.grabCut(small,mask,None,bg,fg,5,cv2.GC_INIT_WITH_MASK);ref=np.isin(mask,[1,3]).astype('uint8')*255;ref=cv2.resize(ref,(w,h),interpolation=cv2.INTER_NEAREST);cv2.imwrite(str(OUT/'reference-mask.png'),ref)
# Manual, source-image anatomical guidance, px at native 2400x3000. Hidden pocket wrist and hips low weight.
targets={'head':([298,111],1),'neck01':([297,143],1),'upperarm01.R':([248,159],1),'upperarm01.L':([354,144],1),'lowerarm01.R':([234,276],.6),'lowerarm01.L':([393,249],.65),'wrist.R':([223,398],1),'wrist.L':([363,337],.2),'upperleg01.R':([276,342],.2),'upperleg01.L':([339,342],.2),'lowerleg01.R':([282,516],.1),'lowerleg01.L':([350,516],.1),'foot.R':([273,708],.5),'foot.L':([360,715],.5)}
save('source-landmarks.json',{'basis':'manual visual interpretation of raw photograph; ImageGen registered as illustrative aid, not detector ground truth','coordinates':{n:{'pixel':(np.array(v[0])*4).tolist(),'weight':v[1],'occluded':v[1]<.5} for n,v in targets.items()},'limitations':'shoulders under shirt estimated; hidden pocket wrist, hips and all leg joints uncertain; footwear ankle location uncertain'})
# Registration of the native generated annotation to unchanged raw photograph, actual SIFT+RANSAC.
gen=cv2.imread(str(OUT/'images/pose-illustrative.png'));ggray=cv2.cvtColor(gen,cv2.COLOR_BGR2GRAY);pgray=cv2.cvtColor(photo,cv2.COLOR_BGR2GRAY);sift=cv2.SIFT_create(2500);kg,dg=sift.detectAndCompute(ggray,None);kp,dp=sift.detectAndCompute(pgray,None);pairs=cv2.BFMatcher().knnMatch(dg,dp,k=2);good=[a for a,b in pairs if a.distance<.7*b.distance];a=np.float32([kg[m.queryIdx].pt for m in good]);b=np.float32([kp[m.trainIdx].pt for m in good]);H,inl=cv2.findHomography(a,b,cv2.RANSAC,6);err=np.linalg.norm(cv2.perspectiveTransform(a[:,None],H)[:,0]-b,axis=1);save('images/registration.json',{'homography_generated_to_source':H.tolist(),'matches':len(good),'inliers':int(inl.sum()),'inlier_mean_error_px':float(err[inl[:,0]>0].mean()),'generated_native_size':[gen.shape[1],gen.shape[0]],'source_size':[w,h],'semantic_check':'Illustrative dots on loose shirt shoulder/waist are not anatomy. Source landmarks manually corrected. Occluded wrist remains weak hypothesis.'});cv2.imwrite(str(OUT/'images/registered-guide.png'),cv2.warpPerspective(gen,H,(w,h)))
r=Runtime();prior=json.loads((BASE/'fixtures/neutral-state.json').read_text());state=copy.deepcopy(prior)
# Whole-pose rotations optimized in real FK/LBS, with local axes from actual rig.
bones=['root','spine01','spine03','neck01','head','upperarm01.R','upperarm01.L','lowerarm01.R','lowerarm01.L','wrist.R','wrist.L','upperleg01.R','upperleg01.L','lowerleg01.R','lowerleg01.L']
# Camera [scale, translationX, translationY, yaw,pitch,roll].
cam=np.array([16.6,1190,2910,0,0,0.]);angles=np.zeros(len(bones)*3)
# Bounds discourage unnatural elbows while permitting fit from neutral rather than hand-authored target pose.
lo=np.tile([-55,-45,-65],len(bones));hi=np.tile([70,45,65],len(bones));lo[:3]=[-12,-15,-12];hi[:3]=[12,15,12]
idx=np.array([r.index[n] for n in targets]);t=np.array([v[0] for v in targets.values()])*4;wt=np.sqrt([v[1] for v in targets.values()])[:,None]
def rotation(c):return Rotation.from_euler('YXZ',c[3:],degrees=True).as_matrix()
def project(p,c):q=p@rotation(c).T;return q[:,:2]*[c[0],-c[0]]+c[1:3]
def unpack(x,pose=True,shape=False):
 s=copy.deepcopy(prior);c=x[:6]
 if pose:
  for j,n in enumerate(bones):s['poseDegrees'][n]=x[6+3*j:9+3*j].tolist()
 if shape:
  for k,val in zip(['shoulders','upperArmLength','forearmLength'],x[6+len(angles):]):s['dimensions'][k]=float(val)
 return s,c
def residual(x,pose=True,shape=False):
 s,c=unpack(x,pose,shape);e=r.evaluate(s);out=((project(e['joints'][idx],c)-t)*wt/18).ravel().tolist()
 if pose:out+=((x[6:6+len(angles)])/65*.3).tolist()
 if shape:out+=((x[-3:]-np.array([37,29,23]))/.5).tolist()
 return out
history=[];initialcam=cam.copy()
for block in range(3):
 p=block>0;sh=block==2
 x=np.r_[cam,angles] if p else cam.copy()
 lower=np.r_[[13,1000,2600,-25,-15,-12],lo] if p else [13,1000,2600,-25,-15,-12]
 upper=np.r_[[19,1400,3100,25,15,12],hi] if p else [19,1400,3100,25,15,12]
 if sh:x=np.r_[x,[37,29,23]];lower=np.r_[lower,[36,28,22]];upper=np.r_[upper,[38,30,24]]
 before=float(np.mean(np.square(residual(x,p,sh))));bt=time.time();fit=least_squares(residual,x,bounds=(lower,upper),args=(p,sh),max_nfev=65,ftol=1e-5,xtol=1e-5,diff_step=1e-3)
 state,cam=unpack(fit.x,p,sh)
 if p:angles=fit.x[6:6+len(angles)]
 history.append({'block':block,'name':['camera only from neutral','pose and camera','bounded shoulder and arm dimensions with pose and camera'][block],'initial_parameters':x.tolist(),'final_parameters':fit.x.tolist(),'initial_mean_squared_residual':before,'final_mean_squared_residual':float(np.mean(np.square(fit.fun))),'nfev':fit.nfev,'seconds':time.time()-bt,'status':fit.message});save('parameter-history.json',history);print('block',block,history[-1]['seconds'],history[-1]['final_mean_squared_residual'],flush=True)
# Keep occluded palm/fingers as explicitly weak hypotheses; no visible finger targets.
state=r.canonical_state(state);save('final-state.json',state);save('initial-state.json',prior);e=r.evaluate(state);ei=r.evaluate(prior)
r.write_obj(OUT/'neutral.obj',e['shape']['rest']);r.write_obj(OUT/'posed.obj',e['posed']);r.write_obj(OUT/'initial-posed.obj',ei['posed'])
R=rotation(cam);P=np.zeros((3,4));P[0,:3]=cam[0]*R[0];P[1,:3]=-cam[0]*R[1];P[:2,3]=cam[1:3];P[2,3]=1
save('camera.json',{'width':w,'height':h,'projection':'orthographic oblique','final':cam.tolist(),'parameter_definition':['px_per_cm','translationX_px','translationY_px','yaw_deg','pitch_deg','roll_deg'],'world_to_pixel_homogeneous':P.tolist(),'world_units':'cm','axes':'X lateral, Y up, Z anterior','depth_semantics':'rotated world Z cm, larger nearer; not metric distance to person'})
save('initial-camera.json',{'width':w,'height':h,'final':initialcam.tolist()})
def render(e,c,prefix):
 q=e['posed']@rotation(c).T;camera={'width':w,'height':h,'depth_range_cm':[-100,100],'views':{'front':{'axis':'front','px_per_cm':float(c[0]),'center_cm':[(w/2-c[1])/c[0],(c[2]-h/2)/c[0]]}}};m,im,d,z=raster(q,r.faces,camera,'front');cv2.imwrite(str(OUT/(prefix+'mask.png')),m);cv2.imwrite(str(OUT/(prefix+'render.png')),im)
 valid=np.isfinite(z)
 if prefix=='final-':np.save(OUT/'depth-raw.npy',z.astype('float32'));cv2.imwrite(str(OUT/'depth-valid.png'),valid.astype('uint8')*255);cv2.imwrite(str(OUT/'depth.png'),d)
 # OpenCV overlap colors, translucent enough to inspect source.
 colors=np.zeros_like(photo);a=ref>0;b=m>0;colors[a&b]=[40,200,40];colors[a&~b]=[180,40,220];colors[b&~a]=[230,220,20];ov=photo.copy();active=a|b;ov[active]=cv2.addWeighted(photo,.65,colors,.35,0)[active];cv2.imwrite(str(OUT/(prefix+'overlay.png')),ov)
 ca=cv2.Canny(ref,100,200)>0;cb=cv2.Canny(m,100,200)>0;da=cv2.distanceTransform((~ca).astype('uint8'),cv2.DIST_L2,5);db=cv2.distanceTransform((~cb).astype('uint8'),cv2.DIST_L2,5);ds=np.r_[da[cb],db[ca]]
 return {'IoU':float((a&b).sum()/(a|b).sum()),'Dice':float(2*(a&b).sum()/(a.sum()+b.sum())),'symmetric_contour_mean_px':float(ds.mean()),'symmetric_contour_p95_px':float(np.percentile(ds,95)),'model_outside_clothed_envelope_fraction':float((b&~a).sum()/b.sum())}
metrics={'initial_frozen_final_camera':render(ei,cam,'initial-'),'final':render(e,cam,'final-'),'initial_original_camera':render(ei,initialcam,'initial-original-'),'reference_sha256':sha(BASE/'inputs/everlane-blue-shirt/original.jpg'),'mask_sha256':sha(OUT/'reference-mask.png'),'resolution':[w,h],'interpretation':'Clothed envelope comparison; loose shirt and trousers are not naked-body silhouette. No true-person accuracy claim.'};shutil.copyfile(OUT/'final-render.png',OUT/'photo-render.png');save('metrics.json',metrics)
print('OVERLAY',OUT/'final-overlay.png',flush=True)
# Canonical views use exactly same state, never pose refitting.
vc={'width':600,'height':750,'depth_range_cm':[-100,100],'views':{n:{'axis':'front' if n in ['pose','depth'] else n,'px_per_cm':4.,'center_cm':[0,85]} for n in ['front','side','back','pose','depth']}}
r.save(state,vc,OUT/'views');coords=project(e['joints'],cam);save('pose-joints.json',{'joints':[{'name':n,'world_cm':p.tolist(),'pixel':q.tolist(),'inside_canvas':bool(0<=q[0]<w and 0<=q[1]<h),'occlusion':'not classified'} for n,p,q in zip(r.names,e['joints'],coords)],'basis':'actual 163-bone FK projection'})
save('joint-residuals.json',{n:{'target_pixel':t[i].tolist(),'projected_pixel':coords[r.index[n]].tolist(),'error_px':float(np.linalg.norm(coords[r.index[n]]-t[i])),'weight':float(wt[i,0]**2)} for i,n in enumerate(targets)})
measurements={'basis':'prior and bounded mesh parameters, not measured person','mesh_sha256':sha(OUT/'neutral.obj'),'prior':prior['dimensions'],'measuredNeutral':state['measuredNeutral'],'target':state['dimensions'],'maximumTargetErrorCm':state['maximumTargetErrorCm'],'measurements':[{'name':k,'value':v,'unit':'cm','basis':'prior' if state['dimensions'][k]==prior['dimensions'][k] else 'mesh_parameter','mesh_checked':True,'prior_value':prior['dimensions'][k],'definition':r.data['measurementDefinition']} for k,v in state['measuredNeutral'].items()],'unavailable_person_dimensions':['underbust','bust_point_spacing','crotch_arc','front_waist_length','back_waist_length'],'limitations':['M170 generic authorized prior','single clothed photograph','hidden palm and pocket wrist uncertain','calibrated adult female anatomical template may not match photographed anatomy']};save('measurements.json',measurements)
import csv
with (OUT/'measurements.csv').open('w') as f:
 wr=csv.writer(f);wr.writerow(['name','target_cm','mesh_measured_cm','prior_cm','basis']);wr.writerows([[k,state['dimensions'][k],v,prior['dimensions'][k],'prior/mesh_parameter'] for k,v in state['measuredNeutral'].items()])
save('timing.json',{'numerical_fit_seconds':sum(x['seconds'] for x in history),'total_solver_seconds':time.time()-start,'token_usage':None});r.close();print('DONE',flush=True)
