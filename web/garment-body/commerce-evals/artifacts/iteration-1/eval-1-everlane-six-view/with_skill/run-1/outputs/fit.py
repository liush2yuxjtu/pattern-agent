import sys,json,time,copy,hashlib
from pathlib import Path
import numpy as np,cv2
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
ROOT=Path('/workspace/work/pattern-agent');sys.path.insert(0,str(ROOT/'tools/human_fit/pose_guided'))
from runtime import Runtime,sha
from render_mesh import raster
O=Path(__file__).parent;I=ROOT/'work/commerce-skill-evals-20261118/inputs/everlane-boatneck';r=Runtime();s=json.load(open(ROOT/'work/commerce-skill-evals-20261118/fixtures/neutral-state.json'));photo=cv2.imread(str(I/'original.jpg'));h,w=photo.shape[:2]
names=['head','neck01','upperarm01.R','upperarm01.L','lowerarm01.R','lowerarm01.L','wrist.R','wrist.L','upperleg01.R','upperleg01.L']
target=np.array([[1210,650],[1190,905],[790,1020],[1610,1020],[690,1710],[1710,1700],[650,2430],[1730,2420],[1000,2360],[1430,2360]],float)
# All internal joints are manual approximate hypotheses; clothing seams do not provide joints.
(O/'reference/landmarks.json').write_text(json.dumps({'source':'manual photo interpretation after illustrative guide inspection','names':names,'pixel':target.tolist(),'guide_caveat':'guide neck point lies on neckline and hip points on trouser waistband; these were NOT used as anatomical joint truth','registration':'SIFT homography recorded separately; manual coordinates refer directly to unmodified original'},indent=2))
bones=['upperarm01.R','upperarm01.L','lowerarm01.R','lowerarm01.L','head','spine03'];x0=np.r_[27.,1200.,4820.,0.,0.,0.,np.zeros(18)]
lo=np.r_[22,900,4200,-25,-12,-8,np.tile([-95,-90,-95],6)];hi=np.r_[33,1450,5300,25,12,8,np.tile([95,90,95],6)]
def unpack(x):
 st=copy.deepcopy(s)
 for i,b in enumerate(bones):st['poseDegrees'][b]=x[6+i*3:9+i*3].tolist()
 return st

def transform(v,x):return v@Rotation.from_euler('YXZ',x[3:6],degrees=True).as_matrix().T

def proj(v,x):
 p=transform(v,x);return np.c_[x[1]+x[0]*p[:,0],x[2]-x[0]*p[:,1]]
def fun(x):
 e=r.evaluate(unpack(x),False);p=proj(e['joints'][[r.index[n] for n in names]],x)
 return np.r_[((p-target)*np.array([1,1,.8,.8,.8,.8,1,1,.65,.65])[:,None]).ravel()/40,x[3:6]/[20,15,10],x[6:]/100]
# True camera/pose alternatives, both optimized rather than relabelled.
history=[];start=time.monotonic()
for block,yaw in enumerate([0.,15.]):
 xx=x0.copy();xx[3]=yaw
 res=least_squares(fun,xx,bounds=(lo,hi),max_nfev=170,diff_step=.002,ftol=1e-6)
 st=unpack(res.x);(O/f'candidate-{block+1}.json').write_text(json.dumps({'state':st,'camera':res.x[:6].tolist(),'objective':float(np.sum(fun(res.x)**2)),'evaluations':res.nfev},indent=2));history.append({'block':block+1,'start':xx.tolist(),'final':res.x.tolist(),'loss':float(np.sum(fun(res.x)**2)),'nfev':res.nfev})
best=min(history,key=lambda a:a['loss']);priorx=np.array(best['final'])
def depthfun(xx):
 e=r.evaluate(unpack(xx),False);j=e['joints'];ids=[r.index[n] for n in ['lowerarm01.R','lowerarm01.L','wrist.R','wrist.L']]
 return np.r_[fun(xx),(j[ids,2]-3)/3,xx[18:21]/15]
res=least_squares(depthfun,priorx,bounds=(lo,hi),max_nfev=130,diff_step=.002,ftol=1e-6)
history.append({'block':3,'purpose':'restore plausible arms-at-sides depth after real side render inspection','start':priorx.tolist(),'final':res.x.tolist(),'loss':float(np.sum(depthfun(res.x)**2)),'nfev':res.nfev})
x=res.x;state=r.canonical_state(unpack(x));(O/'final-state.json').write_text(json.dumps(state,indent=2));(O/'initial-state.json').write_text(json.dumps(s,indent=2));(O/'parameter-history.json').write_text(json.dumps({'blocks':history,'elapsed_seconds':time.monotonic()-start,'dimensions_policy':'fixed shared M170 prior; no photo scale measurement'},indent=2))
# Source camera, native pixel dimensions, with full oblique orthographic matrix.
R=Rotation.from_euler('YXZ',x[3:6],degrees=True).as_matrix();P=np.vstack([np.r_[x[0]*R[0],x[1]],np.r_[-x[0]*R[1],x[2]],np.array([0,0,0,1])]);cam={'width':w,'height':h,'final':x[:6].tolist(),'world_to_pixel_homogeneous':P.tolist(),'projection':'oblique orthographic','rotation_convention':'scipy YXZ yaw pitch roll degrees; Y-up cm','depth_range_cm':[-60,60]};(O/'camera.json').write_text(json.dumps(cam,indent=2));(O/'initial-camera.json').write_text(json.dumps(cam,indent=2));(O/'camera-initialization.json').write_text(json.dumps({'initial':x0[:6].tolist(),'width':w,'height':h},indent=2))
# GrabCut evaluated at source pixels after quarter-scale processing.
small=cv2.resize(photo,(600,750));gc=np.full((750,600),cv2.GC_PR_BGD,np.uint8);poly=np.array([[250,23],[337,20],[370,100],[380,230],[430,260],[450,520],[455,690],[425,750],[155,750],[140,690],[143,500],[157,275],[209,225],[210,90]],np.int32);cv2.fillPoly(gc,[poly],cv2.GC_PR_FGD);gc[:12]=cv2.GC_BGD;gc[:,:50]=cv2.GC_BGD;gc[:,550:]=cv2.GC_BGD;cv2.grabCut(small,gc,None,None,None,5,cv2.GC_INIT_WITH_MASK);ref=cv2.resize(np.isin(gc,[1,3]).astype('uint8')*255,(w,h),interpolation=cv2.INTER_NEAREST);cv2.imwrite(str(O/'reference-mask.png'),ref)
for label,st,xx in [('initial',s,x),('final',state,x)]:
 e=r.evaluate(st);v=e['posed'];rc={'width':w,'height':h,'depth_range_cm':[-60,60],'views':{'photo':{'axis':'front','px_per_cm':xx[0],'center_cm':[(w/2-xx[1])/xx[0],(xx[2]-h/2)/xx[0]]}}};m,img,dep,z=raster(transform(v,xx),r.faces,rc,'photo');cv2.imwrite(str(O/(label+'-mask.png')),m);cv2.imwrite(str(O/(label+'-render.png')),img);ov=photo.copy();inside=(ref>0)&(m>0);onlyref=(ref>0)&(m==0);onlym=(ref==0)&(m>0);colors=np.zeros_like(photo);colors[inside]=[50,210,50];colors[onlyref]=[210,50,210];colors[onlym]=[220,210,0];active=(ref>0)|(m>0);ov[active]=(.65*photo[active]+.35*colors[active]).astype('uint8');cv2.imwrite(str(O/(label+'-overlay.png')),ov)
 if label=='final':
  cv2.imwrite(str(O/'photo-render.png'),img);r.write_obj(O/'neutral.obj',e['shape']['rest']);r.write_obj(O/'posed.obj',v);np.save(O/'rawdepth.npy',z.astype('float32'));cv2.imwrite(str(O/'depth-valid.png'),np.isfinite(z).astype('uint8')*255);cv2.imwrite(str(O/'geometric-depth.png'),dep);points=proj(e['joints'],xx);(O/'projected-pose.json').write_text(json.dumps({'points':[{'name':n,'world_cm':e['joints'][i].tolist(),'pixel':points[i].tolist(),'inside_canvas':bool(0<=points[i,0]<w and 0<=points[i,1]<h)} for i,n in enumerate(r.names)],'edges':[[r.bones[i]['parent'],n] for i,n in enumerate(r.names) if r.bones[i]['parent']],'visibility':'inside_canvas only; occlusion not classified','depth_semantics':'rotated world Z in cm; larger is nearer; orthographic'},indent=2))
vc={'width':768,'height':1024,'depth_range_cm':[-70,70],'views':{n:{'axis':n,'px_per_cm':5.3,'center_cm':[0,86]} for n in ['front','side','back']}};r.save(state,vc,O/'views')
(O/'measurements.json').write_text(json.dumps({'measurements':[{'name':k,'target_cm':v,'value_cm':state['measuredNeutral'][k],'basis':'prior','mesh_checked':True,'definition':r.data['measurementDefinition'],'limitations':'conditional M170 avatar; not measurement of photographed person'} for k,v in state['dimensions'].items()],'unavailable_person_measurements':['bust point separation','underbust','shoulder slope','front/back waist length','crotch arc']},indent=2));r.close();print('FIRST_OVERLAY',O/'final-overlay.png',flush=True)
