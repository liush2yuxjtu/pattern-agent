set -e
python3 - <<'PY'
from pathlib import Path
import urllib.request,json,hashlib
root=Path('/tmp/pattern-agent-human-live')
base='https://liush2yuxjtu.github.io/pattern-agent/'
build=json.load(urllib.request.urlopen(base+'build.json',timeout=25))
assert build['commit']=='e19e2ea63436cc843a7ae121ec3685e1007bdd5c'
for name in ['index.html','app.js','body-engine.js','style.css','assets/human.json','vendor/three.module.js','vendor/three.core.js']:
 key='human-studio/'+name
 data=urllib.request.urlopen(base+key,timeout=25).read()
 assert hashlib.sha256(data).hexdigest()==build['files'][key]
 if name=='assets/human.json':(root/'human.json').write_bytes(data)
print(json.dumps({'deployed_commit':build['commit'],'source_sha256':build['source_sha256'],'primary_asset_hashes_verified':7}))
PY
NODE_PATH=/tmp/pattern-agent-human-live/node_modules CHROMIUM_BIN=/usr/bin/google-chrome node /tmp/pattern-agent-human-live/verify_human_studio.cjs --url https://liush2yuxjtu.github.io/pattern-agent/human-studio/ --output /tmp/pattern-agent-human-live/evidence --expected-commit e19e2ea63436cc843a7ae121ec3685e1007bdd5c
PYTHONPATH=/tmp/pattern-agent-human-live/deps python3 /tmp/pattern-agent-human-live/verify_human_studio_geometry.py --output /tmp/pattern-agent-human-live/evidence --asset /tmp/pattern-agent-human-live/human.json
PYTHONPATH=/tmp/pattern-agent-human-live/deps python3 /tmp/pattern-agent-human-live/test_human_studio_geometry.py --fixture /tmp/pattern-agent-human-live/evidence --asset /tmp/pattern-agent-human-live/human.json
python3 - <<'PY'
from pathlib import Path
import zipfile,hashlib,json
root=Path('/tmp/pattern-agent-human-live')
files=['report.json','independent-geometry.json','negative-controls.json','desktop.png','body-adjusted.png','pose-adjusted.png','seated.png','mobile.png','human-model.json','human-posed-cm.obj','human-rigged.glb','human-view-2x.png','export-geometry.json']
with zipfile.ZipFile(root/'evidence.zip','w',zipfile.ZIP_DEFLATED) as z:
 for name in files:z.write(root/'evidence'/name,name)
data=(root/'evidence.zip').read_bytes()
print(json.dumps({'archive_bytes':len(data),'archive_sha256':hashlib.sha256(data).hexdigest(),'files':files}))
PY
