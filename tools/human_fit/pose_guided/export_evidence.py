#!/usr/bin/env python3
"""Transparent real renders, projected FK, cm measurements and posed/neutral GLB from one state."""
import argparse,json,struct,hashlib
from pathlib import Path
import numpy as np,cv2
from scipy.spatial.transform import Rotation
from runtime import Runtime,sha

def glb(path,vertices,faces):
 p=(np.asarray(vertices,dtype=np.float32)*.01).astype('<f4');idx=np.asarray(faces,dtype='<u4').reshape(-1);n=np.zeros_like(p);tn=np.cross(p[faces[:,1]]-p[faces[:,0]],p[faces[:,2]]-p[faces[:,0]])
 for i in range(3):np.add.at(n,faces[:,i],tn)
 n/=np.maximum(np.linalg.norm(n,axis=1)[:,None],1e-12);pb=p.tobytes();nb=n.astype('<f4').tobytes();ib=idx.tobytes();blob=pb+nb+ib
 doc=dict(asset=dict(version='2.0',generator='actual MakeHuman FK/LBS pose-guided evidence'),scene=0,scenes=[dict(nodes=[0])],nodes=[dict(mesh=0,name='same-state human metres')],meshes=[dict(primitives=[dict(attributes=dict(POSITION=0,NORMAL=1),indices=2,material=0)])],materials=[dict(pbrMetallicRoughness=dict(baseColorFactor=[.62,.67,.68,1],metallicFactor=0,roughnessFactor=.8),doubleSided=True)],buffers=[dict(byteLength=len(blob))],bufferViews=[dict(buffer=0,byteOffset=0,byteLength=len(pb),target=34962),dict(buffer=0,byteOffset=len(pb),byteLength=len(nb),target=34962),dict(buffer=0,byteOffset=len(pb)+len(nb),byteLength=len(ib),target=34963)],accessors=[dict(bufferView=0,componentType=5126,count=len(p),type='VEC3',min=p.min(0).tolist(),max=p.max(0).tolist()),dict(bufferView=1,componentType=5126,count=len(p),type='VEC3'),dict(bufferView=2,componentType=5125,count=len(idx),type='SCALAR')]);j=json.dumps(doc,separators=(',',':')).encode();j+=b' '*((-len(j))%4);blob+=b'\0'*((-len(blob))%4);Path(path).write_bytes(struct.pack('<4sII',b'glTF',2,12+8+len(j)+8+len(blob))+struct.pack('<II',len(j),0x4e4f534a)+j+struct.pack('<II',len(blob),0x004e4942)+blob)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--candidate',required=True);a=ap.parse_args();out=Path(a.candidate);r=Runtime()
 try:
  s=json.load(open(out/'final-state.json'));e=r.evaluate(s);cam=json.load(open(out/'camera.json'));M=np.array(cam['world_to_pixel_homogeneous']);uv=(np.c_[e['joints'],np.ones(len(e['joints']))]@M.T)[:,:2];joints=[dict(name=n,parent=r.bones[i]['parent'],position=e['joints'][i].tolist(),pixel_photo=uv[i].tolist()) for i,n in enumerate(r.names)];(out/'joints.json').write_text(json.dumps(dict(joints=joints),indent=2));sk=np.zeros((1276,1000,4),'uint8');keep={'neck01','head','upperarm01.L','upperarm01.R','lowerarm01.L','lowerarm01.R','wrist.L','wrist.R','spine01','spine02','spine03','spine04','spine05','root','upperleg01.L','upperleg01.R','lowerleg01.L','lowerleg01.R'}
  for i,n in enumerate(r.names):
   parent=r.parent[i]
   if n in keep and parent>=0:cv2.line(sk,tuple(np.rint(uv[i]).astype(int)),tuple(np.rint(uv[parent]).astype(int)),(20,80,240,240),3);cv2.circle(sk,tuple(np.rint(uv[i]).astype(int)),4,(30,240,250,255),-1)
  cv2.imwrite(str(out/'photo-skeleton.png'),sk);im=cv2.imread(str(out/'photo-render.png'));mask=cv2.imread(str(out/'final-mask.png'),0);cv2.imwrite(str(out/'photo-render-alpha.png'),np.dstack([im,mask]));thin=np.zeros_like(sk);cv2.drawContours(thin,cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)[0],-1,(250,180,0,255),2);cv2.imwrite(str(out/'photo-contour.png'),thin)
  if (out/'views/camera.json').exists():
   viewcam=json.load(open(out/'views/camera.json'));cam['views']={}
   for name,c in viewcam['views'].items():
    axis=np.array([0,0,1]) if c['axis']=='side' else np.array([-1,0,0]) if c['axis']=='back' else np.array([1,0,0]);scale=c['px_per_cm'];cx,cy=c['center_cm'];cam['views'][name]=dict(**c,world_to_pixel_homogeneous=[[*list(axis*scale),viewcam['width']/2-cx*scale],[0,-scale,0,viewcam['height']/2+cy*scale],[0,0,0,1]])
   (out/'camera.json').write_text(json.dumps(cam,indent=2))
  glb(out/'posed.glb',e['posed'][r.ids],r.body_faces);glb(out/'neutral.glb',e['shape']['rest'][r.ids],r.body_faces)
  bones={}
  for side in ['L','R']:
   for key,a1,b1 in [('upper_arm','upperarm01.','lowerarm01.'),('forearm','lowerarm01.','wrist.')]:bones[key+'.'+side]=float(np.linalg.norm(e['shape']['heads'][r.index[a1+side]]-e['shape']['heads'][r.index[b1+side]]))
  hands={};pinches=[]
  for side in ['L','R']:
   tips=[]
   for digit in [1,2]:
    b=r.bones[r.index[f'finger{digit}-3.{side}']];tips.append(e['posed'][r.data['joints'][b['tail']]].mean(0))
   pinch=np.mean(tips,axis=0);pinches.append(pinch);hands[side]=dict(wrist_cm=e['joints'][r.index['wrist.'+side]].tolist(),thumb_index_tip_gap_cm=float(np.linalg.norm(tips[0]-tips[1])),pinch_center_cm=pinch.tolist())
  hands['wrist_distance_cm']=float(np.linalg.norm(e['joints'][r.index['wrist.L']]-e['joints'][r.index['wrist.R']]));hands['pinch_center_distance_cm']=float(np.linalg.norm(pinches[0]-pinches[1]));(out/'grasp-geometry.json').write_text(json.dumps(hands,indent=2))
  measures=dict(targets_cm=s['dimensions'],actual_neutral_surface_measurements_cm=s['measuredNeutral'],bone_head_distances_cm=bones,maximum_target_error_cm=s['maximumTargetErrorCm'],basis='Generic M170 prior with actually optimized shoulder/arm ruler candidates; NOT recovered real-person body sizes',posed_height_cm=float(np.ptp(e['posed'][r.ids,1])),angles_local_XYZ_degrees=s['poseDegrees']);(out/'measurements.json').write_text(json.dumps(measures,indent=2));(out/'evidence-manifest.json').write_text(json.dumps({p.name:sha(p) for p in out.iterdir() if p.is_file() and p.name!='evidence-manifest.json'},indent=2))
 finally:r.close()
if __name__=='__main__':main()
