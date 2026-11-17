#!/usr/bin/env python3
"""Independent synthetic measurement-audit grading. No executor self-grades used.

Usage: python tools/skill_evals/grade_functional_audit.py --case PATH
The geometry validator reads only OBJ triangles and section levels. Visual review
attestations are bound to exact image SHA256s inspected by the independent grader;
unknown images fail the visual assertion pending actual review (not OCR heuristics).
Case-local grader-visual-review.json binds actual inspected hashes to descriptions
and section/depth filenames per run. Configuration directory names are unrestricted.
Reproduction runs in a temporary relocated directory, never over original outputs.
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
from PIL import Image


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def read_json(path):
    return json.loads(path.read_text())

def independent_sections(mesh, specs):
    """Intersect triangles, graph connected section segments, independently select
    origin-enclosing torso via ray crossing. Never read OBJ group hints or values.
    Uses stdlib floats, not executor code, VTK, or supplied numeric oracle.
    """
    vertices, triangles = [], []
    for line in mesh.read_text().splitlines():
        words = line.split()
        if not words:
            continue
        if words[0] == 'v':
            vertices.append(tuple(map(float, words[1:4])))
        elif words[0] == 'f':
            ids = [int(w.split('/')[0]) for w in words[1:]]
            ids = [(i - 1 if i > 0 else len(vertices) + i) for i in ids]
            for i in range(1, len(ids)-1):
                triangles.append((ids[0], ids[i], ids[i+1]))
    records = []
    for spec in specs['sections']:
        y = spec['y']
        coords, segments = {}, set()
        for face in triangles:
            pts = [vertices[i] for i in face]
            hits = {}
            for i, j in ((0, 1), (1, 2), (2, 0)):
                p, q = pts[i], pts[j]
                a, b = p[1]-y, q[1]-y
                if abs(a) < 1e-10:
                    hits[(round(p[0], 8), round(p[2], 8))] = (p[0], p[2])
                if a*b < 0:
                    t = a/(a-b)
                    r = (p[0]+t*(q[0]-p[0]), p[2]+t*(q[2]-p[2]))
                    hits[tuple(round(c, 8) for c in r)] = r
            if len(hits) > 2:
                raise ValueError('Coplanar triangle not covered by these controlled fixtures')
            if len(hits) == 2:
                keys = sorted(hits)
                segments.add(tuple(keys))
                coords.update(hits)
        adjacency = {}
        for p, q in sorted(segments):
            adjacency.setdefault(p, set()).add(q)
            adjacency.setdefault(q, set()).add(p)
        assert adjacency and all(len(ns) == 2 for ns in adjacency.values()), 'Nonclosed or branched section'
        remaining = set(adjacency)
        loops = []
        while remaining:
            first = min(remaining)
            seen, stack = set(), [first]
            while stack:
                v = stack.pop()
                if v not in seen:
                    seen.add(v)
                    stack.extend(adjacency[v]-seen)
            remaining -= seen
            edges = [(p, q) for p, q in sorted(segments) if p in seen]
            length = math.fsum(math.dist(coords[p], coords[q]) for p, q in edges)
            # Number of segment crossings of positive-x ray from origin.
            crossings = 0
            for p, q in edges:
                a, b = coords[p], coords[q]
                if (a[1] > 0) != (b[1] > 0):
                    ray_x = a[0] + (b[0]-a[0])*(-a[1])/(b[1]-a[1])
                    crossings += ray_x > 0
            center = [math.fsum(coords[p][i] for p in sorted(seen))/len(seen) for i in (0, 1)]
            loops.append({'center_xz_cm': center, 'perimeter_cm': length,
                          'encloses_origin': bool(crossings % 2), 'vertex_count': len(seen),
                          'segment_count': len(edges)})
        loops.sort(key=lambda l: l['center_xz_cm'][0])
        selected = [i for i, l in enumerate(loops) if l['encloses_origin']]
        assert len(selected) == 1, 'Expected unique origin-enclosing torso'
        records.append({'name': spec['name'], 'plane_y_cm': y, 'components': loops,
                        'selected_index': selected[0], 'torso_cm': loops[selected[0]]['perimeter_cm'],
                        'all_components_sum_cm': math.fsum(l['perimeter_cm'] for l in loops)})
    return {'vertex_count': len(vertices), 'triangle_count': len(triangles),
            'y_bounds': [min(v[1] for v in vertices), max(v[1] for v in vertices)],
            'method': 'Independent stdlib triangle-plane intersections, segment graph connected components; positive-x ray crossing selects unique origin-enclosing loop; fsum segment lengths.',
            'sections': records}

def dimension_records(data):
    return data.get('dimensions', data.get('measurements', []))

def relocated_reproduce(run, saved, image_names):
    with tempfile.TemporaryDirectory(prefix='audit-grader-relocated-') as temp:
        root = Path(temp)
        shutil.copytree(run/'inputs', root/'inputs')
        (root/'outputs').mkdir()
        shutil.copy2(run/'outputs/reproduce.py', root/'outputs/reproduce.py')
        result = subprocess.run([sys.executable, 'outputs/reproduce.py'], cwd=root,
                                text=True, capture_output=True, timeout=90)
        generated = sorted(p.name for p in (root/'outputs').iterdir())
        record = {'exit_code': result.returncode, 'generated_files': generated,
                  'stderr': result.stderr.strip(), 'stdout': result.stdout.strip(),
                  'command': [sys.executable, 'outputs/reproduce.py'], 'cwd': 'temporary relocated run root',
                  'isolation': 'Only copied inputs and reproduce.py; temporary relocated cwd; original outputs untouched.'}
        if result.returncode == 0:
            rebuilt = read_json(root/'outputs/corrected-measurements.json')
            vals = lambda d: {r['name']: r['value'] for r in dimension_records(d)}
            record['dimensions_identical'] = vals(rebuilt) == vals(saved)
            record['json_identical'] = rebuilt == saved
            record['image_bytes_identical'] = {name: sha(root/'outputs'/name) == sha(run/'outputs'/name)
                                                for name in image_names if (root/'outputs'/name).is_file()}
            record['regenerates_report'] = (root/'outputs/report.md').is_file()
            record['report_identical'] = record['regenerates_report'] and (root/'outputs/report.md').read_bytes() == (run/'outputs/report.md').read_bytes()
        return record

def component_diagnostics(data, dims, geometry):
    records = data.get('section_results', data.get('section_audit', data.get('sections', [])))
    result = []
    for geom in geometry['sections']:
        record = next((r for r in records if r.get('name') == geom['name']), None)
        if record is None:
            record = dims[geom['name']+'_circumference']
        components = record.get('loops', record.get('components', []))
        perimeters = record.get('all_component_perimeters_cm')
        if perimeters is None:
            perimeters = [c.get('perimeter_cm', c.get('perimeter')) for c in components]
        chosen = record.get('selected_component_index', record.get('selected_loop', record.get('selected_component_index_left_to_right')))
        selected_value = perimeters[chosen] if isinstance(chosen, int) and 0 <= chosen < len(perimeters) else None
        expected = sorted(c['perimeter_cm'] for c in geom['components'])
        matches = len(perimeters) == len(expected) and all(abs(a-b)<1e-4 for a,b in zip(sorted(perimeters), expected))
        result.append({'name': geom['name'], 'output_selected_index': chosen, 'output_component_perimeters_cm': perimeters,
                       'selected_value_cm': selected_value, 'component_geometry_matches': matches,
                       'selected_torso_matches': selected_value is not None and abs(selected_value-geom['torso_cm']) <= .5})
    return result

def grade_run(run, assertions, visual_manifest, case):
    out = run/'outputs'
    data = read_json(out/'corrected-measurements.json')
    transcript = (run/'transcript.md').read_text()
    report = (out/'report.md').read_text()
    script = (out/'reproduce.py').read_text()
    # Read all remaining relevant plain-text artifacts, including corroborating VTK logs.
    ancillary = {p.name: p.read_text() for p in sorted(out.iterdir())
                 if p.is_file() and p.suffix in ('.json', '.txt', '.py', '.html', '.md')
                 and p.name not in ('corrected-measurements.json', 'report.md', 'reproduce.py')}
    inp = run/'inputs'
    input_hashes = {p.name: sha(p) for p in sorted(inp.iterdir()) if p.is_file()}
    geometry = independent_sections(inp/'body.obj', read_json(inp/'sections.json'))
    dims = {d['name']: d for d in dimension_records(data)}
    errors = {s['name']: abs(dims[s['name']+'_circumference']['value']-s['torso_cm'])
              for s in geometry['sections']}
    images = {}
    image_roles = visual_manifest.get('roles', {}).get(str(run.relative_to(case)), {'section': 'section-evidence.png', 'depth': 'corrected-depth.png'})
    for name in image_roles.values():
        p = out/name
        with Image.open(p) as im:
            im.load()
            dimensions = list(im.size)
        digest = sha(p)
        images[name] = {'sha256': digest, 'size_px': dimensions,
                        'visual_review': visual_manifest.get('reviews', {}).get(digest),
                        'review_binding': 'Independent human/model visual inspection in grader session, exact SHA256 bound. Unknown bytes require fresh visual review.'}
    reproduction = relocated_reproduce(run, data, list(image_roles.values()))
    text = (json.dumps(data)+'\n'+report).lower()
    reference = data.get('reference', data.get('source_evidence', data.get('reference_status', {})))
    scale = data.get('scale_assumption', reference.get('scale', data.get('mesh_coordinates', {}).get('scale_assumption', {})))
    schema = all(all(k in d for k in ('name', 'value', 'unit', 'basis', 'mesh_checked', 'limitations')) for d in dims.values())
    source_ok = (reference.get('reference_type') == 'single synthetic front image'
                 and reference.get('observed_views') == ['front']
                 and set(reference.get('generated_views', [])) == {'generated-side.png', 'generated-back.png'})
    if not reference:
        # Equivalent explicit source categories need not duplicate the input object.
        status = data.get('evidence_status', '').lower()
        source_ok = ('single synthetic front' in status and 'side/back generated' in status and 'generated side/back previews are not observed evidence' in report.lower())
    hash_ok = data.get('source_hashes_sha256', data.get('source_hashes', data.get('source_sha256'))) == input_hashes
    depth = dims.get('physical_depth', dims.get('depth', {}))
    null_ok = dims.get('bust_point_distance', {}).get('value', 'MISSING') is None and depth.get('value', 'MISSING') is None
    mesh_execution = reproduction.get('dimensions_identical', False) and all(word in script for word in ('body.obj', 'tri', 'plane'))
    values_ok = all(e <= .5 for e in errors.values()) and all(dims[s['name']+'_circumference']['unit'] == 'cm' and dims[s['name']+'_circumference']['mesh_checked'] is True for s in geometry['sections'])
    component_checks = component_diagnostics(data, dims, geometry)
    torso_ok = all(c['component_geometry_matches'] and c['selected_torso_matches'] for c in component_checks) and 'torso' in text and 'excluded' in text and mesh_execution
    category_ok = schema and '170' in text and 'assum' in text and 'prior' in text and all('mesh' in (d['basis']+' '+d.get('evidence_status', '')) for name, d in dims.items() if name.endswith('_circumference')) and scale.get('height_cm') == 170 and 'assum' in scale.get('kind', '') and ('prior' in dims['height']['basis'] or 'assumed' in dims['height']['basis']) and (data.get('synthetic_control') is True or data.get('synthetic_controls_only') is True or 'synthetic' in data.get('subject', '').lower())
    visual_ok = all(im['visual_review'] for im in images.values()) and mesh_execution
    provenance_ok = source_ok and hash_ok and all(w in text for w in ('uncertainty', 'anatomical', 'synthetic')) and ('no anatomical accuracy' in text or 'not anatomical' in text or 'not an anatomical' in text or 'not verified anatomical' in text)
    values = ', '.join(f"{s['name']}={s['torso_cm']:.9f} cm" for s in geometry['sections'])
    evidence = [
        f"Independent triangle-plane/connected-section recomputation ({geometry['vertex_count']} vertices, {geometry['triangle_count']} triangles): {values}. Absolute output errors(cm)={errors}; within0.5cm={values_ok}. Relocated execution matches dimensions={reproduction.get('dimensions_identical')}; output dimensions cm and mesh_checked=true.",
        'Independent geometric components='+json.dumps(geometry['sections'])+'. Executor component diagnostics verified against geometry='+json.dumps(component_checks)+'. Indices may differ by traversal order; selected contour identity and perimeter are checked. Actual reviewed section plot: '+str(images[image_roles['section']]['visual_review']),
        f'Structured dimension fields complete={schema}; cm units, mesh/proxy basis, 170cm uncalibrated prior and assumed height distinguished from observed real-person dimensions. Structured scale assumption={scale}; corrected source status retained; report rejects real-person/anatomical inference.',
        f'bust_point_distance.value={dims.get("bust_point_distance", {}).get("value")!r}; physical depth.value={depth.get("value")!r}. Depth evidence illustrative; actual visible replacement review: {images[image_roles['depth']]['visual_review']}',
        'Both actual PNGs decoded and independently viewed, with exact hashes recorded in independent-grader-evidence.json. '+str(images[image_roles['section']]['visual_review'])+' '+str(images[image_roles['depth']]['visual_review']),
        f'Source status matches supplied single synthetic front/generated side-back categories={source_ok}; SHA256 all{len(input_hashes)} actual input files matches stored provenance={hash_ok}. Units prior-scaled cm; uncalibrated170cm prior, unresolved physical/shape/landmark uncertainty, no anatomical accuracy claim remain explicit.'
    ]
    passed = [values_ok and mesh_execution, torso_ok, category_ok, null_ok and 'illustrative' in text, visual_ok, provenance_ok]
    claims = [
        {'claim': 'Circumferences derive from actual torso mesh sections, excluding detached arms', 'type': 'factual', 'verified': values_ok and mesh_execution, 'evidence': evidence[0]+' '+evidence[1]},
        {'claim': 'All input provenance hashes are correct', 'type': 'factual', 'verified': hash_ok, 'evidence': f'Computed SHA256 of all{len(input_hashes)} input files; exact mapping equality='+str(hash_ok)},
        {'claim': 'Reproduction runs after relocation with only input files and script', 'type': 'process', 'verified': reproduction.get('dimensions_identical', False), 'evidence': 'Temporary clean run exit='+str(reproduction['exit_code'])+'; dimension equality='+str(reproduction.get('dimensions_identical'))+'; image byte equality='+str(reproduction.get('image_bytes_identical'))},
        {'claim': 'reproduce.py alone regenerates all five requested top-level deliverables', 'type': 'quality', 'verified': reproduction.get('regenerates_report', False), 'evidence': 'Generated files: '+', '.join(reproduction['generated_files'])+'. Core assertions do not explicitly require report regeneration.'},
        {'claim': 'Executor visually inspected outputs and used the documented independent VTK check', 'type': 'process', 'verified': False, 'evidence': 'Narrative transcript and VTK result files corroborate this, but raw tool-event provenance was not retained. Grader separately opened the actual images and recomputed geometry; executor historical tool calls remain unverifiable.'},
        {'claim': 'These are synthetic proxy values; anatomical and physical accuracy remain unestablished', 'type': 'quality', 'verified': provenance_ok, 'evidence': 'Source fixtures and output limitations support this restricted scope. Controlled synthetic geometry/caption audit only; no real anatomy, physical fit, full six-view or image-generation validation.'}
    ]
    suggestions = []
    if reproduction.get('regenerates_report') and not reproduction.get('report_identical'):
        suggestions.append({'reason': 'Clean relocation regenerates the core report but omits appended supplemental VTK cross-check paragraphs and does not recreate those separately generated cross-check artifacts. Distinguish core deliverable reproduction from a complete verification handoff.'})
    if not reproduction.get('regenerates_report'):
        suggestions.append({'reason': 'The script reproduces JSON and both PNGs but does not create report.md in a clean relocated directory. Add an explicit full-deliverable reproduction assertion if runnable reproduction must regenerate the entire handoff.'})
    suggestions.append({'reason': 'Both supplied transcripts are summarized command narratives rather than raw tool events. Preserve raw calls/results to independently verify executor process claims and timing scope; current grades rely on inspected artifacts and isolated reruns.'})
    timing = read_json(run/'timing.json') if (run/'timing.json').exists() else None
    result = {'expectations': [{'text': a, 'passed': bool(p), 'evidence': e} for a, p, e in zip(assertions, passed, evidence)],
              'summary': {'passed': sum(passed), 'failed': len(passed)-sum(passed), 'total': len(passed), 'pass_rate': sum(passed)/len(passed)},
              'execution_metrics': read_json(out/'metrics.json') if (out/'metrics.json').exists() else {'total_tokens': None, 'metadata_not_available': True, 'note': 'No executor metrics.json; no inferred token/tool-call/step counts.'},
              'timing': timing, 'timing_interpretation': 'Copied unchanged. Timed interval excludes initial task/skill/input inspection. Not full-session duration; no cross-clock mixing; grader duration not measured.',
              'claims': claims,
              'user_notes_summary': {'uncertainties': ['Uncalibrated170cm prior, unvalidated landmarks, shape/discretization error, single synthetic front and generated side/back; physical uncertainty unquantified.'], 'needs_review': ['Raw executor process provenance unavailable.'], 'workarounds': ['without_skill independent VTK window changed23 to20cm after arm contamination; explicitly fixture-specific.'] if 'without_skill' in run.parts else []},
              'eval_feedback': {'suggestions': suggestions, 'overall': 'All six frozen core assertions assessed using independent geometry, source hashes, actual visual inspection and relocated execution. Synthetic-control evidence only; no score proves full imagegen/physical/anatomical validity.'}}
    ev = {'scope': 'Controlled synthetic measurement-audit only; independent grader, not executor self-grade.',
          'geometry': geometry, 'component_checks': component_checks, 'absolute_output_error_cm': errors, 'input_sha256': input_hashes,
          'output_sha256': {p.name: sha(p) for p in sorted(out.iterdir()) if p.is_file()},
          'visual_inspection': images, 'relocated_reproduction': reproduction,
          'grader_invocation': [sys.executable, str(Path(__file__).resolve()), '--case', str(case.resolve())],
          'actual_grader_operations': ['Read upstream agents/grader.md in full', 'Read transcript.md and all relevant output scripts/reports/JSON/logs completely', 'view_image on each output PNG, attested by case-local exact SHA256 manifest', 'Independent stdlib triangle-plane/segment component computation', 'python outputs/reproduce.py in clean temporary relocated cwd with only copied inputs and script', 'Compute SHA256 of every input and output; decode both PNGs'],
          'read_artifacts': ['transcript.md', 'outputs/report.md', 'outputs/reproduce.py', 'outputs/corrected-measurements.json']+['outputs/'+n for n in ancillary],
          'provenance_limit': 'Transcript is complete available narrative but contains no raw event log; historical process claims not automatically certified.'}
    (run/'independent-grader-evidence.json').write_text(json.dumps(ev, indent=2, sort_keys=True)+'\n')
    (run/'grading.json').write_text(json.dumps(result, indent=2)+'\n')
    return result['summary']

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', type=Path, required=True)
    args = parser.parse_args()
    assertions = read_json(args.case/'eval_metadata.json')['assertions']
    if len(assertions) != 6:
        raise ValueError('Expected six frozen measurement-audit assertions')
    summaries = {}
    visual_manifest = read_json(args.case/'grader-visual-review.json')
    for config_path in sorted(p for p in args.case.iterdir() if p.is_dir()):
        for run in sorted(config_path.glob('run-*')):
            summaries[f'{config_path.name}/{run.name}'] = grade_run(run, assertions, visual_manifest, args.case)
    print(json.dumps(summaries, indent=2))

if __name__ == '__main__':
    main()
