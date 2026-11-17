set -e
mkdir -p /tmp/pattern-agent-prototype-331a27d/scripts /tmp/pattern-agent-prototype-331a27d/evidence
python3 -m pip install --no-cache-dir --disable-pip-version-check --target /tmp/pattern-agent-prototype-331a27d/deps 'playwright==1.62.0' Pillow > /tmp/pattern-agent-prototype-331a27d/install.log 2>&1
python3 - <<'PY'
import hashlib,json,urllib.request
from pathlib import Path
root=Path('/tmp/pattern-agent-prototype-331a27d')
sha='331a27daf46f5debf3745834b478641f96ace06a'
checks={'verify_prototype_package.py':'9869a8696c70db0a0237dff37a0321aaa052c3959c9973ebe6dd6d5140620fb2','verify_pages.py':'31d73128e61b35bc0bbc5e4a22d581196f48a6df669f9e097d5e397ef569bc42','verify_fitted_tshirt.py':'344fda87a6ffd2c3322890024ebf19f906deba4d3ca404bc524427047cd1880c'}
for name,digest in checks.items():
 url=f'https://raw.githubusercontent.com/liush2yuxjtu/pattern-agent/{sha}/scripts/{name}'
 with urllib.request.urlopen(url,timeout=20) as response: payload=response.read()
 assert hashlib.sha256(payload).hexdigest()==digest,name
 (root/'scripts'/name).write_bytes(payload)
with urllib.request.urlopen('https://liush2yuxjtu.github.io/pattern-agent/build.json',timeout=20) as response:
 metadata=json.load(response)
assert metadata['commit']==sha,metadata['commit']
(root/'evidence'/'public-source-identity.json').write_text(json.dumps({'commit':sha,'verified_script_sha256':checks,'site_source_sha256':metadata['source_sha256']},indent=2)+'\n')
print(json.dumps({'public_pinned_scripts':'PASS','live_commit':metadata['commit'],'source_sha256':metadata['source_sha256']},indent=2))
PY
