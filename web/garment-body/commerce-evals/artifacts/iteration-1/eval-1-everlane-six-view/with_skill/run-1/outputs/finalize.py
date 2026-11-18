from pathlib import Path
import json,sys,shutil,os,hashlib
import cv2,numpy as np
from scipy.spatial.transform import Rotation
O=Path(__file__).parent;ROOT=Path('/workspace/work/pattern-agent');sys.path.insert(0,str(ROOT/'tools/human_fit/pose_guided'));from runtime import Runtime,sha
from render_mesh import raster
r=Runtime();s=json.loads((O/'final-state.json').read_text());cam=json.loads((O/'camera.json').read_text());x=np.array(cam['final']);w,h=cam['width'],cam['height'];R=Rotation.from_euler('YXZ',x[3:6],degrees=True).as_matrix()
for name in ['photo-render.png','views/front.png','views/side.png','views/back.png']:shutil.copy(O/name,O/'reference'/('generation-input-'+Path(name).name))
(O/'solver-continuous-state.json').write_text(json.dumps(s,indent=2));s['poseDegrees']={k:[round(v,1) for v in a] for k,a in s['poseDegrees'].items()};s=r.canonical_state(s);(O/'final-state.json').write_text(json.dumps(s,indent=2));e=r.evaluate(s);r.write_obj(O/'neutral.obj',e['shape']['rest']);r.write_obj(O/'posed.obj',e['posed']);rc={'width':w,'height':h,'depth_range_cm':[-60,60],'views':{'photo':{'axis':'front','px_per_cm':x[0],'center_cm':[(w/2-x[1])/x[0],(x[2]-h/2)/x[0]]}}};m,im,dep,z=raster(e['posed']@R.T,r.faces,rc,'photo');cv2.imwrite(str(O/'photo-render.png'),im);cv2.imwrite(str(O/'final-render.png'),im);cv2.imwrite(str(O/'final-mask.png'),m);np.save(O/'rawdepth.npy',z.astype('float32'));cv2.imwrite(str(O/'depth-valid.png'),np.isfinite(z).astype('uint8')*255);cv2.imwrite(str(O/'geometric-depth.png'),dep)
p=e['joints']@R.T;xy=np.c_[x[1]+x[0]*p[:,0],x[2]-x[0]*p[:,1]];jp=json.loads((O/'projected-pose.json').read_text());poseim=im.copy()
for i,row in enumerate(jp['points']):
 row['world_cm']=e['joints'][i].tolist();row['pixel']=xy[i].tolist();row['inside_canvas']=bool(0<=xy[i,0]<w and 0<=xy[i,1]<h)
 par=r.parent[i]
 if par>=0 and row['inside_canvas']:cv2.line(poseim,tuple(xy[i].astype(int)),tuple(xy[par].astype(int)),(0,150,255),3)
(O/'projected-pose.json').write_text(json.dumps(jp,indent=2));cv2.imwrite(str(O/'geometric-pose.png'),poseim);vc=json.loads((O/'views/camera.json').read_text());r.save(s,vc,O/'views');r.close()
# Native receipt hashes bind exact generation inputs, preserved before UI rounding.
for name in ['front','side','back','closeup','pose','depth']:
 rp=O/'images'/f'{name}-receipt.json';d=json.loads(rp.read_text());im=cv2.imread(str(O/'images'/f'{name}.png'));d['native_size']=[im.shape[1],im.shape[0]];d['sha256']=sha(O/'images'/f'{name}.png');d['reference_hashes']=[]
 for ref in d['refs']:
  old=Path(ref);actual=O/'reference'/('generation-input-'+old.name) if old.name in ['photo-render.png','front.png','side.png','back.png'] else old
  d['reference_hashes'].append({'original_tool_path':ref,'preserved_exact_input':str(actual),'sha256':sha(actual)})
 rp.write_text(json.dumps(d,indent=2))
I=ROOT/'work/commerce-skill-evals-20261118/inputs/everlane-boatneck';shutil.copy(I/'original.jpg',O/'reference/original.jpg');shutil.copy(I/'source.json',O/'reference/source.json');(O/'input-provenance.json').write_text(json.dumps({'original':json.loads((I/'source.json').read_text()),'asset_sha256':sha(ROOT/'web/human-studio/assets/human.json'),'runtime_sha256':sha(ROOT/'tools/human_fit/pose_guided/runtime.py'),'skill_sha256':sha(ROOT/'work/commerce-skill-evals-20261118/skill-v1/SKILL.md'),'telemetry':{'tokens':None,'image_generation_seconds':None}},indent=2));(O/'run.json').write_text(json.dumps({'mode':'prior_avatar','dimensions_basis':'authorized shared M170 prior','image_generation':'one preliminary plus six independent final actual image_gen calls','final_state_sha256':sha(O/'final-state.json'),'pose_ui_normalization':'rounded to0.1deg after generation; continuous exact generation input preserved','no_real_person_measurement':True},indent=2))
url=os.path.relpath(ROOT/'web/human-studio',O)+'/?model=/'+str((O/'final-state.json').relative_to(ROOT));gallery=''.join(f'<figure><img src="images/{n}.png"><figcaption>{n} — generated hypothesis</figcaption></figure>' for n in ['front','side','back','closeup','pose','depth']);(O/'viewer.html').write_text('<!doctype html><meta charset="utf-8"><title>Everlane conditional avatar</title><style>body{font:16px system-ui;margin:24px}iframe{width:100%;height:850px;border:1px solid #ccc}main{display:flex;flex-wrap:wrap}figure{width:28%}img{width:100%}</style><h1>Everlane: editable conditional avatar</h1><p>M170 prior; inferred hidden views. Pose/depth generated images are illustrative. Serve repository root over HTTP.</p><a href="'+url+'">Open centimetre and full-pose editor</a><iframe src="'+url+'"></iframe><main>'+gallery+'</main>')
print('finalized',len(s['poseDegrees']))
