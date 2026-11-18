#!/usr/bin/env python3
"""Digitize illustrative ImageGen cues; register annotations, never alter raw photograph."""
import cv2, numpy as np, json, hashlib, platform
from pathlib import Path
P=Path(__file__).resolve().parent; R=P.parent/'reference'
a=cv2.imread(str(R/'imagegen-pose.png')); b=cv2.imread(str(R/'original-product.jpg'))
hsv=cv2.cvtColor(a,cv2.COLOR_BGR2HSV)
neon=((hsv[:,:,1]>150)&(hsv[:,:,2]>170)&(hsv[:,:,0]>15)&(hsv[:,:,0]<170)).astype(np.uint8)*255
mask=255-cv2.dilate(neon,np.ones((19,19),np.uint8)); mask[1250:]=0
sift=cv2.SIFT_create(nfeatures=7000);ka,da=sift.detectAndCompute(a,mask);kb,db=sift.detectAndCompute(b,None)
g=[x for x,y in cv2.BFMatcher().knnMatch(da,db,k=2) if x.distance<.72*y.distance]
x=np.float32([ka[z.queryIdx].pt for z in g]);y=np.float32([kb[z.trainIdx].pt for z in g]);M,inliers=cv2.estimateAffinePartial2D(x,y,method=cv2.RANSAC,ransacReprojThreshold=4,maxIters=10000,confidence=.999)
e=np.linalg.norm(x@M[:,:2].T+M[:,2]-y,axis=1);ok=inliers.ravel()>0
sha=lambda f: hashlib.sha256(f.read_bytes()).hexdigest()
reg={'method':'SIFT + Lowe ratio 0.72 + partial-affine RANSAC (4 raw px); neon exclusion dilated 19px; caption excluded','direction':'imagegen_native_to_original_raw','matrix_2x3':M.tolist(),'raw_size_wh':[b.shape[1],b.shape[0]],'imagegen_size_wh':[a.shape[1],a.shape[0]],'keypoints':[len(ka),len(kb)],'ratio_matches':len(g),'inliers':int(ok.sum()),'inlier_mean_error_px':float(e[ok].mean()),'inlier_median_error_px':float(np.median(e[ok])),'inlier_p95_error_px':float(np.percentile(e[ok],95)),'inlier_max_error_px':float(e[ok].max()),'inlier_source_bbox_xyxy':[float(x[ok,0].min()),float(x[ok,1].min()),float(x[ok,0].max()),float(x[ok,1].max())],'matches':[{'native_xy':u.tolist(),'raw_xy':v.tolist(),'inlier':bool(i),'error_px':float(t)} for u,v,i,t in zip(x,y,ok,e)],'sha256':{f.name:sha(f) for f in R.iterdir() if f.is_file()},'software':{'opencv':cv2.__version__,'numpy':np.__version__,'python':platform.python_version()},'limitations':'Similarity registration only; generated underlay has local redrawing. Residual feature error is not anatomical-joint accuracy. Raw photo pixels are unmodified.'}
(P/'registration.json').write_text(json.dumps(reg,indent=2))
# Names describe image side. Image-left is subject right in this approximately frontal image.
# Human reviewed seed locations select marker identity. Pixel center refined by distance-transform disk core.
seeds=[
('eye_image_left',290,178,150,.85,'visible surface','right eye center'),('eye_image_right',387,183,150,.85,'visible surface','left eye center'),
('ear_image_left',251,191,90,.35,'occluded/inferred','right ear proxy'),('ear_image_right',470,204,90,.35,'occluded/inferred','left ear proxy'),
('nose',327,243,0,.85,'visible surface','nose tip'),
('neckline_center',410,441,30,.65,'visible garment surface','upper chest/neckline surface proxy; NOT cervical joint'),
('shoulder_image_left',191,458,20,.45,'joint hidden by garment','right shoulder joint approximate; garment surface marker'),
('shoulder_image_right',647,412,60,.45,'joint hidden by garment','left shoulder joint approximate; garment surface marker'),
('elbow_image_left',129,779,25,.5,'joint hidden by garment','right elbow approximate'),
('elbow_image_right',750,790,60,.5,'joint hidden by garment','left elbow approximate'),
('wrist_image_left',189,878,90,.8,'visible surface','right wrist surface center'),
('wrist_image_right',490,897,90,.8,'visible surface','left wrist surface center'),
('torso_midline',394,715,30,.5,'surface beneath garment','front torso surface midline near lower sternum; NOT spine head'),
('waist_image_left',187,1049,110,.6,'visible waistband surface','right waistband/iliac surface proxy; NOT femoral hip joint'),
('waist_image_right',527,1083,140,.6,'visible waistband surface','left waistband/iliac surface proxy; NOT femoral hip joint'),
('waist_midline',357,1090,30,.65,'visible waistband surface','front waistband center; NOT pelvis bone head'),
('hand_left_index_direction_a',270,827,115,.35,'illustrative hand nodes','subject right hand upper contour knuckle proxy; topology uncertain'),
('hand_left_index_direction_b',317,832,115,.35,'illustrative hand nodes','subject right hand upper contour direction proxy'),
('hand_left_palm',244,898,115,.45,'illustrative hand nodes','subject right palm/knuckle proxy; not verified MCP'),
('hand_right_upper_direction',404,849,115,.35,'illustrative hand nodes','subject left upper finger direction proxy; not verified MCP'),
('hand_right_palm',388,899,115,.45,'illustrative hand nodes','subject left palm/knuckle proxy; not verified MCP'),
('hand_right_lower_direction',397,965,115,.35,'illustrative hand nodes','subject left lower palm contour proxy')]
points=[];native=a.copy();overlay=b.copy()
for name,sx,sy,hue,conf,vis,semantic in seeds:
    radius=15 if 'hand_' not in name and 'eye_' not in name and 'ear_' not in name and name!='nose' else 7
    x0,y0=sx-radius,sy-radius;crop=hsv[y0:sy+radius+1,x0:sx+radius+1];dh=np.minimum(abs(crop[:,:,0].astype(float)-hue),180-abs(crop[:,:,0].astype(float)-hue)); cm=((dh<13)&(crop[:,:,1]>140)&(crop[:,:,2]>140)).astype(np.uint8)
    dist=cv2.distanceTransform(cm,cv2.DIST_L2,5); yy,xx=np.indices(dist.shape);near=((xx-radius)**2+(yy-radius)**2)<(radius*.75)**2;score=dist*near; _,peak,_,loc=cv2.minMaxLoc(score);cx,cy=loc
    # Disk core centroid local to max; avoid including attached skeleton lines.
    core=(dist>=max(1.5,peak*.7))&(((xx-cx)**2+(yy-cy)**2)<max(4,peak)**2)
    if core.sum(): nx,ny=float(xx[core].mean()+x0),float(yy[core].mean()+y0)
    else: nx,ny=float(sx),float(sy)
    raw=M@np.array([nx,ny,1]);p={'id':name,'native_xy':[nx,ny],'raw_xy':raw.tolist(),'semantic':semantic,'confidence':conf,'visibility':vis,'weight':conf,'uncertainty_px':4 if conf>=.8 else (9 if conf>=.5 else 15),'digitization':{'human_seed_xy':[sx,sy],'opencv_method':'HSV hue disk-core distance transform; human seed selects identity','disk_peak_radius_px':peak},'anatomical_side':'right' if 'image_left' in name else ('left' if 'image_right' in name else None)};points.append(p)
    col=(0,180,255) if conf<.7 else (255,160,0)
    for im,pt in [(native,(nx,ny)),(overlay,raw)]:
        pt=tuple(np.round(pt).astype(int));cv2.circle(im,pt,6,col,2);cv2.putText(im,name, (pt[0]+8,pt[1]-8),cv2.FONT_HERSHEY_SIMPLEX,.37,(10,10,10),2,cv2.LINE_AA);cv2.putText(im,name,(pt[0]+8,pt[1]-8),cv2.FONT_HERSHEY_SIMPLEX,.37,(255,255,255),1,cv2.LINE_AA)
links=[('neckline_center','torso_midline'),('torso_midline','waist_midline'),('neckline_center','shoulder_image_left'),('neckline_center','shoulder_image_right'),('shoulder_image_left','elbow_image_left'),('elbow_image_left','wrist_image_left'),('shoulder_image_right','elbow_image_right'),('elbow_image_right','wrist_image_right'),('waist_image_left','waist_midline'),('waist_midline','waist_image_right')]
by={p['id']:p for p in points}
for u,v in links:cv2.line(overlay,tuple(np.round(by[u]['raw_xy']).astype(int)),tuple(np.round(by[v]['raw_xy']).astype(int)),(0,210,210),1,cv2.LINE_AA)
cv2.imwrite(str(P/'raw-target-overlay.png'),overlay);cv2.imwrite(str(P/'native-marker-review.png'),native)
result={'schema':'illustrative-pose-targets-v1','provenance':'OpenCV digitization of human-seeded colored markers in ImageGen illustration. NOT pose-detector truth. NOT measured anatomy.','coordinate_system':'raw original 1000x1276 top-left pixels; ids image_left/image_right refer viewer image sides','registration':'registration.json','raw_source':'../reference/original-product.jpg','imagegen_source':'../reference/imagegen-pose.png','points':points,'links':links,'fitting_guidance':['Use neutral M-size cm priors only as assumed scale, never recovered measurements.','Map neckline/torso/waist markers to front surface proxies at appropriate model heights; do not equate them with bone heads.','ImageGen hip points mark waistband, not femoral joints. Fit pelvis/waist position and torso rotation using surface landmarks plus raw contours.','Use eyes/nose/wrists relatively more; elbows/shoulders are garment-occluded and uncertain. Hand points are contour/direction proxies, not validated MCP joints.','A low point residual does not prove photo match. Inspect raw-photo overlays, torso/waist alignment, garment-vs-body contour semantics, hand direction, and shared 3D state.']}
(P/'pose-targets.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in reg.items() if k not in ['matches','sha256']},indent=2));print([(p['id'],np.round(p['raw_xy'],1).tolist()) for p in points])
feature_review=cv2.drawMatches(a,ka,b,kb,[z for z,i in zip(g,ok) if i],None,flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS)
feature_review=cv2.resize(feature_review,(1266,850));cv2.imwrite(str(P/'registration-feature-matches.jpg'),feature_review)
