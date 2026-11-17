#!/usr/bin/env python3
"""Independently reopen anatomical state-audit outputs; never trust a pass label."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import numpy as np


def grade(run, fixture, oracle, asset, spec):
    expectations = []
    output = run/'outputs'
    errors = []
    try:
        result = json.loads((output/'audit.json').read_text())
        cases = {row['file']: row for row in result['cases']}
        expected = json.loads(oracle.read_text())
        source = json.loads((fixture/'reference.json').read_text())
        payload = asset.read_bytes()
        assert hashlib.sha256(payload).hexdigest() == source['asset']
        data = json.loads(payload)
        vertices = np.array(data['vertices'], dtype=float).reshape(-1,3)
        for control, weight in zip(data['controls'], source['morphWeights']):
            rows = np.array(control['incr' if weight >= 0 else 'decr'],dtype=float)
            np.add.at(vertices, rows[:,0].astype(int), rows[:,1:]*abs(weight))
        truth = {}
        for control in data['controls']:
            if control['key'] == 'height':
                value = np.ptp(vertices[data['bodyVertexIds'],1])
            else:
                value = np.linalg.norm(np.diff(vertices[control['path']],axis=0),axis=1).sum()
            truth[control['key']] = float(value)
        obj = np.array([[float(v) for v in line.split()[1:4]] for line in (fixture/'posed-cm.obj').read_text().splitlines() if line.startswith('v ')])
        bbox = float(np.ptp(obj[:,1]))
        with (output/'measurements.csv').open(newline='') as stream:
            rows = list(csv.DictReader(stream))
        checks = [
            (set(cases)==set(expected['expected']) and all(cases[k]['classification']==v for k,v in expected['expected'].items()), 'classifications='+json.dumps({k:v.get('classification') for k,v in cases.items()})),
            (set(result['measurements'])==set(truth) and all(abs(result['measurements'][k]-v)<.002 for k,v in truth.items()) and cases['reference.json']['neutral_mesh_checked'] is True, 'NumPy sparse morph + fixed tape/landmark reconstruction independently checked all 12 dimensions'),
            (all(cases[k]['classification']=='invalid' for k in ['reported-bust.json','pose-joint.json']) and all(cases[k].get('reason') for k in ['reported-bust.json','pose-joint.json']), 'False bust and unknown pose bone both need explicit rejection reasons'),
            (cases['unreached-target.json']['classification']=='closest_supported' and abs(cases['unreached-target.json']['maximum_target_error_cm']-10)<.002, 'Actual neutral height='+str(truth['height'])+' cm vs target190 cm'),
            (abs(result['pose_bbox_height_cm']-bbox)<.002 and abs(bbox-truth['height'])>10, 'Actual posed OBJ Y extent='+str(bbox)+' cm; neutral height='+str(truth['height'])+' cm'),
            (result['basis']=='mesh_parameter' and result['camera_recovered'] is False and result['real_person_accuracy_established'] is False and len(rows)==12 and {r['key'] for r in rows}==set(truth) and all(r['basis']=='mesh_parameter' and r['unit']=='cm' and abs(float(r['value'])-truth[r['key']])<.002 for r in rows) and (output/'report.md').stat().st_size>100, 'CSV reopened: neutral mesh basis, cm units, unknown camera/person accuracy and report exist'),
            (all(hashlib.sha256((fixture/k).read_bytes()).hexdigest()==expected['sources'][k]==result['input_hashes'].get(k) for k in [*expected['expected'],'posed-cm.obj']), 'Independent SHA256 readback of all original six states and OBJ')
        ]
    except Exception as exc:
        errors.append(type(exc).__name__+': '+str(exc))
        checks = []
    for index, text in enumerate(spec['assertions']):
        passed, evidence = checks[index] if index < len(checks) else (False, 'Output could not be independently reopened: '+'; '.join(errors))
        expectations.append(dict(text=text, passed=bool(passed), evidence=evidence))
    passed = sum(row['passed'] for row in expectations)
    grading = dict(expectations=expectations, summary=dict(passed=passed, failed=len(expectations)-passed,total=len(expectations),pass_rate=passed/len(expectations)), evaluation_errors=errors)
    (run/'grading.json').write_text(json.dumps(grading,indent=2)+'\n')
    return grading


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',type=Path,required=True)
    parser.add_argument('--workspace',type=Path,required=True)
    args=parser.parse_args();root=Path(__file__).resolve().parents[2]
    spec=args.workspace/'state-case-spec.json'
    if not spec.is_file(): spec=args.run/'eval_metadata.json'
    result=grade(args.run,args.workspace/'fixtures/state-audit',args.workspace/'private-oracle/state-audit.json',root/'web/human-studio/assets/human.json',json.loads(spec.read_text()))
    print(json.dumps(result['summary']))
