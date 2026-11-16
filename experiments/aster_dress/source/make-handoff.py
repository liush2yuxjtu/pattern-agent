from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
root=Path('dist')
files=sorted(p for p in root.rglob('*') if p.is_file() and p.suffix!='.zip' and p.name!='index.html')
with ZipFile(root/'aster-handoff.zip','w',ZIP_DEFLATED) as z:
    for path in files:z.write(path,path.relative_to(root))
with ZipFile(root/'aster-handoff.zip') as z:
    assert z.testzip() is None
    assert 'aster-studio.html' in z.namelist()
    assert 'VERIFICATION.md' in z.namelist()
print(f'Handoff ZIP verified: {len(files)} files, {(root/"aster-handoff.zip").stat().st_size} bytes.')
