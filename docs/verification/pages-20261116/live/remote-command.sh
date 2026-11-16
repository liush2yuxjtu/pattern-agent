set -e
mkdir -p /tmp/pattern-agent-browser/scripts /tmp/pattern-agent-browser/evidence
python3 -m pip install --no-cache-dir --disable-pip-version-check --target /tmp/pattern-agent-browser/deps 'playwright==1.62.0' > /tmp/pattern-agent-browser/install.log 2>&1
python3 - <<'PY'
import hashlib,urllib.request
from pathlib import Path
url='https://raw.githubusercontent.com/liush2yuxjtu/pattern-agent/2a254fa7899bce5302aebbae87172ee29d837578/scripts/verify_pages.py'
with urllib.request.urlopen(url,timeout=20) as response: payload=response.read()
assert hashlib.sha256(payload).hexdigest()=='31d73128e61b35bc0bbc5e4a22d581196f48a6df669f9e097d5e397ef569bc42'
Path('/tmp/pattern-agent-browser/scripts/verify_pages.py').write_bytes(payload)
print('Public pinned verifier source hash checked')
PY
PYTHONPATH=/tmp/pattern-agent-browser/deps python3 /tmp/pattern-agent-browser/scripts/verify_pages.py --base-url https://liush2yuxjtu.github.io/pattern-agent/ --expected-commit 2a254fa7899bce5302aebbae87172ee29d837578 --browser /usr/bin/google-chrome --output /tmp/pattern-agent-browser/evidence
