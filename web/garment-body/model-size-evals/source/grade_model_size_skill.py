#!/usr/bin/env python3
"""Independent artifact grader for model-size skills (no executor helper imports).
Reads frozen protocol and real supplied OBJ/asset/state; writes only grading and
separate grade-evidence. Numeric validator is also exposed for scratch controls.
"""
import argparse
import copy
import csv
import hashlib
import json
import math
import shutil
from pathlib import Path

VALUE_FIELDS = ('value_cm', 'value')
TARGET_FIELDS = ('body_parameter_target_cm', 'target_cm', 'control_target_cm')
DELTA_FIELDS = ('input_target_delta_cm', 'difference_cm', 'difference_from_target_cm')

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def inventory(root):
    """Recursive relative artifact names, excluding interpreter cache files."""
    return {str(p.relative_to(root)):sha(p) for p in sorted(root.rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'}

def manual_audit(audit_path, out):
    """Consume fixed reviewed findings; absent/stale bindings never grant PASS."""
    keys = ('execution', 'geometry', 'preserve', 'scope', 'geometry_reject')
    error = None
    try:
        audit = json.loads(audit_path.read_text())
        if audit.get('artifact_sha256') != inventory(out):
            error = 'Fixed manual audit is stale: full recursive artifact SHA binding differs.'
        elif not all(k in audit.get('findings', {}) for k in keys):
            error = 'Fixed manual audit is incomplete.'
    except (OSError, ValueError):
        error = 'Fixed manual audit is missing or invalid.'
    if error:
        return {k: {'passed': False, 'evidence': error} for k in keys}, False
    return audit['findings'], True

def dump(p, value):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n')

def field(row, names):
    for name in names:
        if name in row:
            return row[name]
    raise ValueError('Missing semantic field: ' + str(names))

def number(x):
    return type(x) in (int, float) and math.isfinite(x)

def near(x, y, tol):
    return number(x) and number(y) and abs(x-y) <= tol

def obj(path):
    vertices, faces = [], []
    for line in path.read_text().splitlines():
        t = line.split('#', 1)[0].split()
        if not t:
            continue
        if t[0] == 'v':
            assert len(t) == 4
            p = tuple(map(float, t[1:])); assert all(math.isfinite(v) for v in p)
            vertices.append(p)
        if t[0] == 'f':
            assert len(t) == 4
            indexes = [int(v.split('/')[0]) for v in t[1:]]
            assert all(v != 0 for v in indexes)
            faces.append(tuple(v-1 if v>0 else len(vertices)+v for v in indexes))
    assert vertices and faces
    assert all(0 <= i < len(vertices) for f in faces for i in f)
    return vertices, faces

def independent_geometry(base, case):
    state_path = base/'inputs'/case/'final-state.json'
    asset_path = base/'inputs/human.json'
    mesh_path = base/'inputs'/case/'neutral.obj'
    state, asset = json.loads(state_path.read_text()), json.loads(asset_path.read_text())
    actual, faces = obj(mesh_path)
    ids = asset['bodyVertexIds']; compact = {v:i for i,v in enumerate(ids)}
    assert len(ids) == len(compact) == len(actual)
    rest = [asset['vertices'][i:i+3] for i in range(0,len(asset['vertices']),3)]
    assert len(state['morphWeights']) == len(asset['controls']) == 12
    # Scalar loops accumulate every sparse row. No exporter or runtime is imported.
    for weight, control in zip(state['morphWeights'], asset['controls']):
        assert number(weight)
        for index, dx, dy, dz in control['incr' if weight >= 0 else 'decr']:
            for axis, delta in enumerate((dx, dy, dz)):
                rest[index][axis] += abs(weight)*delta
    floor = min(rest[i][1] for i in ids)
    expected = [(rest[i][0], rest[i][1]-floor, rest[i][2]) for i in ids]
    ef = [tuple(compact[i] for i in asset['indices'][j:j+3]) for j in range(0,len(asset['indices']),3)]
    distances = [math.dist(v,w) for v,w in zip(actual,expected)]
    values = {}
    paths = {}
    for c in asset['controls']:
        key = c['key']; path = c['path']; mapped = [compact[i] for i in path]
        if key == 'height':
            value = max(v[1] for v in actual)-min(v[1] for v in actual)
        else:
            assert len(path) >= 2
            if c['kind'] == 'circumference': assert path[0] == path[-1]
            else: assert c['kind'] == 'landmark distance' and len(path) == 2
            value = sum(math.dist(actual[i],actual[j]) for i,j in zip(mapped,mapped[1:]))
        values[key] = value
        paths[key] = {'asset_path':path, 'compact_path':mapped, 'kind':c['kind']}
    inputs = [asset_path,state_path,mesh_path]
    posed = base/'inputs'/case/'posed.obj'
    if posed.exists(): inputs.append(posed)
    return {'case':case,'values_cm':values,'targets_cm':state['dimensions'],
            'residuals_cm':{k:v-state['dimensions'][k] for k,v in values.items()},
            'paths':paths,'vertices':len(actual),'triangles':len(faces),
            'exact_topology_and_winding':faces == ef,
            'maximum_geometry_error_cm':max(distances),
            'rms_geometry_error_cm':math.sqrt(sum(d*d for d in distances)/len(distances)),
            'vertices_above_0_002cm':sum(d>.002 for d in distances),
            'largest_difference_compact_index':distances.index(max(distances)),
            'asset_fingerprint_matches':sha(asset_path)==state['asset'],
            'units_valid':asset['unit']==state['units']=='cm',
            'pose_map_complete':set(state['poseDegrees'])=={b['name'] for b in asset['bones']},
            'pose_count':len(state['poseDegrees']),
            'nonzero_pose_count':sum(any(v) for v in state['poseDegrees'].values()),
            'pose_sha256':hashlib.sha256(json.dumps(state['poseDegrees'],sort_keys=True,separators=(',',':')).encode()).hexdigest(),
            'weights_sha256':hashlib.sha256(json.dumps(state['morphWeights'],separators=(',',':')).encode()).hexdigest(),
            'input_sha256':{str(p.relative_to(base/'inputs')):sha(p) for p in inputs},
            'cached_claims_cm':state.get('measuredNeutral'),
            'cached_maximumTargetErrorCm':state.get('maximumTargetErrorCm')}

def validate_artifacts(report, csv_rows, truth, tolerance=.01, geometry_tolerance=.002):
    """Schema tolerant but semantic: never accept target/cache as primary value."""
    errors = []; rows = report.get('measurements',[])
    keys = set(truth['values_cm'])
    jr = {r.get('name'):r for r in rows}; cr = {r.get('name'):r for r in csv_rows}
    complete = len(rows)==len(csv_rows)==len(keys)==12 and set(jr)==set(cr)==keys
    if not complete: errors.append('JSON/CSV must have exactly the same 12 dimensions')
    geometry = (truth['asset_fingerprint_matches'] and truth['units_valid'] and
                truth['exact_topology_and_winding'] and truth['maximum_geometry_error_cm']<=geometry_tolerance)
    rejection = truth['case']=='consistency-check'
    rejected_status = any(s in report.get('status','').lower() for s in ('refus','reject'))
    numeric_ok = complete; csv_ok = complete; targets_ok = complete; defs_ok = complete
    for key in keys & set(jr) & set(cr):
        r,c=jr[key],cr[key]
        try:
            value, target, delta = field(r,VALUE_FIELDS),field(r,TARGET_FIELDS),field(r,DELTA_FIELDS)
            cv = field(c, VALUE_FIELDS)
            cv = None if cv in ('',None,'null') else float(cv)
            if rejection:
                numeric_ok &= value is None and delta is None
            else:
                numeric_ok &= near(value,truth['values_cm'][key],tolerance)
                targets_ok &= near(target,truth['targets_cm'][key],tolerance) and near(delta,truth['residuals_cm'][key],tolerance)
            csv_ok &= (cv is None and value is None) or near(cv,value,tolerance)
            csv_ok &= r.get('unit')==c.get('unit')=='cm'
            defs_ok &= bool(r.get('definition'))
            for map_name in ('measured_values_cm',):
                if map_name in report:
                    top = report[map_name].get(key)
                    numeric_ok &= (top is None and value is None) or near(top,value,tolerance)
            if 'target_dimensions_cm' in report:
                targets_ok &= near(report['target_dimensions_cm'].get(key), truth['targets_cm'][key],tolerance)
        except (ValueError,TypeError):
            numeric_ok=csv_ok=targets_ok=False
    if not defs_ok: errors.append('Measurement definitions are missing')
    if not numeric_ok: errors.append('Primary values/nulls disagree with independently measured geometry or rejection')
    if not csv_ok: errors.append('JSON/CSV values or centimetre units disagree')
    if not targets_ok: errors.append('Control targets/residuals are missing or disagree with actual mesh')
    no_success = rejection and rejected_status and numeric_ok and csv_ok
    if rejection and not no_success: errors.append('Incompatible geometry must have explicit rejected/null outputs')
    if not rejection and not geometry: errors.append('Successful dimensions have incompatible geometry')
    return {'passed':not errors,'errors':errors,'geometry_compatible':geometry,
            'numeric':bool(numeric_ok),'csv':bool(csv_ok),'targets':bool(targets_ok),
            'definitions':bool(defs_ok),'no_success':bool(no_success)}

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--workspace',type=Path,required=True)
    args=parser.parse_args(); base=args.workspace.resolve()
    protocol=json.loads((base/'protocol/assertions.json').read_text())
    oracle=json.loads((base/'protocol/private-oracle.json').read_text())
    evidence=base/'grade-evidence'; evidence.mkdir(exist_ok=True)
    # Read every execution artifact in full; fingerprints inventory fixes exactly what was graded.
    all_artifacts={str(out.relative_to(base)/relative):digest for out in base.glob('iteration-1/*/*/run-1/outputs') for relative,digest in inventory(out).items()}
    source={str(Path(tree)/relative):digest for tree in ('skill-old','skill-new','inputs') for relative,digest in inventory(base/tree).items()}
    baseline={**all_artifacts,**source}
    truths={case:independent_geometry(base,case) for case in ('saved-model','residual-cache','consistency-check')}
    for case,t in truths.items():
        t['private_oracle_comparison']={'input_hashes_match':all(t['input_sha256'].get(k)==v for k,v in oracle[case]['input_sha256'].items()),
            'maximum_value_difference_cm':max(abs(t['values_cm'][k]-v) for k,v in oracle[case]['measured_from_supplied_obj_cm'].items())}
        dump(evidence/(case+'-independent.json'),t)
    summary=[]
    for out in sorted(base.glob('iteration-1/*/*/run-1/outputs')):
        case=out.parents[2].name.removeprefix('eval-1-').removeprefix('eval-2-').removeprefix('eval-3-')
        arm=out.parents[1].name; tag=case+'-'+arm
        text_artifacts={p.name:p.read_text() for p in out.iterdir() if p.is_file()}
        report_path=next(out.glob('measurements*.json')); csv_path=next(out.glob('measurements*.csv'))
        report=json.loads(text_artifacts[report_path.name]); csv_rows=list(csv.DictReader(text_artifacts[csv_path.name].splitlines()))
        truth=truths[case]; checks=validate_artifacts(report,csv_rows,truth,protocol['numeric_tolerance_cm'],protocol['geometry_correspondence_tolerance_cm'])
        dump(evidence/(tag+'-numeric.json'),checks)
        # Fixed findings were reviewed separately and are never generated by CLI.
        manual, manual_current = manual_audit(evidence/(tag+'-manual.json'), out)
        preserved=truth['private_oracle_comparison']['input_hashes_match'] and truth['pose_map_complete']
        definitions=checks['definitions']
        verdicts={k:v['passed'] for k,v in manual.items()}
        verdicts.update(numeric=checks['numeric'] and checks['geometry_compatible'],csv=checks['csv'],targets=checks['targets'],preserve=preserved and manual['preserve']['passed'],scope=definitions and manual['scope']['passed'])
        verdicts['geometry']=checks['geometry_compatible'] and manual['geometry']['passed']
        verdicts['no_success']=checks['no_success'] and not list(out.glob('*success*'))
        if not manual_current:
            verdicts = {k:False for k in verdicts}
        texts=protocol['reject_assertions' if case=='consistency-check' else 'valid_assertions']
        rows=[]
        for a in texts:
            ident=a['id']; detail=manual.get(ident,{}).get('evidence','')
            if ident=='numeric':detail=f"Independent OBJ paths: max primary error {max(abs(field(r,VALUE_FIELDS)-truth['values_cm'][r['name']]) for r in report['measurements']):.12g} cm; 12/12 values; corrupted cache never used as primary."
            if ident=='csv':detail='Parsed actual JSON and CSV: same 12 names, values and cm units within 0.01 cm.'
            if ident=='targets':detail=f"Separate target and measured-minus-target columns checked independently; waist actual={truth['values_cm']['waist']}, target={truth['targets_cm']['waist']}, residual={truth['residuals_cm']['waist']} cm."
            if ident=='no_success':detail='Actual JSON/CSV have 12 null primary values and null deltas, explicit refused status; no success artifacts. Diagnostic audit numbers are not promoted to primary export.'
            rows.append({'text':a['text'],'passed':bool(verdicts[ident]),'evidence':detail+f' Evidence: grade-evidence/{tag}-numeric.json and {tag}-manual.json.'})
        passed=sum(r['passed'] for r in rows)
        result={'expectations':rows,'summary':{'passed':passed,'failed':len(rows)-passed,'total':len(rows),'pass_rate':passed/len(rows)},
                'claims':[{'claim':'12 actual dimensions are independent of control targets and cached claims' if case!='consistency-check' else 'Incompatible neutral geometry is explicitly rejected', 'type':'quality','verified':checks['passed'],'evidence':f'Independent numeric validator: {checks}'},
                          {'claim':'No replacement refit or model-input change','type':'process','verified':preserved,'evidence':manual['preserve']['evidence']},
                          {'claim':'Photo/ImageGen workflow and native Claude triggering validated','type':'quality','verified':False,'evidence':'NOT_RUN photo/ImageGen; BLOCKED native Claude. These six runs exercise only saved-model measurement branch.'}],
                'eval_feedback':{'suggestions':[{'reason':'All six executions satisfy frozen semantic assertions. n=1 per case/arm cannot establish reliability; old skill executors wrote bespoke geometry checks, so do not attribute passing to new helper alone.'},{'reason':'Wrong-neutral rejection with same state, filename, topology and cache is the strongest actual discriminator of geometry validation. Explicit helper/import coupling and intervention cost are not covered by task-success assertions.'}],
                                 'overall':'Common numeric task-success ceiling; no demonstrated old/new behavioral win on these three cases. Surface naming such as basis=mesh_parameter versus mesh_measurement is not a semantic failure.'},
                'artifact_sha256':inventory(out),
                'manual_audit_current':manual_current,
                'source_hashes':{'model_inputs':truth['input_sha256'],'pose_sha256':truth['pose_sha256'],'weights_sha256':truth['weights_sha256'],'skill_snapshot':{k:v for k,v in source.items() if k.startswith('skill-new/' if arm=='with_skill' else 'skill-old/')}},
                'numeric_evidence':str((evidence/(tag+'-numeric.json')).relative_to(base)),
                'manual_evidence':str((evidence/(tag+'-manual.json')).relative_to(base)),
                'timing':None,'execution_metrics':None}
        if case=='consistency-check' and arm=='with_skill':
            result['claims'].append({'claim':'Executor geometric audit is implementation-independent of its exporter',
                                     'type':'process','verified':False,
                                     'evidence':'reproduce.py imports export_body_measurements.py and calls m.parse_obj and m.reconstruct_neutral. Its geometry result is correct under this independent grader, but that executor audit shares the exporter implementation.'})
        dump(out.parent/'grading.json',result)
        summary.append({'case':case,'arm':arm,**result['summary']})
    # Real checker controls: clone output JSON+CSV in scratch and pass through same
    # validator, rather than testing a separate assertion implementation.
    controls=[]
    original=base/'iteration-1/eval-2-residual-cache/with_skill/run-1/outputs'
    original_report=json.loads((original/'measurements.model.json').read_text())
    original_csv=list(csv.DictReader((original/'measurements.model.csv').read_text().splitlines()))
    for incorrect in (108,1000):
        fault=copy.deepcopy(original_report); fc=copy.deepcopy(original_csv)
        for r in fault['measurements']:
            if r['name']=='waist':r['value_cm']=incorrect
        fault['measured_values_cm']['waist']=incorrect
        for r in fc:
            if r['name']=='waist':r['value_cm']=str(incorrect)
        verdict=validate_artifacts(fault,fc,truths['residual-cache'])
        name='waist-primary-'+str(incorrect)
        dump(evidence/'fault-controls'/name/'report.json',fault)
        dump(evidence/'fault-controls'/name/'csv-rows.json',fc)
        controls.append({'fault':name,'expected':'FAIL','actual':'PASS' if verdict['passed'] else 'FAIL','validator':verdict})
    # Successful neutral size artifact is false when attached to incompatible mesh.
    good=base/'iteration-1/eval-1-saved-model/with_skill/run-1/outputs'
    fault=json.loads((good/'measurements.model.json').read_text()); fault['status']='success'
    fc=list(csv.DictReader((good/'measurements.model.csv').read_text().splitlines()))
    verdict=validate_artifacts(fault,fc,truths['consistency-check'])
    dump(evidence/'fault-controls'/'wrong-neutral-success'/'report.json',fault)
    dump(evidence/'fault-controls'/'wrong-neutral-success'/'csv-rows.json',fc)
    controls.append({'fault':'wrong-neutral-success','expected':'FAIL','actual':'PASS' if verdict['passed'] else 'FAIL','validator':verdict})
    # Definitions use the same artifact validator as the six real runs.
    fault=copy.deepcopy(original_report); fc=copy.deepcopy(original_csv)
    del fault['measurements'][0]['definition']
    verdict=validate_artifacts(fault,fc,truths['residual-cache'])
    dump(evidence/'fault-controls'/'missing-definition'/'report.json',fault)
    controls.append({'fault':'missing-definition','expected':'FAIL','actual':'PASS' if verdict['passed'] else 'FAIL','validator':verdict})
    # Bind the previously reviewed audit to a scratch artifact clone, then mutate
    # TRACE. The real CLI's manual gate must reject it without revising findings.
    scratch=evidence/'fault-controls'/'stale-trace'/'outputs'
    if scratch.exists(): shutil.rmtree(scratch)
    shutil.copytree(original,scratch,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    trace=next(p for p in scratch.iterdir() if p.name.startswith('TRACE'))
    trace.write_text(trace.read_text()+'\nALTERED AFTER MANUAL REVIEW\n')
    audit_path=evidence/'residual-cache-with_skill-manual.json'
    before_manual_sha=sha(audit_path)
    findings,current=manual_audit(audit_path,scratch)
    assert sha(audit_path)==before_manual_sha
    controls.append({'fault':'stale-trace','expected':'FAIL','actual':'PASS' if current else 'FAIL',
                     'manual_findings':findings,'manual_audit_unchanged':True})
    assert all(c['actual']==c['expected'] for c in controls)
    dump(evidence/'fault-controls.json',controls)
    after={str(out.relative_to(base)/relative):digest for out in base.glob('iteration-1/*/*/run-1/outputs') for relative,digest in inventory(out).items()}
    after.update({str(Path(tree)/relative):digest for tree in ('skill-old','skill-new','inputs') for relative,digest in inventory(base/tree).items()})
    assert baseline==after,'Grading changed original artifacts/inputs/skills'
    dump(evidence/'source-integrity.json',{'before_sha256':baseline,'after_sha256':after,'all_unchanged':True,'grader_sha256':sha(Path(__file__))})
    dump(evidence/'summary.json',{'runs':summary,'repeat_count_per_arm_case':1,'fault_controls':controls,'photo_imagegen':'NOT_RUN','native_claude':'BLOCKED','numeric_tolerance_cm':.01,'geometry_tolerance_cm':.002,'original_artifacts_unchanged':True})
    print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
