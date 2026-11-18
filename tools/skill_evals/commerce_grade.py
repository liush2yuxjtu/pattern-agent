#!/usr/bin/env python3
"""Independent, case-bound grading of actual apparel functional executions.

Private case annotations are evaluator input, never fitting input. This checker
rebuilds source geometry and pixels; manual review is a separately hash-bound
input. A descriptive assertion fraction cannot override a critical failure.
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'tools/human_fit/pose_guided'))
from runtime import Runtime
from render_mesh import raster


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p): return json.loads(Path(p).read_text())
def write(p, value):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    Path(p).write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n')


def output_hashes(folder):
    return {str(p.relative_to(folder)):sha(p) for p in sorted(folder.rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'}


def obj(path):
    vertices, faces = [], []
    for line in Path(path).read_text().splitlines():
        if line.startswith('v '): vertices.append(list(map(float,line.split()[1:4])))
        elif line.startswith('f '):
            ids=[int(x.split('/')[0])-1 for x in line.split()[1:]]
            for i in range(1,len(ids)-1):faces.append([ids[0],ids[i],ids[i+1]])
    v,f=np.asarray(vertices,float),np.asarray(faces,int)
    if v.ndim!=2 or v.shape[1]!=3 or not np.isfinite(v).all():raise ValueError('Invalid actual OBJ vertices')
    if f.ndim!=2 or f.shape[1]!=3 or f.min()<0 or f.max()>=len(v):raise ValueError('Invalid actual OBJ topology')
    return v,f


def project(points, matrix):
    q=np.c_[points,np.ones(len(points))]@matrix.T
    if not np.isfinite(q).all() or (abs(q[:,2])<1e-10).any():raise ValueError('Invalid source-camera projection')
    return q[:,:2]/q[:,2,None]


def projected_mask(points, faces, matrix, size):
    xy=project(points,matrix);mask=np.zeros(size,np.uint8)
    for f in faces:cv2.fillConvexPoly(mask,np.rint(xy[f]).astype(np.int32),255)
    return mask>0


def photo_replay(runtime, evaluated, camera):
    """3x4 matrix is authoritative; don't guess meanings of a six-value final list."""
    matrix=np.asarray(camera['world_to_pixel_homogeneous'],float)
    if matrix.shape!=(3,4) or not np.allclose(matrix[2],[0,0,0,1],atol=1e-9):raise ValueError('Expected declared oblique orthographic matrix')
    scale=float(np.linalg.norm(matrix[0,:3]));rx=matrix[0,:3]/scale;ry=-matrix[1,:3]/scale
    if abs(np.linalg.norm(ry)-1)>1e-6 or abs(rx@ry)>1e-6:raise ValueError('Non-orthographic matrix rows')
    rotation=np.array([rx,ry,np.cross(rx,ry)]);w,h=int(camera['width']),int(camera['height'])
    center=[(w/2-matrix[0,3])/scale,(matrix[1,3]-h/2)/scale]
    replay_camera=dict(width=w,height=h,depth_range_cm=camera.get('depth_range_cm',[-60,60]),
        views={'photo':dict(axis='front',px_per_cm=scale,center_cm=center)})
    return raster(evaluated['posed']@rotation.T,runtime.faces,replay_camera,'photo')


def view_integrity(runtime, evaluated, candidate, camera):
    v=candidate/'views';state=read(v/'state.json');main=read(candidate/'final-state.json');cam=read(v/'camera.json');prov=read(v/'view-provenance.json');joints=read(v/'joints.json')
    checks={};fail=[]
    same=state['dimensions']==main['dimensions'] and state['poseDegrees']==main['poseDegrees'];checks['same_complete_state']=same
    if not same:fail.append('canonical view state differs from final state')
    mesh,_=obj(v/'posed.obj');delta=float(np.max(np.linalg.norm(mesh-evaluated['posed'][runtime.ids],axis=1)));checks['mesh_error_cm']=delta
    if delta>.001:fail.append('canonical mesh differs from source body')
    posehash=hashlib.sha256(json.dumps(state['poseDegrees'],sort_keys=True).encode()).hexdigest()
    for name in ['front','side','back']:
        record=prov[name];hashes=record['state_sha256']==sha(v/'state.json') and record['pose_sha256']==posehash and record['posed_mesh_sha256']==sha(v/'posed.obj')
        projected=runtime.project(evaluated['joints'],cam,name);error=float(np.max(np.linalg.norm(projected-np.asarray(record['projected_joints']),axis=1)))
        actual_mask=cv2.imread(str(v/(name+'-mask.png')),0)>127;independent=runtime.mask(evaluated['posed'],cam,name)>0
        iou=float((actual_mask&independent).sum()/max((actual_mask|independent).sum(),1))
        _,rgb,_,_=raster(evaluated['posed'],runtime.faces,cam,name,joints)
        actual=cv2.imread(str(v/(name+'.png')));difference=float(np.mean(abs(rgb.astype(float)-actual.astype(float))))
        ok=hashes and error<.001 and iou>.999 and difference<.01
        checks[name]=dict(verdict='PASS' if ok else 'FAIL',hashes_match=hashes,joint_reprojection_max_px=error,independent_mask_iou=iou,png_mean_abs_channel_error=difference)
        if not ok:fail.append(name+' real content/state replay failed')
    mask,rgb,_,_=photo_replay(runtime,evaluated,camera);actual=cv2.imread(str(candidate/'photo-render.png'));difference=float(np.mean(abs(rgb.astype(float)-actual.astype(float))))
    actual_mask=cv2.imread(str(candidate/'final-mask.png'),0)>127;mask=mask>0;iou=float((mask&actual_mask).sum()/max((mask|actual_mask).sum(),1));ok=difference<.01 and iou>.999
    checks['photo']=dict(verdict='PASS' if ok else 'FAIL',png_mean_abs_channel_error=difference,independent_mask_iou=iou,camera_basis='Independent decomposition of authoritative 3x4 matrix; no final-list parameter assumption')
    if not ok:fail.append('source-photo PNG/mask replay failed')
    return dict(verdict='FAIL' if fail else 'PASS',checks=checks,failures=fail)


def paired_intervals(depths):
    """Unique crossings, paired in order; odd/open rays are unknown.

    A min/max hull incorrectly fills air between two disconnected limb intervals.
    """
    d=np.sort(np.asarray(depths,float));unique=[]
    for z in d:
        if not unique or z-unique[-1]>.001:unique.append(float(z))
    if len(unique)<2 or len(unique)%2:return None
    return [(unique[i],unique[i+1]) for i in range(0,len(unique),2) if unique[i+1]-unique[i]>=1]


def skin_intervals(runtime, evaluated):
    """Limited hand/core skin intervals; unknown rays are never called clear."""
    rest,posed=evaluated['shape']['rest'],evaluated['posed'];height=np.ptp(rest[runtime.ids,1])
    core=[i for i,n in enumerate(runtime.names) if n=='root' or n.startswith(('spine','pelvis','upperleg'))]
    weights=(np.isin(runtime.skin,core)*runtime.weight).sum(1)
    neutral=rest[runtime.faces]
    keep=np.all((weights[runtime.faces]>.5)&(neutral[:,:,1]>.45*height)&(neutral[:,:,1]<.86*height),axis=1)
    tri=posed[runtime.faces[keep]];A,B,C=tri[:,0],tri[:,1],tri[:,2]
    den=(B[:,1]-C[:,1])*(A[:,0]-C[:,0])+(C[:,0]-B[:,0])*(A[:,1]-C[:,1]);valid=abs(den)>1e-9
    A,B,C,den=A[valid],B[valid],C[valid],den[valid];hands={}
    for side in ['L','R']:
        bones=[i for i,n in enumerate(runtime.names) if n.endswith('.'+side) and n.startswith(('finger','wrist'))]
        select=(np.isin(runtime.skin,bones)*runtime.weight).sum(1)>.5;ids=runtime.ids[select[runtime.ids]]
        covered=0;depths_inside=[];clearances=[];ambiguous=0;multi_interval=0
        for vid in ids:
            x,y,z=posed[vid];u=((B[:,1]-C[:,1])*(x-C[:,0])+(C[:,0]-B[:,0])*(y-C[:,1]))/den
            v=((C[:,1]-A[:,1])*(x-C[:,0])+(A[:,0]-C[:,0])*(y-C[:,1]))/den;w=1-u-v
            hit=(u>=0)&(v>=0)&(w>=0);d=u[hit]*A[hit,2]+v[hit]*B[hit,2]+w[hit]*C[hit,2]
            intervals=paired_intervals(d)
            if intervals is None:ambiguous+=1;continue
            if not intervals:continue
            covered+=1;multi_interval+=int(len(intervals)>1);clearances.append(float(z-max(b for a,b in intervals)))
            local=[min(z-lo,hi-z) for lo,hi in intervals if lo+.05<z<hi-.05]
            if local:depths_inside.append(float(max(local)))
        hands[side]=dict(hand_vertices=len(ids),classified_rays=covered,coverage=covered/max(len(ids),1),
            odd_or_open_rays_unknown=ambiguous,multiple_disjoint_interval_rays=multi_interval,
            detected_inside_vertices=len(depths_inside),maximum_inside_depth_cm=max(depths_inside,default=0),
            minimum_front_clearance_cm=min(clearances) if clearances else None,
            verdict='UNKNOWN' if covered==0 else 'LIMITED_CHECK',
            limitation='Only deduplicated even crossing pairs of the selected hand/core skin patch are classified. Odd/open rays are UNKNOWN; disjoint intervals do not fill air. This is not cloth contact or universal collision proof.')
    return hands


def generation_entries(candidate):
    entries=[]
    per_file=list((candidate/'images').glob('*-receipt.json'))
    if per_file:
        for p in per_file:entries.append(dict(read(p),view=p.name.replace('-receipt.json','')))
        return entries
    for filename in ['generation-provenance.json','generation-receipts.json']:
        if not (candidate/filename).exists():continue
        ledger=read(candidate/filename);raw=ledger.get('images',ledger.get('entries',ledger.get('final',[])))
        if isinstance(raw,dict):raw=[dict(v,view=k) for k,v in raw.items()]
        for e in raw:
            if e.get('status')=='fulfilled':e=e['value']
            entries.append(dict(e,view=e.get('view',e.get('name'))))
        if entries:return entries
    return entries


def generation_evidence(candidate, source_sha):
    views=['front','side','back','closeup','pose','depth'];records=[];fail=[];entries=generation_entries(candidate)
    hashes=[];native_hashes=[];all_refs=[]
    for view in views:
        p=candidate/'images'/f'{view}.png';entry=next((x for x in entries if x.get('view')==view),{})
        if not p.exists():fail.append('Missing independent image '+view);continue
        im=cv2.imread(str(p));h=sha(p);hashes.append(h)
        if im is None:fail.append('Undecodable image '+view);continue
        # Tool output_hint is retained verbatim in both actual receipt formats.
        matches=re.findall(r'/workspace/generated_images/exec-[A-Za-z0-9-]+[.]png',entry.get('output_hint',''))
        native=matches[0] if matches else entry.get('original_tool_file') or entry.get('native_source_path') or entry.get('native_path')
        npath=Path(native) if native else None
        if not npath or not npath.is_file():fail.append(view+' lacks original native tool file')
        elif sha(npath)!=h:fail.append(view+' is not byte-identical to native tool output')
        else:native_hashes.append(sha(npath))
        if min(im.shape[:2])<1024:fail.append(view+' below requested native high-resolution floor1024')
        if entry.get('sha256')!=h:fail.append(view+' receipt does not bind output hash')
        references=entry.get('reference_hashes')
        if references is None:
            raw=entry.get('input_sha256',{})
            references=[dict(original_tool_path=k,sha256=v) for k,v in raw.items()] if isinstance(raw,dict) else []
        if source_sha not in [r.get('sha256') for r in references]:fail.append(view+' receipt does not bind original source')
        verified_refs=[]
        for ref in references:
            declared=ref.get('original_tool_path');expected=ref.get('sha256');preserved=ref.get('preserved_exact_input');candidates=[Path(x) for x in [preserved,declared] if x]
            if declared:
                candidates += [candidate/'reference'/('generation-'+Path(declared).name),candidate/'reference'/('generation-input-'+Path(declared).name)]
            found=next((q for q in candidates if q.is_file() and sha(q)==expected),None)
            if not found:fail.append(view+' referenced input bytes not retained: '+str(declared))
            verified_refs.append(dict(declared_path=declared,sha256=expected,preserved_path=str(found) if found else None,still_matches_declared_current_file=bool(declared and Path(declared).is_file() and sha(Path(declared))==expected)))
        records.append(dict(view=view,sha256=h,width=im.shape[1],height=im.shape[0],native_file=str(npath) if npath else None,references=verified_refs))
        all_refs.extend(verified_refs)
    if len(set(hashes))!=6 or len(set(native_hashes))!=6:fail.append('Six distinct native image outputs not established; collage splitting is insufficient')
    snapshots=[p for p in [candidate/'reference/generation-final-state.json',candidate/'solver-continuous-state.json',candidate/'reference/generation-input-state.json'] if p.exists()]
    state_binding={}
    if snapshots and (candidate/'final-state.json').exists():
        before,after=read(snapshots[0]),read(candidate/'final-state.json')
        delta=max(abs(float(v)-float(after['poseDegrees'][name][i])) for name,a in before['poseDegrees'].items() for i,v in enumerate(a))
        state_binding=dict(generation_state_path=str(snapshots[0]),generation_state_sha256=sha(snapshots[0]),final_state_sha256=sha(candidate/'final-state.json'),same_dimensions=before['dimensions']==after['dimensions'],maximum_pose_angle_difference_degrees=delta,exact_same_state=before==after,
          interpretation='Generation inputs are their retained pre-UI-normalization snapshot when hashes differ; do not relabel them as the final render. This subclaim is reported separately, not retrofitted as a new assertion.')
    if snapshots:
        runtime=Runtime()
        try:
            evaluated=runtime.evaluate(read(snapshots[0]));camera=read(candidate/'camera.json');vc=read(candidate/'views/camera.json');replays={}
            retained={Path(r['declared_path']).name:r['preserved_path'] for r in all_refs if r.get('declared_path') and r.get('preserved_path')}
            for name in ['photo-render','front','side','back']:
                path=retained.get(name+'.png')
                if not path:continue
                if name=='photo-render':_,rgb,_,_=photo_replay(runtime,evaluated,camera)
                else:_,rgb,_,_=raster(evaluated['posed'],runtime.faces,vc,name)
                actual=cv2.imread(path)
                error=float(np.mean(abs(actual.astype(float)-rgb.astype(float)))) if actual.shape==rgb.shape else None
                replays[name]=dict(retained_sha256=sha(path),mean_abs_channel_error=error,verdict='PASS' if error is not None and error<.01 else 'NOT_REPLAYED_WITH_CURRENT_CAMERA',camera_note='Reuses camera whose unchanged matrix is evidenced in TRACE; mismatch would need retained pre-generation camera rather than invention.')
            state_binding['actual_preserved_input_replays']=replays
        except Exception as exc:state_binding['archive_replay_error']=str(exc)
        finally:runtime.close()
    return dict(verdict='PASS' if not fail else 'FAIL',images=records,failures=fail,generation_model_version=state_binding,
        limit='Independent transcript review still needed; retained native files and hashed inputs are verified, not just filename presence.')


def grade(candidate, case_path, out, manual_path=None):
    candidate,case_path,out=Path(candidate).resolve(),Path(case_path).resolve(),Path(out).resolve();out.mkdir(parents=True,exist_ok=True)
    case=read(case_path);base=case_path.parent
    for label,entry in case['files'].items():
        if sha(base/entry['path'])!=entry['sha256']:raise ValueError('Frozen evaluator input changed: '+label)
    annotations=read(base/case['files']['annotations.json']['path']);global_rule=read(base/'global-protocol.json');t=global_rule['thresholds']
    for name,expected in global_rule['runtime_source_hashes'].items():
        if sha(ROOT/name)!=expected:raise ValueError('Frozen source engine changed: '+name)
    image=cv2.imread(str(base/'original.jpg'));ref=cv2.imread(str(base/'reference-mask.png'),0)>127
    if list(image.shape[1::-1])!=annotations['image_size'] or ref.shape!=image.shape[:2]:raise ValueError('Frozen source image/mask dimensions differ')
    yy,xx=np.where(ref);reference_height=int(yy.max()-yy.min()+1);shape=ref.shape
    initial_hashes=output_hashes(candidate);result=dict(case_id=case['case_id'],scope=annotations['generation_scope'],
        protocol_sha256=sha(case_path),global_protocol_sha256=sha(base/'global-protocol.json'),
        input_sha256=sha(base/'original.jpg'),reference_sha256=sha(base/'original.jpg'),artifact_sha256=initial_hashes,
        grader_implementation_sha256=sha(Path(__file__)),grader_version='1.1-paired-crossings',native_claude_execution='BLOCKED: explicitly injected functional subagent runs, not native Claude routing')
    for key,name in [('state_sha256','final-state.json'),('posed_obj_sha256','posed.obj'),('camera_sha256','camera.json')]:
        result[key]=sha(candidate/name) if (candidate/name).exists() else None
    assertions_path=base.parent.parent/'public-assertions.json';assertions=read(assertions_path);result['assertion_spec_sha256']=sha(assertions_path)
    checks={};evidence={};runtime=Runtime()
    try:
        state=read(candidate/'final-state.json');camera=read(candidate/'camera.json');matrix=np.asarray(camera['world_to_pixel_homogeneous'],float)
        if matrix.shape!=(3,4) or [camera['width'],camera['height']]!=annotations['image_size']:raise ValueError('Source camera must use unchanged original pixel frame')
        if state.get('asset')!=sha(runtime.asset) or state.get('units')!='cm':raise ValueError('State asset/unit contract differs')
        if set(state.get('poseDegrees',{}))!=set(runtime.names):raise ValueError('Complete163-bone pose required')
        evaluated=runtime.evaluate(state);vertices,faces=obj(candidate/'posed.obj');neutral,_=obj(candidate/'neutral.obj')
        actual=evaluated['posed'][runtime.ids];rest=evaluated['shape']['rest'][runtime.ids]
        if actual.shape!=vertices.shape or neutral.shape!=rest.shape:raise ValueError('Wrong actual mesh vertex count')
        posed_error=float(np.max(np.linalg.norm(actual-vertices,axis=1)));neutral_error=float(np.max(np.linalg.norm(rest-neutral,axis=1)))
        target_error=float(max(abs(evaluated['shape']['fit']['measurements'][k]-v) for k,v in state['dimensions'].items()))
        weight_error=float(np.max(abs(np.asarray(state['morphWeights'])-evaluated['shape']['fit']['weights'])))
        checks['anatomical_state']=max(posed_error,neutral_error)<t['mesh_reconstruction_max_error_cm'] and target_error<=t['neutral_measurement_max_target_error_cm'] and weight_error<1e-5 and abs(state['dimensions']['height']-170)<=.1
        result['source_reconstruction']=dict(posed_max_error_cm=posed_error,neutral_max_error_cm=neutral_error,neutral_target_max_error_cm=target_error,morph_weight_max_error=weight_error)
        evidence['anatomical_state']=json.dumps(result['source_reconstruction'])
        result['view_integrity']=view_integrity(runtime,evaluated,candidate,camera)
        checks['shared_views']=result['view_integrity']['verdict']=='PASS' and result['view_integrity'].get('checks',{}).get('photo',{}).get('verdict')=='PASS'
        evidence['shared_views']=json.dumps(result['view_integrity'])
        body=projected_mask(vertices,faces,matrix,shape);exterior=body&~ref
        distance=cv2.distanceTransform((~ref).astype('uint8'),cv2.DIST_L2,5)
        contour=body&~cv2.erode(body.astype('uint8'),np.ones((3,3),'uint8')).astype(bool);regions={}
        for name,(x0,y0,x1,y1) in annotations['regions'].items():
            roi=np.zeros(shape,bool);roi[y0:y1,x0:x1]=True;b=body&roi;c=contour&roi
            n=int(b.sum());outside=float((exterior&roi).sum()/max(n,1));p95=float(np.percentile(distance[c],95)) if c.any() else None
            ok=n>=max(100,np.prod(shape)*t['minimum_region_projected_body_area_fraction_of_image']) and outside<=t['region_maximum_outside_fraction'] and p95 is not None and p95<=reference_height*t['region_exterior_contour_p95_max_reference_height_fraction']
            regions[name]=dict(verdict='PASS' if ok else 'FAIL',body_pixels=n,outside_fraction=outside,exterior_contour_p95_px=p95,exterior_contour_p95_reference_height_fraction=p95/reference_height if p95 is not None else None)
        scans=[]
        for scan in annotations.get('scanlines',[]):
            y=scan['y'];lo,hi=scan['x_range'];rr=np.flatnonzero(ref[y,lo:hi]);bb=np.flatnonzero(body[y,lo:hi]);center=ratio=None;ok=False
            if len(rr)>1 and len(bb)>1:
                center=float(abs((bb[0]+bb[-1]-rr[0]-rr[-1])/2));ratio=float((bb[-1]-bb[0])/(rr[-1]-rr[0]))
                ok=center<=reference_height*t['waist_hip_center_max_error_reference_height_fraction'] and scan['width_ratio_min']<=ratio<=scan['width_ratio_max']
            scans.append(dict(y=y,center_error_px=center,width_ratio=ratio,verdict='PASS' if ok else 'FAIL'))
        result['original_photo_regions']=dict(reference_height_px=reference_height,regions=regions,scanlines=scans)
        checks['original_regions']=all(v['verdict']=='PASS' for v in regions.values()) and all(v['verdict']=='PASS' for v in scans)
        evidence['original_regions']=json.dumps(result['original_photo_regions'])
        cv2.imwrite(str(out/'independently-projected-mask.png'),body.astype('uint8')*255)
        overlay=image.copy();overlay[exterior]=(255,180,0);cv2.drawContours(overlay,cv2.findContours(body.astype('uint8'),cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)[0],-1,(255,90,0),2);cv2.imwrite(str(out/'regional-overlay.png'),overlay)
        joint_pixels=project(evaluated['joints'],matrix);points=annotations['reference_points'];cues={};violations=[];directions={}
        for name,point in points.items():
            xy=point['xy'];projected=joint_pixels[runtime.index[point['bone']]]
            error=float(np.linalg.norm(projected-xy)) if xy is not None else None
            visible=point['visibility'].startswith('visible') and xy is not None
            if name.startswith('wrist') and visible and error>reference_height*t['visible_wrist_max_error_reference_height_fraction']:violations.append(name+' observed surface cue too far')
            cues[name]=dict(projected_xy=projected.tolist(),target_xy=xy,error_px=error,visibility=point['visibility'],hard_position_gate=bool(visible and name.startswith('wrist')))
        for side in ['image_left','image_right']:
            for start,end in [('shoulder','elbow'),('elbow','wrist')]:
                a,b=points.get(start+'_'+side),points.get(end+'_'+side)
                if not a or not b or a['xy'] is None or b['xy'] is None:continue
                target=np.asarray(b['xy'])-a['xy'];actual_vec=joint_pixels[runtime.index[b['bone']]]-joint_pixels[runtime.index[a['bone']]]
                if np.linalg.norm(target)<.025*reference_height:continue
                angle=float(np.degrees(np.arccos(np.clip(target@actual_vec/max(np.linalg.norm(target)*np.linalg.norm(actual_vec),1e-12),-1,1))))
                name=side+'_'+start+'_'+end;directions[name]=dict(angle_error_degrees=angle,projected_length_px=float(np.linalg.norm(actual_vec)),reference_hypothesis_length_px=float(np.linalg.norm(target)))
                if angle>t['gross_limb_direction_reversal_degrees'] or np.linalg.norm(actual_vec)<.1*np.linalg.norm(target):violations.append(name+' gross reversed/collapsed limb')
        result['observed_action']=dict(visible_wrist_max_error_px=reference_height*t['visible_wrist_max_error_reference_height_fraction'],cues=cues,coarse_directions=directions,failures=violations)
        checks['observed_action']=not violations;evidence['observed_action']=json.dumps(result['observed_action'])
        result['hand_skin_intervals']=skin_intervals(runtime,evaluated)
    except Exception as exc:
        result['functional_error']=str(exc)
        for key in ['anatomical_state','shared_views','original_regions','observed_action']:checks.setdefault(key,False);evidence.setdefault(key,'Not established: '+str(exc))
    finally:runtime.close()
    # Human review comes from an independent evaluator, never the executor's own report.
    required=[p for p in initial_hashes if p in ['final-state.json','posed.obj','camera.json','photo-render.png','TRACE.md'] or p.startswith('images/') or p in ['views/front.png','views/side.png','views/back.png']]
    manual=read(manual_path) if manual_path and Path(manual_path).exists() else {};reviewed=manual.get('reviewed_artifact_sha256',{})
    manual_current=bool(manual) and manual.get('source_original_sha256')==result['input_sha256'] and all(reviewed.get(p)==initial_hashes[p] for p in required)
    observations={x['id']:x for x in manual.get('observations',[])} if manual_current else {}
    result['evaluation_status']='COMPLETE' if manual_current else 'INCOMPLETE_MANUAL_NOT_RUN'
    result['manual_review']=dict(current=manual_current,path=str(manual_path) if manual_path else None,observations=list(observations.values()))
    for assertion,observation in [('source_and_prior','source_and_prior'),('measurement_claims','measurement_claims')]:
        checks[assertion]=observations.get(observation,{}).get('verdict')=='PASS';evidence[assertion]=observations.get(observation,{}).get('evidence','Independent current source/report review unavailable; no affirmative evidence.')
    hands=result.get('hand_skin_intervals',{});severe=any(h['maximum_inside_depth_cm']>t['hand_maximum_detected_inside_depth_cm'] for h in hands.values())
    coverage_required=annotations['action']['requires_near_torso_hands'];coverage_ok=not coverage_required or (len(hands)==2 and all(h['coverage']>=t['hand_required_near_torso_ray_coverage_min'] for h in hands.values()))
    checks['three_d_action']=observations.get('pose_action_3d',{}).get('verdict')=='PASS' and bool(hands) and not severe and coverage_ok
    evidence['three_d_action']=json.dumps(dict(independent_manual=observations.get('pose_action_3d',{'verdict':'UNKNOWN'}),hand_intervals=hands,near_torso_coverage_required=coverage_required,severe_overlap=severe))
    definitions=assertions['shared_assertions']
    if annotations['generation_scope'].startswith('six_independent'):
        result['generation_evidence']=generation_evidence(candidate,result['input_sha256'])
        checks['native_six_generation']=result['generation_evidence']['verdict']=='PASS' and observations.get('generation_receipts',{}).get('verdict')=='PASS'
        evidence['native_six_generation']=json.dumps(dict(files=result['generation_evidence'],independent_receipts=observations.get('generation_receipts',{'verdict':'UNKNOWN'})))
        checks['garment_fidelity']=observations.get('garment_fidelity',{}).get('verdict')=='PASS';evidence['garment_fidelity']=observations.get('garment_fidelity',{}).get('evidence','Six original-image/item comparisons not independently verified.')
        definitions+=assertions['six_image_branch_additional_assertions']
    result['expectations']=[dict(text=x['text'],passed=bool(checks.get(x['id'],False)),evidence=evidence.get(x['id'],'Not verified')) for x in definitions]
    n=sum(x['passed'] for x in result['expectations']);result['summary']=dict(passed=n,failed=len(definitions)-n,total=len(definitions),pass_rate=n/len(definitions))
    result['overall_verdict']='PASS' if all(x['passed'] for x in result['expectations']) else 'FAIL'
    result['claims']=[dict(type='process',claim='Actual source engine reconstructs the saved adjustable anatomy.',verified=checks['anatomical_state'],evidence=evidence['anatomical_state']),dict(type='quality',claim='This run establishes the photographed person true centimetre dimensions or unique hidden depth.',verified=False,evidence='Single clothed image with generic M170 prior does not identify these quantities.'),dict(type='process',claim='A native Claude trigger benchmark was executed.',verified=False,evidence=result['native_claude_execution'])]
    result['eval_feedback']=dict(suggestions=[dict(reason='Min/max skin-ray hulls can fill air between disconnected anatomical sections; odd/open crossings do not establish clearance.',suggestion='Use deduplicated even crossing pairs, keep unclassified coverage UNKNOWN, and test disconnected/odd crossing controls.'),dict(reason='A camera.final list is representation-dependent; identical 3x4 camera matrices and content must be judged equally.',suggestion='Decompose the authoritative source-camera matrix and independently replay source pixels rather than assume cm-center semantics.'),dict(reason='Native image-generation file receipts establish execution and lineage, not preserved anatomy or photo-pose match.',suggestion='Keep independent cross-view generated/model/source visual review and report partial regional or wrist regressions explicitly; version any new quality assertion before new executions.')],overall='Inspect any non-discriminating assertion, false-positive local control or missing outcome; functional integrity cannot average away visual/action failure. No general skill advantage from n=1 per case.')
    write(out/'grading.json',result)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--candidate',required=True);parser.add_argument('--case',required=True);parser.add_argument('--out',required=True);parser.add_argument('--manual-review');args=parser.parse_args()
    result=grade(args.candidate,args.case,args.out,args.manual_review)
    print(json.dumps(dict(overall=result['overall_verdict'],summary=result['summary'],case=result['case_id'])))
