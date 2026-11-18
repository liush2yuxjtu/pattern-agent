from pathlib import Path
import json,hashlib,sys,cv2,numpy as np
sys.path.insert(0,'tools/human_fit/pose_guided');from runtime import Runtime
B=Path(__file__).resolve().parent;F=B/'final';E=B/'comparison';E.mkdir(exist_ok=True)
ref=cv2.imread(str(B/'reference/reference-mask.png'),0)>0;photo=cv2.imread(str(B/'reference/original-product.jpg'));M=np.array(json.load(open(F/'camera.json'))['world_to_pixel_homogeneous'])
r=Runtime()
try:
 initial=json.load(open(B/'iterations/neutral-new-guide/initial-state.json'));cam=json.load(open(F/'views/camera.json'));r.save(initial,cam,B/'initial');(B/'initial/final-state.json').write_text(json.dumps(initial,indent=2))
finally:r.close()
regions=json.load(open('work/pose-guided-fit-20261118/review/acceptance.json'))['regions'];metrics={}
for label,mesh in [('initial',B/'initial/posed.obj'),('final',F/'posed.obj')]:
 v=[];faces=[]
 for line in mesh.read_text().splitlines():
  if line.startswith('v '):v.append(list(map(float,line.split()[1:4])))
  elif line.startswith('f '):faces.append([int(q.split('/')[0])-1 for q in line.split()[1:]])
 uv=np.c_[v,np.ones(len(v))]@M.T;mask=np.zeros(ref.shape,'uint8')
 for ids in faces:cv2.fillConvexPoly(mask,np.rint(uv[ids,:2]).astype('int32'),255)
 body=mask>0;inter=body&ref;union=body|ref;cont=body & ~cv2.erode(body.astype('uint8'),np.ones((3,3),'uint8')).astype(bool);extdist=cv2.distanceTransform((~ref).astype('uint8'),cv2.DIST_L2,5)
 reg={}
 for n,(x0,y0,x1,y1) in regions.items():
  roi=np.zeros(ref.shape,bool);roi[y0:y1,x0:x1]=True;bc=body&roi;ct=cont&roi;outside=(bc&~ref).sum()/max(bc.sum(),1);p95=float(np.percentile(extdist[ct],95)) if ct.any() else None
  reg[n]={'outside_fraction':float(outside),'exterior_contour_p95_px':p95,'body_pixels':int(bc.sum()),'heuristic_verdict':'FAIL' if outside>.08 or p95 is None or p95>25 else 'PASS'}
 metrics[label]={'mesh_sha256':hashlib.sha256(mesh.read_bytes()).hexdigest(),'silhouette_iou':float(inter.sum()/union.sum()),'silhouette_dice':float(2*inter.sum()/(body.sum()+ref.sum())),'body_outside_clothing_fraction':float((body&~ref).sum()/max(body.sum(),1)),'regions':reg}
 cv2.imwrite(str(E/(label+'-mask.png')),mask);overlay=photo.copy().astype(float)
 for group,color in [(body&ref,[70,200,70]),(ref&~body,[190,60,210]),(body&~ref,[220,200,60])]:overlay[group]=overlay[group]*.84+np.array(color)*.16
 overlay=overlay.astype('uint8');cv2.drawContours(overlay,cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)[0],-1,(255,200,0),2);cv2.drawContours(overlay,cv2.findContours(ref.astype('uint8'),cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)[0],-1,(180,30,210),1);cv2.imwrite(str(E/(label+'-frozen-camera-overlay.png')),overlay)
metrics['method']={'camera':'Both masks independently reprojected from actual OBJ with final camera frozen; no warp','reference':'fresh GrabCut clothing/hair silhouette, NOT naked-body truth','thresholds':'Historical regional-v1 heuristics reused: exterior8%,P9525px; FAIL region veto. Hair/global symmetric scores descriptive only.','registration_sha256':hashlib.sha256((B/'targets/registration.json').read_bytes()).hexdigest(),'camera_sha256':hashlib.sha256((F/'camera.json').read_bytes()).hexdigest(),'final_state_sha256':hashlib.sha256((F/'final-state.json').read_bytes()).hexdigest()}
(E/'metrics.json').write_text(json.dumps(metrics,indent=2));print(json.dumps({k:v for k,v in metrics.items() if k!='method'}))
