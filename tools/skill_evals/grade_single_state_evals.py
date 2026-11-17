#!/usr/bin/env python3
"""Evidence-backed grader for the frozen single-state functional trials.

Reopens actual meshes; compares against a separate Three.js source skinning
export; reconstructs neutral tapes; independently projects/fills triangles and
samples depth rays. Does not import any executor optimizer or accept its grades.
"""
import argparse,copy,hashlib,importlib.util,json,re,shutil,subprocess,sys,tempfile
from pathlib import Path
import cv2
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
ASSET=ROOT/'web/human-studio/assets/human.json'
DATA=json.loads(ASSET.read_text())
NAMES=[b['name'] for b in DATA['bones']]
IDS=np.asarray(DATA['bodyVertexIds'])
INDEX={n:i for i,n in enumerate(NAMES)}

def load(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
def require(v,message):
    if not v:raise ValueError(message)
def module(path,name):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
INSPECT=module(ROOT/'.agents/skills/garment-body-six-view/scripts/inspect_human_state.py','single_state_inspector')
RAYS=module(ROOT/'tools/skill_evals/grade_anatomical_projection.py','single_state_rays')

def pose(s):return {n:s.get('poseDegrees',{}).get(n,[0,0,0]) for n in NAMES}
def same_pose(a,b,tol=1e-8):return bool(max(np.max(np.abs(np.asarray(pose(a)[n])-pose(b)[n])) for n in NAMES)<=tol)
def obj(path):
    v,f=RAYS.read_obj(path);require(v.shape==(13380,3) and f.shape==(26756,3),'Actual13380/26756 anatomical mesh required')
    require(np.isfinite(v).all() and f.min()>=0 and f.max()<len(v),'Invalid mesh vertices/faces');return v,f
def neutral(s):
    v=np.asarray(DATA['vertices'],float).reshape(-1,3).copy()
    for c,w in zip(DATA['controls'],s['morphWeights']):
        a=np.asarray(c['incr' if w>=0 else 'decr'],float)
        if len(a):v[a[:,0].astype(int)]+=a[:,1:]*abs(w)
    v[:,1]-=v[IDS,1].min();return v
def bone_lengths(s):
    v=neutral(s);heads={b['name']:v[DATA['joints'][b['head']]].mean(0) for b in DATA['bones']}
    return {label+'.'+side:float(np.linalg.norm(heads[a+'.'+side]-heads[b+'.'+side])) for side in ['L','R'] for label,a,b in [('upperArm','upperarm01','lowerarm01'),('forearm','lowerarm01','wrist')]}
def independent_model(out,evidence,posed_name='posed.obj'):
    state=load(out/'final-state.json');s=copy.deepcopy(state)
    # Neutral reconstruction is independent of angle quantization. Saved exact
    # pose is separately passed unmodified into the source Three.js exporter.
    s['poseDegrees']={n:[round(float(v),1) for v in a] for n,a in s['poseDegrees'].items()}
    audit=INSPECT.audit(s,ASSET.read_bytes(),sha(ASSET),True)
    expected=neutral(state)[IDS];posed,faces=obj(out/posed_name)
    neutral_error=None
    if (out/'neutral.obj').exists():
        actual,_=obj(out/'neutral.obj');neutral_error=float(np.max(abs(actual-expected)));require(neutral_error<.002,'Neutral OBJ differs from source morph reconstruction')
    prefix=evidence/'source-posed';evidence.mkdir(parents=True,exist_ok=True)
    command=['node',str(ROOT/'tools/skill_evals/single_state_source_export.mjs'),str(out/'final-state.json'),str(prefix)]
    result=subprocess.run(command,cwd=ROOT,text=True,capture_output=True);(evidence/'source-export.log').write_text(result.stdout+result.stderr);require(result.returncode==0,'Independent Three.js source export failed')
    source,_=obj(prefix.with_suffix('.obj'));delta=float(np.max(abs(source-posed)));require(delta<.002,'Posed OBJ differs from actual source Three.js skinning')
    joints=load(evidence/'source-posed-joints.json')['joints'];world=np.asarray([r['position'] for r in joints])
    report=dict(neutral=audit,neutral_obj_max_delta_cm=neutral_error,source_skinning_max_delta_cm=delta,vertices=len(posed),triangles=len(faces),off_step_pose_max_deg=max(abs(float(v)-round(float(v),1)) for a in state['poseDegrees'].values() for v in a))
    write(evidence/'model.json',report);return state,posed,faces,world,report

def matrix(c,view=None):
    spec=c['views'][view] if view is not None else c
    for key in ['world_to_pixel_homogeneous','world_to_pixel']:
        if key in spec:return np.asarray(spec[key],float)
    scale=spec['px_per_cm'];cx,cy=spec['center_cm'];w=spec.get('width',c['width']);h=spec.get('height',c['height']);axis=spec['axis']
    x=np.array([0,0,scale]) if axis=='side' else np.array([scale*(-1 if axis=='back' else 1),0,0])
    return np.array([[*x,w/2-scale*cx],[0,-scale,0,h/2+scale*cy],[0,0,0,1]],float)
def project(v,m):
    p=np.column_stack([v,np.ones(len(v))])@np.asarray(m).T;require(np.isfinite(p).all() and (abs(p[:,2])>1e-9).all(),'Invalid camera projection');return p[:,:2]/p[:,2,None]
def fill(v,f,m,size):
    xy=project(v,m);mask=np.zeros((size[1],size[0]),np.uint8)
    for tri in f:cv2.fillConvexPoly(mask,np.rint(xy[tri]).astype('int32'),255)
    return mask
def mask(path):
    a=cv2.imread(str(path),0);require(a is not None,'Missing mask '+str(path));return a>127
def overlap(a,b):
    a=np.asarray(a)>0;b=np.asarray(b)>0;require(a.shape==b.shape,'Mask shape mismatch');i=int((a&b).sum());u=int((a|b).sum());require(u>0,'Empty masks');return {'iou':i/u,'dice':2*i/max(int(a.sum()+b.sum()),1)}
def verify_views(out,state,v,f,camera,views=('front','side','back')):
    provenance=load(out/'view-provenance.json');records=[provenance[k] for k in views]
    require(len({r['state_sha256'] for r in records})==1 and records[0]['state_sha256']==sha(out/'final-state.json'),'Different/stale state per view')
    require(len({r['posed_mesh_sha256'] for r in records})==1 and records[0]['posed_mesh_sha256']==sha(out/'posed.obj'),'Different/stale posed mesh per view')
    require(len({r['pose_sha256'] for r in records})==1,'Different pose per view')
    result={}
    for view in views:
        spec=camera['views'][view];size=(spec.get('width',camera['width']),spec.get('height',camera['height']));a=fill(v,f,matrix(camera,view),size);b=mask(out/(view+'-mask.png'));score=overlap(a,b);require(score['iou']>.999,'View mask is not projection of the one saved mesh: '+view);result[view]=score
    return result
def frozen_inputs(workspace):
    declared=load(workspace/'fixtures/frozen-inputs.json')['files']
    for name,digest in declared.items():require(sha(workspace/'fixtures'/name)==digest,'Frozen reference/runtime changed: '+name)
    require(sha(workspace/'fixtures/real-photo/original-product.jpg')=='6fd6310bc225b6ba4e80f5b49a57ef75f737c08e5fbd983a95694afb402e1e53','Original source photo changed')
    require(sha(workspace/'fixtures/real-photo/reference-mask.png')=='8a536a126416ab45af1e9db9a1df5b9ea5f4d05f0e74a4268032dc64746d7891','Original source mask changed')
    return True
def metric_check(reported,actual):
    for key in ['iou','dice']:
        value=reported.get(key,reported.get(key.capitalize() if key=='dice' else 'IoU'))
        require(value is not None and abs(value-actual[key])<1e-7,'Incorrect reported '+key)
    return True
def image_ok(p):
    a=cv2.imread(str(p));return a is not None and a.size>100

def grade_fit(workspace,out,evidence):
    state,v,f,world,model=independent_model(out,evidence);camera=load(out/'camera.json');initial=load(workspace/'fixtures/joint-fit/initial-state.json');initialcam=load(workspace/'fixtures/joint-fit/camera.json')
    replay=verify_views(out,state,v,f,camera,('front','side','back','closeup','pose','depth'))
    refs=load(workspace/'fixtures/joint-fit/reference-joints.json')['views'];jerr=[];initialerr=[];ious={};metrics=load(out/'metrics.json')
    # Source initial joints are a frozen fixture, not the executor's self-report.
    iw=np.asarray([j['position'] for j in load(workspace/'fixtures/joint-fit/initial-renders/joints.json')['joints']])
    finalkey='final_camera_final' if 'final_camera_final' in metrics else 'final_final_camera';initialkey='source_camera_initial' if 'source_camera_initial' in metrics else 'initial_source_camera'
    for view in ['front','side']:
        p=project(world,matrix(camera,view));ip=project(iw,matrix(initialcam,view));r=mask(workspace/f'fixtures/joint-fit/reference-{view}-mask.png');score=overlap(r,mask(out/(view+'-mask.png')));base=overlap(r,mask(workspace/f'fixtures/joint-fit/initial-renders/{view}-mask.png'));ious[view]={'initial':base,'final':score};metric_check(metrics[finalkey][view],score);metric_check(metrics[initialkey][view],base)
        for point in refs[view]:jerr.append(float(np.linalg.norm(p[INDEX[point['joint']]]-point['pixel'])));initialerr.append(float(np.linalg.norm(ip[INDEX[point['joint']]]-point['pixel'])))
    back=overlap(mask(out/'back-mask.png'),mask(workspace/'private-oracle/target/back-mask.png'))
    lengths0=bone_lengths(initial);lengths=bone_lengths(state);dims=state['dimensions'];pose_changed=not same_pose(state,initial);cam_changed=abs(camera['views']['front']['px_per_cm']-initialcam['views']['front']['px_per_cm'])>.001
    cm_changed=abs(dims['waist']-initial['dimensions']['waist'])>.1 and any(abs(dims[k]-initial['dimensions'][k])>.1 for k in ['upperArmLength','forearmLength']) and any(abs(lengths[k]-lengths0[k])>.1 for k in lengths)
    bounds=64<=dims['waist']<=80 and 26<=dims['upperArmLength']<=33 and 20<=dims['forearmLength']<=27 and dims['height']==170
    raw=np.load(out/'rawdepth.npy',allow_pickle=False);valid=mask(out/'depth-valid.png');require(raw.shape==valid.shape and np.array_equal(np.isfinite(raw),valid),'Raw depth validity mismatch');yy,xx=np.where(valid);require(len(xx)>100,'Empty raw depth');ii=np.linspace(0,len(xx)-1,20,dtype=int);truth=RAYS.ray_hits(v,f,camera,'depth',list(zip(xx[ii],yy[ii])));require(all(x is not None for x in truth),'Raw valid depth without actual triangle hit');depth_error=float(np.max(abs(np.array(truth)-raw[yy[ii],xx[ii]])));require(depth_error<.001,'Raw depth differs from independently intersected triangles')
    records=load(out/'view-provenance.json');joint_replay=max(float(np.max(abs(project(world,matrix(camera,k))-np.asarray(records[k]['projected_joints'])))) for k in records if 'projected_joints' in records[k]);require(joint_replay<.01,'Wrong projected joint metadata')
    result=dict(model=model,view_replay=replay,metrics=ious,training_joint_mean_px=float(np.mean(jerr)),initial_training_joint_mean_px=float(np.mean(initialerr)),heldout_back_iou=back['iou'],bone_lengths_initial_cm=lengths0,bone_lengths_final_cm=lengths,depth_sample_max_error_cm=depth_error,raw_depth_valid_pixels=len(xx),projected_joint_metadata_max_error_px=joint_replay)
    text=(out/'report.md').read_text();comparisons=len(list(out.glob('*overlay.png')))>=6 and (out/'parameter-block-history.json').exists()
    flags=[True,True,bool(cm_changed and pose_changed and cam_changed and bounds),all(t['final']['iou']>=.93 and t['final']['iou']-t['initial']['iou']>=.015 for t in ious.values()),np.mean(jerr)<=4 and np.mean(jerr)<=.5*np.mean(initialerr) and back['iou']>=.93,comparisons,all(image_ok(out/(k+'.png')) for k in ['front','side','back','closeup','pose','depth']) and ('controlled' in text.lower() or 'synthetic' in text.lower())]
    evidence_rows=[f"Separate Three.js skinning delta {model['source_skinning_max_delta_cm']:.3g}cm; neutral reconstruction residual {model['neutral']['maximumTargetErrorCm']:.3g}cm.",f"Reprojected one saved mesh in six cameras: {replay}; one state/pose/mesh fingerprint.",f"Actual cm/bone change={cm_changed}, pose={pose_changed}, camera={cam_changed}, bounds={bounds}; rest bone lengths {lengths0}→{lengths}.",f"Independently reopened masks: {ious}; frozen references unchanged.",f"Actual mean joint error {np.mean(initialerr):.6g}→{np.mean(jerr):.6g}px; held-out same-state back IoU={back['iou']:.6g}.",f"{len(list(out.glob('*overlay.png')))} actual overlays plus camera-only/source-camera comparisons and block history; saved IoU/Dice independently agree.",f"Six decoded renders, {len(xx)} finite depth pixels;20 independent ray hits max error {depth_error:.3g}cm; report limits this to controlled anatomy."]
    return flags,evidence_rows,result

def grade_editor(workspace,out,evidence):
    state,v,f,world,model=independent_model(out,evidence,'final-posed.obj');source=load(workspace/'fixtures/editor/source-state.json');before=load(out/'geometry-before.json');after=load(out/'geometry-after.json');rows=load(out/'view-states.json');rows=list(rows.values()) if isinstance(rows,dict) else rows
    require(len(rows)==3,'Three saved view states required');states=[r.get('state',r.get('snapshot')) for r in rows];require(all(s['dimensions']==state['dimensions'] and same_pose(s,state) for s in states),'Per-view body/pose changed')
    hashes=[r.get('posedMeshSha256',r.get('posedMeshHash')) for r in rows];require(len(set(hashes))==1 and hashes[0],'Different posed meshes per view')
    command=['node',str(ROOT/'tools/skill_evals/grade_single_state_editor.cjs'),'--source',str(workspace/'fixtures/editor/source-state.json'),'--final',str(out/'final-state.json'),'--out',str(evidence/'browser')]
    r=subprocess.run(command,cwd=ROOT,text=True,capture_output=True);(evidence/'browser.log').write_text(r.stdout+r.stderr);browser=load(evidence/'browser/browser.json');require(r.returncode==0 and browser['verdict']=='PASS','Independent real-browser consumer failed')
    desired={**source['dimensions'],'waist':source['dimensions']['waist']+3,'upperArmLength':source['dimensions']['upperArmLength']+2,'forearmLength':source['dimensions']['forearmLength']+1};dims_ok=state['dimensions']==desired
    before_vertices=np.asarray(before['posed']);after_vertices=np.asarray(after['posed']);require(after_vertices.shape==v.shape and np.max(abs(after_vertices-v))<.002,'Saved browser geometry differs from actual OBJ');delta=float(np.max(np.linalg.norm(after_vertices-before_vertices,axis=1)))
    flags=[dims_ok and delta>.1 and all(abs(browser['bones_after_cm'][k]-browser['bones_before_cm'][k])>.2 for k in browser['bones_before_cm']),same_pose(source,state,.1),len({sha(out/(k+'.png')) for k in ['front','side','back']})==3,True,True,True]
    ev=[f"Independently repeated actual UI edits; delta {delta:.6g}cm and actual bone-head lengths changed. Neutral residual {model['neutral']['maximumTargetErrorCm']:.3g}cm.","Every supplied angular component preserved (missing zero bones filled semantically), not world positions.","Three real camera clicks and screenshots differ; independent browser and saved per-view states retain one body/full pose/mesh.",f"Independent browser downloaded/reimported/reloaded state; source Three.js posed OBJ delta {model['source_skinning_max_delta_cm']:.3g}cm.","Independent actual browser rejects invalid typed JSON and normalizes off-step cm input while preserving the target action.",f"Independent375px browser/mobile capture, no runtime errors; {len(browser['checks'])} real consumer checks. Executor replay and actual before/after vertices reopened."]
    return flags,ev,dict(model=model,browser=browser,mesh_vertex_displacement_cm=delta,pose_unchanged=same_pose(source,state,.1))

def photo_matrix(camera):return matrix(camera)
def grade_photo(workspace,out,evidence,visual):
    state,v,f,world,model=independent_model(out,evidence);camera=load(out/'camera.json');rendercam=load(out/('render-camera.json' if (out/'render-camera.json').exists() else 'three-view-camera.json'));replay=verify_views(out,state,v,f,rendercam)
    rows=load(workspace/'fixtures/real-photo/manual-landmarks.json')['points'];points=project(world,photo_matrix(camera));vertices=project(v,photo_matrix(camera));errors=[];visible=[]
    # Original asset vertex201 is within the first contiguous compact body IDs.
    remap={int(i):k for k,i in enumerate(IDS)}
    for row in rows:
        xy=vertices[remap[row['vertex']]] if 'vertex' in row else points[INDEX[row['joint']]];e=float(np.linalg.norm(xy-row['pixel']));errors.append(e)
        if 'vertex' in row or row.get('joint','').startswith(('eye','wrist')):visible.append(e)
    saved=load(out/'joints.json')['joints'];saved_world=np.asarray([row['position'] for row in saved]);require(np.max(abs(saved_world-world))<.002,'Saved world joints do not match source bone pose')
    m=fill(v,f,photo_matrix(camera),(1000,1276));actual_mask=mask(out/'final-mask.png');require(overlap(m,actual_mask)['iou']>.999,'Original-photo mask not projected from saved single mesh/camera');ref=mask(workspace/'fixtures/real-photo/reference-mask.png');score=overlap(ref,actual_mask);metrics=load(out/'metrics.json');finalmetrics=metrics['final'].get('mask',metrics['final']);metric_check(finalmetrics,score)
    baseline=metrics.get('initial',metrics.get('source-camera-initial'));initial_visible=baseline.get('joints',baseline).get('visible_face_wrists_mean_px',baseline.get('joints',baseline).get('visible_face_wrist_mean_px'))
    reported=metrics['final'].get('joints',metrics['final']).get('visible_face_wrists_mean_px',metrics['final'].get('visible_face_wrist_mean_px'));require(abs(float(reported)-np.mean(visible))<.01,'Incorrect visible joint metric')
    history=load(out/'parameter-block-history.json');require(len(history)>=3,'Missing actual optimization blocks');code=(out/'reproduce.py').read_text();trace=(out/'TRACE.md').read_text();report=(out/'report.md').read_text();blocks=' '.join(str(r.get('block','')) for r in history).lower();cm_trials=any('cm' in str(r.get('block','')).lower() or 'shape' in str(r.get('block','')).lower() for r in history)
    require('private-oracle/' not in code and 'model/original-reference' not in code,'Optimizer reads excluded answers')
    visual=visual.get(out.parent.parent.name,{})
    require(visual.get('files') and all((out/name).is_file() and sha(out/name)==digest for name,digest in visual['files'].items()),'Independent visual review is stale or lacks artifact binding')
    objective=load(out/'objective.json') if (out/'objective.json').exists() else {}
    objective_improves=(objective.get('final',float('inf'))<=.9*objective.get('initial',0))
    if not objective:
        # Recompute the declared perspective residual formula, not just its report.
        def old_cost(s,vertices,joints,c):
            pp=project(joints,matrix(c));vp=project(vertices,matrix(c));r=[]
            for p in rows:
                xy=vp[remap[p['vertex']]] if 'vertex' in p else pp[INDEX[p['joint']]];wt=.32 if p.get('joint','').startswith(('upperarm','lowerarm')) else (.65 if p.get('joint')=='neck01' else 1);r.extend((xy-p['pixel'])/20*wt)
            for side,target in [('L',[287,802]),('R',[280,786])]:r.extend((pp[INDEX['finger3-3.'+side]]-target)/30*.45)
            for side in ['L','R']:r.extend([(joints[INDEX['wrist.'+side],2]-22)/7,(joints[INDEX['lowerarm01.'+side],2]-5)/12*.7])
            for n in ['root','spine01','neck01','head','upperarm01.L','upperarm01.R','lowerarm01.L','lowerarm01.R','wrist.L','wrist.R']:r.extend(np.asarray(s['poseDegrees'][n])*.0025)
            r.extend([(c['distance_cm']-225)/200,(c['focal_px']/c['distance_cm']-14)/15,c['pitch_deg']/40,c['yaw_deg']/60]);return float(np.mean(np.asarray(r)**2))
        initial=load(out/'initial-state.json');iv,_=obj(out/'initial-posed.obj');initial_e=evidence/'initial-source';initial_e.mkdir(exist_ok=True);r=subprocess.run(['node',str(ROOT/'tools/skill_evals/single_state_source_export.mjs'),str(out/'initial-state.json'),str(initial_e/'posed')],cwd=ROOT,text=True,capture_output=True);require(r.returncode==0,'Initial source pose export failed');iw=np.asarray([r['position'] for r in load(initial_e/'posed-joints.json')['joints']]);ci=load(out/'camera-initial.json');objective={'initial':old_cost(initial,iv,iw,ci),'final':old_cost(state,v,world,camera),'method':'Independent reimplementation of declared perspective residual using source Three.js mesh/joints'};objective_improves=objective['final']<=.9*objective['initial']
    consume_command=['node',str(ROOT/'tools/skill_evals/grade_single_state_editor.cjs'),'--source',str(out/'final-state.json'),'--final',str(out/'final-state.json'),'--mesh',str(out/'posed.obj'),'--consume-only','true','--out',str(evidence/'photo-consumer')]
    consume_result=subprocess.run(consume_command,cwd=ROOT,text=True,capture_output=True);(evidence/'photo-consumer.log').write_text(consume_result.stdout+consume_result.stderr);consumer_report=load(evidence/'photo-consumer/browser.json');consumer=consume_result.returncode==0 and consumer_report['verdict']=='PASS';measuretext=(out/'measurements.json').read_text();source_distinction='171' in report and '170' in report and ('prior' in report.lower() or '先验' in report)
    flags=[cm_trials and ('pose' in blocks) and ('camera' in blocks) and 'Runtime' in code,True,np.mean(visible)<=15 and np.mean(visible)<=.5*initial_visible,objective_improves and len(list(out.glob('*overlay.png')))>=2,bool(visual.get('passed',False)),consumer and ('bone' in measuretext.lower() or '骨' in measuretext),source_distinction and ('uncertain' in report.lower() or 'unavailable' in report.lower()) and ('no new' in report.lower() or 'no paid' in report.lower())]
    ev=[f"Actual optimizer entrypoint and {len(history)} shape/bone/pose/camera blocks, source input hashes; selected cm may remain prior after real trials.",f"Separate source skinning and same-state front/side/back replay {replay}; saved163joints agree with actual source FK.",f"Matrix independently gives visible eye/nose/wrist mean {np.mean(visible):.6g}px from initial {initial_visible:.6g}px; hidden annotations remain uncertain.",f"Declared fixed residual objective {objective}; independent original-mask IoU/Dice {score}, saved reports agree; before/after overlays retained.",visual.get('evidence','No independent visual decision saved; FAIL rather than infer from point error.'),f"Neutral independent residual {model['neutral']['maximumTargetErrorCm']:.3g}cm; actual posed mesh source delta {model['source_skinning_max_delta_cm']:.3g}cm; saved consumer link/check and bone-vs-ruler measures.","Original171cm/S and authorized170cm/M prior distinguished; report retains conditional measurements, unknowns and no fresh-generation/true-person/perfect-match claim."]
    return flags,ev,dict(model=model,view_replay=replay,visible_joint_mean_px=float(np.mean(visible)),initial_visible_joint_mean_px=initial_visible,all_joint_mean_px=float(np.mean(errors)),original_mask_metrics=score,objective=objective,visual_review=visual,actual_browser_consumer=consumer_report)

def grade_run(workspace,run,visual):
    meta=load(run/'eval_metadata.json');out=run/'outputs';evidence=workspace/'grade-evidence'/run.relative_to(workspace/'iteration-1');evidence.mkdir(parents=True,exist_ok=True)
    assertions=meta['assertions'];frozen_inputs(workspace)
    try:
        if meta['eval_id']==1:flags,rows,audit=grade_fit(workspace,out,evidence)
        elif meta['eval_id']==2:flags,rows,audit=grade_editor(workspace,out,evidence)
        else:flags,rows,audit=grade_photo(workspace,out,evidence,visual)
        require(len(flags)==len(assertions),'Assertion count changed')
    except Exception as exc:
        flags=[False]*len(assertions);rows=[f"Required independent evidence boundary failed: {type(exc).__name__}: {exc}"]*len(assertions);audit={'error':str(exc)}
    expectations=[dict(text=text,passed=bool(ok),evidence=row) for text,ok,row in zip(assertions,flags,rows)]
    passed=sum(x['passed'] for x in expectations);grading=dict(expectations=expectations,summary=dict(passed=passed,failed=len(expectations)-passed,total=len(expectations),pass_rate=passed/len(expectations)),timing=dict(executor_duration_seconds=None,total_tokens=None),claims=[dict(claim='Outputs match actual source anatomy, pose and projection',verified=all(flags),evidence=str(evidence.relative_to(workspace)))],eval_feedback=dict(overall='Single explicitly injected subagent trial per task/configuration; geometry controls and real-photo attempt are distinct. No native trigger, statistical superiority or token claim.'))
    artifacts={str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*')) if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}
    grading['artifact_sha256']=artifacts;write(evidence/'artifacts.json',artifacts);write(evidence/'audit.json',audit);write(run/'grading.json',grading);return grading

def negative_controls(workspace):
    source=workspace/'iteration-1/eval-1-joint-single-state-fit/with_skill/run-1/outputs';controls=[]
    with tempfile.TemporaryDirectory(prefix='single-state-grader-') as temp:
        p=Path(temp)/'outputs';shutil.copytree(source,p,ignore=shutil.ignore_patterns('__pycache__'));state=load(p/'final-state.json');v,f=obj(p/'posed.obj');c=load(p/'camera.json');ev=Path(temp)/'evidence';ev.mkdir()
        def reject(name,call,pattern):
            try:call()
            except ValueError as error:
                require(re.search(pattern,str(error)) is not None,'Wrong failure boundary in negative control: '+str(error));controls.append(dict(name=name,verdict='REJECTED',reason=str(error)));return
            raise AssertionError('Corruption accepted: '+name)
        # Render a genuinely different side pose but falsely retain the common
        # state/pose metadata. The independent one-mesh projection must catch it.
        alt=copy.deepcopy(state);alt['poseDegrees']['lowerarm01.L'][0]+=12;write(ev/'alternate-state.json',alt)
        r=subprocess.run(['node',str(ROOT/'tools/skill_evals/single_state_source_export.mjs'),str(ev/'alternate-state.json'),str(ev/'alternate')],cwd=ROOT,text=True,capture_output=True);require(r.returncode==0,'Negative alternate source export failed');av,af=obj(ev/'alternate.obj');cv2.imwrite(str(p/'side-mask.png'),fill(av,af,matrix(c,'side'),(c['width'],c['height'])))
        reject('actual different side pose hidden behind common metadata',lambda:grade_fit(workspace,p,ev/'view'),'View mask is not projection');(p/'side-mask.png').write_bytes((source/'side-mask.png').read_bytes())
        lines=(p/'posed.obj').read_text().splitlines()
        for i,line in enumerate(lines):
            if line.startswith('v '):
                xyz=list(map(float,line.split()[1:4]));xyz[0]+=1;lines[i]='v '+' '.join(map(str,xyz));break
        (p/'posed.obj').write_text('\n'.join(lines)+'\n')
        meta=load(p/'view-provenance.json')
        for row in meta.values():row['posed_mesh_sha256']=sha(p/'posed.obj')
        write(p/'view-provenance.json',meta)
        reject('actual OBJ vertex displaced1cm with forged matching hashes',lambda:grade_fit(workspace,p,ev/'mesh'),'Posed OBJ differs');(p/'posed.obj').write_bytes((source/'posed.obj').read_bytes());(p/'view-provenance.json').write_bytes((source/'view-provenance.json').read_bytes())
        metrics=load(p/'metrics.json');metrics['final_final_camera']['front']['IoU']-=.1;write(p/'metrics.json',metrics)
        reject('actual saved metrics IoU falsified',lambda:grade_fit(workspace,p,ev/'metric'),'Incorrect reported iou')
        frozen=Path(temp)/'workspace';shutil.copytree(workspace/'fixtures',frozen/'fixtures',ignore=shutil.ignore_patterns('__pycache__'));ref=frozen/'fixtures/joint-fit/reference-front-mask.png';ref.write_bytes(ref.read_bytes()+b'changed')
        reject('actual frozen reference bytes changed in disposable workspace',lambda:frozen_inputs(frozen),'Frozen reference/runtime changed')
    report=dict(verdict='PASS',controls=controls,limits='Tests independent checks against controlled mutations; not human-pose or cloth physics accuracy.');write(workspace/'grade-evidence/negative-controls.json',report);return report

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--workspace',type=Path,default=ROOT/'work/single-state-skill-evals-20261117');ap.add_argument('--case',type=int);ap.add_argument('--configuration',choices=['old_skill','with_skill']);ap.add_argument('--negative-controls',action='store_true');args=ap.parse_args();w=args.workspace.resolve();visual=load(w/'grade-evidence/visual-review.json') if (w/'grade-evidence/visual-review.json').exists() else {}
    if args.negative_controls:print(json.dumps(negative_controls(w)))
    else:
        summary=[]
        for run in sorted((w/'iteration-1').glob('eval-*/*/run-*')):
            m=load(run/'eval_metadata.json')
            if args.case and m['eval_id']!=args.case:continue
            if args.configuration and run.parent.name!=args.configuration:continue
            g=grade_run(w,run,visual);summary.append(dict(run=str(run.relative_to(w)),**g['summary']))
        print(json.dumps(summary,indent=2))
