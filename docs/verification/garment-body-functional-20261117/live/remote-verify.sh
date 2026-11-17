set -e
NODE_PATH=/tmp/pattern-agent-functional-live/node_modules CHROMIUM_BIN=/usr/bin/google-chrome node /tmp/pattern-agent-functional-live/verify_functional_review.cjs --url https://liush2yuxjtu.github.io/pattern-agent/garment-body/eval.html --out /tmp/pattern-agent-functional-live/evidence/browser --expected-runs 6
python3 /tmp/pattern-agent-functional-live/verify_functional_publish.py --base-url https://liush2yuxjtu.github.io/pattern-agent/ --expected-commit a5f7d073499eba2115da10cdfc653314d8d1cff0 --out /tmp/pattern-agent-functional-live/evidence/assets
python3 - <<'PY'
from pathlib import Path
import zipfile,hashlib,json
root=Path('/tmp/pattern-agent-functional-live')
files=['browser/report.json','browser/desktop.png','browser/benchmark.png','browser/mobile.png','browser/feedback-fixture.json','assets/asset-readback.json']
with zipfile.ZipFile(root/'evidence.zip','w',zipfile.ZIP_DEFLATED) as z:
 for name in files:z.write(root/'evidence'/name,name)
data=(root/'evidence.zip').read_bytes()
print(json.dumps({'archive_bytes':len(data),'archive_sha256':hashlib.sha256(data).hexdigest(),'files':files}))
PY
