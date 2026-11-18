#!/usr/bin/env python3
"""Measure a saved neutral Human Studio surface, never copy dimension targets.

Standard library only. Measurement paths are the asset's declared surface tapes
and landmark distances, not anatomical plane sections or real-person readings.
"""
import argparse
from collections import Counter
import csv
import hashlib
import io
import json
import math
from pathlib import Path

SCHEMA = 'model-derived-measurements-v1'
MODEL_VERSION = 'makehuman-cm-rig-v1'
MESH_TOLERANCE_CM = 0.002
KEYS = ('height', 'bust', 'waist', 'hips', 'shoulders', 'upperArm', 'thigh',
        'neck', 'upperArmLength', 'forearmLength', 'thighLength', 'calf')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def finite(value):
    return type(value) in (float, int) and math.isfinite(value)


def digest(value):
    return hashlib.sha256(value).hexdigest()


def parse_obj(raw):
    """Read only actual OBJ vertices/triangles; ignore materials and normals."""
    vertices, faces = [], []
    for number, line in enumerate(raw.decode('utf-8').splitlines(), 1):
        parts = line.split('#', 1)[0].split()
        if not parts:
            continue
        if parts[0] == 'v':
            require(len(parts) == 4, f'OBJ vertex {number} must contain exactly XYZ')
            try:
                row = tuple(float(x) for x in parts[1:])
            except ValueError as error:
                raise ValueError(f'Invalid OBJ vertex {number}') from error
            require(all(finite(x) for x in row), 'OBJ vertices must be finite')
            vertices.append(row)
        elif parts[0] == 'f':
            require(len(parts) == 4, 'Neutral OBJ must contain triangular faces')
            try:
                row = tuple(int(x.split('/')[0]) for x in parts[1:])
            except ValueError as error:
                raise ValueError(f'Invalid OBJ face {number}') from error
            require(all(x != 0 for x in row), 'OBJ face indices cannot be zero')
            row = tuple(x - 1 if x > 0 else len(vertices) + x for x in row)
            require(all(0 <= x < len(vertices) for x in row), 'OBJ face index outside vertices')
            require(len(set(row)) == 3, 'Degenerate OBJ triangle')
            faces.append(row)
    require(vertices and faces, 'Neutral OBJ must contain vertices and faces')
    return vertices, faces


def triangle_identity(face):
    # Face order and cyclic rotation are harmless; reversing winding is not.
    return min(tuple(face[i:] + face[:i]) for i in range(3))


def reconstruct_neutral(data, weights):
    """Replay saved coefficients only. Never solve/calibrate to input targets."""
    flat = data['vertices']
    require(len(flat) % 3 == 0 and all(finite(v) for v in flat), 'Invalid asset vertices')
    vertices = [list(flat[i:i + 3]) for i in range(0, len(flat), 3)]
    for control, weight in zip(data['controls'], weights):
        for row in control['incr' if weight >= 0 else 'decr']:
            require(len(row) == 4, 'Invalid morph row')
            index, *delta = row
            require(type(index) is int and 0 <= index < len(vertices), 'Invalid morph vertex index')
            require(all(finite(v) for v in delta), 'Invalid morph delta')
            for axis, value in enumerate(delta):
                vertices[index][axis] += abs(weight) * value
    floor = min(vertices[i][1] for i in data['bodyVertexIds'])
    return [tuple(vertices[i][a] - (floor if a == 1 else 0) for a in range(3))
            for i in data['bodyVertexIds']]


def measure(state, asset_bytes, neutral_obj_bytes, state_bytes=None, posed_obj_bytes=None):
    """Return actual mesh measurements plus separate input-target comparisons.

    ``state.measuredNeutral`` is deliberately never read. ``dimensions`` is used
    only after geometric measurement to show target-minus-achieved differences.
    """
    require(state.get('version') == MODEL_VERSION, 'Unsupported model version')
    require(state.get('units') == 'cm', 'State units must be cm')
    require(digest(asset_bytes) == state.get('asset'), 'Asset fingerprint mismatch')
    data = json.loads(asset_bytes)
    require(data.get('schema') == 1 and data.get('unit') == 'cm', 'Unsupported asset schema/units')
    controls = data['controls']
    require(tuple(c['key'] for c in controls) == KEYS, 'Expected all 12 canonical measurement controls')
    ids = data['bodyVertexIds']
    require(ids and all(type(i) is int and 0 <= i < len(data['vertices']) // 3 for i in ids)
            and len(ids) == len(set(ids)), 'Invalid compact body vertex mapping')
    compact = {source: i for i, source in enumerate(ids)}
    weights = state.get('morphWeights')
    require(isinstance(weights, list) and len(weights) == len(controls)
            and all(finite(w) and -2 <= w <= 2 for w in weights), 'Invalid saved morphWeights')
    vertices, faces = parse_obj(neutral_obj_bytes)
    require(len(vertices) == len(ids), 'Neutral OBJ vertex count differs from compact surface')
    indices = data['indices']
    require(len(indices) % 3 == 0 and all(type(i) is int and i in compact for i in indices),
            'Asset triangle indices differ from compact surface')
    expected_faces = [tuple(compact[i] for i in indices[n:n + 3]) for n in range(0, len(indices), 3)]
    require(Counter(triangle_identity(list(f)) for f in faces)
            == Counter(triangle_identity(list(f)) for f in expected_faces), 'Neutral OBJ topology/winding mismatch')
    reconstructed = reconstruct_neutral(data, weights)
    maximum_error = max(math.dist(a, b) for a, b in zip(vertices, reconstructed))
    require(maximum_error <= MESH_TOLERANCE_CM,
            'Neutral OBJ does not match saved neutral morph geometry; posed, changed or wrongly scaled mesh')
    # The numerical result below is computed from OBJ vertices, not reconstructed
    # coefficients and not the saved/claimed measuredNeutral field.
    values, rows = {}, []
    targets = state.get('dimensions', {})
    require(isinstance(targets, dict), 'dimensions targets must be a mapping')
    for c in controls:
        key = c['key']
        path = c.get('path', [])
        require(all(type(i) is int and i in compact for i in path), 'Measurement path leaves compact surface')
        mapped = [compact[i] for i in path]
        points = [vertices[i] for i in mapped]
        if key == 'height':
            value = max(p[1] for p in vertices) - min(p[1] for p in vertices)
            method = 'neutral_mesh_y_extent'
            definition = 'Y-axis extent of the neutral surface in centimetres; not posed bounding-box height.'
        else:
            require(len(points) >= 2, 'Missing surface measurement path')
            if c['kind'] == 'circumference':
                require(path[0] == path[-1], 'Circumference tape path must close')
                method = 'closed_neutral_surface_tape_polyline'
                definition = 'Length of the declared closed neutral surface tape; not a planar intersection circumference.'
            else:
                require(c['kind'] == 'landmark distance' and len(points) == 2, 'Unsupported landmark definition')
                method = 'neutral_surface_landmark_distance'
                definition = 'Straight distance between the declared two neutral surface landmarks; not bone-head length.'
            value = sum(math.dist(a, b) for a, b in zip(points, points[1:]))
        require(finite(value) and value > 0, 'Non-positive or invalid actual mesh measurement: ' + key)
        target = targets.get(key)
        require(target is None or (finite(target) and target > 0), 'Invalid comparison target: ' + key)
        values[key] = value
        rows.append(dict(name=key, label=c['label'], value_cm=value, unit='cm', basis='mesh_measurement',
                         definition=definition, method=method,
                         source_vertices=path, source_mesh_vertex_indices=mapped,
                         path_vertices_cm=[list(p) for p in points], mesh_checked=True,
                         body_parameter_target_cm=target,
                         input_target_delta_cm=value - target if target is not None else None,
                         parameter_basis='prior_or_fitted_parameter',
                         person_accuracy_verified=False))
    if state_bytes is None:
        state_bytes = json.dumps(state, sort_keys=True, separators=(',', ':')).encode()
    fingerprints = dict(state_sha256=digest(state_bytes), asset_sha256=digest(asset_bytes),
                        neutral_mesh_sha256=digest(neutral_obj_bytes))
    if posed_obj_bytes is not None:
        fingerprints['posed_mesh_sha256'] = digest(posed_obj_bytes)
    return dict(schema=SCHEMA, measurement_source='neutral_mesh', measurement_pose='neutral', units='cm',
                measured_values_cm=values,
                target_dimensions_cm={c['key']: targets.get(c['key']) for c in controls},
                measurements=rows, model_fingerprints=fingerprints,
                geometry_verification=dict(neutral_mesh_checked=True, topology_verified=True,
                    neutral_reconstruction_max_error_cm=maximum_error,
                    tolerance_cm=MESH_TOLERANCE_CM, vertices=len(vertices), triangles=len(faces),
                    posed_geometry_checked=False),
                person_accuracy_verified=False,
                limits=['These are measured values of the saved model, not verified measurements of the photographed person.',
                        'Input targets and any saved measuredNeutral claims are not measurement sources.',
                        'A supplied posed mesh is fingerprinted only; posed skinning/photo correspondence is not checked here.'])


def export_report(state_path, asset_path, neutral_path, posed_path=None):
    state_bytes = Path(state_path).read_bytes()
    return measure(json.loads(state_bytes), Path(asset_path).read_bytes(), Path(neutral_path).read_bytes(),
                   state_bytes=state_bytes,
                   posed_obj_bytes=Path(posed_path).read_bytes() if posed_path else None)


def csv_text(report):
    stream = io.StringIO(newline='')
    fields = ('name', 'label', 'value_cm', 'unit', 'basis', 'method', 'body_parameter_target_cm',
              'input_target_delta_cm', 'mesh_checked', 'person_accuracy_verified')
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator='\n')
    writer.writeheader()
    for row in report['measurements']:
        writer.writerow({key: row[key] for key in fields})
    return stream.getvalue()


def write_report(report, out, csv_path=None):
    """Write measured report and optional CSV with the same full-precision values."""
    text = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
    table = csv_text(report) if csv_path is not None else None
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text)
    if csv_path is not None:
        csv_path = Path(csv_path)
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        csv_path.write_text(table)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state', required=True, type=Path)
    parser.add_argument('--asset-json', required=True, type=Path)
    parser.add_argument('--neutral-mesh', required=True, type=Path)
    parser.add_argument('--posed-mesh', type=Path)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--csv', type=Path)
    args = parser.parse_args()
    # Reject before writing either output: no partial/new successful result on an
    # invalid mesh. Existing outputs are left untouched on validation failure.
    report = export_report(args.state, args.asset_json, args.neutral_mesh, args.posed_mesh)
    write_report(report, args.out, args.csv)
    print(json.dumps(dict(schema=SCHEMA, measurement_source='neutral_mesh',
                          measured_values_cm=report['measured_values_cm']), allow_nan=False))


if __name__ == '__main__':
    main()
