#!/usr/bin/env python3
"""Functional negative controls against a frozen real product-case workspace.

Uses actual files and the actual page builder, mutating disposable copies only.
Consistent hashes do not excuse false model measurements or mismatched meshes.
"""
import argparse
from contextlib import contextmanager, redirect_stdout
import copy
import hashlib
import io
import json
from pathlib import Path
import re
import shutil
import tempfile
from PIL import Image
from build_product_case_review import build


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    path.write_text(json.dumps(value, indent=2))


@contextmanager
def restore(paths):
    saved = {path: path.read_bytes() for path in paths}
    try:
        yield
    finally:
        for path, data in saved.items():
            path.write_bytes(data)


def update_source_hashes(work):
    model = work/'model'
    metrics = read(model/'fit/metrics.json')
    metrics['protocol']['final_pose_state_sha256'] = digest(model/'final-state.json')
    metrics['protocol']['final_posed_obj_sha256'] = digest(model/'final-posed.obj')
    write(model/'fit/metrics.json', metrics)
    provenance = read(model/'render-provenance.json')
    provenance['final_state_sha256'] = digest(model/'final-state.json')
    provenance['final_posed_obj_sha256'] = digest(model/'final-posed.obj')
    write(model/'render-provenance.json', provenance)


def displaced_vertex(path):
    lines = path.read_text().splitlines()
    for i, line in enumerate(lines):
        if line.startswith('v '):
            values = list(map(float, line.split()[1:]))
            values[0] += 1
            lines[i] = 'v '+' '.join(map(str, values))
            break
    path.write_text('\n'.join(lines)+'\n')


def verify_native_sources(work):
    records = []
    for number in (1, 2):
        generation = work/f'iterations/generation-{number}'
        manifest = read(generation/'generation.json')
        assert manifest.get('collage_cropped') is False and manifest.get('upscaled') is False, 'Native generation provenance flags missing'
        outputs = manifest.get('native_tool_outputs', manifest.get('outputs'))
        assert isinstance(outputs, list) and len(outputs) == 6, 'Six native tool-output records required'
        assert len({o.get('original_tool_path', o.get('path')) for o in outputs}) == 6, 'Tool outputs must be six independent source files'
        assert {o['view'] for o in outputs} == {'front','side','back','closeup','pose','depth'}
        for o in outputs:
            # Absolute local originals are retained by Image Gen outside the repo.
            native = Path(o.get('original_tool_path', o.get('path')))
            image = generation/(o['view']+'.png')
            assert native.is_file(), 'Retained native tool output not available: '+str(native)
            assert digest(native) == digest(image) == o['sha256'], 'Image differs from retained native tool bytes'
            with Image.open(native) as src:
                assert min(src.size) > 1000, 'Native image below declared high resolution'
                declared = o.get('native_pixels', o.get('pixels'))
                assert list(src.size) == declared, 'Native pixel declaration mismatch'
            records.append(dict(generation=number, view=o['view'], sha256=digest(native), pixels=declared, native_tool_source=str(native)))
    return records


def run(workspace, output):
    output.mkdir(parents=True, exist_ok=True)
    native = verify_native_sources(workspace)
    controls = []
    # Only this task-owned disposable directory is removed on exit.
    with tempfile.TemporaryDirectory(prefix='product-integrity-', dir=output) as temporary:
        root = Path(temporary)
        work = root/'case'
        for name in ('reference', 'iterations', 'case'):
            shutil.copytree(workspace/name, work/name)
        shutil.copytree(workspace/'model', work/'model', ignore=shutil.ignore_patterns('generation-1','fixed-M-baseline','iteration-1','view-specific','__pycache__'))
        site = root/'site'
        def invoke():
            with redirect_stdout(io.StringIO()):
                build(work.resolve(), site.resolve(), True)
        invoke()
        controls.append(dict(name='actual frozen model and six native images', expected='PASS', observed='PASS'))
        model = work/'model'
        state_path, metrics_path, provenance_path = model/'final-state.json', model/'fit/metrics.json', model/'render-provenance.json'
        def reject(name, paths, mutate, pattern):
            with restore(paths):
                mutate()
                try:
                    invoke()
                except (ValueError, AssertionError, KeyError, TypeError) as error:
                    message = str(error)
                    assert re.search(pattern, message, re.I), (name, 'unexpected rejection boundary', message)
                    controls.append(dict(name=name, expected='REJECT', observed='REJECT', rejection=message))
                else:
                    raise AssertionError(name+' was accepted by actual builder')
        front = work/'iterations/generation-2/front.png'
        reject('v1 front substituted without refitting', [front], lambda: shutil.copyfile(work/'iterations/generation-1/front.png', front), r'stale fit|generation|native|hash|provenance')
        closeup = work/'iterations/generation-2/closeup.png'
        generation_path = work/'iterations/generation-2/generation.json'
        def cropped_closeup():
            with Image.open(closeup) as image:
                cropped = image.crop((0, 0, image.width//2, image.height//2))
            cropped.save(closeup)
            generation = read(generation_path)
            generation['paths']['closeup']['sha256'] = digest(closeup)
            generation['paths']['closeup']['pixels'] = list(cropped.size)
            write(generation_path, generation)
        reject('cropped closeup falsely redeclared as native image', [closeup,generation_path], cropped_closeup, r'native|generation|pixels|resolution|hash|provenance')
        def false_measurement():
            state = read(state_path)
            state['measuredNeutral']['bust'] += 1
            state['maximumTargetErrorCm'] = max(abs(state['measuredNeutral'][k]-v) for k,v in state['dimensions'].items())
            write(state_path, state)
            update_source_hashes(work)
        reject('false saved measurement with updated hashes', [state_path,metrics_path,provenance_path], false_measurement, r'measuredNeutral|reconstruct')
        def wrong_asset():
            state = read(state_path);state['asset'] = '0'*64;write(state_path,state);update_source_hashes(work)
        reject('false asset with updated hashes', [state_path,metrics_path,provenance_path], wrong_asset, r'asset|fingerprint')
        neutral = model/'final-neutral.obj'
        reject('neutral mesh vertex shifted 1cm', [neutral], lambda: displaced_vertex(neutral), r'neutral OBJ|morph reconstruction')
        posed = model/'final-posed.obj'
        def wrong_posed():
            displaced_vertex(posed);update_source_hashes(work)
        reject('posed render mesh shifted 1cm with updated hashes', [posed,metrics_path,provenance_path], wrong_posed, r'skinned GLB|posed OBJ')
        render = model/'final-renders/front.png'
        reject('render bytes replaced without rerender provenance', [render], lambda: shutil.copyfile(work/'iterations/generation-1/front.png',render), r'changed render|render artifact')
        def wrong_angle():
            state=read(state_path);state['poseDegrees']['lowerarm01.L'][0]+=1;write(state_path,state);update_source_hashes(work)
        reject('state joint angle changed without actual rig export', [state_path,metrics_path,provenance_path], wrong_angle, r'bone transforms|joint angles')
        # Verify the clean source still builds after every negative mutation.
        invoke()
        controls.append(dict(name='restored actual candidate rebuild',expected='PASS',observed='PASS'))
    report = dict(verdict='PASS',scope='Actual builder stale-generation and independent model-integrity controls; no real-person accuracy or cloth physics claim',source_workspace=str(workspace),native_source_checks=native,controls=controls)
    (output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(verdict='PASS',controls=len(controls),native_images=len(native)),ensure_ascii=False))
    return report


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace',type=Path,default=Path('work/product-red-pointelle-20261117'))
    parser.add_argument('--output',type=Path,default=Path('work/product-red-pointelle-20261117/integrity-verify'))
    args=parser.parse_args()
    run(args.workspace.resolve(),args.output.resolve())
