#!/usr/bin/env python3
"""Source-bound official reviewer for one real full ImageGen skill execution.

No scores are inferred here. --allow-pending exposes missing evidence; a normal
build requires six native receipts and independently hash-bound grading.
"""
import argparse
import hashlib
import html
import json
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from PIL import Image
from build_functional_review import build as official_review, normalize_benchmark

ROOT = Path(__file__).resolve().parents[2]
VIEWS = ('front', 'side', 'back', 'closeup', 'pose', 'depth')


def read(p):
    return json.loads(p.read_text())


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def files(p):
    return sorted(f for f in p.rglob('*') if f.is_file() and '__pycache__' not in f.parts and f.suffix != '.pyc')


def archive(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as z:
        for p in files(source):
            info = zipfile.ZipInfo(str(p.relative_to(source)), (1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, p.read_bytes())


def reproduction_archives(run, stage):
    """Keep one compressed run when possible, otherwise independently reopenable parts."""
    target = stage / 'source/full-run.zip'
    archive(run, target)
    if target.stat().st_size < 90 * 1024 * 1024:
        return ['source/full-run.zip']
    target.unlink()
    groups, group, total = [], [], 0
    for p in files(run):
        if group and total + p.stat().st_size > 70 * 1024 * 1024:
            groups.append(group)
            group, total = [], 0
        group.append(p)
        total += p.stat().st_size
    if group:
        groups.append(group)
    names = []
    for number, group in enumerate(groups, 1):
        name = f'source/full-run-part-{number:02d}.zip'
        with zipfile.ZipFile(stage / name, 'w', zipfile.ZIP_DEFLATED) as z:
            for p in group:
                info = zipfile.ZipInfo(str(p.relative_to(run)), (1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                z.writestr(info, p.read_bytes())
        assert (stage / name).stat().st_size < 90 * 1024 * 1024, 'Single source file exceeds publication archive limit'
        names.append(name)
    return names


def runtime_archive(stage):
    runtime = ROOT / 'tools/human_fit/pose_guided'
    sources = [p for p in runtime.iterdir() if p.is_file() and p.suffix in {'.py', '.mjs', '.md', '.txt'}]
    sources += [ROOT / 'tools/human_fit/verify_measurement_export.cjs']
    sources += [p for p in files(ROOT / 'web/human-studio') if 'assets' not in p.relative_to(ROOT / 'web/human-studio').parts]
    sources += [ROOT / name for name in ['package.json', 'package-lock.json'] if (ROOT / name).exists()]
    inventory = {str(p.relative_to(ROOT)): sha(p) for p in sorted(set(sources))}
    with zipfile.ZipFile(stage / 'source/fit-runtime.zip', 'w', zipfile.ZIP_DEFLATED) as z:
        for p in sorted(set(sources)):
            info = zipfile.ZipInfo(str(p.relative_to(ROOT)), (1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, p.read_bytes())
    asset = ROOT / 'web/human-studio/assets/human.json'
    manifest = dict(source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(), files=inventory, external_asset=dict(href='../../human-studio/assets/human.json', repo_path='web/human-studio/assets/human.json', sha256=sha(asset), bytes=asset.stat().st_size), replay='Restore full-run ZIP at its original workspace relative path, extract fit-runtime.zip at repository root, restore executed skill from skill-executed.zip, obtain human.json and verify SHA, then follow model-fit/REPORT.md. Python requirements are in tools/human_fit/pose_guided/requirements.txt; editor probe needs Playwright and Chromium.')
    (stage / 'source/fit-runtime-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    return manifest


def aggregate_actual_grade(origin, run, grade):
    """Run pinned official aggregator on checked grades; never invent telemetry."""
    with tempfile.TemporaryDirectory(prefix='full-imagegen-official-aggregate-') as directory:
        target = Path(directory) / run.relative_to(origin)
        target.mkdir(parents=True)
        (target / 'grading.json').write_text(json.dumps(dict(expectations=grade['expectations'], summary=grade['summary'])))
        shutil.copyfile(run / 'eval_metadata.json', target / 'eval_metadata.json')
        result = subprocess.run([sys.executable, '-m', 'scripts.aggregate_benchmark', directory, '--skill-name', 'Full ImageGen workflow', '--output', str(origin / 'benchmark-upstream-raw.json')], cwd=ROOT / 'tools/skill_evals/upstream', text=True, capture_output=True)
    (origin / 'aggregate-upstream.log').write_text(result.stdout + result.stderr)
    result.check_returncode()
    benchmark = read(origin / 'benchmark-upstream-raw.json')
    for item in benchmark['runs']:
        item['result'].update(tokens=None, time_seconds=None, tool_calls=None, errors=None)
    benchmark = normalize_benchmark(benchmark)
    # Upstream synthesizes a delta against an absent zero-valued baseline.
    # Preserve its raw JSON, but a one-candidate acceptance has no such delta.
    benchmark['run_summary'].pop('delta', None)
    for summary in benchmark['run_summary'].values():
        summary.pop('tokens', None)
        summary.pop('time_seconds', None)
    benchmark['metadata'].update(skill_name='Full ImageGen workflow candidate acceptance', skill_path='work/full-imagegen-skill-evals-20261118/skill-executed', executor_model='Explicit Codex subagents and root ImageGen orchestration; model telemetry unavailable', analyzer_model='Independent grader; model telemetry unavailable', protocol='One actual candidate N=1; no paired old/new comparison; no native Claude trigger run', resource_metrics='Token/duration telemetry unavailable: null, never inferred from source size')
    benchmark['notes'] = ['Full flow candidate acceptance: original product photo, actual ImageGen six images, adjustable anatomical model, actual fitting/render/overlay, final neutral mesh measurements.', 'N=1, no baseline: this does not establish improvement, reliability, real-person accuracy, or trigger rates.', 'All frozen assertions graded independently. A failed critical visual/3D match is not rescued by a high file/functional pass count.', 'ImageGen pose/depth are illustrative; original photo and independent model geometry evidence are separate.']
    (origin / 'benchmark.json').write_text(json.dumps(benchmark, ensure_ascii=False, indent=2) + '\n')
    return origin / 'benchmark.json'


def build(workspace, site, allow_pending=False):
    origin = workspace / 'iteration-1'
    run = origin / 'eval-1-original-product/with_skill/run-1'
    output = run / 'outputs'
    metadata = read(run / 'eval_metadata.json')
    current_hashes = {str(p.relative_to(output)): sha(p) for p in files(output)}
    grade = read(run / 'grading.json') if (run / 'grading.json').exists() else None
    complete = grade is not None
    if complete:
        assert grade.get('artifact_sha256') == current_hashes, 'Independent grade is stale or lacks full output hash binding'
        assert [x['text'] for x in grade['expectations']] == metadata['assertions'], 'Independent grade must evaluate frozen end-to-end assertions'
        assert grade['summary']['total'] == len(metadata['assertions'])
        assert sum(x['passed'] is True for x in grade['expectations']) == grade['summary']['passed'], 'Grade summary disagrees with actual assertions'
    elif not allow_pending:
        raise ValueError('NOT_GRADED: independent grading required; use --allow-pending only for visible preview')

    receipt_path = output / 'generation-receipts.json'
    receipts = read(receipt_path) if receipt_path.exists() else {}
    receipts = receipts if isinstance(receipts, list) else receipts.get('images', [])
    receipt_map = {r['view']: r for r in receipts}
    generation = []
    missing = []
    for view in VIEWS:
        p = output / 'images' / (view + '.png')
        if not p.exists():
            missing.append(view)
            continue
        with Image.open(p) as im:
            im.verify()
        with Image.open(p) as im:
            dimensions = im.size
        receipt = receipt_map.get(view)
        if not allow_pending:
            assert receipt, f'{view}: missing actual generation receipt'
            assert receipt.get('sha256') == sha(p), f'{view}: stale generation receipt'
            assert receipt.get('status') == 'GENERATED' and receipt.get('native') is True, f'{view}: native generation not demonstrated'
            assert receipt.get('tool') and receipt.get('prompt') and receipt.get('referenced_image_paths'), f'{view}: missing actual tool/prompt/reference evidence'
            assert (receipt.get('width'), receipt.get('height')) == dimensions, f'{view}: native pixels disagree'
            assert receipt.get('collage_cropped') is False and receipt.get('upscaled') is False, f'{view}: independent native image requirement violated'
            native = Path(receipt.get('original_tool_path', ''))
            if native.is_file():
                assert sha(native) == sha(p), f'{view}: output differs from actual native tool bytes'
            assert receipt.get('reference_sha256'), f'{view}: referenced input fingerprints missing'
            for reference, fingerprint in receipt['reference_sha256'].items():
                assert Path(reference).is_file() and sha(Path(reference)) == fingerprint, f'{view}: referenced input has changed: {reference}'
        generation.append(dict(view=view, path=p, width=dimensions[0], height=dimensions[1], receipt=receipt, sha256=sha(p)))
    if not allow_pending:
        assert len(generation) == 6 and len({g['sha256'] for g in generation}) == 6, 'Six distinct actual generated images required'

    # Build in a clean staging directory so rejected builds never overwrite the last review.
    stage = site.with_name(site.name + '-staging')
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True)
    thin = workspace / 'official-review-inputs'
    if thin.exists():
        shutil.rmtree(thin)
    projection = thin / 'eval-1-original-product/with_skill/run-1'
    (projection / 'outputs').mkdir(parents=True)
    shutil.copyfile(run / 'eval_metadata.json', projection / 'eval_metadata.json')
    if grade:
        shutil.copyfile(run / 'grading.json', projection / 'grading.json')
    (projection / 'outputs/EXECUTION.md').write_text('Full end-to-end candidate acceptance. See source-bound image gallery in this Output. N=1; no old/new performance comparison.\n')
    def copy(p, relative):
        dest = stage / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(p, dest)
        return relative
    original = ROOT / 'web/garment-body/product-case/reference/original-product.jpg'
    raw = copy(original, 'inputs/original-product.jpg')
    model_index_path = output / 'model-fit/gallery-index.json'
    model = read(model_index_path) if model_index_path.exists() else {}
    selected = set()
    for key in ['simulation', 'overlay']:
        selected.update('model-fit/' + entry['path'] for entry in model.get(key, []))
    for key in ['model_files', 'required_files']:
        selected.update('model-fit/' + name for name in model.get(key, []))
    for key in ['measurement_json', 'measurement_csv', 'state']:
        if model.get(key):
            selected.add('model-fit/' + model[key])
    publication_hashes = {}
    for p in files(output):
        relative = str(p.relative_to(output))
        # The complete run is downloadable below. Avoid duplicating repeated
        # intermediate OBJ/GLB/depth arrays in the public gallery directory.
        if (relative in selected or relative.startswith(('images/', 'reference/')) or
                (p.suffix.lower() in {'.json', '.csv', '.md', '.txt', '.log', '.py', '.js'} and p.stat().st_size < 5 * 1024 * 1024)):
            copy(p, 'artifacts/' + relative)
            publication_hashes[relative] = sha(p)
    copy(run / 'eval_metadata.json', 'source/eval_metadata.json')
    for p in files(workspace / 'protocol'):
        copy(p, 'source/protocol/' + str(p.relative_to(workspace / 'protocol')))
    archive_names = reproduction_archives(run, stage)
    runtime_manifest = runtime_archive(stage)
    grader_exists = (workspace / 'grader').exists()
    if grader_exists:
        archive(workspace / 'grader', stage / 'source/independent-grader.zip')
    executed_skill = workspace / 'skill-executed'
    if executed_skill.exists():
        snapshot = read(workspace / 'skill-executed-manifest.json')
        assert snapshot['files'] == {str(p.relative_to(executed_skill)): sha(p) for p in files(executed_skill)}, 'Executed skill snapshot changed'
        archive(executed_skill, stage / 'source/skill-executed.zip')
        copy(workspace / 'skill-executed-manifest.json', 'source/skill-executed-manifest.json')
    input_references = {}
    for receipt in receipts:
        for reference, fingerprint in receipt.get('reference_sha256', {}).items():
            source = Path(reference)
            assert source.is_file() and sha(source) == fingerprint, 'Generation input changed: ' + reference
            name = 'inputs/generation-reference-' + fingerprint[:16] + source.suffix
            copy(source, name)
            input_references[reference] = dict(href=name, sha256=fingerprint)
    copy(Path(__file__), 'source/build_full_imagegen_review.py')
    def image_item(relative, label, caption):
        return dict(src=relative, label=label, caption=caption, sha256=sha(stage / relative))
    gen_images = [image_item('artifacts/images/' + g['view'] + '.png', g['view'], f"本轮实际 Image Gen · {g['width']}×{g['height']} 原生像素；" + ('illustrative：生成示意，非检测器/厘米真值。' if g['view'] in ('pose', 'depth') else '原图与人体引导条件生成；背面未见结构属推断。')) for g in generation]
    def model_items(key):
        result = []
        entries = list(model.get(key, []))
        if key == 'overlay':
            # Review-only ordering: final result is the quick-verification hero;
            # the immutable initial gallery entry remains immediately beside it.
            entries.sort(key=lambda entry: 0 if 'final-frozen-camera-overlay' in entry['path'] else 1)
        for entry in entries:
            p = output / 'model-fit' / entry['path']
            assert p.is_file(), 'Gallery refers to nonexistent actual model output: ' + str(p)
            result.append(image_item('artifacts/model-fit/' + entry['path'], entry.get('label', p.stem), entry.get('caption', '本轮真实模型执行产物；详见原始记录。')))
        return result
    simulations = model_items('simulation')
    overlays = model_items('overlay')
    if not allow_pending:
        assert simulations and overlays, 'Actual simulation and overlay galleries required'
    input_images = [image_item(raw, '原始电商模特图', '未经重绘的实际原图；同一提衣动作为拟合目标。')]
    raw_guide = output / 'images/raw-pose-guide.png'
    if raw_guide.exists():
        input_images.append(image_item('artifacts/images/raw-pose-guide.png', '原图上的 Image Gen 姿态引导', '本轮额外实际生成：原图裁切的 illustrative 点线引导，非检测真值。与六图中的 full-body pose.png 是不同文件。'))
    stages = [
        dict(key='input', title='1. 原始商品图与动作引导', status='实际原图', images=input_images),
        dict(key='imagegen', title='2. 本轮 Image Gen 六图', status=('6 张实际生成' if len(gen_images) == 6 else f'执行中 · {len(gen_images)}/6'), images=gen_images),
        dict(key='simulation', title='3. 同一可调人体真实渲染', status=model.get('verdict', 'PENDING'), images=simulations),
        dict(key='overlay', title='4. OpenCV 初始 / 最终叠加', status=model.get('verdict', 'PENDING'), images=overlays),
    ]
    extra = '<h3>本轮执行与独立评分</h3><p>' + ('独立评分完成：' + str(grade['summary']['passed']) + '/' + str(grade['summary']['total']) + '。整体动作是否匹配须看关键区域与三维检查，功能通过数量不能替代。' if grade else 'NOT_GRADED：真实生成/拟合/独立评分仍进行中，不得视为完成或通过。') + '</p>'
    if grade and grade['summary']['failed']:
        extra += '<p role="status" class="overall-failure"><strong>端到端验收 FAIL：存在未通过的要求，不宣称动作已匹配或技能完整通过。</strong></p>'
        extra += '<ul>' + ''.join('<li>' + html.escape(item['text']) + '<br>' + html.escape(item['evidence']) + '</li>' for item in grade['expectations'] if not item['passed']) + '</ul>'
    extra += '<p>N=1：本页为完整流程候选验收，无新旧技能优劣比较。native Claude trigger BLOCKED；真人尺寸准确度未验证；物理试衣 NOT_RUN。生成姿态与深度仅 illustrative；模型尺寸为条件人体实测。</p>'
    extra += '<p>生成条件：front 使用原始商品图及历史保存的人体渲染作姿态引导；其余五图使用原始商品图与本轮 front。六图先于本轮新的拟合完成，最终拟合模型没有作为这批六图的生成输入。后续模型拟合与对照会分别展示，不宣称闭环已回传生成器。</p>'
    measurement = model.get('measurement_json')
    if measurement:
        p = output / 'model-fit' / measurement
        data = read(p)
        values = data.get('measured_values_cm', {})
        extra += '<h3>最终模型实测 · cm</h3><table><thead><tr><th>尺寸</th><th>模型实测值</th></tr></thead><tbody>'
        for name, value in values.items():
            extra += '<tr><td>' + html.escape(name) + '</td><td>' + html.escape(str(value)) + '</td></tr>'
        extra += '</tbody></table>'
        for key in ['measurement_json', 'measurement_csv', 'state']:
            if model.get(key):
                relative = 'artifacts/model-fit/' + model[key]
                extra += f'<p><a download href="{html.escape(relative)}">{html.escape(key)}</a> SHA256 {sha(stage / relative)}</p>'
        if model.get('state'):
            handoff = '../../human-studio/?model=../garment-body/full-imagegen-evals/artifacts/model-fit/' + model['state']
            extra += '<p><a class="human-studio-handoff" href="' + html.escape(handoff) + '">在 Human Studio 打开本轮最终人体，继续调整厘米尺寸与姿态</a>。默认加载同一最终状态；修改后是新状态，不能继续沿用本轮评分。</p>'
    if grade:
        extra += '<details class="claim-audit"><summary>独立 claims 与评测反馈</summary>'
        for claim in grade.get('claims', []):
            extra += '<p><strong>' + ('VERIFIED' if claim.get('verified') else 'NOT VERIFIED') + ' · ' + html.escape(claim['claim']) + '</strong><br>' + html.escape(claim.get('evidence', '')) + '</p>'
        extra += '<p>' + html.escape(grade.get('eval_feedback', {}).get('overall', '')) + '</p></details>'
    for note in model.get('notes', []):
        extra += '<p>' + html.escape(note) + '</p>'
    extra += '<p>公开图库精选最终/初始可视模型及必要状态；完整中间产物均在下列可复现ZIP。artifact_sha256记录全输出，published_artifact_sha256仅记录公开精选。</p>'
    for name in archive_names:
        extra += f'<p><a download data-kind="run-archive" href="{name}">完整本轮 run ZIP · {html.escape(Path(name).name)}</a> SHA256 {sha(stage / name)}</p>'
    extra += '<p><a href="manifest.json">文件指纹 manifest</a> · <a href="source/protocol/assertions.json">冻结断言</a></p>'
    if executed_skill.exists():
        extra += f'<p><a download href="source/skill-executed.zip">本轮执行时的完整技能快照</a> SHA256 {sha(stage / "source/skill-executed.zip")} · <a href="source/skill-executed-manifest.json">快照指纹</a>。后续canonical技能文档更新不倒填为本轮原始指令。</p>'
    extra += '<details><summary>Image Gen 实际输入引用与SHA</summary>'
    for original_path, entry in input_references.items():
        extra += '<p><a download href="' + html.escape(entry['href']) + '">' + html.escape(original_path) + '</a> SHA256 ' + entry['sha256'] + '</p>'
    extra += '</details>'
    extra += '<details><summary>独立验证与底层运行时复现附件</summary>'
    if grader_exists:
        extra += f'<p><a download href="source/independent-grader.zip">独立 grader 源码与真实证据</a> SHA256 {sha(stage / "source/independent-grader.zip")}。不属于执行者自报产物。</p>'
    extra += f'<p><a download href="source/fit-runtime.zip">实际拟合底层运行时与编辑器源码</a> SHA256 {sha(stage / "source/fit-runtime.zip")} · <a href="source/fit-runtime-manifest.json">运行时逐文件SHA、固定来源提交与复现方法</a></p>'
    extra += f'<p><a download href="../../human-studio/assets/human.json">真实解剖模型资源 human.json</a> SHA256 {runtime_manifest["external_asset"]["sha256"]}。此资源复用现有发布文件，不重复打包。</p></details>'
    benchmark_path = aggregate_actual_grade(origin, run, grade) if grade else None
    document, upstream = official_review(thin, benchmark_path)
    if benchmark_path:
        copy(benchmark_path, 'benchmark.json')
        copy(origin / 'benchmark-upstream-raw.json', 'source/benchmark-upstream-raw.json')
    document = document.replace('Executed synthetic controls. Not native Claude triggering, real anatomical validation, or full six-image generation quality.', 'Actual full Image Gen workflow candidate acceptance. Native Claude trigger BLOCKED; N=1; no comparative performance claim.')
    css = (ROOT / 'tools/skill_evals/assets/visual-gallery.css').read_text()
    document = document.replace('</head>', '<style>' + css + '.full-e2e-context{font:14px/1.6 system-ui;overflow-wrap:anywhere}.full-e2e-context table{width:100%;border-collapse:collapse}.full-e2e-context td,.full-e2e-context th{text-align:left;padding:6px;border-bottom:1px solid #ddd}.evidence-stage p{font:12px/1.5 system-ui;overflow-wrap:anywhere}.full-e2e-quick-verdict{font:bold 15px/1.5 system-ui;color:#9b3027;padding:8px 0;overflow-wrap:anywhere}</style><link rel="icon" href="../../assets/favicon.svg"></head>', 1)
    quick_verdict = ('端到端验收 FAIL：' + str(grade['summary']['failed']) + ' 项要求未通过。' if grade and grade['summary']['failed'] else '最终人体与原图的视觉/动作匹配 FAIL；本轮实际生成与拟合证据如下，不能宣称已匹配。' if 'FAIL' in model.get('verdict', '') else 'NOT_GRADED：本轮实际执行与独立评分进行中。' if not grade else '冻结端到端要求均通过；真人尺寸准确度仍未验证。')
    payload = json.dumps(dict(stages=stages, extra_html=extra, quick_verdict=quick_verdict), ensure_ascii=False).replace('<', r'\u003c')
    script = r'''(() => {
 const dialog=document.createElement('dialog');dialog.className='evidence-lightbox';dialog.setAttribute('aria-label','Evidence image viewer');dialog.innerHTML='<div class="lightbox-head"><strong id="lightbox-title"></strong><button id="lightbox-close">Close ×</button></div><img id="lightbox-image" class="lightbox-image" alt=""><p id="lightbox-caption"></p><div class="lightbox-controls"><button id="lightbox-prev">← Previous image</button><span id="lightbox-position"></span><button id="lightbox-next">Next image →</button><a id="lightbox-original" target="_blank" rel="noopener">Open original</a></div>';document.body.append(dialog);
 let images=[],position=0,opener;const find=s=>dialog.querySelector(s);
 function paint(){const im=images[position];find('#lightbox-title').textContent=im.label;find('#lightbox-image').src=im.src;find('#lightbox-image').alt=im.label;find('#lightbox-caption').textContent=im.caption;find('#lightbox-original').href=im.src;find('#lightbox-position').textContent=`${position+1} / ${images.length}`;find('#lightbox-prev').disabled=position===0;find('#lightbox-next').disabled=position===images.length-1;}
 function close(){dialog.close();opener?.focus();}find('#lightbox-close').onclick=close;find('#lightbox-prev').onclick=()=>{if(position>0){position--;paint();}};find('#lightbox-next').onclick=()=>{if(position<images.length-1){position++;paint();}};
 document.addEventListener('keydown',e=>{if(dialog.open&&['ArrowLeft','ArrowRight','Escape'].includes(e.key)){e.preventDefault();e.stopImmediatePropagation();if(e.key==='Escape')close();else find(e.key==='ArrowLeft'?'#lightbox-prev':'#lightbox-next').click();}},true);
 function button(im,index,thumb=false){const b=document.createElement('button');b.type='button';b.className=thumb?'':'evidence-image';b.setAttribute('aria-label','Open '+im.label);const img=document.createElement('img');img.src=im.src;img.alt=im.label;b.append(img);b.onclick=()=>{opener=b;position=index;paint();dialog.showModal();};return b;}
 const original=renderOutputs;renderOutputs=function(run){original(run);images=[];const block=document.createElement('section');block.id='official-case-gallery';block.className='output-file';const head=document.createElement('div');head.className='output-file-header';head.textContent='原图 → 本轮 Image Gen 六图 → 同一可调人体 → OpenCV 叠加';const content=document.createElement('div');content.className='output-file-content';const grid=document.createElement('div');grid.className='evidence-grid';for(const stage of FULL_E2E.stages){const card=document.createElement('section');card.className='evidence-stage';card.dataset.stage=stage.key;const h=document.createElement('h3');h.textContent=stage.title;const status=document.createElement('p');status.className='stage-status';status.textContent=stage.status;card.append(h,status);if(!stage.images.length){const p=document.createElement('p');p.className='evidence-empty';p.textContent='PENDING：本轮实际产物尚未完成；没有以历史文件替代。';card.append(p);}else{const start=images.length;images.push(...stage.images);card.append(button(stage.images[0],start));const caption=document.createElement('p');caption.textContent=stage.images[0].caption;card.append(caption);if(stage.images.length>1){const thumbs=document.createElement('div');thumbs.className='thumb-strip';stage.images.forEach((im,j)=>thumbs.append(button(im,start+j,true)));card.append(thumbs);}}grid.append(card);}const context=document.createElement('div');context.className='full-e2e-context';context.innerHTML=FULL_E2E.extra_html;const quick=document.createElement('p');quick.className='full-e2e-quick-verdict';quick.setAttribute('role','status');quick.textContent=FULL_E2E.quick_verdict;content.append(quick,grid,context);block.append(head,content);document.querySelector('#outputs-body').prepend(block);};showRun(0);
})();'''
    document = document.replace('</body>', '<script>const FULL_E2E=' + payload + ';\n' + script + '</script></body>', 1)
    (stage / 'eval.html').write_text(document)
    manifest = dict(scope='full workflow single-candidate acceptance', complete=complete, status='GRADED' if complete else 'NOT_GRADED', imagegen_count=len(generation), missing_imagegen_views=missing, generation=[{k: v for k, v in g.items() if k != 'path'} for g in generation], generation_input_references=input_references, native_claude_trigger='BLOCKED', real_person_accuracy='NOT_VALIDATED', physical_fit='NOT_RUN', tokens=None, duration=None, input_sha256=sha(original), grading=grade['summary'] if grade else None, model_verdict=model.get('verdict', 'PENDING'), upstream=upstream, artifact_sha256=current_hashes)
    manifest['published_artifact_sha256'] = publication_hashes
    manifest['reproduction_archives'] = [dict(href=name, sha256=sha(stage / name), bytes=(stage / name).stat().st_size) for name in archive_names]
    manifest['overall_acceptance'] = ('FAIL' if grade['summary']['failed'] else 'PASS') if grade else 'NOT_GRADED'
    manifest['runtime_source'] = runtime_manifest
    manifest['files'] = {str(p.relative_to(stage)): sha(p) for p in files(stage)}
    (stage / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    if site.exists():
        shutil.rmtree(site)
    stage.rename(site)
    return dict(out=str(site / 'eval.html'), status=manifest['status'], imagegen_count=len(generation))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--workspace', type=Path, default=ROOT / 'work/full-imagegen-skill-evals-20261118')
    p.add_argument('--site', type=Path, default=ROOT / 'web/garment-body/full-imagegen-evals')
    p.add_argument('--allow-pending', action='store_true')
    a = p.parse_args()
    print(json.dumps(build(a.workspace.resolve(), a.site.resolve(), a.allow_pending)))
