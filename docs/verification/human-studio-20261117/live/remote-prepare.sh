set -e
mkdir -p /tmp/pattern-agent-human-live
python3 - <<'PY'
from pathlib import Path
import urllib.request,json,hashlib,base64,tarfile,io,importlib.util
root=Path('/tmp/pattern-agent-human-live')
for package in ['playwright','playwright-core']:
 meta=json.load(urllib.request.urlopen('https://registry.npmjs.org/'+package+'/1.62.1',timeout=25))
 payload=urllib.request.urlopen(meta['dist']['tarball'],timeout=25).read()
 algorithm,digest=meta['dist']['integrity'].split('-',1)
 assert base64.b64encode(hashlib.new(algorithm,payload).digest()).decode()==digest
 target=root/'node_modules'/package
 target.mkdir(parents=True,exist_ok=True)
 with tarfile.open(fileobj=io.BytesIO(payload),mode='r:gz') as archive:
  for item in archive:
   relative=Path(item.name).relative_to('package')
   assert '..' not in relative.parts
   if item.isdir():(target/relative).mkdir(parents=True,exist_ok=True)
   elif item.isfile():
    (target/relative).parent.mkdir(parents=True,exist_ok=True)
    (target/relative).write_bytes(archive.extractfile(item).read())
   else:raise ValueError('Unexpected package entry')
 print(json.dumps({'package':package,'version':'1.62.1','integrity_verified':True}))
for filename,digest in [
 ('verify_human_studio.cjs','7d42262d09172a2e19ef0e3e843545736a54c7872258a4379e194dac8cc6aa46'),
 ('verify_human_studio_geometry.py','fb35d4371b15bfdbfea55f6a203708af893c1526700dc57f3c99e0def4026a35'),
 ('test_human_studio_geometry.py','d83c5192ef730a239639774b82b2e81d2747bf88ca9effdf5da0c972d0602b9c')]:
 url='https://raw.githubusercontent.com/liush2yuxjtu/pattern-agent/e19e2ea63436cc843a7ae121ec3685e1007bdd5c/scripts/'+filename
 payload=urllib.request.urlopen(url,timeout=25).read()
 assert hashlib.sha256(payload).hexdigest()==digest
 (root/filename).write_bytes(payload)
 print(json.dumps({'public_verifier':filename,'sha256_checked':True}))
print(json.dumps({'numpy_available':importlib.util.find_spec('numpy') is not None}))
PY
