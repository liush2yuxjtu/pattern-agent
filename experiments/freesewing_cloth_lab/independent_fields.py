"""Independent upstream re-draft, material coordinates, mass and hinge fields.

No application JS is imported. Node runs only the pinned upstream Sandy design;
Python uses de Casteljau interpolation and vectorized face-normal geometry.
"""
from functools import lru_cache
import json
from pathlib import Path
import subprocess

import numpy as np


@lru_cache(maxsize=16)
def upstream(waist, length, ratio):
    script = Path(__file__).with_name('redraft_source.mjs')
    return json.loads(subprocess.check_output(
        ['node', str(script)], input=json.dumps({'waist_mm': waist, 'length_mm': length, 'circleRatio': ratio}), text=True))


def redraft(data):
    p = data['parameters']
    return upstream(p['waist_m'] * 1000, p['slant_m'] * 1000, p['circle_ratio'])


def freesewing_reopen(data):
    native = redraft(data)
    profile = data['freesewing']
    assert profile['engine'] == 'FreeSewing' and profile['design'] == 'Sandy' and profile['version'] == '4.10.2'
    assert profile['settings'] == native['settings']
    assert profile['waistbandSimulated'] is False
    pts = {key: np.array(value) for key, value in native['points'].items()}
    center, fold = pts['center'], pts['in2Flipped']
    radius = np.linalg.norm(fold - center)
    axis = (fold - center) / radius
    across = np.array([axis[1], -axis[0]])
    names = {'inner': [['in2Flipped', 'in2cFlipped', 'in1cFlipped', 'in1'], ['in1', 'in1c', 'in2c', 'in2']],
             'outer': [['ex2Flipped', 'ex2cFlipped', 'ex1cFlipped', 'ex1'], ['ex1', 'ex1c', 'ex2c', 'ex2']]}
    for name, groups in names.items():
        expected = np.array([[pts[key] for key in group] for group in groups])
        assert np.max(np.abs(expected - profile['halfPanel'][name])) < 1e-9

    def sample(row, col):
        signed = 2 * col - 1
        t = abs(signed) * 2
        segment = min(1, int(t))
        u = t - segment
        result = []
        for name in ['inner', 'outer']:
            q = np.array([pts[key] for key in names[name][segment]])
            while len(q) > 1:
                q = q[:-1] * (1 - u) + q[1:] * u
            delta = q[0] - center
            result.append(np.array([delta @ across, delta @ axis - radius]))
        v = result[0] * (1 - row) + result[1] * row
        v[0] *= -1 if signed < 0 else 1
        return v

    nc, nr = data['parameters']['NC'], data['parameters']['NR']
    per = nc // 4
    faces = np.asarray(data['triangles']).reshape(-1, 3)
    uv = np.asarray(data['materialCoordinates']).reshape(-1, 3, 2)
    maximum = 0.
    covered = []
    for k, panel in enumerate(data['panels']):
        covered += panel['faces']
        assert len(panel['faces']) == nr * per * 2
        expected_poly = [sample(0, j / (per * 4)) for j in range(per * 4 + 1)]
        expected_poly += [sample(1, 1)] + [sample(1, j / (per * 4)) for j in reversed(range(per * 4))]
        assert np.max(np.abs(np.array(expected_poly) - panel['polygon'])) < 1e-7
        expected = []
        for face in faces[panel['faces']]:
            corners = []
            for vertex in face:
                row, column = divmod(vertex, nc)
                local = (column - k * per) % nc
                if k == 3 and column == 0:
                    local = per
                assert 0 <= local <= per
                corners.append(sample(row / nr, local / per) / 1000)
            expected.append(corners)
        maximum = max(maximum, float(np.max(np.abs(np.array(expected) - uv[panel['faces']]))))
    assert sorted(covered) == list(range(len(faces)))
    assert maximum < 1e-10
    d1, d2 = uv[:, 1] - uv[:, 0], uv[:, 2] - uv[:, 0]
    areas = abs(d1[:, 0] * d2[:, 1] - d1[:, 1] * d2[:, 0]) / 2
    masses = np.zeros(len(data['positions']) // 3)
    for j in range(3):
        np.add.at(masses, faces[:, j], areas * data['material']['density'] / 3)
    inverse = np.asarray(data['inverseMass'])
    assert np.all(inverse[:nc] == 0)
    relative = float(np.max(np.abs(inverse[nc:] * masses[nc:] - 1)))
    assert relative < 1e-12
    return {'upstream': '@freesewing/sandy@4.10.2', 'maxMaterialCoordinateError_m': maximum,
            'maxLumpedMassRelativeError': relative, 'materialArea_m2': float(areas.sum()), 'mass_kg': float(areas.sum() * data['material']['density'])}


def folds_reopen(data):
    points = np.asarray(data['positions']).reshape(-1, 3)
    faces = np.asarray(data['triangles']).reshape(-1, 3)
    uv = np.asarray(data['materialCoordinates']).reshape(-1, 3, 2)
    normal = np.cross(points[faces[:, 1]] - points[faces[:, 0]], points[faces[:, 2]] - points[faces[:, 0]])
    twice_area = np.linalg.norm(normal, axis=1)
    normal /= twice_area[:, None]
    expected = {}
    pending = {}
    for t, face in enumerate(faces):
        for j in range(3):
            a, b, c = map(int, np.roll(face, -j))
            key = tuple(sorted((a, b)))
            if key in pending:
                a0, b0, c0, left = pending.pop(key)
                assert (a, b) == (b0, a0)
                edge = points[b0] - points[a0]
                length = np.linalg.norm(edge)
                theta = float(np.arctan2(np.dot(edge / length, np.cross(normal[left], normal[t])), np.dot(normal[left], normal[t])))
                dual = float((twice_area[left] + twice_area[t]) / (3 * length))
                expected[key] = (a0, b0, c0, c, left, t, theta, dual, theta / dual)
            else:
                pending[key] = (a, b, c, t)
    fields = data['folding']
    assert len(expected) == len(fields['hinges'])
    errors = {'angle_rad': 0., 'curvature_per_m': 0., 'currentDualLength_m': 0.}
    incident = [[] for _ in faces]
    seen = set()
    for i, hinge in enumerate(fields['hinges']):
        key = tuple(sorted((hinge['a'], hinge['b'])))
        assert key not in seen
        seen.add(key)
        a, b, c, d, left, right, angle, dual, curvature = expected[key]
        assert [hinge[x] for x in ['a', 'b', 'c', 'd', 'left', 'right']] == [a, b, c, d, left, right]
        for name, value in [('angle_rad', angle), ('curvature_per_m', curvature), ('currentDualLength_m', dual)]:
            errors[name] = max(errors[name], abs(fields[name][i] - value))
        for t in [left, right]:
            incident[t].append((angle * 180 / np.pi, curvature))
    assert errors['angle_rad'] < 1e-9 and errors['curvature_per_m'] < 1e-7 and errors['currentDualLength_m'] < 1e-10
    for t, values in enumerate(incident):
        for column, name in [(0, 'triangleAngle_deg'), (1, 'triangleCurvature_per_m')]:
            expected_values = np.array(values)[:, column]
            actual = fields[name][t]
            assert np.min(abs(expected_values - actual)) < 1e-7
            assert abs(abs(actual) - np.max(abs(expected_values))) < 1e-7
    proxy = 100 * np.mean(abs(np.asarray(fields['triangleAngle_deg'])) >= 15)
    assert abs(proxy - data['simulation']['wrinkleProxyTrianglePercent']) < 1e-10
    return {'hinges': len(expected), 'maxErrors': errors, 'wrinkleProxyFacePercent': float(proxy),
            'peakAngle_deg': float(np.max(abs(np.asarray(fields['angle_rad']))) * 180 / np.pi),
            'peakSpatialCurvature_per_m': float(np.max(abs(np.asarray(fields['curvature_per_m'])))),
            'physicalCreaseCalibration': 'NOT_RUN'}
