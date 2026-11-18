PYTHONPATH=services/dxf-preview python - <<'PY'
import io, json, subprocess, sys, tempfile, zipfile
from pathlib import Path
from converter.core import convert_dxf
from app import bundle

source_path = Path('services/dxf-preview/public/sample.dxf').resolve()
units = 'mm'
source = source_path.read_bytes()
result = convert_dxf(source, units=units, profile='fitted-tshirt-v1')
archive = bundle(result, source)
Path('work').mkdir(exist_ok=True)
out = Path(tempfile.mkdtemp(prefix='sewn-preview-', dir='work')).resolve()
(out / 'preview.zip').write_bytes(archive)
with zipfile.ZipFile(io.BytesIO(archive)) as z:
    if z.testzip() is not None:
        raise RuntimeError('离线包完整性检查失败')
    z.extractall(out / 'files')
subprocess.run([
    sys.executable, 'services/dxf-preview/verify_connections.py',
    '--dxf', str(source_path), '--glb', str(out / 'files/model.glb'),
    '--units', units, '--out', str(out / 'independent.json'),
], check=True)
print(json.dumps({
    'output': str(out), 'preview': str(out / 'files/preview.html'),
    'model': str(out / 'files/model.glb'),
    'source_sha256': result.report['input_sha256'],
    'model_sha256': result.report['output_sha256'],
    'mode': result.report['mode'], 'physical_fit': 'NOT_RUN',
}, ensure_ascii=False))
PY
