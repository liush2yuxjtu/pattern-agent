from pathlib import Path
import json,cv2,numpy as np
O=Path(__file__).parent;photo=cv2.imread(str(O/'reference/original.jpg')) if (O/'reference/original.jpg').exists() else cv2.imread('/workspace/work/pattern-agent/work/commerce-skill-evals-20261118/inputs/everlane-boatneck/original.jpg');ref=cv2.imread(str(O/'reference-mask.png'),0)>0
regions={'whole':[0,0,2400,3000],'shoulders':[600,900,1800,1300],'arms_left':[540,1250,830,2900],'arms_right':[1530,1250,1840,2900],'torso':[800,1200,1580,2150],'waist_hips':[740,1800,1690,2750]};result={}
def score(a,b):
 k=np.ones((3,3),np.uint8);ea=(a.astype('uint8')-cv2.erode(a.astype('uint8'),k))>0;eb=(b.astype('uint8')-cv2.erode(b.astype('uint8'),k))>0;da=cv2.distanceTransform((~ea).astype('uint8'),cv2.DIST_L2,5);db=cv2.distanceTransform((~eb).astype('uint8'),cv2.DIST_L2,5);ds=np.r_[da[eb],db[ea]];return {'iou':int((a&b).sum())/max(1,int((a|b).sum())),'dice':2*int((a&b).sum())/max(1,int(a.sum()+b.sum())),'contour_mean_px':float(ds.astype('float64').mean()) if ea.any() and eb.any() else None,'contour_p95_px':float(np.percentile(ds,95)) if ea.any() and eb.any() else None,'model_outside_reference_ratio':int((b&~a).sum())/max(1,int(b.sum()))}
for stage in ['initial','final']:
 m=cv2.imread(str(O/(stage+'-mask.png')),0)>0;result[stage]={}
 for name,(x0,y0,x1,y1) in regions.items():result[stage][name]=score(ref[y0:y1,x0:x1],m[y0:y1,x0:x1])
 colors=np.zeros_like(photo);colors[ref&m]=[30,210,30];colors[ref&~m]=[210,30,210];colors[~ref&m]=[220,210,0];active=ref|m;ov=photo.copy();ov[active]=(.7*photo[active]+.3*colors[active]).astype('uint8');cv2.imwrite(str(O/(stage+'-overlay.png')),ov)
result['protocol']={'resolution':[2400,3000],'segmentation':'GrabCut600x750 then nearest resize; includes garment/hair; arm gaps imperfect','regions':regions,'camera':'same final camera for initial/final','units':'pixels; not centimetre error','reference_sha256':__import__('hashlib').sha256((O/'reference-mask.png').read_bytes()).hexdigest()};(O/'metrics.json').write_text(json.dumps(result,indent=2));print(result['initial']['whole'],result['final']['whole'])
