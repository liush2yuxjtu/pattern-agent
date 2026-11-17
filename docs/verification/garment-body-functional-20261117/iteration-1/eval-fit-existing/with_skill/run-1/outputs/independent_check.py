from pathlib import Path
import json
import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import distance_transform_edt
import cv2
P=Path(__file__).resolve().parent
m=json.loads((P/'metrics.json').read_text());results={}
for stage in ['initial','final']:
 for view in ['front','side']:
  a=np.asarray(Image.open(P/f'target-{view}-mask.png').convert('L'))>127
  b=np.asarray(Image.open(P/f'{stage}-{view}-mask.png').convert('L'))>127
  def edge(x):
   c,_=cv2.findContours(x.astype(np.uint8),cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_NONE)
   z=np.zeros_like(x,dtype=np.uint8);cv2.drawContours(z,c,-1,1,1);return z.astype(bool)
  ea,eb=edge(a),edge(b);d=np.r_[distance_transform_edt(~ea)[eb],distance_transform_edt(~eb)[ea]]
  q=dict(iou=float((a&b).sum()/(a|b).sum()),dice=float(2*(a&b).sum()/(a.sum()+b.sum())),mean_symmetric_contour_distance_px=float(d.mean()),p95_symmetric_contour_distance_px=float(np.percentile(d,95)))
  assert all(abs(q[k]-m[stage][view][k])<1e-6 for k in q);results[f'{stage}-{view}']=q
for view in ['front','side']:assert m['final'][view]['iou']-m['initial'][view]['iou']>.03
lines=(P/'fitted.obj').read_text().splitlines();v=np.array([[float(x) for x in l.split()[1:]] for l in lines if l.startswith('v ')]);f=np.array([[int(x)-1 for x in l.split()[1:]] for l in lines if l.startswith('f ')])
for view in ['front','side']:
 im=Image.new('L',(384,640));dr=ImageDraw.Draw(im);x=v[:,0 if view=='front' else 2];xy=np.c_[(x+50)*384/100,(180-v[:,1])*640/184]
 for face in f:dr.polygon([tuple(p) for p in xy[face]],fill=255)
 assert np.array_equal(np.array(im)>127,np.asarray(Image.open(P/f'final-{view}-mask.png').convert('L'))>127)
results['mesh_projection_matches_saved_masks']=True
(P/'independent-check.json').write_text(json.dumps(results,indent=2)+'\n')
canvas=Image.new('RGB',(384*5,680),'white');draw=ImageDraw.Draw(canvas)
for i,n in enumerate(['initial-front-overlay','front-overlay','initial-side-overlay','side-overlay','back']):
 canvas.paste(Image.open(P/f'{n}.png').convert('RGB'),(384*i,40));draw.text((384*i+10,12),n,fill='black')
canvas.save(P/'review-sheet.png')
(P/'index.html').write_text('''<!doctype html><meta charset="utf-8"><title>Synthetic proxy fit</title><style>body{font:16px system-ui;margin:24px;background:#eef1f4} img{max-width:100%} table{border-collapse:collapse}td,th{padding:10px;border:1px solid #bbb}.views{display:flex;flex-wrap:wrap}.views img{width:250px}</style><h1>Synthetic proxy silhouette fit</h1><p>170 cm height prior; frozen orthographic camera. Two synthetic target masks only. No anatomical accuracy claim.</p><table><tr><th>View</th><th>Initial IoU</th><th>Final IoU</th></tr><tr><td>Front</td><td>0.952754</td><td>1.000000</td></tr><tr><td>Side</td><td>0.888754</td><td>1.000000</td></tr></table><p>Overlays: green overlap; pink target-only; cyan mesh-only. Back is an unobserved synthetic projection.</p><img src="review-sheet.png"><div class="views"><img src="front.png"><img src="side.png"><img src="back.png"></div><p><a href="fitted.obj">Actual OBJ</a> · <a href="params.json">Fitted controls</a> · <a href="metrics.json">Metrics</a> · <a href="report.md">Evidence and uncertainty report</a> · <a href="independent-check.json">Independent validation</a> · <a href="reproduce.py">Reproduce</a></p>''')
print(json.dumps(results,indent=2))
