import json,struct,hashlib,sys
from pathlib import Path
import numpy as np
root=Path(sys.argv[1]).resolve()
out={}
for label in ('neutral','posed'):
 p=root/f'{label}.glb'; b=p.read_bytes(); magic,version,total=struct.unpack_from('<4sII',b);assert (magic,version,total)==(b'glTF',2,len(b))
 n,kind=struct.unpack_from('<II',b,12);assert kind==0x4e4f534a
 d=json.loads(b[20:20+n]); bn,bk=struct.unpack_from('<II',b,20+n);assert bk==0x004e4942
 binary=memoryview(b)[28+n:28+n+bn]; ai=d['meshes'][0]['primitives'][0]['attributes']['POSITION'];a=d['accessors'][ai];v=d['bufferViews'][a['bufferView']];assert a['componentType']==5126 and a['type']=='VEC3'
 points=np.frombuffer(binary,dtype='<f4',count=a['count']*3,offset=v.get('byteOffset',0)+a.get('byteOffset',0)).reshape(-1,3)
 obj=np.array([list(map(float,l.split()[1:4])) for l in (root/f'{label}.obj').read_text().splitlines() if l.startswith('v ')])
 assert obj.shape==points.shape and np.isfinite(points).all();err=float(np.max(np.linalg.norm(points*100-obj,axis=1)));assert err<.0001,err
 out[label]={'vertices':len(points),'obj_unit':'cm','glb_unit':'m','maximum_vertex_difference_cm':err,'glb_sha256':hashlib.sha256(b).hexdigest()}
record=Path(sys.argv[2]);record.write_text(json.dumps({'verdict':'PASS','method':'Independent GLB binary parser vs actual OBJ positions; no submitted measurement fields trusted','results':out},indent=2)+'\n');print(record)
