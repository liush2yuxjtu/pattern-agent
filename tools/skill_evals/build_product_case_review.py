#!/usr/bin/env python3
"""Publish the real product case through the pinned Anthropic review viewer.

This is a product-specific generation revision history, not a paired skill
benchmark. Full-resolution Image Gen bytes and every public file hash survive.
Model outputs are opt-in and rejected unless their reference hashes match v2.
"""
import argparse
import csv
import hashlib
import html
import json
from pathlib import Path
import shutil
import zipfile
from PIL import Image
from build_functional_review import build as upstream_build
from visual_gallery import inject, stage
from validate_product_model import validate as validate_model

VIEWS = ('front', 'side', 'back', 'closeup', 'pose', 'depth')
LABELS = dict(front='正面', side='侧面', back='背面', closeup='特写', pose='姿态标注示意', depth='深度风格示意')
MEASURES = dict(height='身高', bust='胸围', waist='腰围', hips='臀围', shoulders='肩宽', upperArm='上臂围', thigh='大腿围', neck='颈围', upperArmLength='上臂长', forearmLength='前臂长', thighLength='大腿长', calf='小腿围')
INITIAL_PRIOR = dict(height=170,bust=90,waist=72,hips=96,shoulders=37,upperArm=27,thigh=54,neck=32,upperArmLength=29,forearmLength=23,thighLength=40,calf=36)
UNAVAILABLE = dict(underbust='下胸围',bustPointDistance='胸点距',shoulderSlope='肩斜',frontWaistLength='前腰节长',backWaistLength='后腰节长',crotchArc='裆弧长')
SOURCE = 'https://www.asos.com/us/asos-design/asos-design-lounge-pointelle-boatneck-3-4-sleeve-top-in-red/prd/211010805'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def verify_generation(workspace, number):
    folder = workspace/f'iterations/generation-{number}'
    metadata = read(folder/'generation.json')
    entries = metadata.get('paths') or {row['view']:row for row in metadata['outputs']}
    if set(entries) != set(VIEWS):
        raise ValueError('Generation must declare exactly six views')
    if metadata.get('collage_cropped') is not False or metadata.get('upscaled') is not False:
        raise ValueError('Native independent output provenance is missing')
    if metadata.get('tool') != 'image_gen.imagegen':
        raise ValueError('Image Gen tool provenance is missing')
    native = metadata.get('native_tool_outputs') or metadata.get('outputs')
    if not native or len(native)!=6 or {row['view'] for row in native}!=set(VIEWS):
        raise ValueError('Six native tool output records required')
    native = {row['view']:row for row in native}
    original_paths = [row.get('original_tool_path',row.get('path')) for row in native.values()]
    if len(set(original_paths))!=6 or any(not name for name in original_paths):
        raise ValueError('Six independent native tool paths required')
    for view in VIEWS:
        entry=entries[view]
        path=folder/(view+'.png')
        if digest(path) != entry['sha256']:
            raise ValueError('Image Gen image hash mismatch: '+view)
        original=native[view]
        if original.get('tool')!='image_gen.imagegen' or original['sha256']!=entry['sha256']:
            raise ValueError('Copied image disagrees with native tool output: '+view)
        with Image.open(path) as image:
            if list(image.size) != (entry.get('pixels') or entry.get('native_pixels')):
                raise ValueError('Image Gen native pixel mismatch: '+view)
            if list(image.size)!=original['native_pixels']:
                raise ValueError('Copied image was cropped or resized: '+view)
        tool_path=Path(original.get('original_tool_path',original.get('path')))
        if tool_path.is_file() and digest(tool_path)!=entry['sha256']:
            raise ValueError('Original tool bytes differ from copied image: '+view)
    return metadata


def reproduction_archive(workspace, site):
    """Keep task evidence and source, exclude caches and redundant trial trees."""
    repo = Path(__file__).resolve().parents[2]
    selected = []
    for path in sorted(workspace.rglob('*')):
        if not path.is_file():
            continue
        rel = path.relative_to(workspace)
        original_previous=rel.parts[:3]==('model','original-reference','iteration-1')
        if '__pycache__' in rel.parts or ('iteration-1' in rel.parts and not original_previous) or path.suffix in ('.b64','.pyc'):
            continue
        if rel.parts[0] not in ('reference','images','iterations','case','model'):
            continue
        if rel.parts[0]=='reference' and path.name not in ('original-product.jpg','asos-page.png','source-verification.json','asos-product-excerpt.md'):
            continue
        if path.name=='contact-review.jpg':
            continue
        native_model_guide=len(rel.parts)>3 and rel.parts[:3]==('model','generation-1','initial-renders') and path.name in {view+'.png' for view in VIEWS}
        if rel.parts[:2]==('model','generation-1') and path.suffix in ('.png','.npy') and not native_model_guide:
            # Original failed-generation photos are retained under iterations/;
            # its old renderer previews are reproducible from archived geometry.
            continue
        if len(rel.parts)>3 and rel.parts[:2]==('model','original-reference') and rel.parts[2].startswith('iteration-') and path.suffix in ('.png','.npy') and path.name!='before-after.png':
            continue
        # Keep all selected evidence and both generation histories. These are
        # superseded diagnostic renders; their states/metrics/search records
        # remain, and the final diagnostics are preserved in full below.
        if rel.parts[:3]==('model','fixed-M-baseline','view-specific') and path.suffix in ('.png','.npy','.obj','.glb'):
            continue
        if rel.parts[:3]==('model','fixed-M-baseline','original-reference') and path.suffix in ('.png','.npy'):
            continue
        if rel.parts[:3]==('model','shape-fit','torso-only-search') and path.suffix in ('.png','.npy'):
            continue
        if path.suffix not in ('.png','.jpg','.json','.npy','.csv','.py','.mjs','.md','.obj','.glb','.log'):
            continue
        selected.append((path,Path('work')/workspace.name/rel))
    renderer = repo/'work/anatomical-skill-evals-20261117/fixtures/render_mesh.py'
    if not renderer.is_file():
        raise ValueError('Reproduction requires the actual renderer source')
    selected.append((renderer,renderer.relative_to(repo)))
    for name in ('measurements.json','measurements.csv'):
        if (site/name).is_file():
            selected.append((site/name,Path('work')/workspace.name/'case'/('published-'+name)))
    hashes = {str(name):digest(source) for source,name in selected}
    canonical = {}
    aliases = {}
    unique=[]
    for source,name in selected:
        name=str(name);sha=hashes[name]
        if sha in canonical:
            aliases[name]=canonical[sha]
        else:
            canonical[sha]=name;unique.append((source,name))
    archive = site/'reproduce.zip'
    instructions = '''# 实际商品案例：复核与重放

先 clone https://github.com/liush2yuxjtu/pattern-agent 并切到发布本包的提交。
从仓库根目录解压 reproduce.zip，然后运行 python REPRODUCE-RESTORE.py。
复核包按SHA256去重：恢复脚本将相同原始字节复制回其所有原有路径，并逐项校验。
包内 work/ 路径须原样保留，不能只移动 model/。
脚本使用仓库现有 web/human-studio/body-engine.js、vendor 与 human.json。
Python 依赖：numpy、scipy、opencv-python、Pillow；Node 使用仓库已有依赖。
读取 work/product-red-pointelle-20261117/model/README.md 的复核与重放命令。
renderer源文件同时解压到 work/anatomical-skill-evals-20261117/fixtures/render_mesh.py。
先核对 REPRODUCE-MANIFEST.json 的逐文件摘要，再在工作副本运行；重跑会覆盖输出。

generation-1 是袖长错误的冻结对照；model/generation-1 只用于历史只读审计，
其中脚本的相对层级是归档前层级，不在该子目录直接执行。当前可执行脚本位于 model/。
保留 generation-2 实际图像、冻结分割、相机、姿态、cm网格、带骨骼GLB、数值深度、
OpenCV图与指标。排除Python缓存、重复的早期iteration-1树、源站抓取base64缓存，
以及已被最终候选替代的M基线单图/原图诊断渲染和torso-only中间图；其状态/指标/搜索记录仍保留。
这是选定复核子集，不是整个执行工作目录：第一轮六张原生照片、审查、状态/网格/指标保留，
第一轮旧模型光栅预览/数值深度未打包（本地完整记录保留，必要时可从归档网格重渲染）。
原图专项旧候选保留状态/网格/指标及前后对比图，省略旧候选的重复光栅预览。
Image Gen是外部非确定性生成，不承诺字节级重新生成相同照片；原始返回字节已保留。
这不是布料/组织物理仿真。人体以中码先验初始化；包络约束下的条件调整值与网格参数，
均不是原模特真人测量。请以当前CSV的basis与模型报告区分先验和条件估计。
'''
    restore = '''#!/usr/bin/env python3
import hashlib,json,pathlib,shutil
root=pathlib.Path(__file__).resolve().parent
manifest=json.loads((root/'REPRODUCE-MANIFEST.json').read_text())
def target(name):
 p=(root/name).resolve()
 if root not in p.parents:raise ValueError('Unsafe archive path')
 return p
for alias,canonical in manifest['aliases'].items():
 source=target(canonical);dest=target(alias)
 if hashlib.sha256(source.read_bytes()).hexdigest()!=manifest['files'][alias]:raise ValueError('Bad canonical bytes')
 dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,dest)
for name,sha in manifest['files'].items():
 if hashlib.sha256(target(name).read_bytes()).hexdigest()!=sha:raise ValueError('Hash mismatch: '+name)
print(json.dumps({'verdict':'PASS','files':len(manifest['files']),'restored_aliases':len(manifest['aliases'])}))
'''
    archive_manifest=dict(scope='Selected reproducible evidence subset, not the entire execution workspace; omissions documented in REPRODUCE.md',files=hashes,aliases=aliases,method='Identical bytes stored once; restore aliases after extraction before replay')
    entries = [(str(name),source.read_bytes()) for source,name in unique]
    entries += [('REPRODUCE.md',instructions.encode()),('REPRODUCE-RESTORE.py',restore.encode()),('REPRODUCE-MANIFEST.json',(json.dumps(archive_manifest,indent=2)+'\n').encode())]
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as output:
        for name, content in sorted(entries):
            info=zipfile.ZipInfo(name,(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o644<<16
            output.writestr(info,content)
    with zipfile.ZipFile(archive) as output:
        if output.testzip() is not None:
            raise ValueError('Reproduction ZIP failed CRC')
        for name, expected in hashes.items():
            if hashlib.sha256(output.read(aliases.get(name,name))).hexdigest()!=expected:
                raise ValueError('Reproduction ZIP hash mismatch: '+name)
    if archive.stat().st_size >= 90*1024*1024:
        raise ValueError('Reproduction ZIP too large for ordinary GitHub publication')
    (site/'REPRODUCE.md').write_text(instructions)
    return {'reproduce.zip':digest(archive),'REPRODUCE.md':digest(site/'REPRODUCE.md')}


def build(workspace, site, include_model=False):
    site.mkdir(parents=True, exist_ok=True)
    previous_files = set(read(site/'manifest.json').get('files', {})) if (site/'manifest.json').exists() else set()
    review_workspace = workspace / 'product-review-inputs'
    # Clear only this builder's generated review staging to avoid stale outputs.
    if review_workspace.exists():
        shutil.rmtree(review_workspace)
    copied = {}

    def copy(source, relative):
        target = site / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        copied[relative] = digest(target)
        return relative

    def item(source, relative, label, caption):
        copy(source, relative)
        with Image.open(source) as image:
            size = list(image.size)
        return dict(src=relative, label=label, caption=caption, sha256=copied[relative], pixels=size)

    inputs = [item(workspace/'reference/original-product.jpg', 'reference/original-product.jpg', '原始电商商品图 · 实际生成输入', '实际 Image Gen 参考照片；弯臂、局部裁切，与后续标准视图的姿态不同。'),
              item(workspace/'reference/asos-page.png', 'reference/asos-page.png', 'ASOS 官方商品页 · 来源核对', '来源与规格核对截图，不是提交给 Image Gen 的输入。官网确认红色 pointelle 船领七分袖，原模特 171 cm、穿 S。')]
    for name in ('source-verification.json', 'asos-product-excerpt.md'):
        copy(workspace/'reference'/name, 'reference/'+name)

    ready = False
    metrics = {}
    independent_model_check = None
    if include_model:
        gate = read(workspace/'model/fit/input-hashes.json')
        if gate.get('generation') != 'generation-2':
            raise ValueError('Model generation marker is not generation-2')
        for view in ('front', 'side', 'back'):
            if gate['reference_image_sha256'][view] != digest(workspace/f'iterations/generation-2/{view}.png'):
                raise ValueError('Stale fit reference: '+view)
        metrics = read(workspace/'model/fit/metrics.json')
        protocol = metrics['protocol']
        if protocol['final_pose_state_sha256'] != digest(workspace/'model/final-state.json'):
            raise ValueError('Metrics do not match final state')
        if protocol['final_posed_obj_sha256'] != digest(workspace/'model/final-posed.obj'):
            raise ValueError('Metrics do not match final mesh')
        independent_model_check = validate_model(workspace,Path(__file__).resolve().parents[2])
        write(site/'provenance/independent-model-check.json',independent_model_check)
        copied['provenance/independent-model-check.json']=digest(site/'provenance/independent-model-check.json')
        ready = True

    gallery = {}
    runs = []
    summaries = {}
    for number in (2, 1):
        verify_generation(workspace,number)
        actual_inputs=list(inputs)
        if number==1:
            for view in VIEWS:
                actual_inputs.append(item(workspace/f'model/generation-1/initial-renders/{view}.png',f'input/generation-1/model-{view}.png','实际首轮三维引导 · '+LABELS[view], '第1轮实际 Image Gen 输入：原始中码人体渲染（170/90/72/96 cm），不是后来69 cm腰围、50 cm大腿围的条件模型。'))
        else:
            for view in ('front','side','back','closeup'):
                actual_inputs.append(item(workspace/f'iterations/generation-1/{view}.png',f'images/generation-1/{view}.png','实际第2轮编辑锚点 · '+LABELS[view], '原商品照片 + 第1轮对应照片用于衣物修正；姿态示意与深度示意都使用第1轮正面锚点。三维引导经第1轮继承，最终69/50 cm模型没有重新送入本轮 Image Gen。'))
        config = 'generation_'+str(number)
        run_config = config if number==2 else 'history_'+config
        directory = review_workspace/'eval-product'/run_config/'run-1'
        output = directory/'outputs'
        output.mkdir(parents=True)
        images = []
        sizes = []
        for view in VIEWS:
            source = workspace/f'iterations/generation-{number}/{view}.png'
            note = '实际 Image Gen 独立文件；原生分辨率、未拼图。'
            if view in ('pose', 'depth'):
                note += ' 仅生成式示意，不是检测器结果或可测量深度。'
            image = item(source, f'images/generation-{number}/{view}.png', LABELS[view], note)
            images.append(image)
            sizes.append(image['pixels'])
        copy(workspace/f'iterations/generation-{number}/generation.json', f'provenance/generation-{number}.json')
        reviewer = workspace/f'case/independent-visual-review-v{number}.json'
        report = read(reviewer) if reviewer.exists() else {}
        review_hashes=report.get('hashes',report.get('reviewed_file_sha256',{}))
        for name, expected in review_hashes.items():
            source=workspace/name
            # V1 reviews refer to the former top-level images before v2
            # replaced them. Resolve only those archived generation-1 images.
            if number==1 and name.startswith('images/'):
                source=workspace/'iterations/generation-1'/Path(name).name
            if number==1 and name.startswith('model/'):
                source=workspace/'model/generation-1'/Path(name).relative_to('model')
            if source.exists() and digest(source)!=expected:
                raise ValueError('Independent review no longer matches reviewed file: '+name)
        if number==2 and ready:
            for name, expected in report.get('reviewed_model_artifact_sha256',{}).items():
                source=(workspace/name).resolve()
                if workspace not in source.parents or not source.is_file() or digest(source)!=expected:
                    raise ValueError('Stale independently reviewed model artifact: '+name)
        if reviewer.exists():
            copy(reviewer, f'provenance/independent-visual-review-v{number}.json')
            shutil.copyfile(reviewer, output/'independent-review.json')
        review_md = reviewer.with_suffix('.md')
        if review_md.exists():
            copy(review_md, f'provenance/independent-visual-review-v{number}.md')
        expectations = [dict(text='六张独立原生高分辨率图像', passed=len(images)==6 and all(min(s)>1000 for s in sizes), evidence='实际文件尺寸：'+json.dumps(dict(zip(VIEWS,sizes)))),
                        dict(text='保留失败轮与实际生成文件摘要', passed=True, evidence=f'provenance/generation-{number}.json；manifest.json逐文件SHA256。')]
        # A reviewer verdict is not silently converted to a pass. Uncertain
        # criteria remain unscored rather than being treated as failed/successful.
        passed = sum(e['passed'] for e in expectations)
        summary = dict(passed=passed, failed=len(expectations)-passed, total=len(expectations), pass_rate=passed/len(expectations))
        grading = dict(expectations=expectations, summary=summary, execution_metrics=dict(total_tokens=None, duration_ms=None, tool_calls=None), notes=['同一商品的生成修正历史；不是配对技能基准、人体真值或物理合身验证。'])
        write(directory/'grading.json', grading)
        write(directory/'eval_metadata.json', dict(eval_id=1, eval_name='ASOS 红色七分袖商品：生成修正历史', prompt='依据原始电商商品图与可调人体，生成正面、侧面、背面、特写、姿态示意和深度风格六张独立图；使用真实参数化人体、相机校准与 OpenCV 叠加验证。第'+str(number)+'轮。未见结构为生成推测，胸腰臀仍为中码先验。'))
        write(directory/'timing.json', dict(total_tokens=None, duration_ms=None, total_duration_seconds=None))
        simulations = []
        overlays = []
        if number == 2 and ready:
            for view in VIEWS:
                simulations.append(item(workspace/f'model/final-renders/{view}.png', f'simulation/{view}.png', '真实人体渲染 · '+LABELS[view], '实际 MakeHuman 参数化网格投影；无服装、无布料物理。'+(' 深度来自数值 Z-buffer。' if view=='depth' else '')))
            for view in ('front', 'side', 'back'):
                for suffix, label in [('before-after','前后对比'), ('final-photo-overlay','最终照片叠加'), ('reference-landmarks-roi','手动关键点与ROI')]:
                    path = workspace/f'model/fit/{view}-{suffix}.png'
                    if path.exists():
                        overlays.append(item(path, f'overlay/{view}-{suffix}.png', LABELS[view]+' · '+label, '实际 OpenCV 输出；照片为生成参考。关键点与轮廓一致性不等于恢复真人裸模尺寸。'))
            for view in ('front','side','back'):
                path=workspace/f'model/shape-fit/{view}-before-after.png'
                if path.exists():
                    overlays.append(item(path,f'overlay/shape-{view}-before-after.png',LABELS[view]+' · 中码到条件体形', '固定相机和共享姿态，比较原始中码与衣物包络约束的条件体形。不是裸身轮廓等值拟合。'))
            for view in ('side','back'):
                view_dir=workspace/f'model/view-specific/{view}'
                if view_dir.exists():
                    state=read(view_dir/'state.json');final_state=read(workspace/'model/final-state.json');diagnostic=read(view_dir/'metrics.json')
                    if state['dimensions']!=final_state['dimensions'] or state['asset']!=final_state['asset']:
                        raise ValueError('View-specific state is not the same selected body: '+view)
                    if diagnostic['protocol']['reference_sha256']!=digest(workspace/f'iterations/generation-2/{view}.png'):
                        raise ValueError('View-specific diagnostic is stale: '+view)
                    for name in ('shared-overlay.png','view_specific-overlay.png','before-after.png'):
                        overlays.append(item(view_dir/name,f'view-specific/{view}/{name}',LABELS[view]+' · '+('共享姿态' if name.startswith('shared') else '单图姿态诊断'), '同一人体尺寸、同一相机；单图仅调姿态以解释生成图的不一致。训练过本图后不再是留出验证。'))
                    for name in ('state.json','metrics.json','camera.json','posed.obj','posed.glb'):
                        if (view_dir/name).exists():copy(view_dir/name,f'view-specific/{view}/{name}')
            for name in ('optimization.json','metrics.json'):
                source=workspace/'model/shape-fit'/name
                if source.exists():copy(source,'model/shape-fit/'+name)
            original_dir=workspace/'model/original-reference'
            if original_dir.exists():
                original_state=read(original_dir/'state.json');final_state=read(workspace/'model/final-state.json')
                if original_state['dimensions']!=final_state['dimensions'] or original_state['morphWeights']!=final_state['morphWeights']:
                    raise ValueError('Original-reference diagnostic must retain selected final body shape')
                for name in ('before-after.png','previous_candidate-overlay.png','refined_head_and_arms-overlay.png'):
                    if (original_dir/name).exists():
                        overlays.append(item(original_dir/name,'original-reference/'+name,'原商品图独立诊断 · '+('前后对比' if name=='before-after.png' else '实际投影叠加'),'原始电商图本身：同一条件人体，仅重新调弯臂、头颈与躯干姿态。与生成图核验分开，不证明恢复真人体形。'))
                for view in ('front','side'):
                    source=original_dir/f'renders/{view}.png'
                    if source.exists():
                        simulations.append(item(source,f'original-reference/renders/{view}.png','原始商品图姿态 · 真实三维'+LABELS[view], '同一条件体形的原图专项姿态诊断；实际网格渲染用于检查手臂和手掌，非生成照片。'))
                for name in ('state.json','camera.json','metrics.json','manual-landmarks.json','hand-depth-check.json','candidate-status.json','ik-depth-feasibility.json','geometry-check.json','inspection-camera.json','torso-front-depth-cm.npy','torso-front-depth-valid.png','posed.obj','posed.glb','renders/front.png','renders/side.png'):
                    if (original_dir/name).exists():copy(original_dir/name,'original-reference/'+name)
            for path in ('final-state.json','final-posed.obj','final-neutral.obj','final-posed.glb','neutral-measurements.csv','final-independent-check.json','final-geometry-check.json','camera.json','camera-calibration.json','README.md','fit/input-hashes.json','fit/metrics.json','fit/camera-pose-contributions.json'):
                source = workspace/'model'/path
                if source.exists():
                    copy(source,'model/'+path)
            for source in (workspace/'model/final-renders').glob('*'):
                if source.suffix in ('.npy','.json') or source.name.endswith('-valid.png'):
                    copy(source,'model/raw-depth/'+source.name)
            shutil.copyfile(workspace/'model/fit/metrics.json',output/'fit-metrics.json')
            shutil.copyfile(workspace/'model/neutral-measurements.csv',output/'measurements.csv')
        title = '第2轮 · 七分袖修正' if number == 2 else '第1轮 · 袖长错误（失败对照）'
        gallery[f'eval-product-{run_config}-run-1'] = dict(title=title, stages=[
            stage('input','1. 实际生成输入与来源',actual_inputs,'实际输入与规格核对分列'),
            stage('imagegen','2. Image Gen 六张输出',images,'已实际执行 · 6 张'),
            stage('simulation','3. 真实三维人体渲染',simulations,'真实模型输出' if simulations else '未在此轮展示','模型输出待核验' if number==2 else '失败轮不复用修正轮模型','只有图像摘要与拟合输入一致、最终网格与metrics摘要一致时才显示。'),
            stage('overlay','4. OpenCV 核验',overlays,'实际叠加与前后比较' if overlays else '未在此轮展示','没有可展示的本轮叠加','第2轮必须重新标注、分割与拟合，不借用上一轮数字。')],note='六张是独立图像文件，可点击缩略图逐张放大并打开原图。姿态图、深度风格图为生成式示意；实际骨架投影、数值深度在三维渲染区。原商品图之外的背面与全长为推测。人体以中码先验初始化；围度条件调整与网格参数均不能作为原模特的真人测量。')
        (output/'artifacts.md').write_text(f'## {title}\n\n本页四阶段画廊保留独立原图与SHA256。\n\n[六张Image Gen文件及模型输出清单](manifest.json)\n\n[实际生成记录](provenance/generation-{number}.json)\n\n同一case修正历史，不是随机或配对技能因果基准。token与完整耗时未记录，保留null。物理服装合身验证 NOT_RUN。\n')
        runs.append(dict(eval_id=1, eval_name='同一商品的修正历史', configuration=config, run_number=1, result={**summary,'tokens':None,'time_seconds':None,'tool_calls':None,'errors':None}, expectations=expectations))
        summaries[config] = dict(pass_rate=dict(mean=summary['pass_rate'],stddev=0.0))
    benchmark = dict(metadata=dict(skill_name='真实商品六图与参数人体：文件执行完整性',timestamp='2026-11-17',evals_run=[1],runs_per_configuration=1), runs=runs, run_summary=summaries, notes=['仅一个商品的两代修正；不是新旧技能配对基准，不报告因果增益。','此处成功率仅汇总六文件与摘要的客观执行完整性。商品主观审查、几何匹配与原图恢复分别列于Outputs，不合并异质断言成功率。第一轮服装袖长错误依然FAIL，即使文件完整。','tokens、完整生成/拟合墙钟耗时未知；保留null。原生Claude触发评测仍BLOCKED，服装物理合身NOT_RUN。'])
    write(site/'benchmark.json',benchmark)
    document, upstream = upstream_build(review_workspace, site/'benchmark.json')
    document = inject(document,gallery)
    document = document.replace('Quick visual verification','快速视觉核验').replace('Input → Image Gen → simulation → overlay. Click an image to inspect it.','原始图 → 六张生成图 → 三维人体 → OpenCV 叠加；点击缩略图放大。').replace('Case & configuration','修正轮次').replace('aria-label="Case and configuration"','aria-label="修正轮次"')
    document = document.replace('<head>','<head><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="icon" href="../../assets/favicon.svg" type="image/svg+xml">',1)
    header = '<nav class="product-nav"><a href="../skill/">技能与下载</a> · <a href="../anatomical-evals/eval.html">历史合成组件评测</a> · <a href="manifest.json">本案例文件摘要</a></nav><div class="product-intro"><h2>从电商原图到六图与可调人体</h2><p>实际商品：<a href="'+SOURCE+'" target="_blank" rel="noopener">ASOS 船领七分袖 pointelle 红色上衣</a>。官网原模特 171 cm、穿 S；演示裸模以用户允许的 170 cm 中码先验初始化。先检查商品，再比较真实网格与照片叠加。</p><p>第1轮袖长错误保留为失败对照；第2轮修正七分袖。六图生成已执行。<strong>原始商品图的人体姿态仍 POSE_FAIL，未达到三维动作匹配。</strong>裸模不是布料仿真，物理合身 <strong>NOT_RUN</strong>。</p>'
    if ready:
        header += '<p><a class="product-primary" id="adjust-model" href="../../human-studio/?model=../garment-body/product-case/model/final-state.json">打开第2轮选中人体，调厘米尺寸与姿态</a></p>'
    header += '<p>输入链：原图 + 初始中码裸模 → 第1轮；原图 + 第1轮照片 → 第2轮衣物修正；最后再拟合 69 cm 腰围 / 50 cm 大腿围的条件人体。最终拟合人体未重新送入这两轮生成。</p></div>'
    document = document.replace('<body>','<body>'+header,1)
    details = '<section class="product-results"><h2>如何判断匹配</h2><p>三维模型与生成图的关键点及轮廓用于检查内部一致性。衣物轮廓含松量，无法证明裸身胸腰臀；原始电商图是弯臂近景，不能用标准正面图的低误差代替原图验证。</p><p><strong>商品审查与几何检查分开：</strong>第二轮七分袖、浅船领、小中央玫瑰与 pointelle 基本视觉特征获条件接受；肩头叠片、玫瑰尺寸与孔眼重复单元仍有细节偏差。未见背面、裤脚与人物身份没有独立真值，六图也不是严格同步的同一姿态。</p><p><a href="provenance/independent-visual-review-v2.json">逐图独立视觉审查与局限</a> · <a href="provenance/independent-visual-review-v1.json">第一轮袖长错误审查</a></p>'
    if ready:
        final_review=read(workspace/'case/independent-visual-review-v2.json')
        if final_review.get('expectations'):
            details += '<h3>独立审查分项结果</h3><p>不将商品视觉、几何内部一致性、原图恢复混成一个通过率。Benchmark 页只统计文件执行完整性。</p><div class="table-scroll"><table class="quality-table"><thead><tr><th>检查范围</th><th>结果</th><th>证据与限制</th></tr></thead><tbody>'
            for expectation in final_review['expectations']:
                details += '<tr><th>'+html.escape(expectation['text'])+'</th><td style="color:'+('#116750' if expectation['passed'] else '#a32626')+';font-weight:700">'+('PASS' if expectation['passed'] else 'FAIL')+'</td><td class="quality-evidence">'+html.escape(expectation['evidence'])+'</td></tr>'
            details += '</tbody></table></div>'
        original_metrics=workspace/'model/original-reference/metrics.json'
        if original_metrics.exists():
            original=read(original_metrics)
            before=original.get(original.get('protocol',{}).get('previous_phase_key','previous_candidate'),{});after=original.get(original.get('protocol',{}).get('selected_phase_key','refined_head_and_arms'),{})
            if before and after:
                details += '<h3>原始商品图本身：姿态尝试（POSE_FAIL）</h3><p><strong>未找到已接受的原图匹配姿态。</strong>原图是弯臂提衣、斜头近景。这里保留同一个 170 cm 条件体形，只调整头颈、躯干和双臂；不与生成图的标准视图指标混算。当前裁图相机不变，手工标点与隐藏关节的估计均有不确定性。</p><figure class="original-comparison"><a href="original-reference/before-after.png" target="_blank" rel="noopener"><img src="original-reference/before-after.png" alt="原始电商商品图上的上一姿态与本轮头颈双臂优化叠加"></a><figcaption>上一候选 → 最新失败候选；原图本身的 OpenCV 叠加，不代表已匹配。完整图也在上方叠加画廊可放大。</figcaption></figure><div class="table-scroll"><table><thead><tr><th>原图标点 / 指标</th><th>前 → 后</th></tr></thead><tbody>'
                a={r['landmark']:r['error_px'] for r in before['manual_joint_errors_px']};b={r['landmark']:r['error_px'] for r in after['manual_joint_errors_px']}
                for landmark,label in [('wrist.L','左腕（px）'),('wrist.R','右腕（px）'),('lowerarm01.L','左肘（px）'),('lowerarm01.R','右肘（px）'),('eye.L','左眼（px）'),('eye.R','右眼（px）'),('nose_vertex201','鼻部网格点（px）'),('upperarm01.L','左肩（px）'),('upperarm01.R','右肩（px）')]:
                    details += '<tr><th>'+label+'</th><td>'+f'{a[landmark]:.2f} → {b[landmark]:.2f}'+'</td></tr>'
                details += '<tr><th>裁图衣物包络 IoU</th><td>'+f"{before['cropped_clothed_envelope']['iou']:.4f} → {after['cropped_clothed_envelope']['iou']:.4f}"+'</td></tr></tbody></table></div><p>这些是本图训练点的投影误差；肩部、脸部身份、衣物形态和手部接触还需核查真实三维投影。受约束关节可能到达搜索边界。低投影误差不能证明真实三维姿态或人体尺寸正确。</p><p><a href="../../human-studio/?model=../garment-body/product-case/original-reference/state.json">打开最新失败候选继续调节</a> · <a href="original-reference/manual-landmarks.json">人工标点与来源</a> · <a href="original-reference/metrics.json">独立原图指标</a> · <a href="original-reference/renders/front.png">真实三维彩色投影</a></p>'
                details += '<div class="pose-comparisons original-solid"><figure><a href="original-reference/renders/front.png" target="_blank" rel="noopener"><img src="original-reference/renders/front.png" alt="最新失败候选的实际三维正面投影"></a><figcaption>真实三维正面：低二维腕肘误差不等于三维动作正确。</figcaption></figure><figure><a href="original-reference/renders/side.png" target="_blank" rel="noopener"><img src="original-reference/renders/side.png" alt="最新失败候选的实际三维侧面，双手远离腹部"></a><figcaption>真实三维侧面：双手悬于腹前约 21–25 cm，未重现近身提衣。<strong>POSE_FAIL。</strong></figcaption></figure></div><p>以下是最新被拒绝的 forward-IK 诊断，未接受为 matched candidate；原图真人动作也没有因此被证明不可能。<a href="original-reference/candidate-status.json">各候选判定与停止原因</a> · <a href="original-reference/ik-depth-feasibility.json">实际骨段与深度分支证据</a>。模型标尺上臂长 29 cm 与逆运动学肩肘骨段约 26.85 cm 是不同定义。</p>'
                if after.get('actual_hand_surface_depth'):
                    details += '<div class="table-scroll"><table><thead><tr><th>实际手表面深度包络</th><th>位于躯干前方比例</th><th>前向净距最小值 cm</th></tr></thead><tbody>'
                    for hand,label in [('L','左手'),('R','右手')]:
                        row=after['actual_hand_surface_depth'][hand]
                        details += '<tr><th>'+label+'</th><td>'+f"{row['hand_surface_fraction_in_front_of_torso']:.3f}"+'</td><td>'+f"{row['hand_surface_torso_front_clearance_cm_min']:.3f}"+'</td></tr>'
                    details += '</tbody></table></div><p>使用实际蒙皮后的手表面与仅躯干三角形的前向深度包络比较；负净距表示仍有越入包络的表面；大幅正净距也不等于贴身接触，当前候选双手远离腹部。不是完整自碰撞、衣物接触或物理合身验证。<a href="original-reference/hand-depth-check.json">数值手深度诊断</a></p>'
        shape_path=workspace/'model/shape-fit/optimization.json'
        if shape_path.exists():
            shape=read(shape_path)
            if shape['selected']['dimensions']!=read(workspace/'model/final-state.json')['dimensions']:
                raise ValueError('Shape optimization does not match selected dimensions')
            details += '<h3>厘米体形调整：减少裸模越出衣物包络</h3><p>固定身高 170 cm、相机与姿态，保留中码初始模型；只在有边界约束的部位作条件调整。腰围 72 → 69 cm、大腿围 54 → 50 cm，其余目标保持。不是将宽松衣物宽度直接当作裸身围度。</p><div class="table-scroll"><table><thead><tr><th>视图</th><th>包含性损失 前 → 后</th><th>越界像素 前 → 后</th></tr></thead><tbody>'
            for view in ('front','side'):
                before=shape['initial']['containment'][view];after=shape['selected']['containment'][view]
                details += '<tr><th>'+LABELS[view]+'</th><td>'+f"{before['containment_loss']:.5f} → {after['containment_loss']:.5f}"+'</td><td>'+str(before['outside_pixels'])+' → '+str(after['outside_pixels'])+'</td></tr>'
            details += '</tbody></table></div><p>损失、越界像素、全衣物 IoU 是不同指标。更小的裸模可能提高包含性，同时降低衣物包络 IoU；不把损失下降解释成人体尺寸更准确。<a href="model/shape-fit/optimization.json">完整搜索历史与协议</a></p>'
        view_summary=workspace/'model/view-specific/summary.json'
        if view_summary.exists():
            details += '<h3>共享姿态与单图姿态诊断</h3><p>六张生成图的手臂姿势不完全同步。默认下载保留共享姿态；以下单图诊断保持同一人体尺寸与相机，分别调姿态，不作为留出泛化得分。</p><div class="pose-tabs" role="tablist" aria-label="姿态比较"><button role="tab" id="pose-mode-shared" aria-selected="true" aria-controls="pose-shared">共享姿态</button><button role="tab" id="pose-mode-specific" aria-selected="false" aria-controls="pose-specific">各视图单独姿态</button></div>'
            for mode,suffix in [('shared','shared-overlay'),('specific','view_specific-overlay')]:
                details += '<div class="pose-comparisons" role="tabpanel" id="pose-'+mode+'"'+(' hidden' if mode=='specific' else '')+'>'
                for view in ('side','back'):
                    details += '<figure><a href="view-specific/'+view+'/'+suffix+'.png" target="_blank" rel="noopener"><img src="view-specific/'+view+'/'+suffix+'.png" alt="'+LABELS[view]+('共享姿态' if mode=='shared' else '单独姿态')+'"></a><figcaption>'+LABELS[view]+' · '+('共享姿态' if mode=='shared' else '<a href="../../human-studio/?model=../garment-body/product-case/view-specific/'+view+'/state.json">打开这一姿态调节</a>')+'</figcaption></figure>'
                details += '</div>'
        details += '<div class="table-scroll"><table><thead><tr><th>视图</th><th>轮廓 IoU 前 → 后</th><th>平均轮廓误差 px 前 → 后</th><th>95% 轮廓误差 px 前 → 后</th></tr></thead><tbody>'
        for view in ('front','side','back'):
            before=metrics[view]['initial']['full_clothed_envelope_comparison'];after=metrics[view]['final']['full_clothed_envelope_comparison']
            details += '<tr><th>'+LABELS[view]+('（未训练共享姿态）' if view=='back' else '')+'</th>'+''.join('<td>'+f'{before[k]:.3f} → {after[k]:.3f}'+'</td>' for k in ('iou','symmetric_contour_mean_px','symmetric_contour_p95_px'))+'</tr>'
        details += '</tbody></table></div><p>相机先独立校准再冻结；上表比较同一相机下的优化。全身衣物包络与裸模轮廓不应完全重合；误差上升的项目如实保留。</p><h3>第2轮选中人体尺寸（cm）</h3><p>以中码先验初始化，经真实网格重新量测；衣物包络约束下的调整是条件估计。它们是可调参数，不是从照片识别出的真人尺寸。依据列保留当前测量文件的分类。</p><div class="table-scroll"><table><thead><tr><th>部位</th><th>原始中码先验 cm</th><th>当前目标 cm</th><th>独立网格量测 cm</th><th>依据</th></tr></thead><tbody>'
        measurements=[]
        with (workspace/'model/neutral-measurements.csv').open() as stream:
            for row in csv.DictReader(stream):
                basis=row.get('basis','unknown')
                basis_label={'prior':'先验 / 网格参数','clothed_envelope_estimate':'衣物包络条件估计','mesh_parameter':'网格参数'}.get(basis,basis)
                measurements.append(dict(key=row['key'],label=MEASURES.get(row['key'],row['key']),initial_prior_cm=INITIAL_PRIOR.get(row['key']),target_cm=float(row['target_cm']),mesh_cm=float(row['independently_measured_cm']),basis=basis,real_person_accuracy=None,unit='cm'))
                details += '<tr><th>'+MEASURES.get(row['key'],html.escape(row['key']))+'</th><td>'+str(INITIAL_PRIOR.get(row['key'],'—'))+'</td><td>'+html.escape(row['target_cm'])+'</td><td>'+f"{float(row['independently_measured_cm']):.4f}"+'</td><td>'+html.escape(basis_label)+'</td></tr>'
        for key,label in UNAVAILABLE.items():
            measurements.append(dict(key=key,label=label,initial_prior_cm=None,target_cm=None,mesh_cm=None,basis='unavailable',real_person_accuracy=None,unit='degree' if key=='shoulderSlope' else 'cm'))
        write(site/'measurements.json',dict(scope='Model parameters and conditional estimates, not real-person measurements',official_model=dict(height_cm=171,size='S US4–6'),measurements=measurements))
        with (site/'measurements.csv').open('w') as stream:
            writer=csv.DictWriter(stream,fieldnames=list(measurements[0]));writer.writeheader()
            writer.writerows({key:('null' if value is None else value) for key,value in row.items()} for row in measurements)
        copied['measurements.json']=digest(site/'measurements.json');copied['measurements.csv']=digest(site/'measurements.csv')
        copied.update(reproduction_archive(workspace,site))
        details += '</tbody></table></div><p>未能可靠获得：'+ '、'.join(UNAVAILABLE.values())+'。这些项在完整 JSON/CSV 中明确为 null、依据 unavailable；没有补造精确数值。肩斜的单位为度，其余未知长度/围度项为 cm。</p><p class="product-downloads"><a download href="measurements.json">完整尺寸与未知项 JSON</a> · <a download href="measurements.csv">完整尺寸与未知项 CSV</a> · '+ ' · '.join('<a download href="model/'+path+'">'+label+'</a>' for path,label in [('final-state.json','可调状态 JSON'),('final-posed.obj','厘米 OBJ'),('final-posed.glb','带骨骼 GLB（米）'),('neutral-measurements.csv','12维网格原始量测 CSV'),('fit/metrics.json','拟合原始指标'),('fit/input-hashes.json','本轮输入摘要')])+'</p><p><a download href="reproduce.zip">下载实际案例复核包（两轮图、网格、原始深度、分割与脚本）</a> · <a href="REPRODUCE.md">解压与重放说明</a>。先 clone 仓库，再从仓库根目录解压，保留包内 work/ 相对路径。</p>'
    else:
        details += '<p>本轮模型尚未通过输入摘要核验，当前页面不展示旧轮次拟合数字。</p>'
    details += '<p><a href="benchmark.json">断言与未知资源值</a> · <a href="reference/source-verification.json">官网图像来源核验</a>。下方保留官方 Anthropic 输出、断言、Benchmark 与反馈下载；输入反馈只保存在当前浏览器。</p></section>'
    extra = '<style>.product-nav{padding:12px 24px;background:#e5ede5;font:14px/1.5 system-ui}.product-nav a,.product-intro a,.product-results a{color:#116750}.product-intro{padding:20px 24px;background:#fff;font:15px/1.65 system-ui}.product-intro h2{font-size:25px;margin:0}.product-intro p{max-width:1000px;margin:8px 0}.product-primary{display:inline-block;background:#145d47;color:#fff!important;border-radius:6px;padding:9px 14px;text-decoration:none}.product-results{font:14px/1.6 system-ui;background:#fff;border:1px solid #dedfd6;border-radius:10px;padding:20px;margin:0 0 20px}.product-results h2{margin-top:0;font-size:23px}.product-results h3{margin-top:22px}.table-scroll{overflow-x:auto}.product-results table{width:100%;border-collapse:collapse;white-space:nowrap}.product-results th,.product-results td{text-align:left;padding:9px;border-bottom:1px solid #e0e4da}.product-results th{font-weight:600}.quality-table{white-space:normal!important;min-width:680px}.quality-table th{min-width:170px}.quality-evidence{white-space:normal;min-width:300px}.product-downloads{line-height:2}.quick-review .evidence-image img{height:280px}.pose-tabs{display:flex;gap:8px;margin:12px 0}.pose-tabs button{font:inherit;padding:8px 14px;border:1px solid #aab8ae;border-radius:6px;cursor:pointer;background:#fff;color:#202b29}.pose-tabs button[aria-selected="true"]{background:#145d47;color:white}.pose-comparisons{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}.pose-comparisons[hidden]{display:none}.pose-comparisons figure{margin:0;text-align:center}.pose-comparisons img{width:100%;height:440px;object-fit:contain;background:#f6f7f2}.pose-comparisons figcaption{padding:7px}@media(max-width:580px){.product-intro{padding:16px}.product-intro h2{font-size:22px}.product-results{padding:14px}.product-nav{padding:10px 16px}.pose-comparisons{grid-template-columns:1fr}}</style>'
    extra += '<style>.original-comparison{margin:16px 0}.original-comparison img{display:block;width:100%;max-height:650px;object-fit:contain;background:#f6f7f2}.original-comparison figcaption{font-size:13px;padding:7px 0}</style>'
    document = document.replace('</head>',extra+'</head>',1)
    # Insert the detailed metric/measurement panel after the actual quick gallery.
    integration = r'''
const galleryShowRun=showRun;
function syncProductResults(index){
  document.querySelector('.product-results').hidden=!VISUAL_EVIDENCE[EMBEDDED_DATA.runs[index].id].title.includes('第2轮');
}
showRun=function(index){galleryShowRun(index);syncProductResults(index);};
syncProductResults(currentIndex);
const poseTabs=[...document.querySelectorAll('.pose-tabs [role=tab]')];
function selectPoseTab(tab){
  poseTabs.forEach(other=>{other.setAttribute('aria-selected',String(other===tab));other.tabIndex=other===tab?0:-1;});
  document.querySelectorAll('.pose-comparisons[role=tabpanel]').forEach(panel=>panel.hidden=panel.id!==tab.getAttribute('aria-controls'));
}
poseTabs.forEach((tab,index)=>{
  tab.tabIndex=index===0?0:-1;
  tab.addEventListener('click',()=>selectPoseTab(tab));
  tab.addEventListener('keydown',event=>{
    if(!['ArrowLeft','ArrowRight','Home','End'].includes(event.key))return;
    event.preventDefault();event.stopPropagation();
    const next=event.key==='Home'?0:event.key==='End'?poseTabs.length-1:(index+(event.key==='ArrowRight'?1:-1)+poseTabs.length)%poseTabs.length;
    selectPoseTab(poseTabs[next]);poseTabs[next].focus();
  });
});
'''
    document = document.replace('</body>','<script>document.querySelector("#quick-review").insertAdjacentHTML("afterend",'+json.dumps(details).replace('<',r'\u003c')+');'+integration+'</script></body>',1)
    (site/'eval.html').write_text(document)
    write(site/'gallery.json', gallery)
    current_files = set(copied) | {'eval.html', 'gallery.json', 'benchmark.json'}
    for name in previous_files - current_files:
        target = (site/name).resolve()
        if site in target.parents and target.is_file():
            target.unlink()
    viewer_sources=['upstream/eval-viewer/generate_review.py','upstream/eval-viewer/viewer.html','build_functional_review.py','visual_gallery.py']
    manifest = dict(scope='Actual product generation revisions and anatomical registration. No real-person measurement accuracy or cloth-physics claim.',model_included=ready,independent_model_check=independent_model_check,upstream=upstream,viewer_source_sha256={name:digest(Path(__file__).resolve().parent/name) for name in viewer_sources},source=SOURCE,model_prior=dict(height_cm=170,bust_cm=90,waist_cm=72,hips_cm=96,shoulders_cm=37),selected_model_dimensions=read(workspace/'model/final-state.json')['dimensions'] if ready else None,official_model=dict(height_cm=171,size='S US4–6'),unknown=dict(native_claude_trigger='BLOCKED',physical_fit='NOT_RUN',tokens=None,time_seconds=None),files={str(p.relative_to(site)):digest(p) for p in sorted(site.rglob('*')) if p.is_file() and p.name!='manifest.json'})
    write(site/'manifest.json', manifest)
    print(json.dumps(dict(site=str(site),images=sum(len(s['images']) for d in gallery.values() for s in d['stages']),model_included=ready,files=len(manifest['files'])),ensure_ascii=False))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace',type=Path,default=Path('work/product-red-pointelle-20261117'))
    parser.add_argument('--site',type=Path,default=Path('web/garment-body/product-case'))
    parser.add_argument('--include-model',action='store_true',help='Require current v2 model hashes, never display stale v1 fitting evidence')
    args=parser.parse_args()
    build(args.workspace.resolve(),args.site.resolve(),args.include_model)
