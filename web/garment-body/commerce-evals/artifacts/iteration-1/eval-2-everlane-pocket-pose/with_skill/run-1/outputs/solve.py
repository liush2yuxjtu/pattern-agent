#!/usr/bin/env python3
from pathlib import Path
import sys,json,copy,time,hashlib,csv
import numpy as np,cv2
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
ROOT=Path(__file__).resolve().parents[7];sys.path.insert(0,str(ROOT/'tools/human_fit/pose_guided'))
from runtime import Runtime,sha
from render_mesh import raster
O=Path(__file__).parent;BASE=ROOT/'work/commerce-skill-evals-20261118';start=time.time()
def dump(p,x): (O/p).write_text(json.dumps(x,indent=2)+'\n')
r=Runtime();prior=json.loads((BASE/'fixtures/neutral-state.json').read_text());photo=cv2.imread(str(BASE/'inputs/everlane-blue-shirt/original.jpg'));H,W=photo.shape[:2]
# Raw-photo observations by solver visual inspection in 600x750 display, not detector data.
obs={'head':(299,82,1.2),'neck01':(296,130,.7),'upperarm01.R':(253,158,1),'upperarm01.L':(363,149,1),'lowerarm01.R':(228,281,.6),'lowerarm01.L':(393,247,.7),'wrist.R':(225,400,1),'wrist.L':(358,347,.18),'upperleg01.R':(278,350,.4),'upperleg01.L':(335,350,.4),'lowerleg01.R':(278,533,.2),'lowerleg01.L':(345,535,.2),'foot.R':(270,715,.4),'foot.L':(353,721,.4)}
dump('observations.json',{'display_to_source':[[4,0,0],[0,4,0],[0,0,1]],'points':{n:{'pixel':[4*a,4*b],'weight':w,'basis':'occluded internal hypothesis' if n in ['wrist.L','upperleg01.R','upperleg01.L','lowerleg01.R','lowerleg01.L'] else 'manual anatomical approximation from raw photo; clothed joint uncertain'} for n,(a,b,w) in obs.items()},'no_detector':True})
# Register illustrative guide using texture correspondences, excluding lower confidence matches via RANSAC.
g=cv2.imread(str(O/'images/original-pose-illustrative.png'));small=cv2.resize(photo,(600,750));gs=cv2.resize(g,(600,750));orb=cv2.ORB_create(5000);k1,d1=orb.detectAndCompute(gs,None);k2,d2=orb.detectAndCompute(small,None);matches=cv2.BFMatcher(cv2.NORM_HAMMING).knnMatch(d1,d2,k=2);good=[a for a,b in matches if a.distance<.7*b.distance];a=np.float32([k1[m.queryIdx].pt for m in good]);b=np.float32([k2[m.trainIdx].pt for m in good]);A,ins=cv2.estimateAffinePartial2D(a,b,method=cv2.RANSAC,ransacReprojThreshold=3)
if A is not None:
 T=np.eye(3);T[:2]=A;T=np.diag([4,4,1])@T@np.diag([600/g.shape[1],750/g.shape[0],1]);err=np.linalg.norm(cv2.transform(a[None],A)[0]-b,axis=1);dump('guide-registration.json',{'native_size':[g.shape[1],g.shape[0]],'guide_native_to_source':T.tolist(),'matches':len(good),'inliers':int(ins.sum()),'inlier_mean_source_px':float(err[ins.ravel()>0].mean()*4),'semantic_review':'Guide neck dot sits on collar, pelvis is clothing-derived; corrected anatomical targets from unchanged raw photo. Hidden wrist is weak hypothesis; knees remain uncertain.'})
# Camera: p_camera=R_xyz(p_cm), u=s*x+cx, v=-s*y+cy; yaw/pitch/roll degrees.
def rot(c):return Rotation.from_euler('YXZ',c[3:6],degrees=True).as_matrix()
def proj(p,c):q=np.asarray(p)@rot(c).T;return np.column_stack([q[:,0]*c[0]+c[1],-q[:,1]*c[0]+c[2]])
# Broad frontal and oblique starting cameras constitute two camera hypotheses in block 1.
names=list(obs);target=np.array([[a*4,b*4] for a,b,w in obs.values()]);weights=np.array([w for a,b,w in obs.values()])
posevars=[(n,j) for n in ['root','spine01','upperarm01.R','upperarm01.L','lowerarm01.R','lowerarm01.L','upperleg01.R','upperleg01.L','lowerleg01.R','lowerleg01.L'] for j in range(3)]
initcam=np.array([16.5,1200,2915,0,0,0.]);x0=np.r_[initcam,np.zeros(len(posevars))];lo=np.r_[[13,900,2700,-25,-8,-8],np.full(len(posevars),-75.)];hi=np.r_[[19,1500,3150,25,8,8],np.full(len(posevars),75.)]
# Keep root and leg rotations within standing support, while allowing asymmetric arms.
for i,(n,j) in enumerate(posevars):
 if n=='root':lo[6+i]=-6;hi[6+i]=6
 if 'leg' in n:lo[6+i]=-12;hi[6+i]=12
 if n=='spine01':lo[6+i]=-10;hi[6+i]=10

def state(x,dimensions=None):
 s=copy.deepcopy(prior)
 if dimensions:s['dimensions'].update(dimensions)
 for (n,j),v in zip(posevars,x[6:]):s['poseDegrees'][n][j]=float(v)
 return s

def fun(x,dimensions=None):
 e=r.evaluate(state(x,dimensions),skin=False);p=e['joints'][[r.index[n] for n in names]];res=((proj(p,x[:6])-target)*np.sqrt(weights[:,None])/35).ravel()
 # Regularization retains standing body, neutral depth for obscured limbs. No silhouette shrink incentive.
 regs=x[6:]/65
 for i,(n,j) in enumerate(posevars):
  if 'leg' in n or n=='root':regs[i]*=3
 return np.r_[res,regs,(x[3:6]/[20,5,5])*.25]
history=[];best=None
for yaw in [0,15]:
 x=x0.copy();x[3]=yaw;t=time.time();fit=least_squares(fun,x,bounds=(lo,hi),max_nfev=110,ftol=.0002,xtol=.0002);cost=float(np.sum(fun(fit.x)**2));history.append({'block':'camera and skeletal pose','initial':x.tolist(),'final':fit.x.tolist(),'cost':cost,'nfev':fit.nfev,'seconds':time.time()-t})
 if best is None or cost<best[0]:best=(cost,fit.x.copy(),copy.deepcopy(prior['dimensions']))
# Block 2 bounded conditional dimensions. Discrete measured-neutral recalibration with pose refinement.
basecost,x,dims=best;conditional=copy.deepcopy(dims);conditional.update(shoulders=35.5,upperArmLength=30,forearmLength=24)
t=time.time();f=least_squares(lambda z:fun(z,conditional),x,bounds=(lo,hi),max_nfev=75,ftol=.0003,xtol=.0003);cost=float(np.sum(fun(f.x,conditional)**2))+.4
history.append({'block':'conditional arm/shoulder dimensions and skeletal pose','dimensions_initial':dims,'dimensions_candidate':conditional,'initial':x.tolist(),'final':f.x.tolist(),'cost_with_dimension_prior':cost,'seconds':time.time()-t,'nfev':f.nfev})
if cost<basecost:best=(cost,f.x.copy(),conditional)
_,x,dimensions=best;final=state(x,dimensions);dump('parameter-block-history.json',history);dump('initial-state.json',prior);dump('initial-camera.json',{'final':initcam.tolist(),'width':W,'height':H})
# Forearm and hand depth is hidden. A mild relaxed finger curl is an explicit prior, not recovered evidence.
for n in final['poseDegrees']:
 if n.startswith('finger') and n.endswith('.L'):final['poseDegrees'][n][0]=12.
for n in final['poseDegrees']:final['poseDegrees'][n]=[round(v,1) for v in final['poseDegrees'][n]]
final=r.canonical_state(final);dump('final-state.json',final);e=r.evaluate(final);ini=r.evaluate(prior)
r.write_obj(O/'neutral.obj',e['shape']['rest']);r.write_obj(O/'posed.obj',e['posed']);r.write_obj(O/'initial-posed.obj',ini['posed'])
R=rot(x[:6]);P=np.vstack([np.r_[x[0]*R[0],x[1]],np.r_[-x[0]*R[1],x[2]],np.array([0,0,0,1])]);camera={'type':'oblique orthographic','width':W,'height':H,'final':x[:6].tolist(),'final_definition':['px_per_cm','pixel_intercept_u','pixel_intercept_v','yaw_Y_degrees','pitch_X_degrees','roll_Z_degrees'],'rotation_order':'intrinsic YXZ scipy, p_camera=R @ p_cm','world_to_pixel_homogeneous':P.tolist(),'units':'cm','depth_semantics':'rotated camera Z in cm, larger is nearer; raw raster invalid=-inf','source_sha256':sha(BASE/'inputs/everlane-blue-shirt/original.jpg')};dump('camera.json',camera)
# Map transformed vertices into generic front raster coordinates, preserving native source pixels.
def render(ev,c,prefix):
 Q=ev['posed']@rot(c).T;cam={'width':W,'height':H,'depth_range_cm':[-60,60],'views':{'photo':{'axis':'front','px_per_cm':float(c[0]),'center_cm':[(W/2-c[1])/c[0],(c[2]-H/2)/c[0]]}}};m,im,dep,z=raster(Q,r.faces,cam,'photo');cv2.imwrite(str(O/(prefix+'mask.png')),m);cv2.imwrite(str(O/(prefix+'render.png')),im);return m,im,dep,z
m,im,dep,z=render(e,x[:6],'final-');cv2.imwrite(str(O/'photo-render.png'),im);np.save(O/'photo-rawdepth.npy',z.astype('float32'));cv2.imwrite(str(O/'photo-depth-valid.png'),np.isfinite(z).astype('uint8')*255);cv2.imwrite(str(O/'photo-depth.png'),dep)
mi,*_=render(ini,initcam,'initial-');mf,*_=render(ini,x[:6],'initial-frozen-camera-')
# Low-resolution GrabCut on original; nearest-neighbor mask back to source is explicitly documented.
small=cv2.resize(photo,(600,750));labels=np.zeros((750,600),np.uint8);labels[:]=cv2.GC_BGD;labels[15:735,205:415]=cv2.GC_PR_FGD;labels[50:130,275:320]=cv2.GC_FGD;labels[180:680,255:350]=cv2.GC_FGD;cv2.grabCut(small,labels,None,np.zeros((1,65)),np.zeros((1,65)),5,cv2.GC_INIT_WITH_MASK);ref=np.isin(labels,[1,3]);ref=cv2.resize(ref.astype('uint8'),(W,H),interpolation=cv2.INTER_NEAREST)>0;cv2.imwrite(str(O/'reference-mask.png'),ref.astype('uint8')*255)
def metrics(mask,prefix):
 a=ref;b=mask>0;inter=a&b;union=a|b;overlay=photo.copy();col=np.zeros_like(photo);col[inter]=[65,190,70];col[a&~b]=[175,65,220];col[b&~a]=[220,210,45];overlay[union]=(photo[union]*.65+col[union]*.35).astype('uint8');cv2.imwrite(str(O/(prefix+'overlay.png')),overlay)
 ca=cv2.morphologyEx(a.astype('uint8'),cv2.MORPH_GRADIENT,np.ones((3,3)));cb=cv2.morphologyEx(b.astype('uint8'),cv2.MORPH_GRADIENT,np.ones((3,3)));da=cv2.distanceTransform(1-ca,cv2.DIST_L2,5);db=cv2.distanceTransform(1-cb,cv2.DIST_L2,5);dist=np.r_[da[cb>0],db[ca>0]]
 return {'IoU':float(inter.sum()/union.sum()),'Dice':float(2*inter.sum()/(a.sum()+b.sum())),'symmetric_contour_mean_px':float(dist.mean()),'symmetric_contour_P95_px':float(np.percentile(dist,95)),'body_outside_clothed_envelope_fraction':float((b&~a).sum()/b.sum())}
dump('metrics.json',{'reference_sha256':sha(BASE/'inputs/everlane-blue-shirt/original.jpg'),'mask_method':'OpenCV GrabCut at 600x750 nearest upsample; clothed envelope, not bare anatomy','initial':metrics(mi,'initial-'),'initial_frozen_final_camera':metrics(mf,'initial-frozen-camera-'),'final':metrics(m,'final-')})
# Save true canonical views from exactly the same state, never independently refit.
vc={'width':600,'height':800,'depth_range_cm':[-65,65],'views':{n:{'axis':a,'px_per_cm':4,'center_cm':[0,87]} for n,a in [('front','front'),('side','side'),('back','back'),('depth','front'),('pose','front')]}}
r.save(final,vc,O/'views');j=e['joints'];pix=proj(j,x[:6]);rows=[]
for n,p,uv in zip(r.names,j,pix):
 inside=0<=uv[0]<W and 0<=uv[1]<H;rows.append({'name':n,'world_cm':p.tolist(),'pixel':uv.tolist(),'inside_canvas':bool(inside),'occlusion':'unknown; not inferred from dot visibility'})
dump('photo-pose-joints.json',{'joints':rows,'edges':[[b['parent'],b['name']] for b in r.bones if b['parent']]});res=proj(j[[r.index[n] for n in names]],x[:6])-target;dump('joint-residuals.json',{n:{'residual_px':v.tolist(),'norm_px':float(np.linalg.norm(v)),'weight':obs[n][2]} for n,v in zip(names,res)})
meas={'units':'cm','basis':'prior / mesh_parameter; never person dimensions','neutral_mesh_sha256':sha(O/'neutral.obj'),'prior_dimensions':prior['dimensions'],'dimensions':final['dimensions'],'measuredNeutral':final['measuredNeutral'],'residuals_cm':{k:final['measuredNeutral'][k]-v for k,v in final['dimensions'].items()},'unavailable':{k:None for k in ['underbust','bust_point_distance','shoulder_slope','front_waist_length','back_waist_length','crotch_arc']},'bone_segments_cm':{b['name']:float(np.linalg.norm(j[i]-j[r.index[b['parent']]])) for i,b in enumerate(r.bones) if b['parent']}}
dump('measurements.json',meas)
with (O/'measurements.csv').open('w') as f:
 w=csv.writer(f);w.writerow(['name','target_cm','measured_neutral_cm','basis']);w.writerows([[k,v,final['measuredNeutral'][k],'mesh_parameter / prior'] for k,v in final['dimensions'].items()])
dump('timing.json',{'actual_solver_wall_seconds':time.time()-start,'token_usage':None,'numerical_fit_seconds':sum(h['seconds'] for h in history)});r.close();print(str(O/'final-overlay.png'));print(json.dumps(history,indent=2))
