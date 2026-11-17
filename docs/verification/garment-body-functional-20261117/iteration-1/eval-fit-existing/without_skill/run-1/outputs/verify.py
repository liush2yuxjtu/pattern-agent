#!/usr/bin/env python3
"""Independent OpenCV mask metric check and OBJ reopen/rerender check."""
from pathlib import Path
import json, numpy as np, cv2
from PIL import Image
import generator
out=Path(__file__).resolve().parent
record=json.loads((out/'metrics.json').read_text())
results={}
for stage in ['initial','final']:
    results[stage]={}
    for view in ['front','side']:
        a=cv2.imread(str(out/f'{stage}-{view}-mask.png'),0)>127
        b=cv2.imread(str(out.parent/'inputs'/f'target-{view}-mask.png'),0)>127
        kernel=cv2.getStructuringElement(cv2.MORPH_CROSS,(3,3))
        ca=a & ~cv2.erode(a.astype('uint8'),kernel).astype(bool)
        cb=b & ~cv2.erode(b.astype('uint8'),kernel).astype(bool)
        da=cv2.distanceTransform((~ca).astype('uint8'),cv2.DIST_L2,cv2.DIST_MASK_PRECISE)
        db=cv2.distanceTransform((~cb).astype('uint8'),cv2.DIST_L2,cv2.DIST_MASK_PRECISE)
        ds=np.concatenate([da[cb],db[ca]]).astype(float)
        inter=np.count_nonzero(a&b)
        m=dict(iou=inter/np.count_nonzero(a|b),dice=2*inter/(a.sum()+b.sum()),mean_symmetric_contour_distance_px=ds.mean(),p95_symmetric_contour_distance_px=np.percentile(ds,95))
        assert all(abs(m[k]-record[stage][view][k])<1e-6 for k in m)
        results[stage][view]={k:float(value) for k,value in m.items()}
v=[];f=[]
for line in (out/'fitted.obj').read_text().splitlines():
    parts=line.split()
    if parts and parts[0]=='v':v.append(list(map(float,parts[1:])))
    elif parts and parts[0]=='f':f.append([int(x)-1 for x in parts[1:]])
v=np.array(v);f=np.array(f)
assert np.isfinite(v).all() and len(f)>0 and f.shape[1]==3
for view in ['front','side','back']:
    path=out/'_verification.png'
    generator.render(v,f,path,view)
    assert np.array_equal(np.asarray(Image.open(path)),np.asarray(Image.open(out/f'{view}.png')))
    if view!='back':
        generator.render(v,f,path,view,True)
        assert np.array_equal(np.asarray(Image.open(path)),np.asarray(Image.open(out/f'final-{view}-mask.png')))
path.unlink()
for view in ['front','side']:assert results['final'][view]['iou']-results['initial'][view]['iou']>=.03
p=json.loads((out/'params.json').read_text());assert p['height']==170 and .45<=p['depth_ratio']<=1.05 and min(p.values())>0
results['checks']={'independent_opencv_metrics_match':True,'obj_reopened':True,'mesh_preview_and_final_mask_rerenders_pixel_identical':True,'both_iou_improvements_at_least_0.03':True,'constraints_pass':True}
(out/'verification.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(results,indent=2))
