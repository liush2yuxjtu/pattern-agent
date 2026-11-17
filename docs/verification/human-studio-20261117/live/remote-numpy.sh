set -e
python3 -m pip install --disable-pip-version-check --no-cache-dir --only-binary=:all: --no-deps --target /tmp/pattern-agent-human-live/deps numpy > /tmp/pattern-agent-human-live/numpy-install.log 2>&1
PYTHONPATH=/tmp/pattern-agent-human-live/deps python3 - <<'PY'
import numpy,json
print(json.dumps({'numpy_version':numpy.__version__}))
PY
