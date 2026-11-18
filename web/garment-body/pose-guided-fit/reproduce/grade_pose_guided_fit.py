#!/usr/bin/env python3
"""Independent matrix/OBJ regional fit critic. Does not grade real-person cm accuracy."""
import argparse,json,hashlib,sys
from pathlib import Path
import cv2,numpy as np

REPO_ROOT=Path(__file__).resolve().parents[2]
ARTIFACT_ROOT=REPO_ROOT/'work/pose-guided-fit-20261118'
if not ARTIFACT_ROOT.exists():ARTIFACT_ROOT=REPO_ROOT/'web/garment-body/pose-guided-fit'

def resolve_path(p):
    p=Path(p);value=str(p)
    prefix='work/pose-guided-fit-20261118/'
    if value.startswith(prefix):return ARTIFACT_ROOT/value[len(prefix):]
    if value=='work/single-state-skill-evals-20261117/fixtures/real-photo/reference-mask.png':return REPO_ROOT/'tools/human_fit/pose_guided/real-photo/reference-mask.png'
    if p.is_absolute():return p
    return REPO_ROOT/p

def sha(p): return hashlib.sha256(resolve_path(p).read_bytes()).hexdigest()

def project_obj(path,matrix,shape):
    vertices=[]; faces=[]
    for line in Path(path).read_text().splitlines():
        if line.startswith('v '): vertices.append(list(map(float,line.split()[1:4])))
        elif line.startswith('f '):
            ids=[int(s.split('/')[0])-1 for s in line.split()[1:]]
            for i in range(1,len(ids)-1): faces.append([ids[0],ids[i],ids[i+1]])
    v=np.array(vertices); q=np.c_[v,np.ones(len(v))]@np.array(matrix).T
    uv=q[:,:2]/q[:,2,None]; mask=np.zeros(shape,np.uint8)
    for ids in faces: cv2.fillConvexPoly(mask,np.rint(uv[ids]).astype(np.int32),255)
    return mask>0,uv

def integrity(candidate):
    sys.path.insert(0,str((REPO_ROOT/'tools/human_fit/pose_guided').resolve()))
    from runtime import Runtime
    r=Runtime()
    try:
        state=json.loads((candidate/'final-state.json').read_text())
        if state.get('asset')!=sha(r.asset):raise ValueError('Candidate asset hash mismatch')
        evaluated=r.evaluate(state)
        obj=np.array([list(map(float,l.split()[1:4])) for l in (candidate/'posed.obj').read_text().splitlines() if l.startswith('v ')])
        expected=evaluated['posed'][r.ids]
        error=float(np.max(np.linalg.norm(obj-expected,axis=1))) if obj.shape==expected.shape else 999
        matrix=np.array(json.loads((candidate/'camera.json').read_text())['world_to_pixel_homogeneous']); jointq=np.c_[evaluated['joints'],np.ones(len(r.names))]@matrix.T
        jp={name:jointq[i,:2]/jointq[i,2] for i,name in enumerate(r.names)}
        tp={v['id']:v for v in json.loads((ARTIFACT_ROOT/'targets/pose-targets.json').read_text())['points']}
        cue={};directions={}
        for side,bone_side in [('image_left','R'),('image_right','L')]:
            for label,bone in [('shoulder','upperarm01'),('elbow','lowerarm01'),('wrist','wrist')]:
                target=tp[label+'_'+side];point=jp[bone+'.'+bone_side];err=float(np.linalg.norm(point-target['raw_xy']))
                cue[label+'_'+side]={'target_xy':target['raw_xy'],'projected_xy':point.tolist(),'error_px':err,'confidence':target['confidence'],'visibility':target['visibility'],'interpretation':'Weak illustrative cue; hidden shoulder/elbow not anatomical truth'}
            for start,end in [('shoulder','elbow'),('elbow','wrist')]:
                a=np.array(cue[end+'_'+side]['target_xy'])-cue[start+'_'+side]['target_xy'];b=np.array(cue[end+'_'+side]['projected_xy'])-cue[start+'_'+side]['projected_xy']
                angle=float(np.degrees(np.arccos(np.clip(a@b/(np.linalg.norm(a)*np.linalg.norm(b)),-1,1))))
                directions[side+'_'+start+'_'+end]={'angle_error_degrees':angle,'interpretation':'2D direction only; depth unobserved'}
        return {'verdict':'PASS' if error<0.001 else 'FAIL','independent_pose_cues':cue,'limb_directions':directions,'independent_source_state_mesh_max_error_cm':error,'vertices':len(obj),'reason':'Fresh source dimension calibration + 163-bone FK/LBS compared vertexwise; no saved metrics trusted.'}
    except Exception as exc: return {'verdict':'FAIL','reason':str(exc)}
    finally:r.close()

def official_fields(result):
    manual=result['pose_plausibility_3d'];observations={v['id']:v for v in manual.get('observations',[])}
    region=result['visual_alignment_2d'];action=result.get('action_alignment_2d',{})
    expectations=[
      {'text':'Fresh source calibration and FK/LBS reproduce the saved actual body mesh.','passed':result['functional_integrity']['verdict']=='PASS','evidence':str(result['functional_integrity'].get('independent_source_state_mesh_max_error_cm','not verified'))+' cm maximum vertex error; see functional_integrity.'},
      {'text':'Canonical front/side/back and photo PNGs use the same real pose/mesh and declared cameras.','passed':result.get('view_integrity',{}).get('verdict')=='PASS' and result.get('view_integrity',{}).get('checks',{}).get('photo',{}).get('verdict')=='PASS','evidence':'Actual PNG replay, camera matrix formula, projected joints and independent silhouettes: '+str(result.get('view_integrity',{}).get('verdict','NOT_RUN'))},
      {'text':'Every frozen critical body region and waist/hip center scanline satisfies the regional protocol.','passed':region.get('regional_gate_verdict',region['verdict'])=='PASS','evidence':'Regional gate '+region.get('regional_gate_verdict',region['verdict'])+'; worst region '+region['worst_region']+'; inspect all regional numbers, never average.'},
      {'text':'Original visible wrists and coarse limb directions do not contradict the reference action.','passed':action.get('verdict')=='PASS','evidence':json.dumps(action,ensure_ascii=False)},
      {'text':'Actual three-dimensional renders reproduce the original opposing shirt-hem grasp.','passed':observations.get('shirt_grasp_action',{}).get('verdict')=='PASS','evidence':observations.get('shirt_grasp_action',{}).get('evidence','No affirmative manual grasp/contact evidence; burden of proof not met.')}
    ]
    result['expectations']=expectations;n=sum(e['passed'] for e in expectations)
    result['summary']={'passed':n,'failed':len(expectations)-n,'total':len(expectations),'pass_rate':n/len(expectations),'interpretation':'Descriptive count only; NEVER overall acceptance. Any critical expectation failure vetoes acceptance.'}
    result['overall_verdict']='PASS' if all(e['passed'] for e in expectations) else 'FAIL'
    result['claim_limits']=result.get('claims','Projection does not determine actual person dimensions.')
    result['claims']=[{'claim':'These outputs are an accurately recovered original 3D grasp and real-person body dimensions.','type':'quality','verified':False,'evidence':'Single photo has ambiguous depth and garment ease; actual grasp needs manual/geometry/contact evidence. M dimensions are conditional avatar parameters.'},{'claim':'Actual output mesh comes from the real adjustable cm/FK body engine.','type':'process','verified':result['functional_integrity']['verdict']=='PASS','evidence':'Fresh source reconstruction and vertexwise comparison recorded.'},{'claim':'The native Anthropic Claude skill execution benchmark ran.','type':'process','verified':False,'evidence':'NOT_RUN: current checks are local executed functional/geometry and artifact reviews, not native Claude runs.'}]
    result['execution_metrics']={'native_claude_execution':'NOT_RUN','unknown_tool_counts_and_timing':'Not invented; no complete native execution metrics/timing transcript supplied.'}
    result['user_notes_summary']={'uncertainties':['Hidden joint depth and true photographed body girths unidentified.'],'needs_review':['All critical FAIL or UNKNOWN findings remain visible.'],'workarounds':['ImageGen is illustrative weak cue; original visible wrist points and regional source-image evidence are separate.']}
    result['eval_feedback']={'suggestions':[{'assertion':'Historical20/20 file/editor/controlled-fixture checks imply original-photo pose accuracy.','reason':'Baseline independently fails both arm contours and right waist/hip by213.56pxP95; functional capabilities cannot establish raw-photo alignment.'},{'assertion':'Body lies inside clothing silhouette implies the original action.','reason':'Actual changed arm moved inside garment and regional left-arm gate passed; wrist182.46px and forearm reversal157degrees required explicitv2 coarse action veto.'},{'assertion':'Low2D wrist error implies correct3D grasp.','reason':'Round9 has low wrist errors but one arm extends far forward, and round13 has cupped palms/collapsed reversed forearm; direct canonical views and actual geometry checks are required.'},{'assertion':'Zero detected torso intersections means both hands are collision-free.','reason':'Round13 left hand has zero classified rays; coverage0 is UNKNOWN, not PASS. Skin ray checks do not prove fabric contact.'}],'overall':'Discriminating regional gates, coarse action gates, actual mesh/PNG replay and independent manual3D review are separate vetoes. Descriptive pass_rate never overrides criticalFAIL. Thev2 addition was explicitly made after a real negative control exposed a gap; regional-v1 thresholds remain frozen.'}
    return result

def grade(candidate,protocol,out):
    candidate=resolve_path(candidate); protocol=resolve_path(protocol); out=Path(out);out.mkdir(parents=True,exist_ok=True)
    a=json.loads(Path(protocol).read_text())
    contract=json.loads((Path(protocol).parent/'provenance-contract.json').read_text())
    for name,entry in contract['files'].items():
        if sha(entry['path'])!=entry['sha256']:raise ValueError('Frozen input/protocol hash mismatch: '+name)
        if 'width_height' in entry and list(cv2.imread(str(resolve_path(entry['path']))).shape[1::-1])!=entry['width_height']:raise ValueError('Frozen input dimension mismatch: '+name)
    ref=cv2.imread(str(resolve_path(a['reference_mask'])),0)>127
    cam=json.loads((candidate/'camera.json').read_text())
    if [cam['width'],cam['height']]!=a['image_size']:raise ValueError('Candidate camera dimensions differ from frozen source')
    body,uv=project_obj(candidate/'posed.obj',cam['world_to_pixel_homogeneous'],ref.shape)
    d=cv2.distanceTransform((~ref).astype(np.uint8),cv2.DIST_L2,5)
    contour=body & ~cv2.erode(body.astype(np.uint8),np.ones((3,3),np.uint8)).astype(bool)
    t=a['thresholds'];regions={}; image=cv2.imread(str(ARTIFACT_ROOT/'reference/original-product.jpg'))
    exterior=body&~ref; heat=image.copy();heat[exterior]=(255,180,0)
    cv2.drawContours(heat,cv2.findContours(body.astype(np.uint8),cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)[0],-1,(0,0,255),2)
    roi_vis=image.copy()
    for name,(x0,y0,x1,y1) in a['regions'].items():
        roi=np.zeros(ref.shape,bool);roi[y0:y1,x0:x1]=True
        b=body&roi;c=contour&roi;n=int(b.sum()); fraction=float((exterior&roi).sum()/max(n,1));p95=float(np.percentile(d[c],95)) if c.any() else 999
        reasons=[]
        if n<t['minimum_region_body_pixels']:reasons.append('insufficient body coverage')
        if fraction>t['maximum_outside_fraction']:reasons.append('body outside clothing')
        if p95>t['maximum_exterior_contour_p95_px']:reasons.append('exterior contour distance')
        regions[name]={'body_pixels':n,'outside_fraction':fraction,'exterior_contour_p95_px':p95,'verdict':'FAIL' if reasons else 'PASS','failures':reasons}
        color=(0,0,255) if reasons else (0,130,0)
        cv2.rectangle(roi_vis,(x0,y0),(x1-1,y1-1),color,2);cv2.putText(roi_vis,name,(x0+3,y0+18),0,.45,color,1)
    scans=[]
    for y in a['scanlines']:
        r=np.flatnonzero(ref[y]);b=np.flatnonzero(body[y]);center=float(abs((b[0]+b[-1]-r[0]-r[-1])/2)) if len(b) and len(r) else 999
        ratio=float((b[-1]-b[0])/(r[-1]-r[0])) if len(b) and len(r)>1 else 0
        ok=center<=t['waist_hip_scanline_center_error_px'] and t['waist_hip_scanline_width_ratio_min']<=ratio<=t['waist_hip_scanline_width_ratio_max']
        scans.append({'y':y,'center_error_px':center,'width_ratio':ratio,'verdict':'PASS' if ok else 'FAIL'})
    worst=max(regions,key=lambda k:regions[k]['exterior_contour_p95_px'])
    result={'protocol_sha256':sha(protocol),'posed_obj_sha256':sha(candidate/'posed.obj'),'state_sha256':sha(candidate/'final-state.json'),'camera_sha256':sha(candidate/'camera.json'),'functional_integrity':integrity(candidate),'visual_alignment_2d':{'verdict':'FAIL' if any(r['verdict']=='FAIL' for r in regions.values()) or any(r['verdict']=='FAIL' for r in scans) else 'PASS','regions':regions,'waist_hip_scanlines':scans,'worst_region':worst},'pose_plausibility_3d':{'verdict':'NOT_RUN','reason':'Side/back independent human review required'},'claims':'Projection evidence only; photo cannot determine true 3D pose or true cm girths.'}
    pose_contract=json.loads((Path(protocol).parent/'pose-sanity-contract.json').read_text())
    pose_cues=result['functional_integrity'].get('independent_pose_cues',{})
    directions=result['functional_integrity'].get('limb_directions',{})
    pose_failures=[]
    original_wrist_errors={}
    for name,target in pose_contract['visible_original_wrist_targets'].items():
        if name in pose_cues:
            error=float(np.linalg.norm(np.array(pose_cues[name]['projected_xy'])-target));original_wrist_errors[name]=error
            if error>pose_contract['visible_wrist_max_error_px']:pose_failures.append(name+' original visible wrist too far')
    for name,direction in directions.items():
        if direction['angle_error_degrees']>pose_contract['gross_limb_direction_reversal_degrees']:pose_failures.append(name+' gross direction reversal')
    result['action_alignment_2d']={'verdict':'FAIL' if pose_failures else ('PASS' if pose_cues else 'NOT_RUN'),'failures':pose_failures,'protocol':'pose-sanity-supplement-v2','protocol_sha256':sha(Path(protocol).parent/'pose-sanity-contract.json'),'original_visible_wrist_errors_px':original_wrist_errors,'limits':'Coarse contradiction gates, not proof of grasp action; manual action review remains required.'}
    result['visual_alignment_2d']['regional_gate_verdict']=result['visual_alignment_2d']['verdict']
    if pose_failures:result['visual_alignment_2d']['verdict']='FAIL'
    if (candidate/'views/view-provenance.json').exists():
        from check_pose_guided_views import check
        result['view_integrity']=check(candidate)
        if result['view_integrity']['verdict']=='FAIL':result['functional_integrity']['verdict']='FAIL'
    for manual in [out/'manual-review.json',ARTIFACT_ROOT/'review/final/manual-review.json']:
        if manual.exists():
            record=json.loads(manual.read_text())
            if record.get('input_hashes')=={f:sha(candidate/f) for f in ['final-state.json','posed.obj','camera.json']}:
                result['pose_plausibility_3d']=record
                result['pose_plausibility_3d']['recorded_review_path']=str(manual)
                break
    result=official_fields(result)
    (out/'grading.json').write_text(json.dumps(result,indent=2));cv2.imwrite(str(out/'regional-exterior-overlay.png'),heat);cv2.imwrite(str(out/'region-mask-definition.png'),roi_vis);cv2.imwrite(str(out/'independently-projected-mask.png'),body.astype(np.uint8)*255)
    return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--candidate',required=True);p.add_argument('--protocol',default='work/pose-guided-fit-20261118/review/acceptance.json');p.add_argument('--out',required=True);p.add_argument('--artifact-root');args=p.parse_args();ARTIFACT_ROOT=Path(args.artifact_root).resolve() if args.artifact_root else ARTIFACT_ROOT;print(json.dumps(grade(args.candidate,args.protocol,args.out),indent=2))
