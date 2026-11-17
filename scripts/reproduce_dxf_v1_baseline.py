#!/usr/bin/env python3
"""Rebuild the preserved v1 GLB from its public commit, then audit actual bytes."""
import argparse,hashlib,importlib.util,json,struct,subprocess,sys,tempfile
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'services/dxf-preview'))
from verification.geometry import mesh_audit,intersect_pairs
SOURCE_COMMIT='0f9edae21e6fc28183bcaedd7c47d03ea29ef5b2'

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    raw=(ROOT/'services/dxf-preview/public/sample.dxf').read_bytes()
    with tempfile.TemporaryDirectory(prefix='pattern-agent-historical-v1-') as folder:
        base=Path(folder)
        for name in ['core.py','profile.json']:(base/name).write_bytes(subprocess.check_output(['git','show',SOURCE_COMMIT+':services/dxf-preview/converter/'+name],cwd=ROOT))
        spec=importlib.util.spec_from_file_location('historical_converter_v1',base/'core.py');module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module);converted=module.convert_dxf(raw,units='mm')
    blob=converted.glb;size=struct.unpack_from('<I',blob,12)[0];doc=json.loads(blob[20:20+size]);binary=blob[28+size:]
    def accessor(i,kind,width):
        item=doc['accessors'][i];view=doc['bufferViews'][item['bufferView']];return np.frombuffer(binary,dtype=kind,count=item['count']*width,offset=view.get('byteOffset',0)).reshape(-1,width)
    vertices=[];faces=[];offset=0
    for mesh in doc['meshes']:
        item=mesh['primitives'][0];v=accessor(item['attributes']['POSITION'],'<f4',3);f=accessor(item['indices'],'<u4',1).reshape(-1,3);vertices.extend(v);faces.extend(f+offset);offset+=len(v)
    vertices=np.array(vertices,float);faces=np.array(faces,int);report=mesh_audit(vertices,faces);pairs=intersect_pairs(vertices,faces);report.update(verdict='FAIL',scope='preserved published v1 outer-shell topology and proper self-intersections',source_commit=SOURCE_COMMIT,input_sha256=hashlib.sha256(raw).hexdigest(),glb_sha256=hashlib.sha256(blob).hexdigest(),proper_self_intersections=len(pairs),intersection_examples=pairs[:20],physical_fit='NOT_RUN')
    assert report['glb_sha256']=='de34bed5c75bc2ee519624cb973891445103aacbf9511fdb8cb1c7ad4a2026a2'
    assert report['connected_components']==9 and len(pairs)==340
    (a.out/'model.glb').write_bytes(blob);(a.out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
    return 0
if __name__=='__main__':raise SystemExit(main())
