#!/usr/bin/env python3
"""Read-only receipt-layout adapter; leaves frozen commerce_grade v1.1 unchanged.

Audits receipts/{view}.json against real native outputs and referenced bytes.
Lossless PNG conversion is accepted only after exact decoded original-pixel
comparison. This is not a quality/pose/depth-style grader.
"""
import argparse,json,pathlib,hashlib,sys
import cv2,numpy as np
from commerce_grade import Runtime,raster,photo_replay
P=pathlib.Path
sha=lambda p:hashlib.sha256(P(p).read_bytes()).hexdigest()
read=lambda p:json.loads(P(p).read_text())
def audit(candidate,source):
 c=P(candidate).resolve();source=P(source).resolve();original=cv2.imread(str(source));records=[];fail=[];native_hashes=[]
 for view in ['front','side','back','closeup','pose','depth']:
  receipt=c/'receipts'/f'{view}.json';r=read(receipt);args=r.get('arguments',r.get('args',{}));native=P(r.get('native_output',r.get('path','')));output=c/'images'/f'{view}.png';im=cv2.imread(str(output));actual=sha(output)
  ok=native.is_file() and sha(native)==actual==r.get('native_sha256',r.get('output_sha256')) and min(im.shape[:2])>=1024
  refs=[];source_match=False
  ok&=set(args.get('referenced_image_paths',[]))==set(r['input_hashes'])
  for name,expected in r['input_hashes'].items():
   p=P(name);retained=p if p.is_file() and sha(p)==expected else c/'generation-inputs'/p.name
   valid=retained.is_file() and sha(retained)==expected;refim=cv2.imread(str(retained)) if valid else None
   pixel_match=refim is not None and refim.shape==original.shape and np.array_equal(refim,original)
   source_match|=pixel_match
   refs.append(dict(path=name,retained_path=str(retained),sha256=expected,byte_hash_verified=valid,exact_original_decoded_pixels=pixel_match))
   ok&=valid
  ok&=source_match
  if not ok:fail.append(view+' native/input verification failed')
  native_hashes.append(actual);records.append(dict(view=view,verdict='PASS' if ok else 'FAIL',receipt_sha256=sha(receipt),native_path=str(native),native_output_sha256=actual,native_size=[im.shape[1],im.shape[0]],references=refs))
 if len(set(native_hashes))!=6:fail.append('Six independent native hashes not established')
 g=c/'generation-inputs'
 if fail:return dict(version='receipt-layout-adapter-v1',adapter_sha256=sha(__file__),verdict='FAIL',images=records,failures=fail)
 state=next(p for p in [g/'state.json',g/'final-state.json'] if p.exists());camera=next(p for p in [g/'source-camera.json',g/'camera.json'] if p.exists());r=Runtime();replays={}
 try:
  e=r.evaluate(read(state));vc=read(c/'views/camera.json')
  for view in ['photo-render','front','side','back','pose','depth']:
   joints={'joints':[dict(name=n,parent=r.bones[i]['parent'],position=e['joints'][i].tolist()) for i,n in enumerate(r.names)]}
   _,rgb,dep,_=photo_replay(r,e,read(camera)) if view=='photo-render' else raster(e['posed'],r.faces,vc,view,joints)
   if view=='depth':rgb=dep
   actual=cv2.imread(str(g/(view+'.png')),cv2.IMREAD_UNCHANGED);delta=float(np.mean(abs(actual.astype(float)-rgb.astype(float))));replays[view]=dict(mean_abs_channel_error=delta,verdict='PASS' if delta<.01 else 'FAIL',sha256=sha(g/(view+'.png')))
 finally:r.close()
 if any(x['verdict']!='PASS' for x in replays.values()):fail.append('Retained generation state/render replay failed')
 return dict(version='receipt-layout-adapter-v1',adapter_sha256=sha(__file__),frozen_numeric_grader_sha256=sha(P(__file__).with_name('commerce_grade.py')),source_original_sha256=sha(source),verdict='FAIL' if fail else 'PASS',images=records,failures=fail,generation_state_sha256=sha(state),generation_camera_sha256=sha(camera),actual_generation_input_replays=replays,limits='Receipt parser compatibility only; no change to frozen assertion wording, numeric geometry thresholds or actual outputs. Six native files do not prove pose fidelity, depth style or unseen anatomy.')
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--candidate',required=True);p.add_argument('--source',required=True);p.add_argument('--out',required=True);a=p.parse_args();d=audit(a.candidate,a.source);out=P(a.out);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n');print(json.dumps(dict(verdict=d['verdict'],replays=d['actual_generation_input_replays'])))
