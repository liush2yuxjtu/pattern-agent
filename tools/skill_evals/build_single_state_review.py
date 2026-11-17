#!/usr/bin/env python3
"""Publish executed single-state skill runs through Anthropic's pinned viewer."""
import argparse
import hashlib
import html
import json
from pathlib import Path
import shutil
import zipfile

from build_functional_review import build as official_review
from visual_gallery import inject, stage

ROOT = Path(__file__).resolve().parents[2]
LABELS = {1: '同一人体联合拟合', 2: '同动作厘米编辑与保存', 3: '原始商品图联合拟合'}
VIEWS = {'front':'正面', 'side':'侧面', 'back':'背面', 'closeup':'特写', 'pose':'真实骨架投影', 'depth':'真实深度'}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text())


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n')


def photo_metrics(output):
    if not (output/'metrics.json').exists():
        return ''
    metrics=load(output/'metrics.json')
    initial=metrics.get('initial',metrics.get('source-camera-initial',{}))
    final=metrics.get('final',{})
    def values(record):
        mask=record.get('mask',record);joints=record.get('joints',record)
        return [mask.get('iou'),joints.get('visible_face_wrists_mean_px',joints.get('visible_face_wrist_mean_px')),mask.get('contour_p95_px',mask.get('symmetric_contour_p95_px')),mask.get('outside_fraction',mask.get('body_outside_envelope_fraction'))]
    before,after=values(initial),values(final)
    rows=[]
    for label,a,b in zip(('穿衣参考/裸模 IoU','可见眼鼻腕平均误差 px','轮廓 P95 px','裸模超出包络比例'),before,after):
        def fmt(v):return '未记录' if v is None else f'{v:.6f}'
        rows.append('<tr><td>'+label+'</td><td>'+fmt(a)+'</td><td>'+fmt(b)+'</td></tr>')
    return '<div class="photo-metrics"><h4>原始照片：真实匹配指标与残差</h4><table><thead><tr><th>指标</th><th>本执行初始</th><th>本执行最终</th></tr></thead><tbody>'+''.join(rows)+'</tbody></table><p><strong>流程达标不等于原图逐像素一致或真实人体尺寸完美恢复。</strong> 两次执行的相机/目标函数协议不同，不能用这些起点与最终值直接判定技能胜负。请查看实际正侧背、失败候选和 Formal Grades。</p></div>'


def archive(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as z:
        for p in sorted(source.rglob('*')):
            if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc':
                info = zipfile.ZipInfo(str(p.relative_to(source)), (1980,1,1,0,0,0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o644 << 16
                z.writestr(info, p.read_bytes())
    with zipfile.ZipFile(target) as z:
        if z.testzip() is not None:
            raise ValueError('Archive CRC mismatch')


def build(workspace, site, allow_pending=False):
    origin = workspace/'iteration-1'
    runs = sorted(origin.glob('eval-*/*/run-*'))
    if len(runs) != 6:
        raise ValueError('Expected all six paired executions')
    complete = all((r/'grading.json').exists() for r in runs) and (origin/'benchmark.json').exists()
    if not complete and not allow_pending:
        raise ValueError('Independent grading and official benchmark are required before publication')
    if complete:
        for run in runs:
            hashes=load(run/'grading.json').get('artifact_sha256')
            if not isinstance(hashes,dict) or not hashes:
                raise ValueError('Independent grader artifact hashes required: '+str(run))
            actual={str(p.relative_to(run/'outputs')) for p in (run/'outputs').rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}
            if set(hashes)!=actual:
                raise ValueError('Graded artifact file set changed: '+str(run))
            for name,expected in hashes.items():
                path=(run/'outputs'/name).resolve()
                if (run/'outputs').resolve() not in path.parents or not path.is_file() or digest(path)!=expected:
                    raise ValueError('Stale graded artifact: '+str(path))
    site.mkdir(parents=True, exist_ok=True)
    previous = set(load(site/'manifest.json').get('files', {})) if (site/'manifest.json').exists() else set()
    copied = set()
    review = workspace/'single-state-review-inputs'
    if review.exists():
        shutil.rmtree(review)

    def copy(source, name):
        dest = site/name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, dest)
        copied.add(name)
        return dest

    def item(source, name, label, caption):
        dest = copy(source, name)
        return dict(src=name, label=label, caption=caption, sha256=digest(dest))

    gallery, inventory, models = {}, [], []
    for run in runs:
        meta = load(run/'eval_metadata.json')
        number, config = int(meta['eval_id']), run.parent.name
        relative = run.relative_to(origin)
        key = str(relative).replace('/', '-')
        base = f'artifacts/{relative.parts[0]}/{config}'
        visual = f'visual/{relative.parts[0]}/{config}'
        output = run/'outputs'
        thin = review/relative
        (thin/'outputs').mkdir(parents=True)
        for name in ('eval_metadata.json', 'grading.json', 'timing.json'):
            if (run/name).exists():
                shutil.copyfile(run/name, thin/name)
        for name in ('report.md', 'TRACE.md', 'metrics.json'):
            if (output/name).exists():
                shutil.copyfile(output/name, thin/'outputs'/name)
        archive_name = base+'.zip'
        archive(run, site/archive_name)
        copied.add(archive_name)
        (thin/'outputs/artifacts.md').write_text(
            f'完整执行文件（包括失败尝试、代码、网格、原始深度、状态和评分）：\n\n'
            f'https://liush2yuxjtu.github.io/pattern-agent/garment-body/single-state-evals/{archive_name}\n\n'
            f'SHA256: {digest(site/archive_name)}\n\n'
            '本页上方图库使用实际原始图片；没有把模型渲染当成 Image Gen。\n')
        inputs, generated, simulations, overlays = [], [], [], []
        if number == 1:
            for view in ('front','side'):
                inputs.append(item(workspace/f'fixtures/joint-fit/reference-{view}.png', visual+'/input-'+view+'.png', '受控输入 '+VIEWS[view], '同一真实 MakeHuman 目标状态的受控参考投影；不是真人照片或 Image Gen。'))
        elif number == 2:
            if (output/'source.png').exists():
                inputs.append(item(output/'source.png', visual+'/input-source.png', '编辑前固定目标动作', '实际编辑器载入的原始动作；调厘米尺寸须保持完整关节角度。'))
        else:
            inputs.append(item(workspace/'fixtures/real-photo/original-product.jpg', visual+'/input-original.jpg', '原始电商商品图', '实际 ASOS 原图；本轮从 neutral M 初始化执行联合拟合。隐藏肩肘标注存在不确定性。'))
            for view in VIEWS:
                source = ROOT/f'web/garment-body/product-case/images/generation-2/{view}.png'
                if source.exists():
                    generated.append(dict(src=f'../product-case/images/generation-2/{view}.png', label='复用已有生成图 '+VIEWS[view], caption='REUSED：前次已存在的 Image Gen 文件；本轮未生成，不是实拍多视角，也不是本轮原图拟合的观测输入。', sha256=digest(source)))
        for view, label in VIEWS.items():
            source = output/(view+'.png')
            if source.exists():
                simulations.append(item(source, visual+'/render-'+view+'.png', '实际三维 '+label, '执行者保存的实际人体渲染/编辑器画面；同一人体与完整姿态，仅相机视角不同。是否满足任务由独立评分判断。'))
        def overlay_order(path):
            name=path.name
            if name=='final-overlay.png':return (0,name)
            if any(token in name for token in ('final_final_camera','final_camera_final')):return (1,name)
            if any(token in name for token in ('before-after','comparison')):return (2,name)
            return (3,name)
        for source in sorted(output.glob('*.png'),key=overlay_order):
            if any(token in source.stem.lower() for token in ('overlay', 'before-after', 'comparison')):
                overlays.append(item(source, visual+'/overlay-'+source.name, source.stem.replace('_',' '), '实际执行保存的 OpenCV 比较；初始、相机贡献和最终版本按文件名区分，不能把局部指标当整体匹配。'))
        if number == 3:
            for folder in sorted(p for p in output.iterdir() if p.is_dir() and any(token in p.name for token in ('attempt','reject'))):
                for view in ('front','side','back'):
                    if (folder/(view+'.png')).exists():
                        simulations.append(item(folder/(view+'.png'),visual+'/rejected-'+folder.name+'-'+view+'.png','已拒绝候选 '+folder.name+' '+VIEWS[view],'失败/中间候选的实际三维渲染，保留回退与姿态问题；不是选定最终结果。'))
                if (folder/'final-overlay.png').exists():
                    overlays.append(item(folder/'final-overlay.png',visual+'/rejected-'+folder.name+'-overlay.png','已拒绝候选 '+folder.name+' 叠加','保留失败尝试的实际叠加，不将低二维点误差当三维动作通过。'))
        state = next((output/name for name in ('final-state.json','state.json','final/state.json') if (output/name).exists()), None)
        if state:
            copy(state, base+'/final-state.json')
            model_url = '../../human-studio/?model=../garment-body/single-state-evals/'+base+'/final-state.json'
            models.append(dict(id=key, eval_id=number, config=config, state=base+'/final-state.json', href=model_url, source=str(state.relative_to(run)), sha256=digest(state),photo_metrics_html=photo_metrics(output) if number==3 else ''))
        for name in ('camera.json','posed.obj','final-posed.obj','neutral.obj','measurements.json','measurements.csv','metrics.json','view-provenance.json','view-states.json'):
            if (output/name).exists():
                copy(output/name, base+'/'+name)
        title = LABELS[number]+' · '+('修订技能' if config=='with_skill' else '旧版对照')
        gallery[key] = dict(title=title, stages=[
            stage('input','1. 输入与目标动作',inputs,'实际输入'),
            stage('imagegen','2. Image Gen',generated,'REUSED · 本轮 NOT_RUN' if generated else 'NOT_RUN','本轮未调用 Image Gen','本任务检查同一人体/动作的实际执行，不新增服装生成图。'),
            stage('simulation','3. 实际三维与编辑器',simulations,'实际执行产物' if simulations else '尚未完成','等待实际渲染','没有用占位图替代执行产物。'),
            stage('overlay','4. OpenCV 比较',overlays,'实际叠加与对照' if overlays else '不适用','此任务不做照片叠加' if number==2 else '尚无实际叠加','厘米编辑案例通过几何、关节角度与真实浏览器验证；不伪造照片拟合。')],
            note='一次独立执行；受控拟合、编辑器行为、原图动作匹配是不同验证范围。所有视图是否真实共享一份状态，请同时查看 Formal Grades、实际侧视图和完整文件。')
        inventory.append(dict(id=key, eval_id=number, config=config, archive=archive_name, sha256=digest(site/archive_name), grading=load(run/'grading.json')['summary'] if (run/'grading.json').exists() else None))

    benchmark = origin/'benchmark.json' if complete else None
    document, upstream = official_review(review, benchmark)
    document = document.replace('<head>', '<head><link rel="icon" href="../../assets/favicon.svg" type="image/svg+xml">',1)
    header = '''<style>#single-state-intro,body>nav{font:15px/1.6 system-ui,sans-serif}#single-state-intro h2{font-size:25px;margin:8px 0}#single-state-intro p{margin:8px 0}#model-handoffs{overflow-wrap:anywhere}.photo-metrics table{border-collapse:collapse;width:100%}.photo-metrics td,.photo-metrics th{text-align:left;padding:8px;border-bottom:1px solid #c5d1c5}.photo-metrics{font-size:14px}.photo-metrics p{max-width:78ch}</style><nav style="padding:12px 24px;background:#e5ede5"><a href="../skill/">当前技能与下载</a> · <a href="../product-case/eval.html">前次真实商品案例</a> · <a href="manifest.json">文件摘要</a></nav><section id="single-state-intro" style="padding:20px 24px;max-width:1100px"><h2>同一人体 · 同一目标动作 · 联合拟合</h2><p>3个任务 × 修订技能/旧版对照，共6次独立子代理实际执行；两组收到相同任务 prompt、同一现有 Pattern Agent 人体及通用 Runtime（FK/LBS/厘米校准）基础设施。Runtime 是评测 fixture 提供的工具，不是 .skill 内置的优化器；各执行者自行实现求解器。这不是仅下载 .skill 即可独立离线运行的测试。</p><p>受控真实网格拟合、真实编辑器动作保持、原始商品照片联合拟合分别评分；每配置20项断言（7＋6＋7）。不是 Claude 原生自动触发测试，当前 Claude CLI <strong>BLOCKED</strong>。</p><p>每个配置每任务只运行一次；不声称统计显著、通用真人精度或 token/耗时优势。本轮 Image Gen <strong>NOT_RUN</strong>；已有六图仅明确标注为复用上下文。</p>'''
    header += '<p><strong>'+('正式独立评分已完成；文件/功能检查不替代原图三维动作匹配。' if complete else 'RUNNING：执行或评分尚未完成，不能据此宣称通过。')+'</strong></p></section>'
    document = document.replace('<body>', '<body>'+header,1)
    # The shared adapter's old generic scope sentence describes only synthetic datasets.
    document = document.replace('Executed synthetic controls. Not native Claude triggering, real anatomical validation, or full six-image generation quality.', 'Executed single-state functional tasks: controlled anatomy, real editor and original-photo fitting. No native Claude trigger, fresh Image Gen or real-person accuracy claim.')
    document = inject(document, gallery)
    panels=[]
    for record in models:
        base=record['state'].rsplit('/',1)[0]
        downloads=[]
        for name,label in [('posed.obj','厘米posed OBJ'),('final-posed.obj','厘米posed OBJ'),('neutral.obj','中性OBJ'),('camera.json','相机参数'),('measurements.csv','尺寸CSV'),('measurements.json','尺寸来源JSON'),('metrics.json','原始指标'),('view-states.json','三视图状态证据')]:
            if base+'/'+name in copied:
                downloads.append('<a download href="'+base+'/'+name+'">'+label+'</a>')
        panels.append('<section data-model-id="'+html.escape(record['id'])+'"><p><a class="model-open" data-model-run="'+html.escape(record['id'])+'" href="'+html.escape(record['href'])+'">打开此执行的可调人体（厘米与角度）</a> · <a download href="'+record['state']+'">状态JSON</a> · <a download href="'+next(r['archive'] for r in inventory if r['id']==record['id'])+'">完整执行ZIP</a></p><p>'+ ' · '.join(downloads)+'</p>'+record['photo_metrics_html']+'</section>')
    extra='<section id="model-handoffs" style="margin:20px 0;padding:16px;background:#e5ede5;border-radius:10px"><h3>当前执行的实际模型与文件</h3>'+''.join(panels)+'</section>'
    script="""<script>(()=>{const handoff=document.createElement('div');handoff.innerHTML=HANDOFF;document.getElementById('quick-review').append(handoff);function sync(){const id=EMBEDDED_DATA.runs[currentIndex].id;document.querySelectorAll('[data-model-id]').forEach(p=>p.hidden=p.dataset.modelId!==id);}const previous=showRun;showRun=function(i){previous(i);sync();};let remembered=null;try{remembered=localStorage.getItem(STATIC_REVIEW_KEY+':visual-case');}catch{}if(remembered===null){const first=EMBEDDED_DATA.runs.findIndex(r=>VISUAL_EVIDENCE[r.id].title.includes('原始商品图')&&VISUAL_EVIDENCE[r.id].title.includes('修订技能'));if(first>=0)showRun(first);}sync();})();</script>""".replace('HANDOFF',json.dumps(extra,ensure_ascii=False).replace('<',r'\u003c'))
    document=document.replace('</body>',script+'\n</body>',1)
    (site/'eval.html').write_text(document)
    copied.add('eval.html')
    write(site/'gallery.json',gallery);copied.add('gallery.json')
    for name in ('evals.json','frozen-assertions.json'):
        copy(workspace/name,name)
    if complete:
        copy(origin/'benchmark.json','benchmark.json')
        for name in ('benchmark.md','analysis.json'):
            if (origin/name).exists():copy(origin/name,name)
    for source,name in ((workspace/'fixtures','fixtures.zip'),(workspace/'skill-old','skill-old.zip'),(workspace/'skill-new','skill-new.zip')):
        archive(source,site/name);copied.add(name)
    if complete:
        archive(workspace/'private-oracle',site/'disclosed-controlled-oracle.zip');copied.add('disclosed-controlled-oracle.zip')
    reproduction='''# Reproduce these functional evaluations

Clone the Pattern Agent repository at the published verification commit. The
`.skill` alone does not contain the MakeHuman asset, JS editor or this evaluation
runtime. Python needs NumPy, SciPy and OpenCV; fitting also uses Node. Browser
replays use the existing Playwright/Chromium setup documented in the repo.

Create `work/single-state-skill-evals-20261117/fixtures/` and extract
`fixtures.zip` there. Extract each `artifacts/CASE/CONFIG.zip` into
`work/single-state-skill-evals-20261117/iteration-1/CASE/CONFIG/run-1/`.
These archives retain the original `outputs/`, metadata, traces, grading and
failed attempts. Keep those directory levels so the saved replay entrypoints
can find the shared fixture runtime and repository model source.

Each `outputs/reproduce.py` or `reproduce.cjs` records its executable workflow;
read that run's report and TRACE for its actual command and environment. The
public state JSON also opens in Human Studio via the page's corresponding link.
The editor rounds dimensions and angles to its documented 0.1 step.

`manifest.json` gives every public file hash plus each complete run ZIP hash.
The independent `grading.json` binds all original output-file bytes. The
controlled oracle is disclosed only after all grading completes; extract it
into `work/single-state-skill-evals-20261117/private-oracle/` for grader replay,
not as solver input. Real-photo pose quality and measurements remain separate
from controlled geometry agreement and file/interaction checks.

For replaying the original grades, copy the hash-bound human action review from
`docs/verification/garment-body-single-state-evals-20261117/independent/visual-review.json`
in the cloned repository to the workspace's `grade-evidence/visual-review.json`.
This preserves a recorded human judgment, not automatic recovery of pose truth;
new or changed candidates require new visual review and matching artifact hashes.
'''
    (site/'REPRODUCE.md').write_text(reproduction)
    copied.add('REPRODUCE.md')
    for name in previous-copied:
        p=(site/name).resolve()
        if site.resolve() in p.parents and p.is_file():p.unlink()
    manifest=dict(scope='Six executed explicitly injected subagent functional trials, not native Claude routing or fresh Image Gen',complete=complete,upstream=upstream,runs=inventory,models=models,unknown=dict(tokens=None,duration=None,native_claude_trigger='BLOCKED',physical_fit='NOT_RUN'),files={str(p.relative_to(site)):digest(p) for p in sorted(site.rglob('*')) if p.is_file() and p.name!='manifest.json'})
    write(site/'manifest.json',manifest)
    print(json.dumps(dict(complete=complete,runs=len(runs),images=sum(len(s['images']) for g in gallery.values() for s in g['stages']),files=len(manifest['files']))))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--workspace',type=Path,default=ROOT/'work/single-state-skill-evals-20261117')
    p.add_argument('--site',type=Path,default=ROOT/'web/garment-body/single-state-evals')
    p.add_argument('--allow-pending',action='store_true')
    a=p.parse_args();build(a.workspace.resolve(),a.site.resolve(),a.allow_pending)
