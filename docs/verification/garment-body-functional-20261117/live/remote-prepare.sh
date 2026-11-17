set -e
mkdir -p /tmp/pattern-agent-functional-live
python3 - <<'PY'
from pathlib import Path
import urllib.request,json,hashlib,base64,tarfile,io
root=Path('/tmp/pattern-agent-functional-live')
version='1.62.1'
for package in ['playwright','playwright-core']:
    meta=json.load(urllib.request.urlopen('https://registry.npmjs.org/'+package+'/'+version,timeout=30))
    data=urllib.request.urlopen(meta['dist']['tarball'],timeout=30).read()
    algorithm,expected=meta['dist']['integrity'].split('-',1)
    assert base64.b64encode(hashlib.new(algorithm,data).digest()).decode()==expected
    destination=root/'node_modules'/package
    destination.mkdir(parents=True,exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(data),mode='r:gz') as archive:
        for item in archive:
            relative=Path(item.name).relative_to('package')
            assert '..' not in relative.parts
            target=destination/relative
            if item.isdir():target.mkdir(parents=True,exist_ok=True)
            elif item.isfile():
                target.parent.mkdir(parents=True,exist_ok=True)
                target.write_bytes(archive.extractfile(item).read())
            else:raise ValueError('Unexpected archive entry type')
    print(json.dumps({'package':package,'version':version,'integrity_verified':True}))
for path,digest in [
 ('tools/skill_evals/verify_functional_review.cjs','fe594db629851ae9dfe12ec6bf8f1ae764cbc8f8fc46cde6850d6bc2c4bec5d1'),
 ('tools/skill_evals/verify_functional_publish.py','e26398a0c3e355c12651e3d05fb23eafebd559beaba06a88f2ea8926fb1dcca4')]:
    url='https://raw.githubusercontent.com/liush2yuxjtu/pattern-agent/a5f7d073499eba2115da10cdfc653314d8d1cff0/'+path
    data=urllib.request.urlopen(url,timeout=30).read()
    assert hashlib.sha256(data).hexdigest()==digest
    (root/Path(path).name).write_bytes(data)
    print(json.dumps({'public_pinned_source':path,'sha256_verified':digest}))
PY
NODE_PATH=/tmp/pattern-agent-functional-live/node_modules node -p "require('playwright/package.json').version"
