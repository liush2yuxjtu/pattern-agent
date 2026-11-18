#!/usr/bin/env python3
"""Publish source-bound commerce functional runs in the pinned official viewer."""
import argparse, hashlib, json, shutil, zipfile
from pathlib import Path
from PIL import Image
import cv2
import numpy as np
from build_functional_review import build as official_review
ROOT=Path(__file__).resolve().parents[2]
WORK=ROOT/'work/commerce-skill-evals-20261118'
SITE=ROOT/'web/garment-body/commerce-evals'
ROLES=('front','side','back','closeup','pose','depth')
COPY_EXT={'.png','.jpg','.jpeg','.json','.md','.csv','.obj','.glb','.py','.mjs','.cjs','.txt'}

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):return json.loads(Path(path).read_text())
def write(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def valid_image(path):
    try:
        with Image.open(path) as im:im.verify()
        return True
    except Exception:return False

def archive(source,target):
    target.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(source.rglob('*')):
            if not p.is_file() or '__pycache__' in p.parts or p.suffix=='.pyc':continue
            info=zipfile.ZipInfo(str(p.relative_to(source)),(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o644<<16
            z.writestr(info,p.read_bytes())
    with zipfile.ZipFile(target) as z:
        if z.testzip():raise ValueError('Archive CRC failure')

def independent_overlay(output,source,target):
    """Review-derived actual mesh projection; never warp or alter the source file."""
    mesh=output/'posed.obj';camera=output/'camera.json'
    if not mesh.exists() or not camera.exists():return None
    try:
        cam=read(camera);matrix=np.asarray(cam['world_to_pixel_homogeneous'],float)
        if matrix.shape!=(3,4) or not np.isfinite(matrix).all():return None
        vertices=[];faces=[]
        for line in mesh.read_text().splitlines():
            if line.startswith('v '):vertices.append(list(map(float,line.split()[1:4])))
            elif line.startswith('f '):
                ids=[int(v.split('/')[0]) for v in line.split()[1:]]
                faces.extend([[ids[0],ids[i],ids[i+1]] for i in range(1,len(ids)-1)])
        vertices=np.asarray(vertices,float);faces=np.asarray(faces,int);faces=np.where(faces<0,len(vertices)+faces,faces-1)
        projected=np.c_[vertices,np.ones(len(vertices))]@matrix.T
        if not np.isfinite(projected).all() or np.any(np.abs(projected[:,2])<1e-8):return None
        uv=projected[:,:2]/projected[:,2,None]
        if np.abs(uv).max()>1e7:return None
        photo=cv2.imread(str(source));mask=np.zeros(photo.shape[:2],np.uint8)
        for face in faces:
            if np.all(projected[face,2]>0):cv2.fillConvexPoly(mask,np.rint(uv[face]).astype('int32'),255)
        result=photo.copy();inside=mask>0;result[inside]=(photo[inside]*.9+np.array([250,180,0])*.1).astype('uint8')
        cv2.drawContours(result,cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)[0],-1,(250,180,0),max(1,round(photo.shape[0]/1000)))
        review=target/'review';review.mkdir(exist_ok=True);cv2.imwrite(str(review/'thin-overlay.png'),result)
        write(review/'overlay-provenance.json',dict(method='Review-derived OpenCV union of actual OBJ triangles projected by declared 3x4 photo camera; 10% alpha and thin contour on unchanged original; no 2D warp',reference_sha256=sha(source),posed_obj_sha256=sha(mesh),camera_sha256=sha(camera),native_size=[photo.shape[1],photo.shape[0]],declared_camera_size=[cam.get('width'),cam.get('height')],limitations='Projection consistency is not measurement or hidden anatomy accuracy'))
        return review/'thin-overlay.png'
    except (ValueError,KeyError,IndexError,TypeError):return None

def output_files(output):
    return {str(p.relative_to(output)):sha(p) for p in sorted(output.rglob('*')) if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}

def verify_grade(run,grade,source):
    output=run/'outputs';actual=output_files(output);bindings=grade.get('artifact_sha256')
    if not isinstance(bindings,dict) or not bindings:raise ValueError('Final grader must bind complete artifact_sha256: '+str(run))
    if bindings!=actual:raise ValueError('Graded artifacts changed or incomplete: '+str(run))
    for key,name in [('state_sha256','final-state.json'),('posed_obj_sha256','posed.obj'),('camera_sha256','camera.json')]:
        if grade.get(key) and grade[key]!=actual.get(name):raise ValueError('Stale '+key+': '+str(run))
    expected_input=grade.get('reference_sha256',grade.get('input_sha256'))
    if isinstance(expected_input,str) and expected_input!=sha(source):raise ValueError('Wrong source reference')
    expectations=grade.get('expectations',[])
    if not expectations or any(not {'text','passed','evidence'}<=set(e) or type(e['passed']) is not bool or not e['text'] or not e['evidence'] for e in expectations):raise ValueError('Official expectation fields/evidence missing')
    summary=grade.get('summary',{});passed=sum(e['passed'] for e in expectations)
    if summary.get('passed')!=passed or summary.get('failed')!=len(expectations)-passed or summary.get('total')!=len(expectations) or abs(summary.get('pass_rate',-1)-passed/len(expectations))>1e-6:raise ValueError('Grader summary disagrees with actual assertions')
    return actual

def preflight(workspace,iteration,include_holdout):
    """Fail closed before mutating already usable published evidence."""
    origin=workspace/f'iteration-{iteration}';runs=sorted(origin.glob('eval-*/*/run-*'))
    if len(runs)!=(4 if iteration==1 else 6):raise ValueError('Expected complete paired run set')
    expected={}
    for run in runs:
        meta=read(run/'eval_metadata.json');case=meta.get('input_case') or {1:'everlane-boatneck',2:'everlane-blue-shirt',3:'holdout-c-reformation'}[int(meta['eval_id'])]
        heldout='holdout' in str(case) or int(meta['eval_id'])==3
        if heldout and (not include_holdout or not (workspace/'skill-v2-manifest.json').exists()):raise ValueError('Heldout publication requires explicit release and frozen v2')
        source=workspace/'inputs'/case/'original.jpg'
        if read(source.parent/'source.json').get('sha256')!=sha(source):raise ValueError('Original input changed')
        if not (run/'grading.json').exists():raise ValueError('Final independent grading missing: '+str(run))
        grade=read(run/'grading.json');verify_grade(run,grade,source)
        key=(str(meta['eval_id']),run.parent.name,int(run.name.split('-')[-1]));expected[key]=grade['summary']
    bp=origin/'benchmark.json'
    if not bp.exists():raise ValueError('Actual aggregated benchmark missing')
    benchmark=read(bp);actual={}
    for r in benchmark.get('runs',[]):actual[(str(r['eval_id']),r['configuration'],int(r['run_number']))]=r['result']
    if actual.keys()!=expected.keys():raise ValueError('Benchmark run inventory differs from actual graded runs')
    for key,summary in expected.items():
        for metric in ['passed','failed','total','pass_rate']:
            if abs(actual[key].get(metric,-1)-summary[metric])>1e-6:raise ValueError('Benchmark disagrees with actual grading')

def snapshot(workspace,site,iteration,allow_pending,include_holdout):
    origin=workspace/f'iteration-{iteration}';runs=sorted(origin.glob('eval-*/*/run-*'))
    expected=4 if iteration==1 else 6
    if not allow_pending and len(runs)!=expected:raise ValueError(f'Expected {expected} paired runs, found {len(runs)}')
    thin=workspace/'review-inputs/garment-body-six-view-workspace'/f'iteration-{iteration}'
    if thin.exists():shutil.rmtree(thin)
    thin.mkdir(parents=True)
    public=site/'artifacts'/f'iteration-{iteration}'
    if public.exists():shutil.rmtree(public)
    galleries={};inventory=[]
    for run in runs:
        meta=read(run/'eval_metadata.json');case=meta.get('input_case')
        if not case:
            case={1:'everlane-boatneck',2:'everlane-blue-shirt',3:'holdout-c-reformation'}.get(int(meta['eval_id']))
        heldout='holdout' in str(case) or int(meta['eval_id'])==3
        if heldout and not include_holdout:
            if allow_pending:continue
            raise ValueError('Explicit --include-holdout required after v2 freeze')
        if heldout and not (workspace/'skill-v2-manifest.json').exists():raise ValueError('Holdout cannot publish before v2 is frozen')
        source=workspace/'inputs'/case/'original.jpg'
        if read(source.parent/'source.json').get('sha256')!=sha(source):raise ValueError('Original source bytes changed: '+case)
        output=run/'outputs';grade=read(run/'grading.json') if (run/'grading.json').exists() else None
        if not allow_pending and grade is None:raise ValueError('Final independent grading missing: '+str(run))
        grade_error=None
        if grade:
            try:hashes=verify_grade(run,grade,source)
            except ValueError as error:
                if not allow_pending:raise
                grade_error=str(error);grade=None;hashes=output_files(output)
        else:hashes=output_files(output)
        relative=run.relative_to(origin);key=str(relative).replace('/','-');base=f'artifacts/iteration-{iteration}/'+str(relative)
        target=site/base;target.mkdir(parents=True,exist_ok=True)
        thin_run=thin/relative;(thin_run/'outputs').mkdir(parents=True)
        write(thin_run/'eval_metadata.json',meta)
        if grade:write(thin_run/'grading.json',grade)
        for name in ['timing.json']:
            if (run/name).exists():shutil.copyfile(run/name,thin_run/name)
        for path in sorted(output.rglob('*')):
            if path.is_file() and path.suffix.lower() in COPY_EXT and '__pycache__' not in path.parts:
                if path.suffix.lower() in {'.png','.jpg','.jpeg'} and not valid_image(path):
                    if allow_pending:continue
                    raise ValueError('Image decode failure '+str(path))
                dest=target/'outputs'/path.relative_to(output);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,dest)
        for path in (run/'eval_metadata.json',run/'grading.json',run/'timing.json'):
            if path.exists() and (path.name!='grading.json' or grade):shutil.copyfile(path,target/path.name)
        input_dir=site/'inputs'/case;input_dir.mkdir(parents=True,exist_ok=True)
        for name in ['original.jpg','source.json','official-excerpt.md']:
            p=source.parent/name
            if p.exists():shutil.copyfile(p,input_dir/name)
        status=grade.get('overall_verdict',grade.get('overall','NOT_GRADED')) if grade else ('RUNNING · STALE_GRADE_NOT_USED' if grade_error else 'RUNNING · NOT_GRADED')
        skill_version='skill-v'+(str(iteration) if run.parent.name=='with_skill' else '0')
        title=f"{meta.get('eval_name',case)} · {'修订技能' if run.parent.name=='with_skill' else '冻结旧技能'} {skill_version}"+(' · HELD-OUT' if heldout else ' · DEVELOPMENT')
        report=output/'report.md'
        text=report.read_text() if report.exists() else '执行中：尚无最终报告。已存在的图片是实际中间产物，不代表执行完成或评分通过。'
        (thin_run/'outputs/01-report.md').write_text(f'{title}\n\nOVERALL: {status}\n\n'+text)
        fingerprints={'reference_sha256':sha(source),'state_sha256':hashes.get('final-state.json'),'posed_obj_sha256':hashes.get('posed.obj'),'camera_sha256':hashes.get('camera.json')}
        write(thin_run/'outputs/02-source-fingerprints.json',dict(source_fingerprints=fingerprints,execution='Explicit subagent functional execution, not native Claude triggering',role='sealed heldout' if heldout else 'development',imagegen_scope='full six-image branch' if int(meta['eval_id'])==1 else 'pose-guide/body-fit branch only'))
        def item(path,label,caption):
            p=site/path
            return dict(src=path,label=label,caption=caption,sha256=sha(p)) if p.exists() and valid_image(p) else None
        def own(name,label,caption):return item(base+'/outputs/'+name,label,caption)
        inp=[item('inputs/'+case+'/original.jpg','原始电商输入','原始响应字节；未用截图或生成图替换。')]
        generated=[];seen=set();final_count=0
        for role in ROLES:
            for suffix in ['png','jpg','jpeg']:
                image=own('images/'+role+'.'+suffix,'Image Gen '+role,'独立原生生成图；未见背面和示意深度不是观测真值。')
                if image:generated.append(image);seen.add(image['src']);final_count+=1;break
        for path in sorted((target/'outputs').rglob('*')):
            rel=path.relative_to(target/'outputs')
            if path.suffix.lower() not in {'.png','.jpg','.jpeg'}:continue
            native_names={'guide.png','pose-guide.png','imagegen-guide.png','guide-native.png','pose-guide-native.png','imagegen-pose.png','original-pose-illustrative.png'}
            if not (rel.parts[0]=='images' or path.name.lower() in native_names):continue
            image=own(str(rel),'Image Gen 原姿态引导','实际生成的示意点线，用于原图拟合；与最终六张角色图分开标注。')
            if image and image['src'] not in seen:generated.append(image);seen.add(image['src'])
        renders=[]
        for name,label in [('photo-render.png','原相机实际投影'),('views/front.png','同一状态正面'),('views/side.png','同一状态侧面'),('views/back.png','同一状态背面')]:
            image=own(name,label,'真实网格渲染，不是 Image Gen。');
            if image:renders.append(image)
        overlays=[]
        review_overlay=independent_overlay(output,source,target)
        if review_overlay:
            overlays.append(item(str(review_overlay.relative_to(site)),'独立细轮廓叠加（review-derived）','从实际OBJ与相机矩阵独立重投影；10%浅色不遮住偏差，无二维扭曲。'))
        for name,label in [('final-overlay.png','最终实际叠加'),('overlay.png','实际叠加'),('initial-overlay.png','初始实际叠加')]:
            image=own(name,label,'实际执行保存的 OpenCV 对比；保留偏差，不改成通过图。')
            if image:overlays.append(image)
        downloads=[dict(label='原始商品来源与获取证据JSON',href='inputs/'+case+'/source.json')]
        for name in ['final-state.json','posed.obj','neutral.obj','camera.json','measurements.json','measurements.csv','input-provenance.json','report.md','TRACE.md']:
            if (target/'outputs'/name).exists():downloads.append(dict(label=name,href=base+'/outputs/'+name))
        if grade:
            zip_path=site/(base+'.zip');archive(run,zip_path);downloads.append(dict(label='完整执行ZIP（含原始深度/代码/失败尝试）',href=base+'.zip'))
        galleries[key]=dict(title=title,overall=status,version=run.parent.name,source_fingerprints=fingerprints,legacy_feedback_key=None,
            stages=[dict(title='1. 原始电商输入',status='原始文件',images=[x for x in inp if x]),dict(title='2. Image Gen 实际输出',status=f'最终六图 {final_count}/6；额外引导 {max(0,len(generated)-final_count)}' if int(meta['eval_id'])==1 else '本任务仅姿态引导；六图 NOT_REQUESTED',images=generated),dict(title='3. 实际人体与三维',status='真实执行' if renders else '尚未完成',images=renders),dict(title='4. OpenCV 比较',status='实际输出' if overlays else '尚未完成',images=overlays)],downloads=downloads,
            model='../../human-studio/?model=../garment-body/commerce-evals/'+base+'/outputs/final-state.json' if fingerprints['state_sha256'] else None)
        inventory.append(dict(id=key,case=case,configuration=run.parent.name,skill_version=skill_version,heldout=heldout,overall=status,source_fingerprints=fingerprints,artifact_sha256=hashes,graded=grade is not None))
    return thin,galleries,inventory

def build(workspace,site,iteration=1,allow_pending=False,include_holdout=False):
    workspace=workspace.resolve();site=site.resolve();site.mkdir(parents=True,exist_ok=True)
    if not allow_pending:preflight(workspace,iteration,include_holdout)
    if iteration>1:build(workspace,site,iteration-1,allow_pending,False)
    thin,galleries,inventory=snapshot(workspace,site,iteration,allow_pending,include_holdout)
    if not inventory:raise ValueError('No actual runs available')
    benchmark=workspace/f'iteration-{iteration}/benchmark.json'
    if not benchmark.exists() and not allow_pending:raise ValueError('Actual aggregated benchmark missing')
    previous=None
    if iteration>1:
        previous,_,_=snapshot(workspace,site,iteration-1,allow_pending,False)
    document,upstream=official_review(thin,benchmark if benchmark.exists() else None,previous)
    document=document.replace('Executed synthetic controls. Not native Claude triggering, real anatomical validation, or full six-image generation quality.','Executed paired e-commerce functional tasks with explicit skill injection; not native Claude triggering. Full six-image generation is tested only where requested. Critical fit failures remain separate from assertion counts.')
    css=(ROOT/'tools/skill_evals/assets/official-output-gallery.css').read_text()
    script=(ROOT/'tools/skill_evals/assets/official-output-gallery.js').read_text()
    script=script.replace("[{label:'打开此版本可调人体',href:data.model},...data.downloads,\n      {label:'同画幅交互详情（当前候选）',href:'../pose-guided-fit/details.html'},\n      {label:'历史六次技能执行及原始 Benchmark',href:'../single-state-evals/history.html'}]", "[...(data.model?[{label:'打开此执行可调人体',href:data.model}]:[]),...data.downloads,{label:'此前商品姿态案例',href:'../single-state-evals/eval.html'}]")
    script=script.replace("const data = OUTPUT_GALLERIES[run.id];\n    if (feedbackMap[run.id] || !data) continue;", "const data = OUTPUT_GALLERIES[run.id];\n    if (feedbackMap[run.id] || !data || !data.legacy_feedback_key) continue;")
    script=script.replace('该版本未使用 Image Gen 引导；没有用渲染图替代生成图。','该阶段尚无实际产物；没有用其他图像冒充输出。状态以上方执行标记为准。')
    if '同画幅交互详情（当前候选）' in script:raise ValueError('Shared artifact adapter changed; commerce-specific links were not applied')
    script=script.replace('这是保存候选的实际证据。功能断言计数不是姿态准确率；请查看官方 Formal Grades，并在下方 Feedback 留言。','这是本次独立执行的实际产物。未评分/未运行不会冒充通过；功能断言计数不是原图姿态或真人尺寸准确率。请查看 Formal Grades，并在官方 Feedback 留言。')
    payload=json.dumps(galleries,ensure_ascii=False).replace('<',r'\u003c')
    document=document.replace('</head>','<style>'+css+'</style></head>',1).replace('</body>','<script>const OUTPUT_GALLERIES='+payload+';\n'+script+'</script></body>',1)
    (site/f'iteration-{iteration}.html').write_text(document);(site/'eval.html').write_text(document);(site/'index.html').write_text(document)
    if benchmark.exists():shutil.copyfile(benchmark,site/f'benchmark-iteration-{iteration}.json')
    for name in ['evals.json','plan.json','skill-v0-manifest.json','skill-v1-manifest.json','skill-v2-manifest.json']:
        if (workspace/name).exists():shutil.copyfile(workspace/name,site/name)
    write(site/'viewer-provenance.json',dict(upstream=upstream,template_sha256=sha(ROOT/'tools/skill_evals/upstream/eval-viewer/viewer.html'),format='Official shell unchanged; gallery only inside native Output',iteration=iteration,previous_iteration=iteration-1 if iteration>1 else None,scope='Explicit injected subagent functional runs; no native Claude trigger result'))
    write(site/'manifest.json',dict(iteration=iteration,complete=not allow_pending,runs=inventory,scope='Paired actual commerce functional runs; original-photo and 3D failures cannot be averaged away',files={str(p.relative_to(site)):sha(p) for p in sorted(site.rglob('*')) if p.is_file() and p.name!='manifest.json'}))
    print(json.dumps(dict(site=str(site),iteration=iteration,runs=len(inventory),graded=sum(x['graded'] for x in inventory),complete=not allow_pending)))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--workspace',type=Path,default=WORK);p.add_argument('--site',type=Path,default=SITE);p.add_argument('--iteration',type=int,default=1);p.add_argument('--allow-pending',action='store_true');p.add_argument('--include-holdout',action='store_true');a=p.parse_args();build(a.workspace,a.site,a.iteration,a.allow_pending,a.include_holdout)
