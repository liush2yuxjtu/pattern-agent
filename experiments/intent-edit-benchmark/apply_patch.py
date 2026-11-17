from pathlib import Path
import argparse
import json
import engine

p=argparse.ArgumentParser(description='带基准摘要和旧值保护的规格或DXF补丁重放。')
p.add_argument('kind',choices=['spec','dxf']);p.add_argument('base',type=Path);p.add_argument('patch',type=Path);p.add_argument('output',type=Path)
a=p.parse_args()
data=(engine.apply_spec_patch if a.kind=='spec' else engine.apply_dxf_patch)(a.base.read_bytes(),json.loads(a.patch.read_text()))
a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_bytes(data)
print(json.dumps({'output':str(a.output),'sha256':engine.digest(data)}))
