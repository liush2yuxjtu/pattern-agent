#!/usr/bin/env python3
"""Official iterative viewer for current skill execution and frozen historical output.

The previous run is reused context, never a newly executed comparison arm.
Uses the existing strict full-workflow builder and the pinned Anthropic reviewer
with its previous-workspace path. All gallery additions remain in native Output.
"""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from PIL import Image
import build_full_imagegen_review as full
from build_functional_review import build as official_review

ROOT = Path(__file__).resolve().parents[2]
OLD = ROOT / 'work/full-imagegen-skill-evals-20261118'
DEFAULT = ROOT / 'work/full-imagegen-hillclimb-20261118'


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def freeze_previous(workspace):
    freeze = full.read(workspace / 'baseline-freeze.json')
    old_run = OLD / 'iteration-1/eval-1-original-product/with_skill/run-1'
    actual = {str(p.relative_to(old_run / 'outputs')): full.sha(p) for p in full.files(old_run / 'outputs')}
    assert actual == freeze['baseline']['original_outputs'], 'Historical output changed'
    assert full.sha(old_run / 'grading.json') == freeze['baseline']['grading_sha256'], 'Historical grade changed'
    projection = workspace / 'official-previous-inputs'
    if projection.exists():
        shutil.rmtree(projection)
    previous = projection / 'eval-1-original-product/with_skill/run-1'
    (previous / 'outputs').mkdir(parents=True)
    shutil.copyfile(old_run / 'eval_metadata.json', previous / 'eval_metadata.json')
    shutil.copyfile(old_run / 'grading.json', previous / 'grading.json')
    (previous / 'outputs/00-HISTORICAL-REUSED.md').write_text(
        '# Previous Output · REUSED HISTORY\n\n'
        'This is the frozen previous real end-to-end execution, not a new paired baseline run. '
        'Its independent grade remains11/13, overallFAIL: generated views do not establish '
        'the same exact body/pose; waist/hip and cup-like/far-forward hands do not match '
        'the source action. Original inputs, model, images and grades are unchanged. '
        'The current candidate is independently rerun; differences cannot establish general '
        'skill improvement, reliability, speed or native routing accuracy.\n\n'
        'Full prior official review and six original ImageGen files: '
        'https://liush2yuxjtu.github.io/pattern-agent/garment-body/full-imagegen-evals/eval.html\n')
    # These are original historical bytes, not new renderings or generation.
    for name, rel in [('01-original-photo.jpg', 'reference/original-product.jpg'),
                      ('02-historical-model.png', 'model-fit/final/photo-render.png'),
                      ('03-historical-final-overlay.png', 'model-fit/comparison/final-frozen-camera-overlay.png')]:
        shutil.copyfile(old_run / 'outputs' / rel, previous / 'outputs' / name)
    return projection


def generation_attempts(output, site, manifest):
    import html
    selection_path = next((output / name for name in ['generation-selection.json', 'selection.json'] if (output / name).is_file()), None)
    if selection_path is None:
        return None, '', []
    selection = full.read(selection_path)
    chosen = {row['view']: row['relative_path'] for row in manifest['generation']}
    for view, row in selection.get('selected', {}).items():
        path = row if isinstance(row, str) else row['path']
        assert chosen.get(view) == path, 'Selected generation receipt disagrees with selection manifest: ' + view
    rows, events = [], []
    for item in selection.get('attempts', []):
        if not item.get('path'):
            assert item.get('status') in {'BLOCKED_NO_OUTPUT', 'FAILED_NO_OUTPUT'}, 'Missing attempt file needs explicit no-output status'
            receipt = Path(item['receipt'])
            assert not receipt.is_absolute() and (output / receipt).resolve().is_relative_to(output.resolve()), 'No-output receipt escapes executor output'
            assert (output / receipt).is_file(), 'Actual no-output receipt missing'
            events.append(dict(view=item['view'], status=item['status'], reason=item.get('reason', ''), receipt='artifacts/' + str(receipt), sha256=full.sha(output / receipt)))
            continue
        relative = Path(item['path'])
        source = output / relative
        assert not relative.is_absolute() and source.resolve().is_relative_to(output.resolve()), 'Attempt path escapes executor output'
        assert source.is_file(), 'Retained generation attempt missing'
        published = site / 'artifacts' / relative
        assert published.is_file() and full.sha(source) == full.sha(published), 'Published attempt differs from executor bytes'
        selected = chosen.get(item['view']) == str(relative)
        status = item.get('status') or ('SELECTED' if selected else 'REJECTED' if item.get('accepted') is False else 'RETAINED')
        reason = item.get('reason') or item.get('rejection_reason') or json.dumps(item.get('metrics', {}), ensure_ascii=False)
        rows.append(dict(view=item['view'], src='artifacts/' + str(relative), sha256=full.sha(source), selected=selected, status=status, reason=reason))
    text = '<details class="retake-history" open><summary>实际 Image Gen 失败与修正轮次（原始图不覆盖）</summary><p>仅选定的六张进入主要验收；以下保留每次真实生成及其选择理由，重试不冒充新的配对技能基线。</p><div class="retake-grid">'
    for i, row in enumerate(rows):
        label = row['view'] + ' · ' + ('SELECTED · ' if row['selected'] else '') + row['status']
        text += '<section><strong>' + html.escape(label) + '</strong><button type="button" data-retake-image="' + str(i) + '"><img src="' + html.escape(row['src']) + '" alt="' + html.escape(label) + '"></button><p>' + html.escape(str(row['reason'])) + '</p><a download href="' + html.escape(row['src']) + '">原生文件</a></section>'
    text += '</div>'
    if events:
        text += '<h4>实际无图返回事件（不计入原生图数量）</h4><ul>'
        for event in events:
            text += '<li>' + html.escape(event['view'] + ' · ' + event['status'] + ' · ' + event['reason']) + ' <a href="' + html.escape(event['receipt']) + '">真实工具receipt</a> SHA256 ' + event['sha256'] + '</li>'
        text += '</ul>'
    text += '</details>'
    return dict(path=str(selection_path.relative_to(output)), sha256=full.sha(selection_path), selected=chosen, attempts=rows, no_output_events=events), text, rows


def development_attempts(workspace, site, offset=0):
    import html
    path = workspace / 'development-history.json'
    if not path.exists():
        return None, '', []
    data = full.read(path)
    text = '<details class="development-history"><summary>开发失败轨迹与独立诊断（非 fresh 技能执行，不计 Benchmark）</summary><p>' + html.escape(data['scope']) + '</p><div class="retake-grid">'
    images = []
    for number, item in enumerate(data['examples']):
        published = {}
        for relative, fingerprint in item['sha256'].items():
            source = workspace / relative
            assert source.resolve().is_relative_to(workspace.resolve()) and full.sha(source) == fingerprint, 'Development history source changed'
            target = site / 'source/development' / item['id'] / Path(relative).name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            published[relative] = str(target.relative_to(site))
        src = published[item['image']]
        images.append(dict(view=item['title'], status='DEVELOPMENT FAIL · NOT_FRESH', src=src, reason=item['reason'], sha256=item['sha256'][item['image']]))
        text += '<section><strong>' + html.escape(item['title']) + '</strong><button type="button" data-retake-image="' + str(offset + number) + '"><img src="' + html.escape(src) + '" alt="' + html.escape(item['title']) + '"></button><p>' + html.escape(item['reason']) + '</p>'
        for relative in item['evidence']:
            text += '<p><a download href="' + html.escape(published[relative]) + '">' + html.escape(Path(relative).name) + '</a> SHA256 ' + item['sha256'][relative] + '</p>'
        text += '</section>'
    text += '</div></details>'
    shutil.copyfile(path, site / 'source/development-history.json')
    return dict(scope=data['scope'], source='source/development-history.json', sha256=full.sha(path)), text, images


def visible_projection_evidence(workspace, site, manifest, offset=0):
    import html
    selected = {row['sha256']: row['view'] for row in manifest['generation']}
    records, images = [], []
    text = '<section class="visible-projection-gallery"><h3>生成图 vs 同一最终人体投影：独立可见一致性核对</h3><p>下列图仅来自与当前选定原生图 SHA 完全匹配的独立检查。固定画幅均匀缩放、未重新配准或warp；衣物包络与人工可见锚点分列，不能据此证明隐藏精确三维或真人尺寸。</p><div class="retake-grid">'
    for mask_path in sorted((workspace / 'grader').glob('generated-*/mask-audit.json')):
        mask = full.read(mask_path)
        view = selected.get(mask.get('image_sha256'))
        if not view:
            continue
        overlay = mask_path.with_name('fixed-guide-overlay.png')
        anchor_path = mask_path.with_name('anchor-audit.json')
        if not overlay.is_file() or not anchor_path.is_file():
            continue
        assert mask.get('registration_refit') is False, 'Visible consistency evidence cannot refit/warp generated images'
        anchor = full.read(anchor_path)
        metrics = anchor.get('views', {}).get(view, {})
        published = {}
        for source in [overlay, mask_path, anchor_path, mask_path.with_name('anchors.json')]:
            if source.exists():
                target = site / 'source/visible-projection' / mask_path.parent.name / source.name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
                published[source.name] = dict(href=str(target.relative_to(site)), sha256=full.sha(source))
        direction = [r.get('angle_deg') for r in metrics.get('limb_angles', [])]
        reason = '包络外溢=' + str(mask['body_outside_fraction']) + '；轮廓P95=' + str(mask['body_contour_p95_px']) + 'px；锚点数=' + str(metrics.get('observed_anchors')) + '，mean/height=' + str(metrics.get('mean_error_fraction_height')) + '，max/height=' + str(metrics.get('max_error_fraction_height')) + '；肢体方向差(deg)=' + str(direction) + '。数值来自独立实际文件，最终验收另看Formal Grades。'
        images.append(dict(view=view + ' · 生成图/真实投影叠加', src=published[overlay.name]['href'], sha256=full.sha(overlay), status='INDEPENDENT_VISIBLE_AUDIT', reason=reason))
        text += '<section><strong>' + html.escape(view) + ' · 当前 selected 原生图</strong><button type="button" data-retake-image="' + str(offset + len(images) - 1) + '"><img src="' + html.escape(published[overlay.name]['href']) + '" alt="' + html.escape(view) + ' fixed guide overlay"></button><p>' + html.escape(reason) + '</p>'
        for name, entry in published.items():
            if name.endswith('.json'):
                text += '<p><a href="' + html.escape(entry['href']) + '">' + html.escape(name) + '</a> SHA256 ' + entry['sha256'] + '</p>'
        text += '</section>'
        records.append(dict(view=view, selected_image_sha256=mask['image_sha256'], guide_sha256=mask.get('guide_sha256'), uniform_scale=mask.get('fixed_uniform_scale'), registration_refit=False, mask_metrics=mask, anchor_metrics=metrics, files=published))
    text += '</div></section>'
    return records, text if records else '', images


RETAKE_SCRIPT = r"""(() => {
 const entries=RETAKE_HISTORY;if(!entries.length)return;
 const dialog=document.createElement('dialog');dialog.className='evidence-lightbox';dialog.setAttribute('aria-label','Iteration evidence viewer');
 dialog.innerHTML='<div class="lightbox-head"><strong id="retake-title"></strong><button id="retake-close">Close ×</button></div><img id="retake-image" class="lightbox-image" alt=""><p id="retake-reason"></p><div class="lightbox-controls"><button id="retake-prev">← Previous attempt</button><span id="retake-position"></span><button id="retake-next">Next attempt →</button><a id="retake-original" target="_blank" rel="noopener">Open original</a></div>';document.body.append(dialog);
 let position=0,opener;const q=s=>dialog.querySelector(s);
 function paint(){const x=entries[position];q('#retake-title').textContent=x.view+' · '+(x.selected?'SELECTED · ':'')+x.status;q('#retake-image').src=x.src;q('#retake-image').alt=x.view+' '+x.status;q('#retake-reason').textContent=x.reason;q('#retake-position').textContent=(position+1)+' / '+entries.length;q('#retake-original').href=x.src;q('#retake-prev').disabled=position===0;q('#retake-next').disabled=position===entries.length-1;}
 function close(){dialog.close();opener?.focus();}q('#retake-close').onclick=close;q('#retake-prev').onclick=()=>{if(position){position--;paint();}};q('#retake-next').onclick=()=>{if(position<entries.length-1){position++;paint();}};
 document.addEventListener('keydown',e=>{if(dialog.open&&['ArrowLeft','ArrowRight','Escape'].includes(e.key)){e.preventDefault();e.stopImmediatePropagation();if(e.key==='Escape')close();else q(e.key==='ArrowLeft'?'#retake-prev':'#retake-next').click();}},true);
 const original=renderOutputs;renderOutputs=function(run){original(run);for(const button of document.querySelectorAll('#outputs-body [data-retake-image]'))button.onclick=()=>{opener=button;position=Number(button.dataset.retakeImage);paint();dialog.showModal();};};showRun(0);
})();"""




def selected_six_archive(output, site, generation, acceptance):
    """Package selected native bytes under canonical names, without image edits."""
    if len(generation) != 6:
        return None
    rows = {row['view']: row for row in generation}
    assert set(rows) == set(full.VIEWS), 'Selected archive needs exactly six declared views'
    selection = dict(schema='selected-six-native-archive-v1', scope='Review-derived delivery package; no collage, crop, resampling, image rewrite or new generation. Failed attempts stay in complete run/history, not this package.', overall_acceptance=acceptance, images={})
    target = site / 'source/selected-six.zip'
    with full.zipfile.ZipFile(target, 'w', full.zipfile.ZIP_DEFLATED) as archive:
        for view in full.VIEWS:
            row = rows[view]
            source = output / row['relative_path']
            assert full.sha(source) == row['sha256'], 'Selected source changed during packaging'
            info = full.zipfile.ZipInfo(view + '.png', (1980, 1, 1, 0, 0, 0)); info.compress_type = full.zipfile.ZIP_DEFLATED
            archive.writestr(info, source.read_bytes())
            selection['images'][view] = dict(archive_file=view + '.png', source_output_path=row['relative_path'], sha256=row['sha256'], native_pixels=[row['width'], row['height']], original_tool_path=row['receipt'].get('original_tool_path'))
        for name, data in [('source-selection.json', json.dumps(selection, ensure_ascii=False, indent=2) + '\n'), ('README.md', '# Selected six native images\n\nThis is a review-derived ZIP of byte-identical selected originals, named front/side/back/closeup/pose/depth.png for convenient delivery. Source paths, native pixels and SHA are in source-selection.json. It is not a collage, crop, upscale or new image generation. Failed/blocked attempts remain in the separate complete-run and review history. Pose/depth are illustrative; no exact latent3D or real-person size accuracy claim.\n')]:
            info = full.zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0)); info.compress_type = full.zipfile.ZIP_DEFLATED
            archive.writestr(info, data.encode())
    with full.zipfile.ZipFile(target) as archive:
        assert archive.testzip() is None
        for view, row in rows.items():
            assert hashlib.sha256(archive.read(view + '.png')).hexdigest() == row['sha256'], 'Packaged native bytes differ'
    return dict(href='source/selected-six.zip', sha256=full.sha(target), bytes=target.stat().st_size, derived_packaging_only=True, source_selection=selection, entries_crc_sha_verified=True)



def replace_presentation_references(value, replacements):
    if isinstance(value, dict):
        return {key: replace_presentation_references(item, replacements) for key, item in value.items()}
    if isinstance(value, list):
        return [replace_presentation_references(item, replacements) for item in value]
    if isinstance(value, str):
        for old, new in replacements.items():
            value = value.replace(old, new)
    return value


def deduplicate_derived_inputs(site, document, manifest):
    """Remove only byte-identical review input copies, preserving source PNGs."""
    candidates = [p for p in full.files(site) if not str(p.relative_to(site)).startswith('inputs/generation-reference-')]
    by_hash = {}
    for path in candidates:
        by_hash.setdefault(full.sha(path), []).append(path)
    replacements, aliases = {}, []
    for source in sorted((site / 'inputs').glob('generation-reference-*')):
        same = by_hash.get(full.sha(source), [])
        if not same:
            continue
        same.sort(key=lambda path: (not str(path.relative_to(site)).startswith('artifacts/'), len(str(path.relative_to(site)))))
        target = same[0]
        assert source.read_bytes() == target.read_bytes(), 'Review input alias requires exact source bytes'
        relative, canonical = str(source.relative_to(site)), str(target.relative_to(site))
        replacements[relative] = canonical
        aliases.append(dict(removed_duplicate_path=relative, canonical_original_href=canonical, canonical_href=canonical, sha256=full.sha(source), bytes=source.stat().st_size))
        source.unlink()
    for old, new in replacements.items():
        document = document.replace(old, new)
    return document, replace_presentation_references(manifest, replacements), aliases


def externalize_rejected_closeups(workspace, site, document, manifest):
    """Only the four authorized rejected closeup presentation copies move."""
    allowed = ['artifacts/images/closeup.png', 'artifacts/images/attempt-2/closeup.png', 'artifacts/images/attempt-4/closeup.png', 'artifacts/images/attempt-5/closeup.png']
    selected = {'artifacts/' + row['relative_path'] for row in manifest['generation']}
    records, replacements = [], {}
    for relative in allowed:
        assert relative not in selected, 'Never move a primary selected image out of Pages'
        source = site / relative
        assert source.is_file(), 'Authorized rejected closeup presentation copy missing: ' + relative
        fingerprint, size = full.sha(source), source.stat().st_size
        with full.Image.open(source) as native_image:
            pixels = list(native_image.size)
            native_image.verify()
        target = ROOT / 'eval-artifacts' / workspace.name / (fingerprint[:16] + '-rejected-' + relative.replace('artifacts/images/', '').replace('/', '-'))
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            assert full.sha(target) == fingerprint and target.stat().st_size == size, 'Content-addressed image collision; never overwrite'
        else:
            temporary = target.with_name(target.name + '.tmp-' + str(os.getpid()))
            shutil.copyfile(source, temporary)
            assert full.sha(temporary) == fingerprint, 'Rejected image copy changed bytes'
            temporary.replace(target)
        repo_path = str(target.relative_to(ROOT)); url = 'https://raw.githubusercontent.com/liush2yuxjtu/pattern-agent/main/' + repo_path
        records.append(dict(original_logical_path=relative, sha256=fingerprint, bytes=size, native_pixels=pixels, repo_path=repo_path, url=url, role='Rejected closeup history only; original native bytes, not selected output'))
        replacements[relative] = url
        source.unlink()
    for old, new in replacements.items():
        document = document.replace(old, new)
    manifest = replace_presentation_references(manifest, replacements)
    manifest['external_images'] = records
    return document, manifest, replacements


def externalize_archives(workspace, site, document, manifest):
    """Move only this new generated site's ZIP copies to immutable repo artifacts."""
    namespace = ROOT / 'eval-artifacts' / workspace.name
    records = []
    for source in sorted((site / 'source').rglob('*.zip')):
        relative = str(source.relative_to(site))
        fingerprint = full.sha(source)
        size = source.stat().st_size
        target = namespace / (fingerprint[:16] + '-' + source.name)
        target.parent.mkdir(parents=True, exist_ok=True)
        with full.zipfile.ZipFile(source) as archive:
            assert archive.testzip() is None, 'New reproduction archive CRC failed: ' + relative
            entries = len(archive.namelist())
        if target.exists():
            assert full.sha(target) == fingerprint and target.stat().st_size == size, 'Content-addressed archive collision; never overwrite'
        else:
            temporary = target.with_name(target.name + '.tmp-' + str(os.getpid()))
            shutil.copyfile(source, temporary)
            assert full.sha(temporary) == fingerprint and temporary.stat().st_size == size, 'Archive copy changed bytes'
            temporary.replace(target)
        repo_path = str(target.relative_to(ROOT))
        url = 'https://raw.githubusercontent.com/liush2yuxjtu/pattern-agent/main/' + repo_path
        records.append(dict(original_href=relative, sha256=fingerprint, bytes=size, repo_path=repo_path, url=url, zip_entries=entries, local_crc_verified=True))
    def replace_values(value):
        if isinstance(value, dict):
            return {key: replace_values(item) for key, item in value.items()}
        if isinstance(value, list):
            return [replace_values(item) for item in value]
        if isinstance(value, str):
            for record in records:
                value = value.replace(record['original_href'], record['url'])
        return value
    for record in records:
        document = document.replace(record['original_href'], record['url'])
        (site / record['original_href']).unlink()
    manifest = replace_values(manifest)
    manifest['external_archives'] = records
    manifest['archive_delivery'] = 'ZIP originals remain byte-identical in this repository under content-addressed eval-artifacts paths, served by raw.githubusercontent.com; only current new site ZIP copies removed, historical sites untouched.'
    return document, manifest


def build(workspace, site, allow_pending=False, external_archives=False):
    if external_archives and allow_pending:
        raise ValueError('--external-archives is final-only; do not combine with --allow-pending')
    if site.resolve().is_relative_to((ROOT / 'web').resolve()) and site.resolve() != (ROOT / 'web/garment-body/hillclimb-evals').resolve():
        raise ValueError('This builder cannot overwrite any historical or unrelated public site')
    destination = site
    site = site.with_name(site.name + '-candidate-staging')
    previous = freeze_previous(workspace)
    protocol_file = workspace / 'protocol/acceptance-v1.json'
    protocol_freeze = workspace / 'protocol/freeze.json'
    if protocol_freeze.exists():
        frozen = full.read(protocol_freeze)
        for relative, fingerprint in frozen['sha256'].items():
            assert full.sha(workspace / 'protocol' / relative) == fingerprint, 'Prospective protocol changed: ' + relative
    candidate_grade = workspace / 'iteration-1/eval-1-original-product/with_skill/run-1/grading.json'
    if external_archives and not candidate_grade.exists():
        raise ValueError('Final external archives require actual independent grading first')
    if candidate_grade.exists():
        bound = full.read(candidate_grade)
        assert bound.get('protocol_sha256') == full.sha(protocol_file), 'Grade does not bind actual frozen protocol'
        assert bound.get('source_protocol_freeze_sha256') == full.sha(protocol_freeze), 'Grade does not bind protocol freeze'
        evidence = bound.get('independent_evidence_sha256')
        assert isinstance(evidence, dict) and evidence, 'Independent grader evidence must be hash-bound'
        for relative, fingerprint in evidence.items():
            path = workspace / relative
            assert not Path(relative).is_absolute() and path.resolve().is_relative_to(workspace.resolve()), 'Grader evidence path escapes workspace'
            assert full.sha(path) == fingerprint, 'Independent grader evidence changed after grade: ' + relative
    runtime_freeze = workspace / 'runtime-executed-manifest.json'
    if runtime_freeze.exists():
        frozen = full.read(runtime_freeze)
        for relative, fingerprint in frozen['files'].items():
            assert full.sha(ROOT / relative) == fingerprint, 'Executed runtime changed after freeze: ' + relative
        assert full.sha(ROOT / frozen['asset']['path']) == frozen['asset']['sha256'], 'Executed runtime asset changed'
    # The shared builder only accepts original13 statements, actual receipts and
    # hash-bound independent grading. The official viewer receives previous data.
    def with_previous(thin, benchmark_path=None):
        return official_review(thin, benchmark_path, previous_workspace=previous)
    original_official = full.official_review
    original_aggregate = full.aggregate_actual_grade
    def current_aggregate(origin, run, grade):
        path = original_aggregate(origin, run, grade)
        benchmark = full.read(path)
        benchmark['metadata'].update(skill_name='Same-state generation and source-pose fitting · hill climb', skill_path=str((workspace / 'skill-executed').relative_to(ROOT)), protocol='One fresh feedback-assisted candidate; real failed ImageGen views were retaken; frozen prior outputs are reused history, not a new paired baseline or blind unaided trial')
        benchmark['notes'].append('New prospective visible-projection/grasp gates are separate from original13 semantic assertions. Hidden exact3D/person accuracy remains unverified. Actual input/model/frame/source hashes and independent negative controls are downloadable.')
        write(path, benchmark)
        return path
    full.official_review = with_previous
    full.aggregate_actual_grade = current_aggregate
    try:
        result = full.build(workspace, site, allow_pending=allow_pending)
    finally:
        full.official_review = original_official
        full.aggregate_actual_grade = original_aggregate
    document = (site / 'eval.html').read_text()
    marker = re.search(r'const FULL_E2E=([^\n]+);\n', document)
    assert marker, 'Full-workflow payload missing'
    payload = json.loads(marker.group(1))
    output = workspace / 'iteration-1/eval-1-original-product/with_skill/run-1/outputs'
    independent_files = {}
    grader_root = workspace / 'grader'
    for source in sorted(grader_root.rglob('*.json')) if grader_root.exists() else []:
        if source.stat().st_size > 512 * 1024:
            continue
        relative = source.relative_to(grader_root)
        target = site / 'source/grader-evidence' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        independent_files[str(relative)] = dict(href=str(target.relative_to(site)), sha256=full.sha(source))
    if independent_files:
        import html
        payload['extra_html'] += '<details class="independent-numeric-evidence"><summary>独立逐项数值、锚点与真实反例 JSON（可直接打开）</summary><p>语义13项、前置数值门槛及开发诊断各自分列；坐标、均值/最大误差、方向、包络和失败反例以原始文件为准，不能只看通过总数。</p><ul>'
        for name, entry in independent_files.items():
            payload['extra_html'] += '<li><a href="' + html.escape(entry['href']) + '">' + html.escape(name) + '</a> SHA256 ' + entry['sha256'] + '</li>'
        payload['extra_html'] += '</ul></details>'
    arm_audit = workspace / 'arm-audit'
    if arm_audit.exists():
        full.archive(arm_audit, site / 'source/arm-surface-audit.zip')
        generic = ROOT / 'tools/human_fit/pose_guided/render_semantic_view.py'
        if generic.exists():
            shutil.copyfile(generic, site / 'source/render_semantic_view.py')
        payload['extra_html'] += '<details class="post-execution-control"><summary>执行反馈后新增的语义控制与表面审查（来源分列）</summary><p>本轮实际新增反馈/重试不是blind无辅助一次成功。早期不可变native_side_semantic.png由当时VTK脚本生成，ImageGen仍按其真实输入指纹记录；后来通用CPU CLI仅为经验证的复现工具，不倒填原skill/runtime快照或旧生成来源。</p><p><a download href="source/arm-surface-audit.zip">实际arm审查代码、原图、独立报告及通用CLI真实验证证据</a> SHA256 ' + full.sha(site / 'source/arm-surface-audit.zip') + '</p>'
        if generic.exists():
            payload['extra_html'] += '<p><a download href="source/render_semantic_view.py">后续通用语义渲染CLI源码</a> SHA256 ' + full.sha(generic) + '。权重分区非精确解剖；辅助生成控制，非碰撞测试或grader oracle。</p>'
        payload['extra_html'] += '</details>'
    case_inputs = workspace / 'case-inputs'
    if case_inputs.exists():
        case_manifest = full.read(case_inputs / 'input-manifest.json')
        for relative, fingerprint in case_manifest['files'].items():
            assert full.sha(case_inputs / relative) == fingerprint, 'Fresh case input changed after freezing: ' + relative
        full.archive(case_inputs, site / 'source/case-inputs.zip')
        shutil.copyfile(case_inputs / 'input-manifest.json', site / 'source/case-inputs-manifest.json')
        raw_guide = case_inputs / 'raw-pose-guide.png'
        if raw_guide.exists():
            shutil.copyfile(raw_guide, site / 'inputs/current-raw-pose-guide.png')
            payload['stages'][0]['images'].append(dict(src='inputs/current-raw-pose-guide.png', label='本轮原始照片 Image Gen 姿态引导', caption='本轮实际原生生成；先经SIFT similarity注册，手工语义与可见性审查；不是检测真值，腹部虚线节点未观测。', sha256=full.sha(raw_guide)))
        payload['extra_html'] += '<p><a download href="source/case-inputs.zip">本轮 fresh case 输入包（旧失败初态、原图、新姿态引导/receipt、手工标记与协议）</a> SHA256 ' + full.sha(site / 'source/case-inputs.zip') + ' · <a href="source/case-inputs-manifest.json">输入指纹</a>。初态是已声明的旧失败模型，不是开发成功 final。</p>'
    run_path = output / 'run.json'
    run = full.read(run_path) if run_path.exists() else {}
    lineage = run.get('generation', {}).get('lineage', 'PENDING: 新候选尚未执行生成，不能以历史图片替代。')
    old_text = '生成条件：front 使用原始商品图及历史保存的人体渲染作姿态引导；其余五图使用原始商品图与本轮 front。六图先于本轮新的拟合完成，最终拟合模型没有作为这批六图的生成输入。后续模型拟合与对照会分别展示，不宣称闭环已回传生成器。'
    import html
    payload['extra_html'] = payload['extra_html'].replace(old_text, '本轮生成条件与版本关系：' + html.escape(lineage))
    document = document.replace('Full ImageGen workflow candidate acceptance', 'Hill climb: same-state generation and source-pose fitting')
    # The shared builder's Human Studio destination is specific to the prior site.
    payload['extra_html'] = payload['extra_html'].replace('../garment-body/full-imagegen-evals/artifacts/model-fit/', '../garment-body/hillclimb-evals/artifacts/model-fit/')
    historical_note = '<p><a href="source/protocol/acceptance-v1.json">本轮前置可见一致性/动作数值协议</a> · <a href="source/protocol/freeze.json">冻结指纹</a>。可见一致性不证明隐藏精确三维结构。</p><p>Previous Output 为冻结的历史11/13执行（REUSED_HISTORY），不是本轮重新执行的旧版基线；没有配对新执行，不报告技能因果提升或新旧统计差值。</p>'
    payload['extra_html'] = payload['extra_html'].replace('<h3>本轮执行与独立评分</h3>', '<h3>本轮执行与独立评分</h3>' + historical_note)
    for source in [workspace / 'baseline-freeze.json', workspace / 'baseline/grading.json', workspace / 'baseline/assertions-original13.json']:
        target = site / 'source/history' / source.name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    full.archive(workspace / 'skill-baseline', site / 'source/history/skill-baseline.zip')
    assertions_alias = site / 'source/protocol/assertions.json'
    assertions_alias.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(workspace / 'baseline/assertions-original13.json', assertions_alias)
    grade_path = workspace / 'iteration-1/eval-1-original-product/with_skill/run-1/grading.json'
    grade = full.read(grade_path) if grade_path.exists() else None
    gates = grade.get('quantitative_gates', []) if grade else []
    base_manifest = full.read(site / 'manifest.json')
    selected_archive = selected_six_archive(output, site, base_manifest['generation'], grade.get('overall_acceptance', 'NOT_GRADED') if grade else 'NOT_GRADED')
    if selected_archive:
        label = '下载最终六张原生图' if grade and grade.get('overall_acceptance') == 'PASS' else '下载当前 selected 六张原生图（验收未完成）'
        payload['extra_html'] = '<p class="selected-six-download"><strong><a download data-kind="selected-six-archive" href="source/selected-six.zip">' + label + '</a></strong> SHA256 ' + selected_archive['sha256'] + '。canonical文件名，字节等于实际选定原件；失败尝试另留full-run/history。</p>' + payload['extra_html']
    selection_info, attempt_html, attempt_rows = generation_attempts(output, site, base_manifest)
    development_info, development_html, development_rows = development_attempts(workspace, site, len(attempt_rows))
    payload['extra_html'] += attempt_html + development_html
    payload['extra_html'] += '<p>本次 fresh 执行者在真实运行后收到独立诊断反馈，并实际重新生成失败的视图；不是 blind 无辅助一次通过，也不是重新执行旧技能的配对因果实验。隐藏精确三维结构与真人围度未验证；通过仅表示本轮前置可见投影/动作门槛得到实际证据。</p>'
    attempt_rows = attempt_rows + development_rows
    visible_records, visible_html, visible_rows = visible_projection_evidence(workspace, site, base_manifest, len(attempt_rows))
    payload['extra_html'] += visible_html
    combined_anchor = workspace / 'grader/generated-visible/audit.json'
    if combined_anchor.exists():
        payload['extra_html'] += '<p><a href="source/grader-evidence/generated-visible/audit.json">当前 selected 正/侧/背锚点联合审计</a> SHA256 ' + full.sha(combined_anchor) + '。单视图原始文件的顶层passed可能因尚缺另外两视图而为false；单视图数值与完整三视图联合结论分开，原诊断不改写。</p>'
    attempt_rows = attempt_rows + visible_rows
    if grade:
        overall = grade.get('overall_acceptance') or ('FAIL' if grade['summary']['failed'] else 'NOT_VERIFIED')
        if overall == 'PASS':
            assert grade['summary']['failed'] == 0, 'Overall PASS cannot override failed original requirements'
            assert gates and all(g.get('passed') is True for g in gates), 'Overall PASS requires every frozen numeric gate to pass'
        gate_html = '<h3>本轮前置数值门槛（与原13语义断言分列）</h3><p>隐藏真实三维结构仍未验证，不列入已通过事实。</p><ul>'
        for gate in gates:
            label = 'PASS' if gate.get('passed') is True else 'FAIL' if gate.get('passed') is False else 'UNKNOWN'
            gate_html += '<li><strong>' + label + ' · ' + html.escape(str(gate.get('id'))) + '</strong> ' + html.escape(str(gate.get('evidence', ''))) + '</li>'
        gate_html += '</ul>'
        payload['extra_html'] = payload['extra_html'].replace('<h3>最终模型实测 · cm</h3>', gate_html + '<h3>最终模型实测 · cm</h3>')
        payload['quick_verdict'] = '本轮独立整体验收：' + overall + '；原13语义断言与新增数值门槛分别展示。'
    current_marker = re.search(r'const FULL_E2E=([^\n]+);\n', document)
    encoded = json.dumps(payload, ensure_ascii=False).replace('<', r'\u003c')
    document = document[:current_marker.start(1)] + encoded + document[current_marker.end(1):]
    if attempt_rows:
        encoded_history = json.dumps(attempt_rows, ensure_ascii=False).replace('<', r'\u003c')
        document = document.replace('</body>', '<style>.retake-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px}.retake-grid img{width:100%;height:240px;object-fit:contain}.retake-grid button{display:block;width:100%;cursor:zoom-in}.retake-grid section{border:1px solid #ddd;padding:8px}</style><script>const RETAKE_HISTORY=' + encoded_history + ';\n' + RETAKE_SCRIPT + '</script></body>', 1)
    (site / 'eval.html').write_text(document)
    manifest = full.read(site / 'manifest.json')
    manifest['generation_selection'] = selection_info
    manifest['selected_six_archive'] = selected_archive
    manifest['development_history'] = development_info
    manifest['visible_projection_evidence'] = visible_records
    manifest['independent_numeric_evidence'] = independent_files
    if (workspace / 'runtime-executed-manifest.json').exists():
        shutil.copyfile(workspace / 'runtime-executed-manifest.json', site / 'source/runtime-executed-manifest.json')
        manifest['executed_runtime_freeze'] = full.read(workspace / 'runtime-executed-manifest.json')
    manifest['post_execution_tools'] = [dict(path='tools/human_fit/pose_guided/render_semantic_view.py', role='Feedback-time supplemental control/reproduction, not retroactively in executed snapshot', sha256=full.sha(ROOT / 'tools/human_fit/pose_guided/render_semantic_view.py'))] if (ROOT / 'tools/human_fit/pose_guided/render_semantic_view.py').exists() else []
    manifest.update(previous_output=dict(status='REUSED_HISTORY', source_workspace=str(OLD.relative_to(ROOT)), grading=full.read(workspace / 'baseline/grading.json')['summary'], frozen_manifest='source/history/baseline-freeze.json'), iteration_scope='current actual candidate with frozen prior outputs, not a new paired experiment')
    if grade:
        manifest['overall_acceptance'] = overall
        manifest['quantitative_gates'] = gates
        manifest['hidden_structure_accuracy'] = 'NOT_VERIFIED'
    manifest['upstream']['previous_workspace'] = str(previous.relative_to(ROOT))
    shutil.copyfile(Path(__file__), site / 'source/build_hillclimb_review.py')
    shutil.copyfile(Path(__file__).with_name('verify_hillclimb_review.cjs'), site / 'source/verify_hillclimb_review.cjs')
    if external_archives:
        document, manifest, input_aliases = deduplicate_derived_inputs(site, document, manifest)
        document, manifest = externalize_archives(workspace, site, document, manifest)
        document, manifest, image_replacements = externalize_rejected_closeups(workspace, site, document, manifest)
        for alias in input_aliases:
            alias['canonical_href'] = image_replacements.get(alias['canonical_original_href'], alias['canonical_original_href'])
        manifest['derived_input_aliases'] = input_aliases
        (site / 'eval.html').write_text(document)
        write(site / 'external-archives.json', dict(scope='Only current hillclimb site ZIP copies moved; all source bytes retained in content-addressed repository paths', archives=manifest['external_archives']))
        write(site / 'external-images.json', dict(scope='Only four rejected closeup presentation copies moved; selected six remain local and executor originals untouched', images=manifest['external_images']))
        write(site / 'derived-input-aliases.json', dict(scope='Byte-identical review input duplicates only, not source/receipt rewrites', aliases=input_aliases))
    manifest['files'] = {str(p.relative_to(site)): full.sha(p) for p in full.files(site) if p.name != 'manifest.json'}
    write(site / 'manifest.json', manifest)
    if destination.exists():
        shutil.rmtree(destination)
    site.rename(destination)
    result['out'] = str(destination / 'eval.html')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, default=DEFAULT)
    parser.add_argument('--site', type=Path, default=ROOT / 'web/garment-body/hillclimb-evals')
    parser.add_argument('--allow-pending', action='store_true')
    parser.add_argument('--external-archives', action='store_true', help='Final-only: store current site ZIP originals in content-addressed repository artifacts and link actual raw GitHub downloads')
    args = parser.parse_args()
    print(json.dumps(build(args.workspace, args.site, args.allow_pending, args.external_archives)))
