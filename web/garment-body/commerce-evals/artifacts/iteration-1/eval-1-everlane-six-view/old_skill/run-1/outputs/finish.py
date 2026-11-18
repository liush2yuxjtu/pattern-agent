from pathlib import Path
import cv2,numpy as np,json,hashlib,os
P=Path(__file__).parent
ref=cv2.imread(str(P/'reference-mask.png'),0)>127
metrics=json.load(open(P/'metrics.json'))
def contours(m):return m & ~cv2.erode(m.astype('uint8'),np.ones((3,3),np.uint8)).astype(bool)
for name in ['initial','final']:
 m=cv2.imread(str(P/f'{name}-mask.png'),0)>127;a=contours(ref);b=contours(m);da=cv2.distanceTransform((~a).astype('uint8'),cv2.DIST_L2,5);db=cv2.distanceTransform((~b).astype('uint8'),cv2.DIST_L2,5);d=np.r_[da[b],db[a]];metrics[name]['symmetric_contour_mean_px']=float(d.mean());metrics[name]['symmetric_contour_p95_px']=float(np.percentile(d,95))
 regions={}
 for k,(x0,y0,x1,y1) in {'shoulders':(550,850,1850,1350),'arms':(500,1300,1850,2800),'torso':(800,1100,1550,2050),'waist_hips':(700,1900,1700,2600)}.items():
  a=ref[y0:y1,x0:x1];b=m[y0:y1,x0:x1];regions[k]={'iou':float((a&b).sum()/max((a|b).sum(),1)),'outside_fraction':float((b&~a).sum()/max(b.sum(),1))}
 metrics[name]['regions']=regions
json.dump(metrics,open(P/'metrics.json','w'),indent=2)
root=Path('/workspace/work/pattern-agent');rel=os.path.relpath(root/'web/human-studio/index.html',P)
(P/'viewer.html').write_text('''<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Editable conditional Everlane avatar</title><style>body{margin:0;font:16px system-ui}header{padding:12px;background:#eee}iframe{width:100%;height:90vh;border:0}</style><header>Conditional M170 avatar, not measured person. Full Human Studio controls below. Serve repository root over HTTP. <a href="final-state.json" download>Save fitted state</a> · <a href="overlay.png">Original overlay</a><span id="status"> Loading final state…</span></header><iframe id="studio" src="'''+rel+'''"></iframe><script>const f=document.querySelector('iframe');fetch('final-state.json').then(r=>r.json()).then(s=>{let tries=0;const t=setInterval(()=>{const m=f.contentWindow.humanStudio;if(m?.ready){m.setDimensions(s.dimensions);m.setPose(s.poseDegrees);document.querySelector('#status').textContent=' Final state loaded. Editing changes geometry; saved overlay belongs to frozen fit.';clearInterval(t)}else if(++tries>200){clearInterval(t);document.querySelector('#status').textContent=' Import final-state.json with Human Studio Import.'}},200)});</script>''')
(P/'run.json').write_text(json.dumps(dict(mode='prior_avatar',original='../../../inputs/everlane-boatneck/original.jpg',height_prior_cm=170,generic_size='M',person_measurement_accuracy='unavailable',image_generation='six independent final native calls + one preliminary guide',tokens=None),indent=2))
files={str(f.relative_to(P)):hashlib.sha256(f.read_bytes()).hexdigest() for f in P.rglob('*') if f.is_file() and f.name!='artifact-hashes.json'}
(P/'artifact-hashes.json').write_text(json.dumps(files,indent=2))
print(json.dumps(metrics))
