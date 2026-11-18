#!/usr/bin/env python3
"""Reopen recorded states in fresh native/BVH processes and compare the next step.

This invokes the real runtime, never an imported Python model of the solver.
Positions, Verlet history, constitutive fields, contact flags and clocks must all
match the saved next frame exactly. A replay viewer's array seek is separate.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
def sha(raw): return hashlib.sha256(raw).hexdigest()

def run(directory, indices):
    directory = directory.resolve()
    input_raw = (directory/'input.json').read_bytes()
    recording_raw = (directory/'trajectory.json').read_bytes()
    recording = json.loads(recording_raw)
    failures = []; rows = []
    for index in indices:
        if not 0 <= index < len(recording['frames'])-1:
            failures.append(f'No saved successor for frame {index}')
            continue
        with tempfile.TemporaryDirectory(dir=directory) as tmp:
            request = Path(tmp)/'request.json'; output = Path(tmp)/'output.json'
            request.write_text(json.dumps({'frame':recording['frames'][index]}))
            result = subprocess.run(['node',str(HERE/'run_native.mjs'),str(directory),'--resume',str(request),str(output)],
                                    capture_output=True,text=True)
            if result.returncode:
                failures.append(f'Frame {index}: native resume exited {result.returncode}: {result.stderr[-1000:]}')
                continue
            actual = json.loads(output.read_bytes()); expected = recording['frames'][index+1]
            matches = {key:actual[key] == expected[key]
                       for key in ['positions','previous','fields','contacts','step','time']}
            rows.append({'restored_frame':index, 'next_frame':index+1, 'exact':matches})
            if not all(matches.values()): failures.append(f'Frame {index}: saved-state continuation differs')
    report = {'verdict':'FAIL' if failures else 'PASS','input_sha256':sha(input_raw),
              'recording_sha256':sha(recording_raw),'wasm_sha256':sha((directory/'solver.wasm').read_bytes()),
              'runtime_sha256':sha((HERE/'run_native.mjs').read_bytes()),'checks':rows,'failures':failures,
              'scope':'Fresh native WASM and contact BVH next-step continuation; no garment/fit acceptance claim.'}
    (directory/'resume-independent.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    return not failures

if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('directory',type=Path)
    p.add_argument('--frames',default='0,30,59');args=p.parse_args()
    raise SystemExit(0 if run(args.directory,[int(v) for v in args.frames.split(',')]) else 1)
