#!/usr/bin/env python3
"""Audit a Human Studio export; optionally reconstruct neutral mesh dimensions.

Standard library only. This does not certify posed skinning or photo accuracy.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re

RANGES = dict(height=(145,195), bust=(72,120), waist=(54,108), hips=(80,126),
              shoulders=(30,46), upperArm=(20,40), thigh=(40,76), neck=(28,44),
              upperArmLength=(24,38), forearmLength=(18,31), thighLength=(30,52), calf=(28,48))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def number(value):
    return type(value) in (int, float) and math.isfinite(value)


def audit(state, asset_bytes=None, expected_asset=None, require_match=False):
    require(state.get('version') == 'makehuman-cm-rig-v1', 'Unsupported model version')
    require(state.get('units') == 'cm', 'State units must be cm')
    require(isinstance(state.get('asset'), str) and re.fullmatch('[a-f0-9]{64}', state['asset']), 'Invalid asset SHA256')
    if expected_asset:
        require(state['asset'] == expected_asset, 'Expected asset fingerprint mismatch')
    for field in ('dimensions', 'measuredNeutral'):
        values = state.get(field)
        require(isinstance(values, dict) and set(values) == set(RANGES), field + ' must contain all 12 controls')
        require(all(number(v) and v > 0 for v in values.values()), field + ' must contain finite positive numbers')
    for key, (low, high) in RANGES.items():
        value = state['dimensions'][key]
        require(low <= value <= high and abs(value * 10 - round(value * 10)) < 1e-7, 'Invalid target: ' + key)
    weights = state.get('morphWeights')
    require(isinstance(weights, list) and len(weights) == 12 and all(number(v) and -2 <= v <= 2 for v in weights), 'Invalid morphWeights')
    pose = state.get('poseDegrees')
    require(isinstance(pose, dict), 'Missing poseDegrees map')
    for key, triple in pose.items():
        require(isinstance(key, str) and key and isinstance(triple, list) and len(triple) == 3
                and all(number(v) and -180 <= v <= 180 and abs(v*10-round(v*10)) < 1e-7 for v in triple), 'Invalid joint rotation')
    residual = max(abs(state['dimensions'][k] - state['measuredNeutral'][k]) for k in RANGES)
    reported = state.get('maximumTargetErrorCm')
    require(number(reported) and reported >= 0 and abs(reported-residual) < .002, 'False maximumTargetErrorCm')
    result = dict(verdict='STRUCTURE_ONLY', neutral_mesh_checked=False,
                  asset=state['asset'], units='cm', reportedMaximumTargetErrorCm=residual,
                  dimensions_matched=None,
                  limits='No posed skinning, camera, photo match or real-person accuracy validation.')
    if asset_bytes is not None:
        require(hashlib.sha256(asset_bytes).hexdigest() == state['asset'], 'Asset bytes fingerprint mismatch')
        data = json.loads(asset_bytes)
        require(data.get('schema') == 1 and data.get('unit') == 'cm', 'Unsupported asset schema/units')
        controls = data['controls']
        require([c['key'] for c in controls] == list(RANGES), 'Unexpected morph control order')
        require(set(pose) <= {b['name'] for b in data['bones']}, 'Unknown pose bone')
        positions = list(data['vertices'])
        require(len(positions) % 3 == 0 and all(number(v) for v in positions), 'Invalid asset vertices')
        for control, weight in zip(controls, weights):
            for index, x, y, z in control['incr' if weight >= 0 else 'decr']:
                require(type(index) is int and 0 <= index < len(positions)//3, 'Invalid morph index')
                for axis, delta in enumerate((x,y,z)):
                    require(number(delta), 'Invalid morph delta')
                    positions[index*3+axis] += abs(weight)*delta
        ys = [positions[i*3+1] for i in data['bodyVertexIds']]
        measured = {'height': max(ys)-min(ys)}
        # Translation to the floor cancels in path lengths and the height range.
        for control in controls[1:]:
            path = control['path']
            require(len(path) >= 2, 'Missing measurement path')
            measured[control['key']] = sum(math.dist(positions[a*3:a*3+3], positions[b*3:b*3+3]) for a,b in zip(path,path[1:]))
        difference = max(abs(measured[k]-state['measuredNeutral'][k]) for k in RANGES)
        require(difference < .002, 'Saved measuredNeutral disagrees with reconstructed mesh')
        residual = max(abs(measured[k]-state['dimensions'][k]) for k in RANGES)
        result.update(verdict='PASS', neutral_mesh_checked=True, measuredNeutral=measured,
                      maximumReconstructionDifferenceCm=difference, maximumTargetErrorCm=residual,
                      dimensions_matched=residual <= .2)
    if require_match:
        require(asset_bytes is not None, '--require-match needs --asset-json for independent measurement')
        require(result['dimensions_matched'], 'Reconstructed target residual exceeds 0.2 cm')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state', type=Path, required=True)
    parser.add_argument('--asset-json', type=Path)
    parser.add_argument('--expected-asset')
    parser.add_argument('--require-match', action='store_true')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    try:
        result = audit(json.loads(args.state.read_text()), args.asset_json.read_bytes() if args.asset_json else None,
                       args.expected_asset, args.require_match)
    except (ValueError, KeyError, TypeError, IndexError, OSError) as exc:
        result = dict(verdict='FAIL', error=str(exc))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps(result, allow_nan=False))
    return 2 if result['verdict'] == 'FAIL' else 0


if __name__ == '__main__':
    raise SystemExit(main())
