#!/usr/bin/env python3
"""Publish canonical skill resources and the upstream-built package without forks."""
import hashlib
import html
import json
from pathlib import Path
import re
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT/'.agents/skills/garment-body-six-view'
OUTPUT = ROOT/'web/garment-body/skill'


def render(markdown):
    """Small escaped Markdown subset for the maintained reference, no raw HTML."""
    def inline(value):
        value = html.escape(value)
        value = re.sub(r'\[([^\]]+)\]\((https://[^ )]+)\)', r'<a href="\2">\1</a>', value)
        value = re.sub(r'`([^`\n]+)`', r'<code>\1</code>', value)
        return re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', value)
    result, paragraph, code, table = [], [], False, False
    def flush():
        if paragraph:
            result.append('<p>'+inline(' '.join(paragraph))+'</p>'); paragraph.clear()
    for line in markdown.splitlines():
        if line.startswith('```'):
            flush()
            if table: result.append('</tbody></table></div>'); table = False
            result.append('</code></pre>' if code else '<pre><code>'); code = not code; continue
        if code:
            result.append(html.escape(line)); continue
        if line.startswith('|'):
            flush()
            if re.fullmatch(r'[| :\-]+', line): continue
            if not table: result.append('<div class="table"><table><tbody>'); table = True
            result.append('<tr>' + ''.join('<td>'+inline(c.strip())+'</td>' for c in line.strip('|').split('|')) + '</tr>'); continue
        if table: result.append('</tbody></table></div>'); table = False
        heading = re.match(r'^(#{1,3}) (.*)', line)
        if heading:
            flush(); level = len(heading[1]); result.append(f'<h{level}>{inline(heading[2])}</h{level}>')
        elif not line.strip(): flush()
        else: paragraph.append(line)
    flush()
    if code or table: raise ValueError('Unclosed Markdown block')
    return '\n'.join(result)


def build():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    # Navigation only: keep historical embedded runs, grades and feedback keys intact.
    review = ROOT/'web/garment-body/eval.html'
    document = review.read_text()
    if 'id="current-workflow-link"' not in document:
        document = document.replace('<head>', '<head>\n  <link rel="icon" href="../assets/favicon.svg" type="image/svg+xml">', 1)
        document = document.replace('<body>', '<body>\n<nav id="current-workflow-link" style="padding:12px 24px;background:#e5ede5">Historical synthetic control review · <a href="skill/">Current anatomical model skill & workflow</a> · <a href="../human-studio/">Human Studio</a></nav>', 1)
        review.write_text(document)
    package = ROOT/'skill-packages/garment-body-six-view.skill'
    with zipfile.ZipFile(package) as archive:
        for name in archive.namelist():
            source = SKILL.parent/name
            if not source.is_file() or source.read_bytes() != archive.read(name):
                raise ValueError('Package is stale: ' + name)
        required = ['SKILL.md','references/human-studio.md','scripts/inspect_human_state.py']
        for name in required: assert 'garment-body-six-view/'+name in archive.namelist()
        entries = {name:hashlib.sha256(archive.read(name)).hexdigest() for name in archive.namelist()}
    for relative in ['SKILL.md','INSTALL.md'] + [str(p.relative_to(SKILL)) for p in sorted((SKILL/'references').glob('*.md'))]:
        target = OUTPUT/relative; target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(SKILL/relative, target)
    shutil.copyfile(package, OUTPUT/package.name)
    body = render((SKILL/'references/human-studio.md').read_text())
    page = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Body & six-view skill — Pattern Agent</title><link rel="icon" href="../../assets/favicon.svg" type="image/svg+xml"><style>
*{box-sizing:border-box}body{margin:0;background:#f5f4ef;color:#202a28;font:17px/1.65 system-ui,sans-serif}main,nav{max-width:960px;margin:auto;padding:24px}nav{display:flex;gap:20px;flex-wrap:wrap}a{color:#116750}h1{font-size:clamp(28px,5vw,44px);line-height:1.15}h2{margin-top:48px}pre{background:#202a28;color:#f5f4ef;padding:18px;overflow:auto;border-radius:8px}code{font-size:.9em}p{overflow-wrap:anywhere}table{border-collapse:collapse;width:100%}td{padding:10px;border-bottom:1px solid #cfd6d0}.table{overflow:auto}.notice{background:#e5ede5;border-radius:12px;padding:22px}.download{display:inline-block;background:#116750;color:white;padding:10px 18px;border-radius:8px;margin:8px 12px 8px 0}footer{border-top:1px solid #ccc;margin-top:40px;padding-top:24px}
</style><nav><a href="../../">Pattern Agent</a><a href="../../human-studio/">Open Human Studio</a><a href="../eval.html">Historical evaluations</a></nav><main>
<h1>Reference photo → six views → verified body parameters</h1>
<p>商品模特图 → 六张独立图像 → 可调节人体 → 三维快照与 OpenCV 叠加 → 带证据的人体参数。</p>
<div class="notice"><strong>Current workflow</strong><p>Use the anatomical Human Studio model: 12 dimensions in centimetres, 163 bones and pose controls in degrees. Keep requested sizes, measured mesh values and image-based estimates separate.</p>
<a class="download" href="garment-body-six-view.skill" download>Download .skill</a><a href="SKILL.md">Canonical instructions</a> · <a href="INSTALL.md">Installation</a></div>
<p>人体尺寸主要输出由最终裸模网格实际复量；输入先验、控制目标和模型实测值分列。<a href="references/model-measurements.md">模型实测导出合同与命令</a></p><p><a href="../full-imagegen-evals/eval.html">端到端实际执行：本轮 Image Gen 六图 → 可调人体拟合 → OpenCV → 模型实测（官方格式）</a></p><p><a href="../model-size-evals/eval.html">更新后技能：六次独立子代理尺寸导出功能评测（官方格式）</a></p><p><a href="../commerce-evals/eval.html">新增电商原图：两轮配对功能评测与留出案例（官方格式）</a></p><p><a href="../single-state-evals/eval.html">官方 Eval Review：原图 / 引导 / 模型 / 叠加</a> · <a href="../pose-guided-fit/details.html">可选交互详情</a></p><p>区域视觉验收、三维动作审查与功能测试分别报告；历史功能满分不能证明照片匹配。</p><p><a href="../product-case/eval.html">历史真实商品案例：输入 → 六张生成图 → 可调人体 → 叠加核验</a></p><p><a href="../anatomical-evals/eval.html">Anatomical component evaluations & hill climb</a> · <a href="../anatomical-evals/iteration-3.html">Untuned camera transfer check</a></p><p>Deliver six separate images: front, side, back, close-up, pose annotation and relative depth. Record the original item photo, model state and actual generation/rendering provenance. The editor supplies the adjustable mannequin; generation and fitting require their own tools.</p>
''' + body + '''<footer><a href="references/human-studio.md">Workflow source</a> · <a href="references/tools-and-evidence.md">Tools & evidence</a> · <a href="references/test-status.md">Evaluation limits</a> · <a href="references/evaluation-workflow.md">反馈与评测迭代流程</a> · <a href="manifest.json">Download hashes</a><p>Earlier loft-model scores remain historical. The real product case has separate scoped visual and geometry evidence; it does not establish general generation quality, real-person measurement accuracy or a new native Claude trigger score.</p></footer></main></html>'''
    (OUTPUT/'index.html').write_text(page)
    files = {str(p.relative_to(OUTPUT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(OUTPUT.rglob('*')) if p.is_file() and p.name != 'manifest.json'}
    (OUTPUT/'manifest.json').write_text(json.dumps(dict(skill='garment-body-six-view', files=files, package_entries=entries),indent=2)+'\n')
    print(json.dumps(dict(output=str(OUTPUT.relative_to(ROOT)), files=len(files), package_entries=len(entries))))


if __name__ == '__main__': build()
