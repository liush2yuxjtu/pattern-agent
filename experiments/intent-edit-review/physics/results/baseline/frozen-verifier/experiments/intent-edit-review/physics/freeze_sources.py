#!/usr/bin/env python3
"""Freeze exact local source bytes before starting an immutable trial."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def freeze(directory):
    data=json.loads((directory/'input.json').read_bytes());records=dict(data['source_hashes'])
    extra=[HERE/name for name in ['run_native.mjs','create-self-contact.mjs','mesh-contact.mjs','swept-edge.mjs','swept-vertex.mjs','self_step_guard.mjs','verify_preparation.py']]
    extra+=[ROOT/'experiments/freesewing_cloth_lab/source/self-contact.js']
    for path in extra:records[str(path.relative_to(ROOT))]=hashlib.sha256(path.read_bytes()).hexdigest()
    target=directory/'frozen-source'
    for name,digest in records.items():
        path=ROOT/name
        if hashlib.sha256(path.read_bytes()).hexdigest()!=digest:raise ValueError('Prepared source changed: '+name)
        destination=target/name;destination.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,destination)
    (target/'manifest.json').write_text(json.dumps(records,indent=2)+'\n')
    print(json.dumps({'frozen_source_files':len(records),'directory':str(target)}))
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('directory',type=Path);freeze(p.parse_args().directory.resolve())
