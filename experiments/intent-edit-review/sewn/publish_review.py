#!/usr/bin/env python3
"""Publish only fresh accepted sewing artifacts and explicit unsupported decisions."""
import argparse
import hashlib
import html
import json
from pathlib import Path
import shutil
import zipfile
from datetime import datetime
from zoneinfo import ZoneInfo

REPO = Path(__file__).resolve().parents[3]


def esc(value):
    return html.escape(str(value), quote=True)


def build(run, output, verification=None):
    manifest = json.loads((run / 'manifest.json').read_text())
    expected = [('sew-pattern-to-3d', 'STARTED'), ('sew-pattern-to-3d', 'COMPLETED'),
                ('verify-seaming', 'STARTED'), ('verify-seaming', 'COMPLETED')]
    if [(e['phase'], e['state']) for e in manifest['phases']] != expected:
        raise ValueError('The first two skills did not complete in the required order')
    if output.exists() and any(output.iterdir()):
        raise ValueError('Publish to a new empty directory; stale models must not survive')
    output.mkdir(parents=True, exist_ok=True)
    rows, panels, inventory = [], [], {}
    for entry in manifest['cases']:
        cid = entry['id']; source = run / cid; dest = output / cid; dest.mkdir()
        dxf = (REPO / entry['source_dxf']).read_bytes()
        spec = (REPO / entry['source_yaml']).read_bytes()
        if hashlib.sha256(dxf).hexdigest() != entry['source_dxf_sha256'] or hashlib.sha256(spec).hexdigest() != entry['source_yaml_sha256']:
            raise ValueError('A source changed after generation')
        (dest / 'source-input.dxf').write_bytes(dxf); (dest / 'source-spec.yaml').write_bytes(spec)
        shutil.copyfile(source / 'decision.json', dest / 'decision.json')
        href = lambda name: f'{cid}/{name}'
        files = f'<a href="{href("source-spec.yaml")}" download>规格YAML</a> · <a href="{href("source-input.dxf")}" download>原始DXF</a>'
        if entry['verdict'] == 'PASS':
            actual = json.loads((source / 'independent.json').read_text())
            if actual['verdict'] != 'PASS':
                raise ValueError('Independent acceptance missing')
            shutil.copytree(source / 'files', dest / 'files')
            shutil.copyfile(source / 'independent.json', dest / 'independent.json')
            model = (dest / 'files/model.glb').read_bytes()
            if hashlib.sha256(model).hexdigest() != entry['model_sha256']:
                raise ValueError('Published GLB differs from independently reopened bytes')
            with zipfile.ZipFile(dest / 'delivery.zip', 'w', zipfile.ZIP_DEFLATED) as z:
                for path in sorted(dest.rglob('*')):
                    if path.is_file() and path.name != 'delivery.zip':
                        info = zipfile.ZipInfo(str(path.relative_to(dest)), (1980, 1, 1, 0, 0, 0))
                        info.compress_type = zipfile.ZIP_DEFLATED; z.writestr(info, path.read_bytes())
            checks = actual['checks']; topo = checks['topology']
            metrics = (f'{len(checks["seams"])}条缝 · {topo["connected_components"]}连通组件 · '
                       f'{topo["boundary_cycles"]}个正常开口 · 穿插{checks["proper_self_intersections"]}')
            measurements = ''.join('<tr>' + ''.join(f'<td>{esc(value)}</td>' for value in
                [s['name'], f'{s["processed_residual_mm"]:.6f}', f'{s["length_error_mm"]:.6f}', f'{s["max_gap_mm"]:.6f}']) + '</tr>' for s in checks['seams'])
            panels.append(f'''<section class="panel" data-case="{cid}"><h2>{esc(entry['label'])}</h2>
<p class="metrics">修正外壳几何 PASS · {metrics}</p><iframe title="{esc(entry['label'])}的本次缝合三维预览" data-case="{cid}" src="{href('files/preview.html')}"></iframe>
<div class="actions"><a class="primary" href="{href('delivery.zip')}" download>完整交付包</a><a href="{href('files/model.glb')}" download>GLB模型</a><a href="{href('independent.json')}">独立报告</a><a href="{href('files/corrected-seam-lines.svg')}">原线与修正线</a></div>
<p>本次 {entry['vertices']} 顶点 / {entry['triangles']} 三角面。最大点位修正 {entry['max_vertex_edit_mm']:.6f} mm；原始DXF与YAML未改写。</p>
<details><summary>查看15条缝的实际测量（毫米假定）</summary><div class="table-wrap"><table><thead><tr><th>缝名</th><th>加工后平面残差</th><th>三维缝长误差</th><th>间隙</th></tr></thead><tbody>{measurements}</tbody></table></div></details></section>''')
            detail = metrics + f'；最大三维缝长误差 {checks["max_3d_seam_length_error_mm"]:.6f} mm'
            files += f' · <a href="{href("files/preview.html")}">独立三维预览</a> · <a href="{href("delivery.zip")}" download>完整包</a>'
        else:
            if (source / 'files/model.glb').exists():
                raise ValueError('A rejected case unexpectedly retained a model')
            detail = entry.get('reason', '未生成可验收模型') + ' 需要新的明确配置与缝合合同。'
            files += f' · <a href="{href("decision.json")}">拒绝记录</a>'
        rows.append(f'<tr data-result="{esc(cid)}"><th>{esc(entry["label"])}</th><td class="status">{esc(entry["verdict"])}</td><td>{esc(detail)}</td><td>{files}</td></tr>')
    s = manifest['summary']
    template = (Path(__file__).with_name('review-template.html')).read_text()
    replacements = {'__SUMMARY__': f'{s["PASS"]}项几何通过，{s["FAIL"]}项失败，{s["BLOCKED"]}项受限',
                    '__VERDICT__': esc(manifest['verdict']), '__ROWS__': ''.join(rows), '__PANELS__': ''.join(panels)}
    for key, value in replacements.items():
        if template.count(key) != 1: raise ValueError('Template placeholder missing')
        template = template.replace(key, value)
    (output / 'index.html').write_text(template)
    if verification:
        result = json.loads(verification.read_text())
        accepted = {r['id']: r for r in manifest['cases'] if r['verdict'] == 'PASS'}
        if result['verdict'] != 'PASS' or result['workflow_verdict'] != manifest['verdict']:
            raise ValueError('Preview report must preserve the whole workflow outcome')
        if result['catalog_sha256'] != hashlib.sha256((output / 'index.html').read_bytes()).hexdigest():
            raise ValueError('Preview report is for a different catalog')
        if {r['id'] for r in result['cases']} != set(accepted):
            raise ValueError('Preview report has missing or invented accepted cases')
        for row in result['cases']:
            if row['model_sha256'] != accepted[row['id']]['model_sha256'] or row['downloaded_glb_independent'] != 'PASS':
                raise ValueError('Downloaded model was not independently accepted')
        shutil.copyfile(verification, output / 'preview-verification.json')
        manifest['phases'].append({'phase': 'verify', 'state': 'COMPLETED',
                                   'recorded_at': datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),
                                   'preview_delivery_verdict': result['verdict'], 'whole_workflow_verdict': manifest['verdict']})
        manifest['preview_verification_sha256'] = hashlib.sha256(verification.read_bytes()).hexdigest()
    (output / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    for path in sorted(output.rglob('*')):
        if path.is_file(): inventory[str(path.relative_to(output))] = {'bytes': path.stat().st_size, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
    (output / 'files-manifest.json').write_text(json.dumps(inventory, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'output': str(output), 'workflow_verdict': manifest['verdict'], 'summary': s, 'files': len(inventory)}, ensure_ascii=False))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run', type=Path, required=True); p.add_argument('--output', type=Path, required=True)
    p.add_argument('--verification', type=Path)
    a = p.parse_args(); build(a.run.resolve(), a.output.resolve(), a.verification.resolve() if a.verification else None)
