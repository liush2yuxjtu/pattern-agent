#!/usr/bin/env python3
"""Run the full synthetic sleeve experiment and fail closed on quality.

Execution completion and geometric quality are independent. A quality failure
still produces diagnostics, measured replay, and optional real Blender video.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
import importlib.util

ROOT=Path(__file__).resolve().parent


def summarize(rows, expected, negatives=None):
    frame_ids=[r.get('frame') for r in rows]
    complete=frame_ids==list(range(1,expected+1))
    negative_ok=bool(negatives and negatives.get('all_detected') and negatives.get('control_count',0)>=7)
    arm=bool(complete and negative_ok and all(r.get('arm_entry_pass') is True for r in rows))
    cloth=bool(arm and all(r.get('cloth_sim_pass') is True for r in rows))
    def maximum(key):
        values=[float(r[key]) for r in rows if r.get(key) is not None]
        return max(values) if values else None
    return {'schema_version':1,'scope':'new synthetic preassembled T-shirt fixture',
        'expected_frames':expected,'observed_frames':len(rows),'complete_frame_coverage':complete,
        'negative_controls_pass':negative_ok,'ARM_ENTRY_PASS':arm,'CLOTH_SIM_PASS':cloth,
        'PHYSICAL_FIT_PASS':None,'physical_fit_status':'NOT_RUN',
        'original_project_status':'BLOCKED_ORIGINAL_ARCHIVE_NOT_RECOVERED',
        'verdict':'SYNTHETIC_GEOMETRY_PASS' if cloth else 'SYNTHETIC_GEOMETRY_FAIL',
        'arm_entry_pass_frames':sum(r.get('arm_entry_pass') is True for r in rows),
        'cloth_sim_pass_frames':sum(r.get('cloth_sim_pass') is True for r in rows),
        'arm_entry_fail_frames':[r['frame'] for r in rows if r.get('arm_entry_pass') is not True],
        'cloth_sim_fail_frames':[r['frame'] for r in rows if r.get('cloth_sim_pass') is not True],
        'max_seam_gap_mm':maximum('seam_max_gap_mm'),
        'max_self_intersection_pairs':maximum('self_intersection_pairs'),
        'max_cloth_body_intersection_pairs':maximum('cloth_body_intersection_pairs'),
        'max_body_self_intersection_pairs':maximum('body_self_intersection_pairs'),
        'max_inside_sample_count':maximum('body_inside_sample_count'),
        'max_body_penetration_mm':maximum('body_penetration_max_mm'),
        'max_strain_p95_pct':maximum('strain_abs_p95_pct'),
        'max_local_strain_pct':maximum('strain_abs_max_pct'),
        'limits':['Synthetic, uncalibrated body and material. Original project is a separate gate.',
                  'Preassembled welded seams, not a simulated sewing process.',
                  'Saved-frame geometry; not a continuous-time collision certificate.',
                  'Strain is measured against the assembled mesh; it does not certify comfort.']}


def command(args,log,allowed=(0,)):
    with Path(log).open('w') as stream:
        process=subprocess.run([str(a) for a in args],stdout=stream,stderr=subprocess.STDOUT,cwd=ROOT)
    if process.returncode not in allowed:
        raise RuntimeError(f'Command exited {process.returncode}; see {log}')
    return process.returncode


def manifest(directory):
    directory=Path(directory)
    result={}
    for file in sorted(directory.rglob('*')):
        if (file.is_file() and file.name!='SHA256.json' and '__pycache__' not in file.parts
                and 'video-frames' not in file.parts and not file.name.endswith('.blend1')):
            result[str(file.relative_to(directory))]={'bytes':file.stat().st_size,
                     'sha256':hashlib.file_digest(file.open('rb'),'sha256').hexdigest()}
    (directory/'SHA256.json').write_text(json.dumps(result,indent=2))
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',required=True,help='New run directory, or existing run with --verify-existing')
    parser.add_argument('--builder',default='simulation/full_arm_scene.py')
    parser.add_argument('--frames',type=int,default=241)
    parser.add_argument('--verify-existing',action='store_true')
    parser.add_argument('--render-video',action='store_true')
    parser.add_argument('--blender',default='blender')
    parser.add_argument('--jobs',type=int,choices=[1,2],default=2,help='Independent geometry verifier processes')
    args=parser.parse_args()
    out=Path(args.out).resolve()
    started=time.time()
    if not args.verify_existing:
        if out.exists():raise FileExistsError('Use a new output directory; existing evidence is preserved')
        out.parent.mkdir(parents=True,exist_ok=True)
        log=out.with_suffix('.simulation.log')
        command([args.blender,'-b','-t','2','--python-exit-code','2','--python',ROOT/args.builder,'--',
                 '--out',out,'--frames',args.frames,'--no-render'],log)
    elif not (out/'frames').is_dir():raise FileNotFoundError('Existing run has no frames directory')
    verification=out/'verification';verification.mkdir(exist_ok=True)
    base=[args.blender,'-b','-t','2','--python-exit-code','2']
    if args.jobs==1:
        command([*base,'--python',ROOT/'verification/geometry.py','--','--frames',out/'frames',
                 '--topology',out/'topology.json','--out',verification],out/'verification.log',allowed=(0,2))
    else:
        middle=(args.frames+1)//2
        chunks=[('chunk-a',1,middle),('chunk-b',middle+1,args.frames)]
        def verify_chunk(item):
            name,start,end=item
            command([args.blender,'-b','-t','1','--python-exit-code','2','--python',ROOT/'verification/geometry.py',
                     '--','--frames',out/'frames','--topology',out/'topology.json','--out',verification/name,
                     '--start-frame',start,'--end-frame',end],out/(name+'.log'),allowed=(0,2))
            return verification/name/'verification.json'
        with ThreadPoolExecutor(max_workers=2) as executor:
            chunk_reports=list(executor.map(verify_chunk,chunks))
        command([sys.executable,ROOT/'verification/merge_chunks.py','--expected',args.frames,'--out',verification,
                 *chunk_reports],out/'verification.log')
    command([*base,'--python',ROOT/'verification/test_geometry.py','--','--frame',out/'frames/frame-0001.npz',
             '--topology',out/'topology.json','--out',verification/'real-negative-controls.json'],
             out/'negative-controls.log',allowed=(0,2))
    replay=out/'replay'
    command([*base,'--python',ROOT/'simulation/replay_and_render.py','--','--run',out,'--out',replay,
             '--stills',*(['--render'] if args.render_video else [])],out/'replay.log')
    command([*base,'--python',ROOT/'verification/verify_replay.py','--','--blend',replay/'measured-replay.blend',
             '--frames',out/'frames','--out',verification/'replay-check.json'],out/'replay-check.log')
    if args.render_video:
        command(['ffmpeg','-y','-framerate','24','-i',replay/'video-frames/%04d.png',
                 '-c:v','libx264','-crf','20','-pix_fmt','yuv420p','-movflags','+faststart',out/'full-motion.mp4'],out/'ffmpeg.log')
    report=json.loads((verification/'verification.json').read_text())
    controls=json.loads((verification/'real-negative-controls.json').read_text())
    status=summarize(report['frames'],args.frames,controls)
    replay_ok=json.loads((verification/'replay-check.json').read_text())
    status['replay_verification']=replay_ok
    status['execution_complete']=True
    status['elapsed_s']=time.time()-started
    (out/'status.json').write_text(json.dumps(status,indent=2))
    manifest(out)
    print(json.dumps({k:status[k] for k in ['verdict','execution_complete','ARM_ENTRY_PASS','CLOTH_SIM_PASS','physical_fit_status']}))
    return 0 if status['CLOTH_SIM_PASS'] else 2


if __name__=='__main__':
    try:sys.exit(main())
    except Exception as error:
        print(f'EXECUTION_ERROR: {error}',file=sys.stderr)
        sys.exit(3)
