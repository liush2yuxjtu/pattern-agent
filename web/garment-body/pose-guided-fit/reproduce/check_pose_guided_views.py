#!/usr/bin/env python3
"""Replay all canonical view PNGs from one state and independently project silhouettes."""
import sys,json,hashlib,importlib.util
from pathlib import Path
import cv2,numpy as np
from scipy.spatial.transform import Rotation
sys.path.insert(0,str((Path(__file__).resolve().parents[2]/'tools/human_fit/pose_guided').resolve()))
from runtime import Runtime,sha

def check(candidate):
 p=Path(candidate);v=p/'views';r=Runtime();checks={};fail=[]
 try:
  state=json.loads((v/'state.json').read_text());main=json.loads((p/'final-state.json').read_text());ev=r.evaluate(state);cam=json.loads((v/'camera.json').read_text());prov=json.loads((v/'view-provenance.json').read_text())
  same=state['dimensions']==main['dimensions'] and state['poseDegrees']==main['poseDegrees'];checks['same_pose_dimensions']=same
  if not same:fail.append('view state differs from main state')
  mainv=np.array([list(map(float,l.split()[1:4])) for l in (p/'posed.obj').read_text().splitlines() if l.startswith('v ')])
  err=float(np.max(np.linalg.norm(mainv-ev['posed'][r.ids],axis=1)));checks['main_mesh_vs_view_state_error_cm']=err
  if err>.001:fail.append('view state generates different mesh')
  ph=hashlib.sha256(json.dumps(state['poseDegrees'],sort_keys=True).encode()).hexdigest()
  spec=importlib.util.spec_from_file_location('replay_raster',str(Path(__file__).resolve().parents[2]/'tools/human_fit/pose_guided/render_mesh.py'));renderer=importlib.util.module_from_spec(spec);spec.loader.exec_module(renderer)
  joints=json.loads((v/'joints.json').read_text())
  for name in ['front','side','back']:
   pr=prov[name];hashok=pr['state_sha256']==sha(v/'state.json') and pr['pose_sha256']==ph and pr['posed_mesh_sha256']==sha(v/'posed.obj')
   projected=r.project(ev['joints'],cam,name);joint_error=float(np.max(np.linalg.norm(projected-np.array(pr['projected_joints']),axis=1)))
   independent=r.mask(ev['posed'],cam,name)>0;actual=cv2.imread(str(v/(name+'-mask.png')),0)>0;intersection=(independent&actual).sum();union=(independent|actual).sum();iou=float(intersection/max(union,1))
   mask,image,depth,z=renderer.raster(ev['posed'],r.faces,cam,name,joints)
   png=cv2.imread(str(v/(name+'.png')));png=cv2.cvtColor(png,cv2.COLOR_BGR2RGB) if False else png
   # renderer uses BGR OpenCV arrays just as Runtime.save.
   diff=float(np.mean(np.abs(image.astype(float)-png.astype(float))))
   ok=hashok and joint_error<.001 and iou>.999 and diff<.01
   checks[name]={'verdict':'PASS' if ok else 'FAIL','hashes_match':hashok,'joint_reprojection_max_px':joint_error,'independent_mask_iou':iou,'replay_png_mean_abs_channel_error':diff}
   if not ok:fail.append(name+' view failed content/provenance replay')
  photo=json.loads((p/'camera.json').read_text()) if (p/'camera.json').exists() else {}
  if (p/'photo-render.png').exists() and len(photo.get('final',[]))==6:
   pars=photo['final'];rot=Rotation.from_euler('YXZ',pars[3:],degrees=True).as_matrix();scale,cx,cy=pars[:3]
   expected_matrix=np.array([[*(scale*rot[0]),photo['width']/2-scale*cx],[*(-scale*rot[1]),photo['height']/2+scale*cy],[0,0,0,1]])
   matrix_error=float(np.max(abs(expected_matrix-np.array(photo['world_to_pixel_homogeneous']))))
   pc={'width':photo['width'],'height':photo['height'],'depth_range_cm':[-100,100],'views':{'photo':{'axis':'front','px_per_cm':scale,'center_cm':[cx,cy]}}}
   _,image,_,_=renderer.raster(ev['posed']@rot.T,r.faces,pc,'photo')
   png=cv2.imread(str(p/'photo-render.png'));photo_diff=float(np.mean(abs(image.astype(float)-png.astype(float))))
   ok=matrix_error<1e-8 and photo_diff<.01;checks['photo']={'verdict':'PASS' if ok else 'FAIL','camera_formula_matrix_max_abs_error':matrix_error,'replay_png_mean_abs_channel_error':photo_diff}
   if not ok:fail.append('photo PNG or camera matrix failed replay')
  return {'verdict':'FAIL' if fail else 'PASS','checks':checks,'failures':fail,'method':'One fresh FK/LBS state: independent silhouette raster, joint reprojection, hash contract and deterministic saved RGB renderer replay per front/side/back; excludes only differing cameras.'}
 except Exception as exc:return {'verdict':'FAIL','checks':checks,'failures':[str(exc)]}
 finally:r.close()
if __name__=='__main__':print(json.dumps(check(sys.argv[1]),indent=2))
