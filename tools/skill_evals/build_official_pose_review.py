#!/usr/bin/env python3
"""Use the pinned Anthropic viewer; visual evidence stays inside native Outputs."""
import hashlib
import json
import re
import shutil
from pathlib import Path
import cv2
import numpy as np
from build_functional_review import build as official_review

ROOT = Path(__file__).resolve().parents[2]
SITE = ROOT/'web/garment-body/pose-guided-fit'
WORK = ROOT/'work/garment-body-official-review'

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p): return json.loads(p.read_text())
def write(p, value):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n')

def build(site=SITE):
    source = read(site/'manifest.json')
    if not source.get('complete'): raise ValueError('Actual graded candidate required')
    current, previous = WORK/'iteration-2', WORK/'iteration-1'
    for p in (current, previous):
        if p.exists(): shutil.rmtree(p)
    galleries, benchmark_runs, summaries = {}, [], {}
    for version, config, title in [('model','candidate','当前候选 · round14'),('baseline','baseline','修改前基线')]:
        grade = source['grades']['final' if version=='model' else 'baseline']
        for key, filename in [('state_sha256','final-state.json'),('posed_obj_sha256','posed.obj'),('camera_sha256','camera.json')]:
            if grade[key] != sha(site/version/filename): raise ValueError('Stale grading: '+version+'/'+filename)
        run = current/'eval-1-source-pose'/config/'run-1'
        (run/'outputs').mkdir(parents=True)
        prompt = ('使用原始商品照片和用户选定的 Image Gen 姿态引导，调整同一个可调厘米尺寸与骨骼姿态的人体；'
                  '正侧背共享完整状态，用实际三维渲染、OpenCV 叠加与独立评分核验。\n\n'
                  +title+'：此处查看已保存并独立复算的实际产物，不是新执行的 Claude 技能测试。'
                  '原图动作与尺寸准确性不能由文件/编辑器功能通过来证明。')
        write(run/'eval_metadata.json',dict(eval_id=1,prompt=prompt,configuration=config))
        write(run/'grading.json',grade)
        report = (f'{title}\n\nOVERALL: {grade["overall_verdict"]}\n\n'
                  '来源：已保存的真实模型及独立重算，不重新生成图片或冒充新旧技能配对实验。\n'
                  '2/5 只描述断言计数，不是姿态准确率；关键匹配失败不能被功能通过平均抵消。\n'
                  f'原图 SHA256: {source["files"]["reference/original-product.jpg"]}\n'
                  f'状态 SHA256: {grade["state_sha256"]}\n'
                  f'网格 SHA256: {grade["posed_obj_sha256"]}\n'
                  f'相机 SHA256: {grade["camera_sha256"]}\n\n'
                  '实际逐项证据见官方 Formal Grades；图库、下载、可调人体入口在本案例 Outputs 内。\n'
                  '当前候选仍有手臂/腰臀轮廓、右腕和提衣掌型失配；真实人体尺寸和隐藏深度不确定。\n')
        (run/'outputs/01-result.txt').write_text(report)
        shutil.copyfile(site/version/'final-state.json',run/'outputs/02-human-state.json')
        if version=='model':
            old = previous/'eval-1-source-pose'/config/'run-1/outputs'; old.mkdir(parents=True)
            old_grade = source['grades']['baseline']
            (old/'previous-result.txt').write_text('修改前保存的候选；整体 FAIL。右腰臀外轮廓 P95 213.56 px。\n状态 SHA256: '+old_grade['state_sha256'])
        run_id = str(run.relative_to(current)).replace('/','-')
        def item(path,label,caption):
            if not (site/path).is_file(): raise ValueError('Missing evidence '+path)
            return dict(src='../pose-guided-fit/'+path,label=label,caption=caption,sha256=sha(site/path))
        image = cv2.imread(str(site/'reference/original-product.jpg'))
        mask = cv2.imread(str(site/version/'final-mask.png'),0)>127
        preview=image.astype(float);preview[mask]=preview[mask]*.88+np.array([250,180,0])*.12
        preview=preview.astype('uint8');cv2.drawContours(preview,cv2.findContours(mask.astype('uint8'),cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)[0],-1,(250,180,0),2)
        overlay = 'review/'+('final' if version=='model' else 'baseline')+'/official-overlay.png'
        cv2.imwrite(str(site/overlay),preview)
        renders=[item(version+'/photo-render.png','原相机真实模型投影','同一实际人体，原图 1000×1276 画幅。')]
        for view,label in [('front','正面'),('side','侧面'),('back','背面')]:
            path=version+'/views/'+view+'.png'
            if not (site/path).exists():path=version+'/'+view+'.png'
            renders.append(item(path,'真实三维'+label,'同一完整状态，仅观察相机不同。'))
        generated=[] if version=='baseline' else [
            item('reference/imagegen-pose.png','实际 Image Gen 姿态图','复用已有示意输出；不是姿态检测真值。'),
            item('targets/raw-target-overlay.png','映回原图的引导点线','全局配准，无人体像素扭曲。')]
        fingerprints=dict(reference_sha256=source['files']['reference/original-product.jpg'],state_sha256=grade['state_sha256'],posed_obj_sha256=grade['posed_obj_sha256'],camera_sha256=grade['camera_sha256'])
        galleries[run_id]=dict(title=title,overall=grade['overall_verdict'],version=version,source_fingerprints=fingerprints,
            legacy_feedback_key='pattern-agent:human-review:v1:pose-guided-fit:'+version+':'+':'.join(fingerprints.values()),
            stages=[dict(title='1. 原始商品照片',status='实际输入',images=[item('reference/original-product.jpg','原始商品图','原始文件未改动。')]),
                    dict(title='2. Image Gen 姿态引导',status='REUSED · illustrative' if generated else '基线未使用此引导',images=generated),
                    dict(title='3. 实际三维模型',status='真实渲染',images=renders),
                    dict(title='4. OpenCV 叠加',status='实际网格轮廓',images=[item(overlay,'原图与真实模型细轮廓','浅青色来自保存模型的实际投影掩膜，不遮住偏差。')])],
            downloads=[dict(label=name,href='../pose-guided-fit/'+version+'/'+name) for name in ['final-state.json','posed.obj','neutral.obj','posed.glb','camera.json','measurements.json','pose-guided-reproduction.zip'] if (site/version/name).exists()],
            model='../../human-studio/?model=../garment-body/pose-guided-fit/'+version+'/final-state.json')
        summary=grade['summary'];summaries[config]=dict(pass_rate=dict(mean=summary['pass_rate'],stddev=0,min=summary['pass_rate'],max=summary['pass_rate']))
        benchmark_runs.append(dict(eval_id=1,eval_name='保存模型的原图姿态核验',configuration=config,run_number=1,result={k:summary[k] for k in ['passed','failed','total','pass_rate']},expectations=grade['expectations']))
    benchmark=dict(metadata=dict(skill_name='garment-body-six-view',evals_run=[1],runs_per_configuration=1,
        protocol='Archived actual candidates, not a controlled skill experiment'),run_summary=summaries,runs=benchmark_runs,
        notes=['这是保存的基线与当前候选各一次独立复算，非新旧技能配对执行或原生 Claude benchmark。',
               '两个版本整体均 FAIL；40% 仅为 2/5 断言计数，不是人体或姿态准确率。',
               'n=1，没有统计显著性、token 或耗时优势结论。真实尺寸和隐藏深度仍不确定。',
               '历史六次技能功能执行及原有成绩单独保留在 history.html；未混入这次候选比较。'])
    write(current/'benchmark.json',benchmark)
    document, provenance = official_review(current,current/'benchmark.json',previous)
    document=document.replace('Executed synthetic controls. Not native Claude triggering, real anatomical validation, or full six-image generation quality.',
        'Saved original-photo candidates, independently replayed. Both overall FAIL. Assertion counts are not pose accuracy or a new Claude skill benchmark.')
    css=(ROOT/'tools/skill_evals/assets/official-output-gallery.css').read_text()
    script=(ROOT/'tools/skill_evals/assets/official-output-gallery.js').read_text()
    payload=json.dumps(galleries,ensure_ascii=False).replace('<',r'\u003c')
    document=document.replace('</head>','<style>'+css+'</style></head>',1)
    document=document.replace('</body>','<script>const OUTPUT_GALLERIES='+payload+';\n'+script+'</script></body>',1)
    for folder in [site,site.parent/'single-state-evals']:
        folder.mkdir(exist_ok=True)
        (folder/'eval.html').write_text(document)
        if folder==site:(folder/'index.html').write_text(document)
        write(folder/'pose-benchmark.json',benchmark)
        write(folder/'official-viewer.json',dict(provenance=provenance,format='Pinned Anthropic viewer; only case artifacts rendered within native Outputs',
            upstream_sha256=sha(ROOT/'tools/skill_evals/upstream/eval-viewer/viewer.html'),candidate_grading_sha256=sha(site/'review/final/grading.json')))
        manifest=read(folder/'manifest.json') if (folder/'manifest.json').exists() else {}
        manifest['current_viewer']=dict(format='Anthropic skill-creator',runs=2,comparison='archived body candidates, not new skill executions',history='../single-state-evals/history.html',details='../pose-guided-fit/details.html')
        manifest['files']={str(p.relative_to(folder)):sha(p) for p in sorted(folder.rglob('*')) if p.is_file() and p.name!='manifest.json'}
        write(folder/'manifest.json',manifest)
    print(json.dumps(dict(official_runs=2,overall='FAIL',template=provenance['upstream'])))

if __name__=='__main__':build()
