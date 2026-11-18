#!/usr/bin/env python3
"""Export/reopen the source-bound reference shell with the strict sewing oracle.

Only the existing supported profile is accepted here. Research simulation of a
different input does not expand that profile or inherit its PASS.
"""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'services/dxf-preview'))
from converter.core import encode_glb
from verification.seams import audit_glb, CONTRACT_PATH


def run(directory):
    input_raw=(directory/'input.json').read_bytes()
    data=json.loads(input_raw)
    page=(ROOT/'web/intent-edit-review/index.html').read_text()
    package=json.loads(re.search(r'<script[^>]*id="app-data"[^>]*>(.*?)</script>',page,re.S)[1])
    entry=next(c for c in [package['baseline'],*package['cases']] if c['id']==data['case'])
    source=(ROOT/entry['files']['dxf']['path']).read_bytes()
    assert hashlib.sha256(source).hexdigest()==data['source_dxf_sha256']
    assert not data['config']['数值条件']['袖子预变形'], 'Retargeted placement is not the original static shell'
    ids=np.asarray(data['global_ids']);unique,first,inverse=np.unique(ids,return_index=True,return_inverse=True)
    vertices=np.asarray(data.get('source_reference_positions',data['placement_before_contact']))[first].copy()
    if 'depth_placement' in data['initialization']:
        placement=data['initialization']['depth_placement'];blend=np.clip((abs(vertices[:,0])-.25)/.20,0,1);blend=blend*blend*(3-2*blend)
        vertices[:,2]=(vertices[:,2]-placement['offset_m']-placement['arm_offset_m']*blend)/placement['scale']
    vertices-=np.asarray(data['initialization']['translation_m'])
    faces=inverse[np.asarray(data['triangles'],int)]
    manifest=deepcopy(data['source_sewing'])
    manifest.update(input_sha256=data['source_dxf_sha256'],input_units='mm',physical_scale=1.,
        input_registration={'canonical_to_input':list(range(126)),'input_reversed':[False]*126},
        contract_sha256=hashlib.sha256(CONTRACT_PATH.read_bytes()).hexdigest())
    cross=np.cross(vertices[faces[:,1]]-vertices[faces[:,0]],vertices[faces[:,2]]-vertices[faces[:,0]])
    normals=np.zeros_like(vertices)
    for k in range(3):np.add.at(normals,faces[:,k],cross)
    normals/=np.maximum(np.linalg.norm(normals,axis=1)[:,None],1e-15)
    report={'profile':'fitted-tshirt-v1','conversion_id':'research-quality-mesh','mode':'static source reference; not the physical recording'}
    blob=encode_glb([('source-reference',vertices.astype('<f4'),normals.astype('<f4'),faces.astype('<u4'))],report,manifest)
    (directory/'source-reference.glb').write_bytes(blob)
    result=audit_glb((directory/'source-reference.glb').read_bytes(),source,'mm')
    result['glb_sha256']=hashlib.sha256(blob).hexdigest()
    result['experiment_input_sha256']=hashlib.sha256(input_raw).hexdigest()
    (directory/'source-independent.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'verdict':result['verdict'],'failures':result['failures'],'seams':len(result['checks'].get('seams',[]))},ensure_ascii=False))
    return result['verdict']=='PASS'


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('directory',type=Path)
    raise SystemExit(0 if run(p.parse_args().directory) else 1)
