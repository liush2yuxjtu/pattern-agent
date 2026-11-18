from pathlib import Path
import cv2,numpy as np,json,hashlib,shutil
B=Path(__file__).resolve().parent
shutil.copy2(B.parent/'images/raw-pose-guide.png',B/'reference/imagegen-pose.png')
a=cv2.imread(str(B/'reference/imagegen-pose.png')); b=cv2.imread(str(B/'reference/original-product.jpg'));hsv=cv2.cvtColor(a,cv2.COLOR_BGR2HSV)
neon=((hsv[:,:,1]>150)&(hsv[:,:,2]>170)&(hsv[:,:,0]>15)&(hsv[:,:,0]<170)).astype('uint8')*255
mask=255-cv2.dilate(neon,np.ones((19,19),np.uint8));sift=cv2.SIFT_create(nfeatures=7000);ka,da=sift.detectAndCompute(a,mask);kb,db=sift.detectAndCompute(b,None);pairs=cv2.BFMatcher().knnMatch(da,db,k=2);g=[x for x,y in pairs if x.distance<.72*y.distance];x=np.float32([ka[z.queryIdx].pt for z in g]);y=np.float32([kb[z.trainIdx].pt for z in g]);M,ins=cv2.estimateAffinePartial2D(x,y,method=cv2.RANSAC,ransacReprojThreshold=4,maxIters=10000,confidence=.999);assert M is not None;err=np.linalg.norm(x@M[:,:2].T+M[:,2]-y,axis=1);ok=ins.ravel()>0;assert ok.sum()>=10
reg=dict(method='SIFT Lowe0.72 similarity RANSAC4px; neon excluded19px',matrix_native_to_raw=M.tolist(),matches=len(g),inliers=int(ok.sum()),inlier_mean_error_px=float(err[ok].mean()),inlier_p95_error_px=float(np.percentile(err[ok],95)),limitations='Generated photograph locally redrawn; affine only and landmarks illustrative, not detector truth',input_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [B/'reference/imagegen-pose.png',B/'reference/original-product.jpg']});(B/'targets/registration.json').write_text(json.dumps(reg,indent=2))
old=json.load(open(B/'targets/pose-targets.json'));by={p['id']:p for p in old['points']};seeds={'neckline_center':(428,447),'shoulder_image_left':(194,458),'shoulder_image_right':(666,420),'elbow_image_left':(132,758),'elbow_image_right':(775,759),'wrist_image_left':(207,866),'wrist_image_right':(500,901),'torso_midline':(411,700),'waist_image_left':(212,1065),'waist_image_right':(536,1071),'waist_midline':(373,1068),'hand_left_palm':(246,901),'hand_right_palm':(399,929)}
for k,(sx,sy) in seeds.items():
 p=by[k];p['native_xy']=[sx,sy];p['raw_xy']=(M@np.array([sx,sy,1])).tolist();p['digitization']={'method':'Fresh generated image inspected; manually seeded visible marker center','native_seed_xy':[sx,sy]};p['uncertainty_px']=15 if 'wrist' in k else 25 if 'elbow' in k else 20
 if k=='torso_midline':p['digitization']['method']='Manually selected point on generated green torso line, weak clothing-surface proxy'
for k in ['eye_image_left','eye_image_right','nose']:
 p=by[k];p['native_xy']=None;p['digitization']={'method':'Original source-photo visible face landmark, reviewed at same pixels; no generated face dot exists'};p['visibility']='visible original surface';p['uncertainty_px']=8
# Remove stale historical guide hand markers not used by runtime.
keep=set(seeds)|{'eye_image_left','eye_image_right','nose'};old['points']=[p for p in old['points'] if p['id'] in keep];old['links']=[l for l in old['links'] if all(k in keep for k in l)];old['provenance']='Fresh ImageGen pose image manually digitized then OpenCV similarity-registered to original photo; original face landmarks separate. NOT pose detector or real anatomy truth.'
(B/'targets/pose-targets.json').write_text(json.dumps(old,indent=2));overlay=b.copy()
for p in old['points']:
 xy=tuple(np.rint(p['raw_xy']).astype(int));cv2.circle(overlay,xy,5,(0,240,200),2);cv2.putText(overlay,p['id'],(xy[0]+6,xy[1]-4),0,.33,(0,0,0),2);cv2.putText(overlay,p['id'],(xy[0]+6,xy[1]-4),0,.33,(255,255,255),1)
cv2.imwrite(str(B/'targets/raw-target-overlay.png'),overlay)
registered=cv2.warpAffine(a,M,(b.shape[1],b.shape[0]));cv2.imwrite(str(B/'targets/pose-registered.png'),registered)
print(json.dumps(reg));print([(p['id'],np.round(p['raw_xy'],1).tolist()) for p in old['points']])
