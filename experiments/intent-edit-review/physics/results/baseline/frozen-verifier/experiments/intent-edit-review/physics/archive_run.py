#!/usr/bin/env python3
"""Archive one immutable, source-bound experiment, including failures."""
import argparse
import base64
import gzip
import hashlib
import json
from pathlib import Path
import re
import shutil
import yaml
from human_conditions import readable_conditions

ROOT=Path(__file__).resolve().parents[3]
def sha(raw):return hashlib.sha256(raw).hexdigest()

def archive(run,destination):
    data=json.loads((run/'input.json').read_bytes());record=json.loads((run/'trajectory.json').read_bytes())
    audit=json.loads((run/'audit.json').read_bytes())
    if record['input_sha256']!=sha((run/'input.json').read_bytes()) or audit['recording_sha256']!=sha((run/'trajectory.json').read_bytes()):
        raise ValueError('Input/recording/audit are different revisions')
    if record['wasm_sha256']!=sha((run/'solver.wasm').read_bytes()):raise ValueError('Executable differs from actual recording')
    destination.mkdir(parents=True,exist_ok=False);files={}
    def put(name,raw,compressed=False):
        stored=gzip.compress(raw,compresslevel=9,mtime=0) if compressed else raw
        target=destination/(name+'.gz' if compressed else name);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(stored)
        files[str(target.relative_to(destination))]={'bytes':len(stored),'sha256':sha(stored),'uncompressed_bytes':len(raw),'uncompressed_sha256':sha(raw)}
    for name in ['input.json','trajectory.json']:put(name,(run/name).read_bytes(),True)
    for name in ['solver-capacity.c','solver.wasm','source-reference.glb','source-independent.json','preparation-final.bin',
                 'preparation-gate.json','resume-independent.json','audit.json']:
        put(name,(run/name).read_bytes())
    for folder in ['frozen-source','frozen-verifier','controls']:
        for path in sorted((run/folder).rglob('*')):
            if path.is_file():put(str(path.relative_to(run)),path.read_bytes())
    catalog=json.loads(re.search(r'<script[^>]*id="app-data"[^>]*>(.*?)</script>',(ROOT/'web/intent-edit-review/index.html').read_text(),re.S)[1])
    entry=next(e for e in [catalog['baseline'],*catalog['cases']] if e['id']==data['case'])
    for descriptor in entry['files'].values():
        raw=base64.b64decode(descriptor['base64'],validate=True)
        if sha(raw)!=descriptor['sha256'] or raw!=(ROOT/descriptor['path']).read_bytes():raise ValueError('CAD/spec source mismatch')
        put(descriptor['name'],raw)
    put('intent.txt',entry.get('intent','原型输入；未应用新设计意图。').encode())
    put('experiment-conditions.yaml',yaml.safe_dump(readable_conditions(data),allow_unicode=True,sort_keys=False).encode())
    manifest={'format':'source-bound-physics-archive/1','case':data['case'],'garment_verdict':audit['verdict'],
        'preparation_gate':record.get('preparation_gate','NOT_RUN'),'recording_role':record.get('recording_role','legacy failure benchmark'),
        'input_sha256':record['input_sha256'],'recording_sha256':audit['recording_sha256'],
        'source_dxf_sha256':data['source_dxf_sha256'],'source_spec_sha256':data['source_spec_sha256'],
        'frames':len(record['frames']),'physical_fit':'NOT_RUN','material_calibration':'NOT_RUN','files':files}
    (destination/'artifact-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    readme=f'''# {data['case']}：来源绑定物理记录

整衣结论 **{audit['verdict']}**；准备状态 **{manifest['preparation_gate']}**。记录角色：`{manifest['recording_role']}`。
机制对照或查看器通过不能覆盖该结论。真人合身及面料实测仍为 NOT_RUN。

- [完整文件摘要](artifact-manifest.json)
- [实际条件（中文 YAML）](experiment-conditions.yaml)
- [设计意图](intent.txt)
- [逐帧独立报告](audit.json)
- [准备状态检查](preparation-gate.json)
- [新进程继续检查](resume-independent.json)
- [完整输入 JSON（无损压缩）](input.json.gz)
- [全部{len(record['frames'])}帧真实记录（无损压缩）](trajectory.json.gz)

原始规格、DXF与该案例实际差异文件均在本目录，文件名和内容保持原样。
`source-reference.glb`只是从二维来源复核的静态壳，不是物理轨迹。
`solver.wasm`及`solver-capacity.c`是实际执行文件与生成源码；`frozen-source/`记录运行时源码字节。

将两份 `.json.gz` 解压为同名 JSON 后，按[上级物理实验说明](../../README.md)从仓库根复验。
所有文件均有压缩字节及原始字节SHA-256，解压不作量化或坐标取整。
'''
    (destination/'README.md').write_text(readme)
    print(json.dumps({'archive':str(destination),'case':data['case'],'garment_verdict':audit['verdict'],'files':len(files)},ensure_ascii=False))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('run',type=Path);p.add_argument('destination',type=Path)
    a=p.parse_args();archive(a.run.resolve(),a.destination.resolve())
