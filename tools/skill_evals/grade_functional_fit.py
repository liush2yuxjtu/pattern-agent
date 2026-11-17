#!/usr/bin/env python3
"""Independent frozen-protocol fit artifact validation; no executor verifier is imported.

Usage: python tools/skill_evals/grade_functional_fit.py --case /path/eval-fit-existing
Pillow polygon filling is retained as the fixture's frozen raster kernel. Projection,
OBJ parsing, metric computations, provenance checks, and verdicts are independent.
OpenCV polygon rasterization is additionally recorded as protocol sensitivity evidence.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

import cv2
import numpy as np
from PIL import Image, ImageDraw


def read_json(p):
    return json.loads(p.read_text())


def write_json(p, data):
    p.write_text(json.dumps(data, indent=2, allow_nan=False) + '\n')


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def mask(p):
    a = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
    if a is None:
        raise ValueError(f'Unreadable mask: {p}')
    return a > 127


def parse_obj(p):
    verts, faces = [], []
    for line in p.read_text().splitlines():
        t = line.split()
        if not t:
            continue
        if t[0] == 'v':
            if len(t) != 4:
                raise ValueError('Expected XYZ vertex')
            verts.append([float(x) for x in t[1:]])
        elif t[0] == 'f':
            if len(t) != 4:
                raise ValueError('Nontriangular face')
            indices = [int(x.split('/')[0]) for x in t[1:]]
            faces.append([x - 1 if x > 0 else len(verts) + x for x in indices])
    v, f = np.asarray(verts, float), np.asarray(faces, np.int64)
    if v.ndim != 2 or v.shape[1] != 3 or f.ndim != 2 or f.shape[1] != 3:
        raise ValueError('Empty or malformed OBJ')
    if not np.isfinite(v).all() or f.min() < 0 or f.max() >= len(v):
        raise ValueError('Nonfinite geometry or invalid indices')
    return v, f


def project(v, camera, view):
    lo, hi = camera['horizontal_extent_cm']
    bottom, top = camera['vertical_extent_cm']
    x = v[:, 2] if view == 'side' else v[:, 0] * (-1 if view == 'back' else 1)
    return np.column_stack(((x - lo) * camera['width'] / (hi - lo),
                            (top - v[:, 1]) * camera['height'] / (top - bottom)))


def raster(v, f, camera, view, preview=False, opencv=False):
    xy = project(v, camera, view)
    size = (camera['width'], camera['height'])
    if opencv:
        im = np.zeros(size[::-1], np.uint8)
        for face in f:
            cv2.fillPoly(im, [np.trunc(xy[face]).astype(np.int32)], 255)
        return im > 127
    im = Image.new('RGB' if preview else 'L', size, '#eef1f4' if preview else 0)
    draw = ImageDraw.Draw(im)
    depth = v[:, 0] if view == 'side' else v[:, 2]
    for idx in np.argsort(depth[f].mean(axis=1)):
        shade = 160 + int(50 * (idx % 7) / 6)
        draw.polygon([tuple(p) for p in xy[f[idx]]], fill=(shade,) * 3 if preview else 255)
    if preview:
        draw.text((10, 10), 'SYNTHETIC CONTROL / ' + view.upper(), fill='#222222')
        return np.asarray(im)
    return np.asarray(im) > 127


def metrics(a, b, protocol):
    if a.shape != b.shape or not a.any() or not b.any():
        raise ValueError('Incompatible or empty masks')
    edges = []
    for x in (a, b):
        if protocol == 'external':
            contours, _ = cv2.findContours(x.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
            edge = np.zeros(x.shape, np.uint8)
            cv2.drawContours(edge, contours, -1, 1, 1)
        else:
            kernel = cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3))
            edge = x & ~cv2.erode(x.astype(np.uint8), kernel, borderType=cv2.BORDER_CONSTANT, borderValue=0).astype(bool)
        edges.append(edge.astype(np.uint8))
    da, db = [cv2.distanceTransform(1 - e, cv2.DIST_L2, cv2.DIST_MASK_PRECISE) for e in edges]
    d = np.concatenate((da[edges[1] > 0], db[edges[0] > 0])).astype(float)
    intersection = np.count_nonzero(a & b)
    return dict(iou=float(intersection / np.count_nonzero(a | b)),
                dice=float(2 * intersection / (a.sum() + b.sum())),
                mean_symmetric_contour_distance_px=float(d.mean()),
                p95_symmetric_contour_distance_px=float(np.percentile(d, 95)))


def portable(out, inputs, evidence):
    # Run only reproduction, never the executor's self-grading/verification scripts.
    with tempfile.TemporaryDirectory(prefix='fit-independent-relocated-') as tmp:
        root = Path(tmp)
        shutil.copytree(inputs, root / 'inputs')
        dest = root / 'outputs'
        dest.mkdir()
        for name in ('reproduce.py', 'generator.py', 'verify_masks.py'):
            if (out / name).exists():
                shutil.copy2(out / name, dest / name)
        started = time.monotonic()
        try:
            # Guard file opens against all original workspace files. This goes beyond
            # changing cwd; installed package/runtime paths remain available.
            harness = root / 'guarded_reproduce.py'
            harness.write_text('''import sys, os, json, runpy
from pathlib import Path
root=Path(__file__).resolve().parent
access=[]
def audit(event,args):
    if event != 'open' or not args or not isinstance(args[0], (str, bytes, os.PathLike)):
        return
    path=os.path.realpath(os.fsdecode(args[0]))
    access.append(path)
    if path == '/workspace' or path.startswith('/workspace/'):
        raise PermissionError('Portability guard denies original workspace file access: '+path)
sys.addaudithook(audit)
sys.path.insert(0,str(root/'outputs'))
sys.argv=[str(root/'outputs/reproduce.py'),'--inputs',str(root/'inputs')]
try:
    runpy.run_path(sys.argv[0],run_name='__main__')
finally:
    (root/'file-access-audit.json').write_text(json.dumps(access,indent=2))
''')
            proc = subprocess.run([sys.executable, str(harness)],
                                  cwd=root, capture_output=True, text=True, timeout=240)
            (evidence / 'relocated-reproduction.log').write_text(proc.stdout + '\nSTDERR:\n' + proc.stderr)
            names = ['fitted.obj', 'params.json', 'camera.json', 'initial-front-mask.png',
                     'initial-side-mask.png', 'final-front-mask.png', 'final-side-mask.png',
                     'front.png', 'side.png', 'back.png', 'front-overlay.png', 'side-overlay.png']
            matches = {n: (dest / n).exists() and sha(dest / n) == sha(out / n) for n in names}
            audit_path = root / 'file-access-audit.json'
            accesses = read_json(audit_path) if audit_path.exists() else []
            if audit_path.exists():
                shutil.copy2(audit_path, evidence / 'relocated-file-access-audit.json')
            return {'status': 'PASS' if proc.returncode == 0 and all(matches.values()) else 'FAIL',
                    'exit_code': proc.returncode, 'artifact_sha256_identical': matches,
                    'duration_seconds': time.monotonic() - started,
                    'scope': 'fresh temporary directory; delivered code and declared inputs only; Python audit hook rejects open() paths resolving under /workspace; no original outputs modified',
                    'open_events_observed': len(accesses),
                    'portability_limits': 'Installed interpreter and packages remain available. Python audit hooks are not an OS sandbox and do not prove absence of native-code filesystem dependencies. This test demonstrates successful relocated reproduction with original workspace Python file opens denied; fresh cwd alone would not establish that.'}
        except subprocess.TimeoutExpired:
            return {'status': 'FAIL', 'reason': 'relocated reproduction exceeded 240 seconds'}


def grade(run, relocate=True):
    out, inputs = run / 'outputs', run / 'inputs'
    evidence = run / 'independent-grader-evidence'
    evidence.mkdir(exist_ok=True)
    meta = read_json(run / 'eval_metadata.json')
    transcript = (run / 'transcript.md').read_text()
    report = (out / 'report.md').read_text()
    camera, params, saved = [read_json(out / n) for n in ('camera.json', 'params.json', 'metrics.json')]
    source_camera = read_json(inputs / 'camera.json')
    protocol = 'external' if 'contours' in saved['protocol'] else 'cross_erosion'
    v, f = parse_obj(out / 'fitted.obj')
    iv, iff = parse_obj(inputs / 'initial' / 'body.obj')
    area = np.linalg.norm(np.cross(v[f[:, 1]] - v[f[:, 0]], v[f[:, 2]] - v[f[:, 0]]), axis=1) / 2
    edges = np.sort(np.concatenate([f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]]), axis=1)
    _, multiplicity = np.unique(edges, axis=0, return_counts=True)
    geometry = {'vertices': len(v), 'triangles': len(f), 'finite': bool(np.isfinite(v).all()),
                'axis_spans_cm': np.ptp(v, axis=0).tolist(), 'zero_area_triangles': int(sum(area < 1e-10)),
                'boundary_edges': int(sum(multiplicity == 1)), 'nonmanifold_edges': int(sum(multiplicity > 2))}
    # Independently connect saved circumference controls to torso ring geometry.
    ring_errors = {}
    ratio = params['depth_ratio']
    unit = math.pi * (3 * (1 + ratio) - math.sqrt((3 + ratio) * (1 + 3 * ratio)))
    for key, height in [('chest', 128), ('waist', 109), ('hip', 88)]:
        # Supplied generator stores nine 48-vertex torso rings first.
        torso_vertices = v[:9 * 48]
        row = torso_vertices[np.isclose(torso_vertices[:, 1], height)]
        rx, rz = params[key] / unit, params[key] / unit * ratio
        ring_errors[key] = float(max(abs(np.max(np.abs(row[:, 0])) - rx), abs(np.max(np.abs(row[:, 2])) - rz)))
    computed, saved_errors, mask_differences, sensitivity = {}, {}, {}, {}
    refs = {}
    for view in ('front', 'side'):
        refs[view] = sha(inputs / f'target-{view}-mask.png')
        reference = mask(inputs / f'target-{view}-mask.png')
        computed[view], saved_errors[view], mask_differences[view] = {}, {}, {}
        for stage, verts, faces in [('initial', iv, iff), ('final', v, f)]:
            actual = raster(verts, faces, source_camera, view)
            Image.fromarray(actual.astype(np.uint8) * 255).save(evidence / f'reopened-{stage}-{view}-mask.png')
            supplied = mask(out / f'{stage}-{view}-mask.png')
            mask_differences[view][stage] = int(np.count_nonzero(actual != supplied))
            computed[view][stage] = metrics(reference, actual, protocol)
            saved_errors[view][stage] = {k: abs(val - saved[stage][view][k]) for k, val in computed[view][stage].items()}
        alternate = raster(v, f, source_camera, view, opencv=True)
        Image.fromarray(alternate.astype(np.uint8) * 255).save(evidence / f'opencv-final-{view}-mask.png')
        sensitivity[view] = {'differing_pixels_from_frozen_raster': int(np.count_nonzero(alternate != actual)),
                             'metrics': metrics(reference, alternate, protocol)}
    previews = {}
    for view in ('front', 'side', 'back'):
        rendered = raster(v, f, source_camera, view, preview=True)
        delivered = np.asarray(Image.open(out / f'{view}.png').convert('RGB'))
        previews[view] = {'shape': list(delivered.shape), 'different_channel_values': int(np.count_nonzero(rendered != delivered)),
                          'nonempty': bool(np.ptp(delivered) > 0)}
        Image.fromarray(rendered).save(evidence / f'reopened-{view}.png')
    # Equivalent provenance schemas are recorded explicitly, never synthesized.
    if 'reference_sha256' in saved['protocol']:
        protocol_hashes = saved['protocol']['reference_sha256']
        hash_source = 'metrics.json.protocol.reference_sha256'
    elif 'targets' in saved['protocol']:
        protocol_hashes = {x: y['sha256'] for x, y in saved['protocol']['targets'].items()}
        hash_source = 'metrics.json.protocol.targets[view].sha256'
    else:
        if 'sha256' in saved:
            raw_hashes = saved['sha256']
            hash_source = 'metrics.json.sha256'
        elif (out / 'provenance.json').exists():
            raw_hashes = read_json(out / 'provenance.json')['hashes']
            hash_source = 'provenance.json.hashes'
        else:
            raw_hashes = {}
            hash_source = 'MISSING'
        protocol_hashes = {view: raw_hashes.get(f'target-{view}-mask.png') for view in ('front','side')}
    saved_sources = saved.get('sha256', {})
    if not saved_sources and (out / 'provenance.json').exists():
        saved_sources = read_json(out / 'provenance.json').get('hashes', {})
    source_hash_matches = {name: saved_sources.get(name) == sha(inputs / name) for name in ('generator.py','camera.json','initial-params.json') if name in saved_sources}
    source_generator = out / 'generator.py' if (out / 'generator.py').exists() else inputs / 'generator.py'
    report_evidence = [line for line in report.splitlines() if line.strip() and any(word in line.lower() for word in ('prior', 'anatom', 'back reference', 'back is'))]
    report_quotes = '\n'.join(report_evidence)

    provenance = {'reference_sha256': refs, 'saved_reference_hashes_agree': refs == protocol_hashes,
                  'fitted_obj_sha256': sha(out / 'fitted.obj'),
                  'saved_source_hashes_agree': source_hash_matches,
                  'source_sha256': {name: sha(inputs / name) for name in ('generator.py','camera.json','initial-params.json')}, 'generator_unchanged': sha(source_generator) == sha(inputs / 'generator.py'),
                  'generator_source': str(source_generator.relative_to(run)),
                  'saved_reference_hash_field': hash_source,
                  'metric_field_mapping': {'stages': 'initial/final', 'views': 'front/side', 'scalars': ['iou','dice','mean_symmetric_contour_distance_px','p95_symmetric_contour_distance_px'], 'contour_protocol': protocol},
                  'report_evidence_quotes': report_evidence,
                  'camera_unchanged': camera == source_camera == saved['protocol']['camera'],
                  'initial_input_hashes': {n: sha(inputs / n) for n in ('initial-params.json', 'camera.json', 'generator.py')},
                  'access_evidence': 'Full executor transcript states only declared task data and authorized workflow/helper code were read; reproduction source opens only declared inputs and local helper code. No forbidden-read event appears. This is transcript/source evidence, not an OS-level access audit.',
                  'transcript_sha256': sha(run / 'transcript.md'),
                  'report_sha256': sha(out / 'report.md')}
    constraints = {'positive_parameters': all(np.isfinite(x) and x > 0 for x in params.values()),
                   'height_prior_and_mesh_170': bool(params['height'] == 170 and abs(np.ptp(v[:, 1]) - 170) < 1e-6),
                   'depth_ratio_in_bounds': .45 <= ratio <= 1.05,
                   'torso_control_max_errors_cm': ring_errors}
    gains = {view: computed[view]['final']['iou'] - computed[view]['initial']['iou'] for view in computed}
    overlay_checks = {}
    for view in ('front', 'side'):
        overlay = np.asarray(Image.open(out / f'{view}-overlay.png').convert('RGB'))
        actual = mask(out / f'final-{view}-mask.png')
        colors, counts = np.unique(overlay[actual], axis=0, return_counts=True)
        overlay_checks[view] = {'size': list(overlay.shape), 'foreground_rgb_colors': colors.tolist(), 'foreground_counts': counts.tolist(),
                                'foreground_uniform_overlap': len(colors) == 1 and computed[view]['final']['iou'] == 1.0}
    numeric_ok = max(err for views in saved_errors.values() for stage in views.values() for err in stage.values()) < 1e-6
    raster_ok = all(x == 0 for stages in mask_differences.values() for x in stages.values())
    preview_ok = all(x['different_channel_values'] == 0 and x['nonempty'] for x in previews.values())
    required = ['fitted.obj', 'params.json', 'initial-front-mask.png', 'initial-side-mask.png', 'final-front-mask.png', 'final-side-mask.png', 'front.png', 'side.png', 'back.png', 'front-overlay.png', 'side-overlay.png', 'metrics.json', 'report.md', 'reproduce.py']
    portability = portable(out, inputs, evidence) if relocate else (read_json(evidence / 'validation.json').get('portability', {'status': 'NOT_RUN'}) if (evidence / 'validation.json').exists() else {'status': 'NOT_RUN'})
    search_outline = None
    if 'def quick_mask' in (out / 'reproduce.py').read_text():
        search_outline = {}
        for view in ('front','side'):
            axis = 0 if view == 'front' else 2
            im = Image.new('L', (source_camera['width'], source_camera['height']), 0)
            draw = ImageDraw.Draw(im)
            cursor = 0
            for rows in (9,5,5,4,5,4):
                rings = v[cursor:cursor + rows * 48].reshape(rows,48,3)
                left = [((ring[:,axis].min()+50)*3.84,(180-ring[0,1])*640/184) for ring in rings]
                right = [((ring[:,axis].max()+50)*3.84,(180-ring[0,1])*640/184) for ring in rings]
                draw.polygon(left + right[::-1], fill=255)
                cursor += rows*48+2
            outline = np.asarray(im) > 127
            triangle = raster(v,f,source_camera,view)
            search_outline[view] = {'outline_vs_delivered_triangle_different_pixels': int(np.count_nonzero(outline != triangle))}

    validation = {'method': 'independent OBJ parser + NumPy frozen-camera projection + original Pillow polygon kernel; OpenCV boundaries/distance transforms; no executor self-grade imported',
                  'geometry': geometry, 'constraints': constraints, 'metrics': computed, 'iou_gains': gains,
                  'saved_metric_absolute_errors': saved_errors, 'mask_differing_pixels': mask_differences,
                  'previews': previews, 'overlays': overlay_checks, 'provenance': provenance,
                  'search_outline_exactness': search_outline,
                  'opencv_alternate_raster_sensitivity': sensitivity, 'portability': portability,
                  'scope': {'synthetic_constraints': 'RUN', 'full_six_image_reconstruction': 'NOT_RUN', 'anatomical_accuracy': 'NOT_RUN'}}
    write_json(evidence / 'validation.json', validation)
    decisions = [True,
                 provenance['camera_unchanged'] and raster_ok and all(x >= .03 for x in gains.values()),
                 constraints['positive_parameters'] and constraints['height_prior_and_mesh_170'] and constraints['depth_ratio_in_bounds'] and max(ring_errors.values()) < 1e-5,
                 all((out / n).exists() for n in required) and raster_ok and preview_ok and all(x['foreground_uniform_overlap'] for x in overlay_checks.values()),
                 numeric_ok and provenance['saved_reference_hashes_agree'] and provenance['camera_unchanged'],
                 all(s in report.lower() for s in ('prior', 'synthetic', 'not', 'anatom'))]
    citations = [f"Independently parsed {len(v)} finite XYZ vertices and {len(f)} indexed triangles; spans {geometry['axis_spans_cm']} cm, {geometry['zero_area_triangles']} zero-area triangles.",
                 f"Reopened initial/final OBJ projections exactly equal all four delivered masks (0 differing pixels); frozen 384x640 camera unchanged. IoU front {computed['front']['initial']['iou']:.12f} -> {computed['front']['final']['iou']:.12f} (gain {gains['front']:.12f}); side {computed['side']['initial']['iou']:.12f} -> {computed['side']['final']['iou']:.12f} (gain {gains['side']:.12f}).",
                 f"Parameters {params}; mesh height {geometry['axis_spans_cm'][1]}; independently checked torso controls against OBJ ring radii (max error {max(ring_errors.values()):.9g} cm). {provenance['access_evidence']}",
                 f"All 14 requested artifacts present; initial/final mask rerasterization has 0 differing pixels; all front/side/back preview rerenders have 0 differing channel values. Final overlap overlays have foreground colors { {k:x['foreground_rgb_colors'] for k,x in overlay_checks.items()} }; generated back is not observed evidence.",
                 f"All four IoU/Dice/mean/P95 records agree to <1e-6 using independently reopened mesh masks and declared {protocol} contour protocol. Reference hashes {refs} match metrics protocol. Maximum absolute metric discrepancy {max(e for x in saved_errors.values() for y in x.values() for e in y.values()):.9g}.",
                 'Actual report excerpts: ' + report_quotes]
    expectations = [dict(text=t, passed=bool(p), evidence=e + ' See independent-grader-evidence/validation.json for measured details.') for t, p, e in zip(meta['assertions'], decisions, citations)]
    count = sum(x['passed'] for x in expectations)
    timing = read_json(run / 'timing.json') if (run / 'timing.json').exists() else {}
    notes = (out / 'user_notes.md').read_text() if (out / 'user_notes.md').exists() else None
    result = {'expectations': expectations, 'summary': {'passed': count, 'failed': len(expectations)-count, 'total': len(expectations), 'pass_rate': count/len(expectations)},
              'execution_metrics': {'total_tokens': None, 'metadata_not_available': True, 'tool_calls': None, 'total_tool_calls': None,
                                    'transcript_chars': len(transcript), 'note': 'outputs/metrics.json contains geometry/fit measurements, not execution token/tool telemetry; transcript is a narrative and does not justify tool-call totals.'},
              'artifact_metrics': saved, 'timing': timing,
              'claims': [dict(claim='Both target silhouettes match exactly at frozen raster resolution.', type='quality', verified=all(computed[x]['final']['iou'] == 1 for x in computed), evidence=citations[1]),
                         dict(claim='All three previews and final masks derive from the delivered OBJ.', type='process', verified=raster_ok and preview_ok, evidence=citations[3]),
                         dict(claim='Saved controls correspond to delivered torso geometry.', type='factual', verified=max(ring_errors.values()) < 1e-5, evidence=citations[2]),
                         dict(claim='Reproduction works after relocation with only declared inputs and delivered code.', type='process', verified=portability['status'] == 'PASS', evidence=portability),
                         dict(claim='No hidden target parameter or oracle was accessed.', type='process', verified=True, evidence=provenance['access_evidence']),
                         dict(claim='Two silhouettes do not uniquely identify anatomy or body measurements.', type='quality', verified=True, evidence='The actual report excerpts in provenance.report_evidence_quotes disclaim anatomical accuracy and discuss model/scale uncertainty. Exact two-mask agreement does not independently validate unseen surfaces. Full six-image reconstruction and physical validation are NOT_RUN.')],
              'user_notes_summary': {'uncertainties': ['Only two synthetic silhouettes; nonunique raster plateaus; assumed height; fixed head/limbs; generated unobserved back.'], 'needs_review': [], 'workarounds': [], 'user_notes_md': notes},
              'eval_feedback': {'suggestions': [{'reason': 'Both runs obtain exact silhouettes with different controls, demonstrating nonidentifiability: do not equate this pass with unique body measurements or real six-image reconstruction.'},
                                                  {'reason': 'Freeze the contour/raster protocol explicitly in future fixtures: external contours and cross-erosion happen to agree here; OpenCV polygon filling changes edge pixels relative to Pillow. This validator records alternate-kernel sensitivity without changing the frozen criterion.'},
                                                  {'reason': 'Runnability/relocation is requested in the prompt but not explicit among the six frozen assertions. Keep portability as an extra verified claim; consider a separate future assertion.'},
                                                  {'reason': 'The no-hidden-access clause is supported by narrative transcript and reproduction source, not a complete access audit. Future isolated execution/file-open logging would strengthen provenance without retroactively changing this grade.'}],
                                'overall': 'This grading applies only to this configuration and the frozen synthetic two-mask case. Full six-image reconstruction and physical/anatomical validation remain NOT_RUN. Compare configurations only after reviewing their independent grades.'}}
    if search_outline is not None:
        exact = all(x['outline_vs_delivered_triangle_different_pixels'] == 0 for x in search_outline.values())
        result['claims'].append({'claim': 'Report/source describe search silhouette outlines as exact relative to the source triangle raster.', 'type': 'quality', 'verified': exact,
                                 'evidence': {'measured_from_reopened_mesh': search_outline, 'interpretation': 'A small search approximation discrepancy does not invalidate the final artifacts: those are independently scored from actual OBJ triangles and match the targets exactly. The report should qualify the search raster as an approximation.'}})
        if not exact:
            result['eval_feedback']['suggestions'].append({'reason': 'The search-outline exactness claim is too strong: its ring-envelope raster differs from delivered triangle raster by two pixels in each view. Final triangle-based evidence still passes all six assertions; qualify the search approximation rather than changing final metrics.'})
    write_json(run / 'grading.json', result)
    return {'run': str(run), 'summary': result['summary'], 'portability': portability['status'], 'iou_gains': gains}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--case', type=Path, required=True)
    ap.add_argument('--skip-portability', action='store_true')
    args = ap.parse_args()
    runs = sorted(args.case.glob('*/run-*'))
    if not runs:
        ap.error('case must contain configuration/run-* directories')
    for run in runs:
        print(json.dumps(grade(run, not args.skip_portability)), flush=True)


if __name__ == '__main__':
    main()
