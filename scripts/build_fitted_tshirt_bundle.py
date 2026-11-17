#!/usr/bin/env python3
"""Package the fitted T-shirt source and final artifacts deterministically."""
from pathlib import Path
import hashlib,json,zipfile
ROOT=Path(__file__).resolve().parents[1]
def build():
    exp=ROOT/'experiments/fitted_tshirt';web=ROOT/'web/fitted-tshirt'
    paths=sorted(p for p in exp.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc')
    paths+=sorted(p for p in (web/'assets').iterdir() if p.is_file())
    paths+=[web/'index.html',web/'style.css',web/'viewer.js',ROOT/'web/assets/site.css',ROOT/'web/assets/favicon.svg',ROOT/'scripts/build_fitted_tshirt_bundle.py',ROOT/'scripts/verify_fitted_tshirt.py',ROOT/'scripts/verify_pages.py']
    destination=web/'downloads/fitted-tshirt-complete.zip';destination.parent.mkdir(exist_ok=True)
    manifest={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    with zipfile.ZipFile(destination,'w',compression=zipfile.ZIP_DEFLATED) as z:
        for p in paths:
            info=zipfile.ZipInfo(str(p.relative_to(ROOT)),(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o644<<16;z.writestr(info,p.read_bytes())
        z.writestr('manifest.json',json.dumps(manifest,ensure_ascii=False,indent=2))
    (web/'downloads/manifest.json').write_text(json.dumps({'scope':'source and visual artifacts only','physical_fit':'NOT_RUN','files':manifest,'archive_sha256':hashlib.sha256(destination.read_bytes()).hexdigest()},ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'archive':str(destination.relative_to(ROOT)),'bytes':destination.stat().st_size,'files':len(paths)}))
if __name__=='__main__':build()
