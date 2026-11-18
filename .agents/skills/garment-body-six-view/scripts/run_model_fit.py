#!/usr/bin/env python3
"""Execute source-configured anatomical body/grip fitting, then measure real mesh.

No Image Gen calls or simulated receipts. Solver code is a fixed repository
runtime, inputs are case-local files, and the output is always a new directory.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def run(case_path, repo_root, output):
    case_path = case_path.resolve()
    repo_root = repo_root.resolve()
    output = output.resolve()
    case = json.loads(case_path.read_text())
    if case.get('schema') != 'garment-body-fit-case-v1':
        raise ValueError('Expected garment-body-fit-case-v1')
    allowed = {'schema', 'input_state', 'input_camera', 'source_photo', 'source_mask', 'region_protocol', 'grip_case', 'asset_json', 'body', 'pose_guide', 'pose_markers'}
    if set(case) - allowed:
        raise ValueError('Unknown case fields: ' + ', '.join(sorted(set(case) - allowed)))
    names = ['input_state', 'input_camera', 'source_photo', 'source_mask', 'region_protocol', 'grip_case', 'asset_json']
    inputs = {}
    for name in names:
        path = (case_path.parent / case[name]).resolve()
        if not path.is_file():
            raise ValueError(f'Missing real input {name}: {path}')
        inputs[name] = path
    for name in ['pose_guide', 'pose_markers']:
        if case.get(name):
            path = (case_path.parent / case[name]).resolve()
            if not path.is_file():
                raise ValueError('Missing real input ' + name)
            inputs[name] = path
    if 'pose_markers' in inputs and 'pose_guide' not in inputs:
        raise ValueError('pose_markers requires pose_guide')
    runtime = repo_root / 'tools/human_fit/pose_guided'
    body_entry = runtime / 'refine_body_envelope.py'
    grip_entry = runtime / 'fit_grip.py'
    exporter = Path(__file__).resolve().with_name('export_body_measurements.py')
    registrar = exporter.with_name('register_pose_guide.py')
    required = [registrar, body_entry, grip_entry, exporter, runtime / 'runtime.py',
                runtime / 'calibrate-worker.mjs', runtime / 'render_mesh.py',
                repo_root / 'web/human-studio/body-engine.js']
    for path in required:
        if not path.is_file():
            raise ValueError(f'Required actual runtime missing: {path}')
    if output.exists():
        raise ValueError('Output already exists; choose a new candidate directory, never overwrite history')
    if output == case_path.parent or output in case_path.parents:
        raise ValueError('Output cannot replace the input directory')
    actual_asset = repo_root / 'web/human-studio/assets/human.json'
    if digest(inputs['asset_json']) != digest(actual_asset):
        raise ValueError('Case asset differs from the actual fixed repository runtime asset')
    grip_case = json.loads(inputs['grip_case'].read_text())
    if grip_case.get('schema') != 'pose-grip-case-v1' or grip_case.get('asset_sha256') != digest(actual_asset):
        raise ValueError('Grip case must declare pose-grip-case-v1 and exact runtime asset SHA')
    if grip_case.get('containment_mask'):
        mask = (inputs['grip_case'].parent / grip_case['containment_mask']).resolve()
        if not mask.is_file():
            raise ValueError('Grip containment mask does not exist')
        inputs['grip_containment_mask'] = mask
    body_options = case.get('body', {})
    if not isinstance(body_options, dict):
        raise ValueError('body must be an object')
    if 'stages' in body_options:
        if set(body_options) != {'stages'}:
            raise ValueError('body.stages cannot mix with single-stage settings')
        stages = body_options['stages']
    else:
        stages = [body_options]
    if not isinstance(stages, list) or not stages or len(stages) > 20:
        raise ValueError('body.stages must contain1..20 stage objects')
    for options in stages:
        if not isinstance(options, dict) or set(options) - {'steps', 'camera_fit', 'standing_prior'}:
            raise ValueError('Each body stage accepts only steps, camera_fit, standing_prior')
        steps = options.get('steps', 100)
        if type(steps) is not int or not 1 <= steps <= 10000:
            raise ValueError('body stage steps must be integer1..10000')
        for key in ['camera_fit', 'standing_prior']:
            if key in options and type(options[key]) is not bool:
                raise ValueError('body stage ' + key + ' must be boolean')
    output.mkdir(parents=True)
    source_commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo_root, text=True).strip()
    manifest = dict(schema='garment-body-fit-execution-v1', source_commit=source_commit,
                    case=dict(path=str(case_path), sha256=digest(case_path)),
                    inputs={k: dict(path=str(v), sha256=digest(v)) for k, v in inputs.items()},
                    runtime={str(p): digest(p) for p in required}, stages=[],
                    generation='NOT_RUN: executor must separately call real Image Gen using frozen final guides',
                    person_accuracy_verified=False)
    write(output / 'execution.json', manifest)

    def execute(name, argv, expected):
        result = subprocess.run(argv, cwd=repo_root, text=True, capture_output=True)
        (output / (name + '.stdout.log')).write_text(result.stdout)
        (output / (name + '.stderr.log')).write_text(result.stderr)
        stage = dict(name=name, argv=argv, returncode=result.returncode)
        manifest['stages'].append(stage)
        write(output / 'execution.json', manifest)
        result.check_returncode()
        for p in expected:
            if not p.is_file():
                raise ValueError(f'{name} did not create real required output: {p}')
        stage['outputs'] = {str(p.relative_to(output)): digest(p) for p in expected}
        write(output / 'execution.json', manifest)

    if 'pose_guide' in inputs:
        registration_dir = output / 'guide-registration'
        argv = [sys.executable, str(registrar), '--reference', str(inputs['source_photo']),
                '--guide', str(inputs['pose_guide']), '--out', str(registration_dir)]
        if 'pose_markers' in inputs:
            argv += ['--markers', str(inputs['pose_markers'])]
        execute('register-pose-guide', argv, [registration_dir / 'registration.json', registration_dir / 'guide-registered.png'])
    state_path, camera_path = inputs['input_state'], inputs['input_camera']
    for number, options in enumerate(stages, 1):
        body_dir = output / 'body' / ('stage-' + str(number))
        argv = [sys.executable, str(body_entry), '--state', str(state_path),
                '--camera', str(camera_path), '--mask', str(inputs['source_mask']),
                '--photo', str(inputs['source_photo']), '--acceptance', str(inputs['region_protocol']),
                '--out', str(body_dir), '--steps', str(options.get('steps', 100))]
        if options.get('camera_fit', False):
            argv.append('--camera-fit')
        if options.get('standing_prior', False):
            argv.append('--standing-prior')
        execute('body-fit-' + str(number), argv, [body_dir / 'final-state.json', body_dir / 'camera.json'])
        state_path, camera_path = body_dir / 'final-state.json', body_dir / 'camera.json'
    final = output / 'final'
    execute('grip-fit', [sys.executable, str(grip_entry), '--case', str(inputs['grip_case']),
                        '--out', str(final), '--initial-state', str(state_path),
                        '--camera', str(camera_path)],
            [final / 'final-state.json', final / 'camera.json', final / 'neutral.obj', final / 'posed.obj',
             final / 'provenance.json', final / 'diagnostics.json'])
    grip_provenance = json.loads((final / 'provenance.json').read_text())
    frame = grip_provenance.get('frame', {})
    if frame.get('units') != 'cm' or frame.get('fast_fk_and_lbs_apply_same_floor') is not True:
        raise ValueError('Final solver must record shared centimetre FK/LBS frame and actual floor')
    manifest['coordinate_frame'] = frame
    manifest['grip_provenance'] = grip_provenance
    write(output / 'execution.json', manifest)
    execute('measure-final-mesh', [sys.executable, str(exporter), '--state', str(final / 'final-state.json'),
                                  '--asset-json', str(inputs['asset_json']), '--neutral-mesh', str(final / 'neutral.obj'),
                                  '--posed-mesh', str(final / 'posed.obj'), '--out', str(output / 'measurements.model.json'),
                                  '--csv', str(output / 'measurements.model.csv')],
            [output / 'measurements.model.json', output / 'measurements.model.csv'])
    for name, path in inputs.items():
        if digest(path) != manifest['inputs'][name]['sha256']:
            raise ValueError(f'Input changed while fitting: {name}')
    for path in required:
        if digest(path) != manifest['runtime'][str(path)]:
            raise ValueError('Runtime changed during fitting: ' + str(path))
    manifest['completed'] = True
    manifest['verdict'] = 'EXECUTED; independent visual/geometry acceptance required, not automatic PASS'
    write(output / 'execution.json', manifest)
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', type=Path, required=True)
    parser.add_argument('--repo-root', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    print(run(args.case, args.repo_root, args.out))
