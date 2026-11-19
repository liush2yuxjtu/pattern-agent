"""Package the reviewed HTML and per-feature sources, without runtime dependencies."""
from pathlib import Path
import json,hashlib,shutil,zipfile
root=Path(__file__).resolve().parents[1];output=root.parent/'outputs';output.mkdir(exist_ok=True)
html=root/'dist/garment-gpu-studio.html';shutil.copy2(html,output/html.name)
shutil.copy2(root/'dist/verify-garment.js',output/'verify-garment.js')
report=root/'VERIFICATION.md'
if report.exists():shutil.copy2(report,output/'garment-gpu-studio-verification.md')
paths=[]
for file in root.rglob('*'):
    rel=file.relative_to(root)
    if not file.is_file() or file.is_symlink():continue
    if any(p in {'node_modules','__pycache__','.git'} for p in rel.parts):continue
    if file.suffix.lower() in {'.png','.jpg','.jpeg','.webp','.pyc'}:continue
    if file.name in {'native-server.log','unit-console.txt','browser-console.txt'}:continue
    paths.append(file)
with zipfile.ZipFile(output/'garment-gpu-studio-source.zip','w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for file in sorted(paths):z.write(file,'garment-gpu-studio/'+file.relative_to(root).as_posix())
manifest={p.name:{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in output.iterdir() if p.is_file()}
(output/'delivery-manifest.json').write_text(json.dumps(manifest,indent=2));print(json.dumps(manifest,indent=2))
