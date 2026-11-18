#!/usr/bin/env python3
"""Build an offline, single-HTML reviewer from actual, hash-bound recordings."""
import argparse
import base64
import gzip
import hashlib
import json
import re
from pathlib import Path
import subprocess
import tempfile
import zipfile
import yaml
from recording_codec import encode, decode
from human_conditions import readable_conditions

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
def sha(raw): return hashlib.sha256(raw).hexdigest()


def build(args):
    cases = []
    comparison=(ROOT/'web/intent-edit-review/index.html').read_text()
    catalog=json.loads(re.search(r'<script[^>]*id="app-data"[^>]*>(.*?)</script>',comparison,re.S)[1])
    for directory in args.runs:
        input_raw = (directory/'input.json').read_bytes(); trajectory_raw = (directory/'trajectory.json').read_bytes()
        source = json.loads(input_raw); recording = json.loads(trajectory_raw); audit = json.loads((directory/'audit.json').read_bytes())
        if recording['input_sha256'] != sha(input_raw) or audit['input_sha256'] != sha(input_raw) or audit['recording_sha256'] != sha(trajectory_raw):
            raise ValueError('Actual input / recording / independent report are not the same revision')
        if len(recording['frames']) < 2: raise ValueError('No actual physical trajectory')
        if any('folds' not in f for f in recording['frames']): raise ValueError('Actual geometric fold fields missing')
        entry=next(e for e in [catalog['baseline'],*catalog['cases']] if e['id']==source['case'])
        if entry['twoD']['source_dxf_sha256']!=source['source_dxf_sha256'] or entry['twoD']['source_yaml_sha256']!=source['source_spec_sha256']:
            raise ValueError('2D pattern is a different revision from the physical input')
        for file in entry['files'].values():
            raw=base64.b64decode(file['base64'],validate=True)
            if sha(raw)!=file['sha256'] or raw!=(ROOT/file['path']).read_bytes():
                raise ValueError('Complete source download differs from actual repository file')
        source_package={key:entry.get(key) for key in ['files','twoD','intent','changes']}
        source_package['intent']=entry.get('intent','原型输入；尚未应用新的设计意图。')
        control_path=directory/'controls/manifest.json'
        controls=json.loads(control_path.read_bytes()) if control_path.exists() else {'results':{}}
        if control_path.exists() and (controls.get('input_sha256')!=sha(input_raw) or controls.get('wasm_sha256')!=recording['wasm_sha256']):
            raise ValueError('Engine controls belong to a different input or executable')
        source_report=json.loads((directory/'source-independent.json').read_bytes())
        resume=json.loads((directory/'resume-independent.json').read_bytes())
        results=controls['results'];rows=audit['frames']
        complete=audit['frames_checked']==audit['total_frames']==len(recording['frames'])==source['config']['数值条件']['记录步数']+1
        seams_ok=source_report['verdict']=='PASS' and complete and all(r['max_seam_gap_mm']<=2 for r in rows)
        body_controls=results.get('kernel','NOT_RUN')
        if source.get('solver_features',{}).get('body_feature_contacts'):
            body_values=[body_controls,results.get('body-feature','NOT_RUN')]
            body_controls='FAIL' if 'FAIL' in body_values else 'PASS' if all(v=='PASS' for v in body_values) else 'NOT_RUN'
        current_engines=[
            'PASS' if seams_ok else 'FAIL',body_controls,
            'FAIL' if results.get('kernel')=='FAIL' or any(r['tensor_pass'] is False for r in rows) else 'PASS' if complete and results.get('kernel')=='PASS' and all(r['tensor_pass'] for r in rows) else 'NOT_RUN',
            'FAIL' if results.get('hinges')=='FAIL' or any(r['fold_pass'] is False for r in rows) else 'PASS' if complete and results.get('hinges')=='PASS' and all(r['fold_pass'] is True for r in rows) else 'NOT_RUN',
            'PASS' if resume.get('verdict')=='PASS' and resume.get('input_sha256')==sha(input_raw) and resume.get('recording_sha256')==sha(trajectory_raw) else 'FAIL',
            'NOT_RUN',
            'FAIL' if results.get('kernel')=='FAIL' or not audit['checks']['connections']['all_pairs_accounted_for'] else 'PASS' if results.get('kernel')=='PASS' else 'NOT_RUN']
        labels = {'baseline':'原型 · 女士贴身长袖T恤', '03_cuff_width':'改版 · 袖口展开宽 +10U'}
        packed,blocks=encode(recording)
        if decode(packed,blocks)!=recording:raise ValueError('Lossless recording roundtrip failed')
        cases.append({'label': labels.get(source['case'],source['case']), 'input': source, 'recording': packed, 'recording_blocks':blocks, 'audit': audit,
                      'conditions':yaml.safe_dump(readable_conditions(source),allow_unicode=True,sort_keys=False),'source_package':source_package,
                      'engine_verdicts':current_engines,'controls':controls})
    engines = [
        ('缝合关系检查', '漏缝、反向配对和间隙故障对照；逐缝与二维走缝分开检查。'),
        ('人体碰撞计算', '真实 MakeHuman 三角面、独立射线复核；双向交叉检查。'),
        ('应力应变热图', '正交各向异性试片与独立张量计算；实际 GPU 颜色读回。'),
        ('衣服折角计算', '有向二面角、曲率和 170° 折返对照；不预测永久折痕。'),
        ('物理回放', '每个保存状态精确读回；seek 不积分，继续计算逐位一致。'),
        ('物理调试视图', '接触、面片、场与真实导出；界面收据绑定本次程序与数据。'),
        ('布料连接约束', '真实约束激活及故障注入；当前整衣另查全部连接数量。')]
    viewer_sources={name:sha((HERE/name).read_bytes()) for name in ['viewer.mjs','viewer.css','viewer.template.html','recording-codec.mjs']}
    receipts=[json.loads(path.read_bytes()) for path in args.viewer_receipt]
    for case in cases:
        if any(r.get('verdict')=='PASS' and r.get('viewer_sources')==viewer_sources and r.get('case')==case['input']['case']
               and r.get('input_sha256')==case['audit']['input_sha256'] and r.get('recording_sha256')==case['audit']['recording_sha256'] for r in receipts):
            case['engine_verdicts'][5]='PASS'
    def combined(index):
        values=[case['engine_verdicts'][index] for case in cases]
        return 'FAIL' if 'FAIL' in values else 'PASS' if all(v=='PASS' for v in values) else 'NOT_RUN'
    payload = {'format':'intent-physics-review/1', 'cases':cases,'viewer_sources':viewer_sources,
        'engines':[{'name':name,'verdict':combined(i),'note':note} for i,(name,note) in enumerate(engines)],
        'engine_receipts':{'viewer_receipt_sha256':[sha(path.read_bytes()) for path in args.viewer_receipt],
                           'scope':'Source-bound mechanism controls. Case geometry and garment acceptance remain separate in each audit.'}}
    with tempfile.TemporaryDirectory(dir=ROOT/'work') as tmp:
        bundle = Path(tmp)/'viewer.js'
        subprocess.run([str(ROOT/'experiments/freesewing_cloth_lab/node_modules/.bin/esbuild'),str(HERE/'viewer.mjs'),
            '--bundle','--format=esm','--target=es2022','--minify','--legal-comments=inline','--outfile='+str(bundle)],check=True)
        js = bundle.read_text().replace('</script','<\\/script')
    page = (HERE/'viewer.template.html').read_text()
    compressed = gzip.compress(json.dumps(payload,ensure_ascii=False,separators=(',',':')).encode(),compresslevel=9,mtime=0)
    for marker,value in [('__STYLE__',(HERE/'viewer.css').read_text()),('__PAYLOAD__',base64.b64encode(compressed).decode()),('__BUNDLE__',js)]:
        if page.count(marker) != 1: raise ValueError('Invalid build template marker '+marker)
        page = page.replace(marker,value)
    args.output.mkdir(parents=True,exist_ok=True); (args.output/'index.html').write_text(page)
    manifest={'format':'intent-physics-review-manifest/1','html_sha256':sha(page.encode()),'bytes':len(page.encode()),
              'viewer_sources':viewer_sources,
              'cases':[{'id':c['input']['case'],'source_dxf_sha256':c['input']['source_dxf_sha256'],
                        'source_spec_sha256':c['input']['source_spec_sha256'],'recording_sha256':c['audit']['recording_sha256'],
                        'garment_verdict':c['audit']['verdict'],'frames':len(c['recording']['frames'])} for c in cases],
              'material_calibration':'NOT_RUN','physical_fit':'NOT_RUN'}
    (args.output/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(manifest,ensure_ascii=False))


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('runs',type=Path,nargs='+')
    p.add_argument('--engine-evidence',type=Path,help='Legacy compatibility only; old standard-cloth receipts do not make current cards PASS')
    p.add_argument('--viewer-receipt',type=Path,action='append',default=[])
    p.add_argument('--output',type=Path,default=ROOT/'web/intent-edit-review/physics');build(p.parse_args())
