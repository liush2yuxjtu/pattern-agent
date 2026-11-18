"""Source-bound U-unit static assembly for the offline intent review.

Reads every actual DXF again.  Only parse_dxf, constrained triangulate and the
generic harmonic solver are reused from the existing preview service.  The
service's millimetre registration, garment corrections and sewn.build are never
called. No historic GLB is read, resized or used as a mesh template.
"""
from __future__ import annotations

from collections import defaultdict, deque
from copy import deepcopy
from decimal import Decimal
from pathlib import Path
import argparse
import hashlib
import json
import math
import sys

import numpy as np
import yaml

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / 'services/dxf-preview'))
from converter.core import parse_dxf
from converter.sewn import triangulate, harmonic

CASES = ['baseline', '01_sleeve_length', '02_body_length', '03_cuff_width', '04_front_neck']
TOLERANCE_U = .05


def sha(data):
    return hashlib.sha256(data).hexdigest()


def clean(value):
    if isinstance(value, np.ndarray): return clean(value.tolist())
    if isinstance(value, np.generic): return clean(value.item())
    if isinstance(value, float):
        if not math.isfinite(value): raise ValueError('Nonfinite geometry')
        return round(value, 7)
    if isinstance(value, dict): return {k: clean(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)): return [clean(v) for v in value]
    return value


def point_xy(point):
    return np.array([point['横'], point['高']], dtype=float)


def canonical(points):
    return tuple(tuple(round(float(v), 6) for v in p) for p in points)


def source_map(baseline, polylines):
    lookup = defaultdict(deque)
    for index, curve in enumerate(polylines): lookup[canonical(curve)].append(index)
    result = {}
    for name, piece in baseline['完整二维几何'].items():
        origin = piece['排版放置点']
        result[name] = {}
        for curve in piece['线条']:
            if curve['线型'] != '折线': continue
            points = [[float(Decimal(str(p[k])) + Decimal(str(origin[k]))) for k in ('横', '高')]
                      for p in curve['点位']]
            matches = lookup[canonical(points)]
            if not matches: raise ValueError('Missing original DXF binding: ' + curve['名称'])
            result[name][curve['名称']] = matches.popleft()
    if any(lookup.values()): raise ValueError('Unbound DXF polylines')
    return result


def curve_length(points):
    return float(np.linalg.norm(np.diff(points, axis=0), axis=1).sum())


def fractions(points):
    distances = np.r_[0., np.cumsum(np.linalg.norm(np.diff(points, axis=0), axis=1))]
    if distances[-1] <= 0: raise ValueError('Degenerate source curve')
    return distances / distances[-1]


def get_sources(model, polylines, bindings):
    sources = {}
    for name, piece in model['完整二维几何'].items():
        origin = point_xy(piece['排版放置点'])
        curves = {}
        for curve in piece['线条']:
            if curve['线型'] != '折线': continue
            index = bindings[name][curve['名称']]
            actual = np.asarray(polylines[index], dtype=float) - origin
            declared = np.array([point_xy(p) for p in curve['点位']])
            if actual.shape != declared.shape or np.max(np.abs(actual - declared)) > 1.1e-6:
                raise ValueError('Actual DXF differs from selected YAML: ' + curve['名称'])
            curves[curve['名称']] = actual
        sources[name] = {'curves': curves, 'origin': origin, 'piece': piece, 'bindings': bindings[name]}
    return sources


def contour(source):
    """A real named inner contour with explicit tiny drafting-junction joins."""
    points, refs, edges, joins = [], [], [], []
    for edge in source['piece']['轮廓']['内圈']['组成']:
        name = edge['线条']; raw = source['curves'][name]
        indices = list(range(len(raw)))
        if edge['方向'] == '反向': indices.reverse()
        walked = raw[indices]; t = fractions(walked)
        start = 0
        if points:
            gap = float(np.linalg.norm(points[-1] - walked[0]))
            if gap > TOLERANCE_U: raise ValueError(f'Unresolved display contour junction {name}: {gap}U')
            joins.append({'incoming_curve': name, 'gap_U': gap, 'handling': 'drop next coincident/near first sample; preserve previous exact source vertex'})
            start = 1
        begin = len(points)
        for j in range(start, len(indices)):
            points.append(walked[j].copy())
            refs.append({'curve': name, 'polyline_index': source['bindings'][name], 'vertex_index': indices[j], 'walk_parameter': float(t[j])})
        edges.append({'curve': name, 'polyline_index': source['bindings'][name], 'direction': edge['方向'], 'appended_boundary_range': [begin, len(points)]})
    gap = float(np.linalg.norm(points[-1] - points[0]))
    if gap > TOLERANCE_U: raise ValueError('Open selected display contour')
    joins.append({'incoming_curve': edges[0]['curve'], 'gap_U': gap, 'handling': 'drop duplicate closing source vertex'})
    points.pop(); refs.pop()
    edges[-1]['appended_boundary_range'][1] = len(points)
    # Preserve exact surviving source vertices; the only implicit segments are
    # the recorded sub-0.05U source drafting joins.
    return np.asarray(points), refs, edges, joins


def baseline_pose(model):
    front = model['完整二维几何']['前片']['定位点']
    back = model['完整二维几何']['后片']['定位点']
    sleeve = model['完整二维几何']['袖片']['定位点']
    fy = (front['前片图面左侧肩袖交点']['高'] + front['前片图面右侧肩袖交点']['高']) / 2
    by = (back['后片图面左侧肩袖交点']['高'] + back['后片图面右侧肩袖交点']['高']) / 2
    body = {}
    for label, marks, off in [('前片', front, 0.), ('后片', back, fy - by)]:
        prefix = label
        under = np.mean([marks[prefix + '图面' + side + '侧腋下点']['高'] for side in ['左', '右']])
        shoulder = np.mean([marks[prefix + '图面' + side + '侧肩袖交点']['高'] for side in ['左', '右']])
        neck_half = np.mean([abs(marks[prefix + '图面' + side + '侧领肩交点']['横']) for side in ['左', '右']])
        body[label] = {'y_offset_U': float(off), 'underarm_y_U': float(under), 'shoulder_y_U': float(shoulder),
                       'neck_half_width_U': float(neck_half), 'neck_depth_display_U': 65. if label == '前片' else 48.,
                       'arm_depth_display_U': 70., 'hem_depth_display_U': 92., 'interior_bulge_U': 48.}
    sx = np.mean([abs(front['前片图面右侧肩袖交点']['横']), abs(back['后片图面右侧肩袖交点']['横'])])
    ux = np.mean([abs(front['前片图面右侧腋下点']['横']), abs(back['后片图面右侧腋下点']['横'])]) * .72
    uy = np.mean([body['前片']['underarm_y_U'], body['后片']['underarm_y_U'] + body['后片']['y_offset_U']])
    shoulder = np.array([sx, fy]); under = np.array([ux, uy]); center = (shoulder + under) / 2; major = (shoulder - under) / 2
    return {'units': 'U', 'axis': 'X right, Y up, Z front; no physical conversion', 'body': body,
            'sleeve_root_center_U': [float(center[0]), float(center[1]), 0.],
            'sleeve_root_major_U': [float(major[0]), float(major[1]), 0.],
            'sleeve_root_depth_U': 70., 'sleeve_axis': [.36, -math.sqrt(1 - .36**2), 0.],
            'sleeve_transition_U': 45., 'sleeve_underarm_source_y_U': float(np.mean([sleeve['袖片图面左侧腋下点']['高'], sleeve['袖片图面右侧腋下点']['高']])),
            'band_fold_display': {'profile': 'sinusoidal illustrative fold', 'height_fraction_of_flat_width': .5, 'radial_fraction_of_flat_width': .05,
                                  'approval': 'display-only; actual fold/workmanship unconfirmed'},
            'placement_policy': 'Calculated from baseline once and reused byte-for-byte for every edited model.'}


def side_at(source, side, y):
    curves = [points for name, points in source['curves'].items()
              if source['piece'] and (('图面' + side + '侧边') in name)]
    if not curves: raise ValueError('Missing side outline')
    points = np.vstack(curves); order = np.argsort(points[:, 1]); points = points[order]
    ys, indices = np.unique(points[:, 1], return_index=True); xs = points[indices, 0]
    return np.interp(np.atleast_1d(y), ys, xs)


def body_map(source, label, uv, refs, pose):
    cfg = pose['body'][label]; sign = 1 if label == '前片' else -1
    targets = []
    for p, ref in zip(uv, refs):
        x, y = p; half = float((side_at(source, '右', y)[0] - side_at(source, '左', y)[0]) / 2)
        theta = float(np.clip(x / half, -1, 1)) * np.pi / 2
        alpha = float(np.clip((y - cfg['underarm_y_U']) / (cfg['shoulder_y_U'] - cfg['underarm_y_U']), 0, 1))
        X = (1 - alpha) * half * .72 * math.sin(theta) + alpha * x
        name = ref['curve']
        if '领口' in name:
            depth = cfg['neck_depth_display_U'] * max(0., math.cos(np.pi * x / (2 * cfg['neck_half_width_U'])))
        elif '袖窿' in name:
            depth = cfg['arm_depth_display_U'] * math.sin(np.pi * ref['walk_parameter'])
        elif '下摆' in name:
            depth = cfg['hem_depth_display_U'] * max(0., math.cos(theta))
        else: depth = 0.
        targets.append([X, y + cfg['y_offset_U'], sign * depth])
    return np.asarray(targets)


def edge_distance(points, boundary):
    result = np.full(len(points), np.inf)
    for a, b in zip(boundary, np.roll(boundary, -1, axis=0)):
        v = b - a; norm = float(v @ v)
        if norm == 0: continue
        t = np.clip(((points - a) @ v) / norm, 0, 1)
        result = np.minimum(result, np.linalg.norm(points - a - t[:, None] * v, axis=1))
    return result


def sleeve_domain(source, boundary, refs):
    side_curves = [points for name, points in source['curves'].items() if '袖底边' in name and '外' not in name]
    if len(side_curves) != 2: raise ValueError('Need two actual inner sleeve side edges')
    side_lengths = [curve_length(curve) for curve in side_curves]
    cuffs = [points for name, points in source['curves'].items() if name.startswith('袖片袖口横线')]
    cuff = np.vstack(cuffs); xmin, xmax = float(cuff[:, 0].min()), float(cuff[:, 0].max())
    underarm_y = float(np.mean([curve[np.argmax(curve[:, 1]), 1] for curve in side_curves]))
    cuff_y = float(cuff[:, 1].mean()); L = underarm_y - cuff_y
    if L <= 0: raise ValueError('Nonpositive sleeve axial source span')
    apex = point_xy(source['piece']['定位点']['袖山中接点'])
    domains = []
    for point, ref in zip(boundary, refs):
        name = ref['curve']; raw = source['curves'][name]; i = ref['vertex_index']
        s = fractions(raw)[i]
        if '袖山' in name:
            if np.linalg.norm(raw[-1] - apex) < np.linalg.norm(raw[0] - apex): s = 1 - s
            domains.append([0., (1 if '图面左' in name else -1) * np.pi * s])
        elif '袖底边' in name:
            if raw[0, 1] < raw[-1, 1]: s = 1 - s
            domains.append([L * s, np.pi if '图面左' in name else -np.pi])
        elif '袖口' in name:
            domains.append([L, np.pi - 2 * np.pi * (point[0] - xmin) / (xmax - xmin)])
        else: raise ValueError('Unexpected sleeve contour edge: ' + name)
    return np.asarray(domains), {'axis_length_U': L, 'underarm_source_y_U': underarm_y, 'side_length_mean_U': float(np.mean(side_lengths)),
                                 'side_lengths_U': side_lengths, 'cuff_source_y_U': cuff_y,
                                 'cuff_width_U': xmax - xmin, 'display_cap_mapping': 'left half -> positive Z, right half -> negative Z; actual front/back remains unconfirmed'}


def sleeve_map(source, domains, config, pose, sign):
    u, theta = domains.T; L = config['axis_length_U']
    source_y = config['underarm_source_y_U'] + np.clip(u / L, 0, 1) * (config['cuff_source_y_U'] - config['underarm_source_y_U'])
    sides = {}
    for side in ['左', '右']:
        q = next(v for k, v in source['curves'].items() if k == '袖片图面' + side + '袖底边')
        order = np.argsort(q[:, 1]); sides[side] = np.interp(source_y, q[order, 1], q[order, 0])
    radius = (sides['右'] - sides['左']) / (2 * np.pi)
    if np.min(radius) <= 0: raise ValueError('Nonpositive sleeve display radius')
    w = np.clip(u / pose['sleeve_transition_U'], 0, 1); w = w * w * (3 - 2 * w)
    axis = np.array(pose['sleeve_axis']); axis[0] *= sign
    perpendicular = np.array([-axis[1] * sign, abs(axis[0]), 0.])
    major = np.array(pose['sleeve_root_major_U']); major[0] *= sign
    major = (1 - w[:, None]) * major + w[:, None] * radius[:, None] * perpendicular
    minor = (1 - w) * pose['sleeve_root_depth_U'] + w * radius
    center = np.array(pose['sleeve_root_center_U']); center[0] *= sign
    result = center + u[:, None] * axis + major * np.cos(theta)[:, None]
    result[:, 2] += minor * np.sin(theta)
    return result


def full_neck(source, label, pose):
    curves, refs = [], []
    for side in ['左', '右']:
        name = label + '图面' + side + '领口'; q = source['curves'][name]
        idx = list(range(len(q)))
        if q[0, 0] > q[-1, 0]: idx.reverse()
        q = q[idx]
        if curves: q = q[1:]; idx = idx[1:]
        curves.extend(q)
        refs.extend({'curve': name, 'polyline_index': source['bindings'][name], 'vertex_index': i, 'walk_parameter': 0.} for i in idx)
    return body_map(source, label, np.asarray(curves), refs, pose)


def band_map(points, source, front_source, back_source, pose):
    a = full_neck(front_source, '前片', pose); b = full_neck(back_source, '后片', pose)[::-1]
    ring = np.vstack([a, b, a[:1]])
    d = np.r_[0., np.cumsum(np.linalg.norm(np.diff(ring, axis=0), axis=1))]
    marks = source['piece']['定位点']; xmin = marks['领条内圈左下角']['横']; xmax = marks['领条内圈右下角']['横']
    ymin = marks['领条内圈左下角']['高']; ymax = marks['领条内圈左上角']['高']; width = ymax - ymin
    t = np.clip((points[:, 0] - xmin) / (xmax - xmin), 0, 1); v = np.clip((points[:, 1] - ymin) / width, 0, 1)
    base = np.column_stack([np.interp(t * d[-1], d, ring[:, j]) for j in range(3)])
    radial = base[:, [0, 2]]; radial /= np.maximum(np.linalg.norm(radial, axis=1, keepdims=True), 1e-12)
    offsets = width * pose['band_fold_display']['radial_fraction_of_flat_width'] * np.sin(2 * np.pi * v)
    base[:, 0] += radial[:, 0] * offsets; base[:, 2] += radial[:, 1] * offsets
    base[:, 1] += width * pose['band_fold_display']['height_fraction_of_flat_width'] * np.sin(np.pi * v)
    return base, {'neck_ring_U': ring.tolist(), 'neck_ring_length_U': float(d[-1]), 'flat_length_U': float(xmax - xmin), 'flat_width_U': float(width),
                  'mapping': 'normalized actual strip x follows current displayed neck ring; full strip y is an illustrative fold, not certified fabric stretch'}


def normals(vertices, faces):
    face = np.cross(vertices[faces[:, 1]] - vertices[faces[:, 0]], vertices[faces[:, 2]] - vertices[faces[:, 0]])
    result = np.zeros_like(vertices)
    for j in range(3): np.add.at(result, faces[:, j], face)
    lengths = np.linalg.norm(result, axis=1, keepdims=True)
    if np.min(lengths) < 1e-10: raise ValueError('Unused or degenerate display vertex normal')
    return result / lengths


def build_panel(source, label, kind, pose, spacing, front_source=None, back_source=None, sign=1):
    boundary, refs, edge_refs, joins = contour(source)
    uv, faces, edges = triangulate(boundary, spacing)
    count = len(boundary); extra = {}
    if kind == 'body':
        boundary_targets = body_map(source, label, boundary, refs, pose)
        positions, _ = harmonic(uv, faces, edges, boundary_targets)
        distances = edge_distance(uv, boundary)
        direction = 1 if label == '前片' else -1
        positions[:, 2] += direction * pose['body'][label]['interior_bulge_U'] * (1 - np.exp(-distances / 35.))
        positions[:count] = boundary_targets
        extra = {'map': 'body-harmonic-plus-source-boundary-bulge', 'boundary_targets_U': boundary_targets.tolist(), 'distance_to_boundary_U': distances.tolist()}
    elif kind == 'sleeve':
        boundary_domains, config = sleeve_domain(source, boundary, refs)
        domains, _ = harmonic(uv, faces, edges, boundary_domains)
        positions = sleeve_map(source, domains, config, pose, sign)
        extra = {'map': 'sleeve-harmonic-domain-to-static-tube', 'domain': domains.tolist(), 'boundary_domains': boundary_domains.tolist(),
                 'source_config': config, 'instance_sign': sign}
    else:
        positions, config = band_map(uv, source, front_source, back_source, pose)
        extra = {'map': 'current-neck-ring-with-illustrative-band-fold', 'source_config': config}
    values = normals(positions, faces)
    if not np.isfinite(positions).all(): raise ValueError('Nonfinite model position')
    source_curves = {name: points.tolist() for name, points in source['curves'].items()}
    return clean({'id': 'front' if label == '前片' else 'back' if label == '后片' else 'sleeve_a' if kind == 'sleeve' and sign < 0 else 'sleeve_b' if kind == 'sleeve' else 'band',
                  'label': label if kind != 'sleeve' else '袖片展示实例' + ('A' if sign < 0 else 'B'), 'source_piece': label,
                  'positions': positions, 'triangles': faces, 'normals': values, 'uv': uv,
                  'binding': {'uv_coordinate_system': 'piece-local DXF U coordinates', 'dxf_layout_origin_U': source['origin'],
                              'selected_contour': '内圈（仅展示选择，不批准为净样）', 'boundary_vertex_count': count,
                              'boundary_sources': refs, 'edges': edge_refs, 'joins': joins, 'display_junction_tolerance_U': TOLERANCE_U,
                              'source_piece_polyline_sha256': sha(json.dumps(source_curves, sort_keys=True, separators=(',', ':')).encode()),
                              'placement': 'All positions baked in the shared U-unit pose; identity node transform.'},
                  'construction': extra})


def build_model(case_id, baseline, bindings, pose, spacing):
    if case_id == 'baseline':
        dxf = REPO / 'patterns/fitted-tshirt/input.dxf'; spec = REPO / 'patterns/fitted-tshirt/input-spec.yaml'
    else:
        dxf = REPO / 'experiments/intent-edit-benchmark/results' / case_id / 'output.dxf'
        spec = dxf.with_name('new-spec.yaml')
    dxf_bytes = dxf.read_bytes(); spec_bytes = spec.read_bytes(); model = yaml.safe_load(spec_bytes)
    if model['单位与坐标']['坐标单位'] != 'U':
        raise ValueError('This static display expects the declared U coordinate model; no implicit unit conversion')
    polylines, source_counts = parse_dxf(dxf_bytes)
    sources = get_sources(model, polylines, bindings)
    panels = [build_panel(sources[label], label, 'body', pose, spacing) for label in ['前片', '后片']]
    panels += [build_panel(sources['袖片'], '袖片', 'sleeve', pose, spacing, sign=sign) for sign in [-1, 1]]
    panels += [build_panel(sources['领条'], '领条', 'band', pose, spacing, front_source=sources['前片'], back_source=sources['后片'])]
    bounds = np.vstack([np.asarray(panel['positions']) for panel in panels])
    return clean({'format': 'source-bound-static-assembly/1', 'id': case_id, 'units': 'U',
        'mode': 'static_geometric_assembly', 'physical_fit': 'NOT_RUN', 'cloth_simulation': 'NOT_RUN', 'sewing_validation': 'NOT_RUN',
        'source_unit_calibration': deepcopy(model['单位与坐标']['实际比例']),
        'source_dxf': str(dxf.relative_to(REPO)), 'source_spec': str(spec.relative_to(REPO)),
        'source_dxf_sha256': sha(dxf_bytes), 'source_spec_sha256': sha(spec_bytes), 'source_counts': source_counts,
        'pose': pose, 'spacing_U': spacing, 'bounds_U': {'min': bounds.min(0), 'max': bounds.max(0)}, 'panels': panels,
        'limits': ['U未标定，不代表毫米或米。', '从各自DXF真实裁片重建的静态几何示意，不是布料仿真。',
                   '源内圈仅用作展示轮廓；净裁角色、裁数、纱向、袖山前后及工艺仍待确认。',
                   '两只袖子为镜像展示实例，不批准镜像裁剪；衣领折叠和摆放是显式展示假设。',
                   '裁片接口未进行生产级缝合与相交验收；不得以可旋转模型代替版型或合身通过。']})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument('--spacing', type=float, default=18.)
    args = parser.parse_args()
    if not 8 <= args.spacing <= 30: parser.error('display spacing must be between 8 and 30 U')
    args.output.mkdir(parents=True, exist_ok=True)
    base_spec = (REPO / 'patterns/fitted-tshirt/input-spec.yaml').read_bytes(); baseline = yaml.safe_load(base_spec)
    polylines, _ = parse_dxf((REPO / 'patterns/fitted-tshirt/input.dxf').read_bytes())
    bindings = source_map(baseline, polylines); pose = baseline_pose(baseline)
    models = {}; entries = []
    for case_id in CASES:
        model = build_model(case_id, baseline, bindings, pose, args.spacing)
        data = (json.dumps(model, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n').encode()
        path = args.output / (case_id + '.mesh.json'); path.write_bytes(data); models[case_id] = model
        entries.append({'id': case_id, 'file': path.name, 'sha256': sha(data), 'byte_length': len(data),
                        'source_dxf_sha256': model['source_dxf_sha256'], 'source_spec_sha256': model['source_spec_sha256'],
                        'vertices': sum(len(p['positions']) for p in model['panels']), 'triangles': sum(len(p['triangles']) for p in model['panels'])})
    builder_sources = {str(path.relative_to(REPO)): sha(path.read_bytes()) for path in [Path(__file__),
        REPO / 'services/dxf-preview/converter/core.py', REPO / 'services/dxf-preview/converter/sewn.py']}
    (args.output / 'manifest.json').write_text(json.dumps({'format': 'intent-edit-review-models/1', 'models': entries,
       'common_pose': pose, 'units': 'U', 'physical_fit': 'NOT_RUN', 'cloth_simulation': 'NOT_RUN',
       'builder_sources': builder_sources}, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(entries, ensure_ascii=False, indent=2))


if __name__ == '__main__': main()
