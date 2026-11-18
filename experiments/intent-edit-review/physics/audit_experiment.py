#!/usr/bin/env python3
"""Independently reopen recorded cloth arrays. No C/JS solver is imported.

Strict triangle intersections include incident faces. Contact-response adjacency
exclusions are deliberately unavailable to this verifier. A completed calculation
is not a passing garment, and assumed mechanics are never labelled measured.
"""
import argparse
from concurrent.futures import ProcessPoolExecutor
import multiprocessing
import base64
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'tools/cloth_lab'))
sys.path.insert(0, str(ROOT/'experiments/oneshot_control'))
from oracle import tensors, segment_hits
from independent_oracle_v2 import intersect_pairs, mesh_audit
from exact_body_oracle import closest_body
from arm_wear_oracle import check_arm_wear


def sha(raw): return hashlib.sha256(raw).hexdigest()
def unpack(value, width=1, dtype='<f4'):
    values = np.frombuffer(base64.b64decode(value, validate=True), dtype=dtype).astype(float)
    return values.reshape(-1, width) if width > 1 else values


def fold_oracle(points, faces):
    """Oriented adjacent-face atan2; flat=0, folded-back approaches +/-180deg."""
    edges = {}
    triangle_angle = np.zeros(len(faces)); triangle_curvature = np.zeros(len(faces))
    angles = []; curvatures = []
    for fi, face in enumerate(faces):
        for j in range(3):
            a, b, c = map(int, [face[j], face[(j+1)%3], face[(j+2)%3]])
            key = tuple(sorted([a, b]))
            if key not in edges:
                edges[key] = (a, b, c, fi); continue
            aa, bb, cc, left = edges.pop(key)
            if (aa, bb) != (b, a): raise ValueError('Inconsistent oriented material hinge')
            e = points[bb]-points[aa]; edge_length = np.linalg.norm(e)
            n1 = np.cross(e, points[cc]-points[aa]); n2 = np.cross(points[c]-points[aa], e)
            l1, l2 = np.linalg.norm(n1), np.linalg.norm(n2)
            if min(edge_length, l1, l2) < 1e-14: raise ValueError('Degenerate recorded hinge')
            n1 /= l1; n2 /= l2
            angle = np.arctan2(np.dot(np.cross(n1, n2), e/edge_length), np.clip(np.dot(n1, n2), -1, 1))
            curvature = angle / ((l1+l2)/(3*edge_length))
            angles.append(angle); curvatures.append(curvature)
            for target in [left, fi]:
                if abs(angle*180/np.pi) > abs(triangle_angle[target]): triangle_angle[target] = angle*180/np.pi
                if abs(curvature) > abs(triangle_curvature[target]): triangle_curvature[target] = curvature
    return dict(triangleAngle_deg=triangle_angle, triangleCurvature_per_m=triangle_curvature,
                angle_rad=np.asarray(angles), curvature_per_m=np.asarray(curvatures))


def _frame_context(data, recording):
    bv=unpack(data['body']['positions'],3);bf=unpack(data['body']['indices'],3,'<i4').astype(int)
    ids=np.asarray(data['global_ids'],int);_,first,inverse=np.unique(ids,return_index=True,return_inverse=True)
    return dict(data=data,recording=recording,body=trimesh.Trimesh(bv,bf,process=False),bv=bv,
                uv=np.asarray(data['uv']),faces=np.asarray(data['triangles'],int),first=first,
                welded_faces=inverse[np.asarray(data['triangles'],int)],pairs=np.asarray(data['seams'],int))


def _frame_check(context,index):
    data=context['data'];recording=context['recording'];body=context['body'];bv=context['bv']
    uv=context['uv'];faces=context['faces'];first=context['first'];welded_faces=context['welded_faces'];pairs=context['pairs']
    failures=[]
    def require(condition,message):
        if not bool(condition):failures.append(message)
    frame = recording['frames'][index]; x = unpack(frame['positions'], 3); previous = unpack(frame['previous'], 3)
    # Recompute in float64 from the actual float32 material coordinates used
    # by the executable, then independently bind them to the exact CAD UVs.
    kernel_uv = np.asarray(uv, dtype=np.float32).astype(float)
    if 'rest_uv' in recording:
        kernel_uv = unpack(recording['rest_uv'], 2)
        require(np.array_equal(kernel_uv, np.asarray(uv, dtype=np.float32).astype(float)), 'Runtime material UVs differ from input')
    actual = unpack(frame['fields'], 8); expected = tensors(x, kernel_uv, faces, data['material'])
    wx = x[first]; cloth = trimesh.Trimesh(wx, welded_faces, process=False); edges = cloth.edges_unique
    topology = mesh_audit(wx, welded_faces)
    gap = float(np.linalg.norm(x[pairs[:, 0]]-x[pairs[:, 1]], axis=1).max()*1000)
    samples = np.concatenate([wx, wx[edges].mean(1), wx[welded_faces].mean(1)])
    inside = body.contains(samples)
    # The sign is from independent ray parity, not interpolated solver normals.
    distances = closest_body(body, samples[inside])[1] if inside.any() else np.array([0.])
    max_penetration = float(distances.max()*1000)
    hits = segment_hits(body, wx[edges[:, 0]], wx[edges[:, 1]])
    be = body.edges_unique; a, b = bv[be[:, 0]], bv[be[:, 1]]
    keep = np.all(np.minimum(a, b) <= wx.max(0)+1e-5, axis=1) & np.all(np.maximum(a, b) >= wx.min(0)-1e-5, axis=1)
    reverse_hits = segment_hits(cloth, a[keep], b[keep])
    self_pairs = intersect_pairs(wx, welded_faces, epsilon_m=1e-6)
    atol = np.array([2e-5, 2e-5, 2e-5, .15, .15, 2e-5, 2e-5, 2e-5])
    tensor_pass = bool(np.allclose(actual, expected, rtol=3e-4, atol=atol))
    fold_error = None
    try:
        fold = fold_oracle(wx, welded_faces)
    except ValueError as exc:
        fold_error = str(exc); require(False, f'Frame {index}: {exc}')
        fold = {'triangleAngle_deg': np.array([np.nan]), 'triangleCurvature_per_m': np.array([np.nan])}
    fold_pass = 'NOT_RUN'
    if 'folds' in frame and fold_error is None:
        exported = unpack(frame['folds'], 2)
        fold_expected = np.column_stack([fold['triangleAngle_deg'], fold['triangleCurvature_per_m']])
        fold_pass = bool(np.allclose(exported, fold_expected, rtol=2e-5, atol=2e-4))
    invalid = {k: topology[k] for k in ['nonmanifold_edges', 'winding_conflicts', 'degenerate_triangles', 'duplicate_faces', 'orphan_vertices', 'boundary_branch_vertices'] if topology[k]}
    require(np.isfinite(x).all() and np.isfinite(previous).all() and np.isfinite(actual).all(), f'Frame {index}: nonfinite')
    require(topology['connected_components'] == 1 and topology['boundary_cycles'] == 4 and not invalid, f'Frame {index}: invalid sewn topology {invalid}')
    require(gap <= 2, f'Frame {index}: seam gap {gap}mm')
    require(max_penetration <= .2 and hits == reverse_hits == 0, f'Frame {index}: body penetration/intersections')
    require(len(self_pairs) == 0, f'Frame {index}: {len(self_pairs)} strict self intersections')
    require(tensor_pass, f'Frame {index}: material tensor mismatch')
    if fold_pass != 'NOT_RUN': require(fold_pass, f'Frame {index}: fold field mismatch')
    require(frame['step'] == index and abs(frame['time']-index/120) < 2e-6, f'Frame {index}: wrong physical clock')
    row = dict(frame=index, sampled_points=len(samples), max_seam_gap_mm=gap, inside_samples=int(inside.sum()),
               max_body_penetration_mm=max_penetration, cloth_edge_body_hits=hits, body_edge_cloth_hits=reverse_hits,
               strict_self_intersections=len(self_pairs), intersection_examples=self_pairs[:12],
               tensor_pass=tensor_pass, tensor_absolute_errors=np.max(abs(actual-expected), axis=0).tolist(),
               max_principal_strain_percent=float(expected[:, 0].max()*100), p95_principal_strain_percent=float(np.percentile(expected[:, 0], 95)*100),
               max_cauchy_stress_kpa=float(expected[:, 3].max()/1000),
               max_abs_fold_deg=None if fold_error else float(np.max(abs(fold['triangleAngle_deg']))), fold_pass=fold_pass, fold_error=fold_error, topology=topology)
    if data.get('initialization',{}).get('actual_arm_seed') is not None:
        arm_wear=check_arm_wear(data,x)
        row['arm_wear']=arm_wear
        require(arm_wear['both_arms_threaded'],f'Frame {index}: digital arm routing failed or inconclusive')
    row['verdict']='FAIL' if failures else 'PASS'
    row['failures']=failures.copy()
    return row,failures


_WORKER_CONTEXT=None

def _initialize_frame_worker(data,recording):
    global _WORKER_CONTEXT
    _WORKER_CONTEXT=_frame_context(data,recording)


def _frame_worker(index):
    return _frame_check(_WORKER_CONTEXT,index)


def audit(directory, indices=None, workers=1):
    raw_input = (directory/'input.json').read_bytes(); data = json.loads(raw_input)
    raw_trajectory = (directory/'trajectory.json').read_bytes(); recording = json.loads(raw_trajectory)
    failures = []; checks = {}
    def require(condition, message):
        if not bool(condition): failures.append(message)
    require(recording['input_sha256'] == sha(raw_input), 'Recording input binding')
    require(recording['wasm_sha256'] == sha((directory/'solver.wasm').read_bytes()), 'Recording executable binding')
    require(recording['source_dxf_sha256'] == data['source_dxf_sha256'], 'DXF binding')
    require(recording['source_spec_sha256'] == data['source_spec_sha256'], 'Spec binding')
    frozen_path=directory/'frozen-source/manifest.json'
    if frozen_path.exists():
        frozen=json.loads(frozen_path.read_bytes())
        for name,digest in frozen.items():
            saved=directory/'frozen-source'/name
            require(saved.is_file() and sha(saved.read_bytes())==digest,'Frozen source bytes differ: '+name)
        for name,digest in data['source_hashes'].items():
            require(frozen.get(name)==digest,'Prepared source absent or stale in snapshot: '+name)
        runtime_bindings={'run_native.mjs':'runtime_source_sha256','create-self-contact.mjs':'contact_adapter_sha256',
            'mesh-contact.mjs':'mesh_contact_source_sha256','swept-edge.mjs':'swept_edge_source_sha256',
            'swept-vertex.mjs':'swept_vertex_source_sha256','self_step_guard.mjs':'self_guard_source_sha256'}
        for name,key in runtime_bindings.items():
            require(recording.get(key)==frozen.get('experiments/intent-edit-review/physics/'+name),'Executed runtime differs from frozen source: '+name)
        require(recording.get('self_contact_source_sha256')==frozen.get('experiments/freesewing_cloth_lab/source/self-contact.js'),'Executed shared contact differs from frozen source')
        checks['frozen_sources']={'files':len(frozen),'manifest_sha256':sha(frozen_path.read_bytes())}
    else:require(False,'Frozen actual source snapshot missing')
    require(recording.get('preparation_gate') == 'PASS', 'Initial-state preparation gate not passed')
    preparation_path=directory/'preparation-gate.json';checkpoint_path=directory/'preparation-final.bin'
    if preparation_path.exists() and checkpoint_path.exists():
        preparation_raw=preparation_path.read_bytes();preparation=json.loads(preparation_raw)
        require(preparation.get('verdict')=='PASS', 'Independent initial-state geometry failed')
        require(preparation.get('input_sha256')==sha(raw_input), 'Preparation input binding')
        require(preparation.get('positions_sha256')==sha(checkpoint_path.read_bytes()), 'Actual preparation checkpoint binding')
        require(recording.get('preparation_gate_sha256')==sha(preparation_raw), 'Recording preparation-report binding')
        require(base64.b64decode(recording['frames'][0]['positions'])==checkpoint_path.read_bytes(), 'First physical frame differs from the checked initial state')
        checks['preparation']={'verdict':preparation.get('verdict'),'report_sha256':sha(preparation_raw)}
    else:require(False,'Independent preparation geometry/checkpoint missing')
    source_report_path = directory/'source-independent.json'
    if source_report_path.exists():
        source_report = json.loads(source_report_path.read_bytes())
        require(source_report.get('verdict') == 'PASS', 'Independent CAD/sewing source reference failed')
        require(source_report.get('experiment_input_sha256') == sha(raw_input), 'Independent source-reference input binding')
        checks['source_reference'] = {'verdict':source_report.get('verdict'), 'report_sha256':sha(source_report_path.read_bytes())}
    else:
        require(False, 'Independent source-reference report missing')
    reference = json.loads((ROOT/data['body']['source']).read_bytes())
    require(sha((ROOT/data['body']['source']).read_bytes()) == data['body']['source_sha256'], 'Actual body source digest')
    bv = unpack(data['body']['positions'], 3); bf = unpack(data['body']['indices'], 3, '<i4').astype(int)
    require(np.max(abs(np.array(reference['positions']).reshape(-1, 3)-bv)) < 1e-7, 'Body positions substituted')
    require(np.array_equal(np.array(reference['triangles']).reshape(-1, 3), bf), 'Body topology substituted')
    body = trimesh.Trimesh(bv, bf, process=False)
    require(body.is_watertight and body.is_winding_consistent and body.volume > 0, 'Body is not closed/outward')
    uv = np.asarray(data['uv']); faces = np.asarray(data['triangles'], int); ids = np.asarray(data['global_ids'], int)
    unique, first, inverse = np.unique(ids, return_index=True, return_inverse=True)
    welded_faces = inverse[faces]; pairs = np.asarray(data['seams'], int)
    require(recording.get('verified_self_contact_triangles') == len(faces), 'Actual self-contact BVH did not visit every cloth triangle')
    require(np.array_equal(unique, np.arange(len(unique))), 'Non-contiguous weld IDs')
    expected_pairs = []; roots = {}
    for i, gid in enumerate(ids):
        if gid in roots: expected_pairs.append([roots[gid], i])
        else: roots[gid] = i
    require(np.array_equal(pairs, expected_pairs), 'Missing/reversed/extra positional connection constraints')
    require(len(data['source_sewing']['seams']) == 15, 'Missing semantic sewing pair')
    for patch in data['panels']:
        p = data['source_sewing']['patches'][patch['name']]; s = slice(patch['start'], patch['start']+patch['vertices'])
        require(np.max(abs(uv[s]+np.asarray(patch.get('uv_origin_m', [0, 0]))-np.asarray(p['flat_points'])/1000)) < 1e-12, 'Rest UV changed: '+patch['name'])
        require(np.array_equal(ids[s], p['global_vertices']), 'Weld mapping changed: '+patch['name'])
        fs = slice(patch['face_start'], patch['face_start']+patch['faces'])
        require(np.array_equal(faces[fs], np.asarray(p['local_faces'])+patch['start']), 'Actual faces differ: '+patch['name'])
    checks['connections'] = {'semantic_pairs': 15, 'positional_pairs': len(pairs), 'all_pairs_accounted_for': np.array_equal(pairs, expected_pairs)}
    selected = list(range(len(recording['frames']))) if indices is None else indices
    rows = []
    if workers>1:
        pool=ProcessPoolExecutor(max_workers=workers,mp_context=multiprocessing.get_context('spawn'),
                                 initializer=_initialize_frame_worker,initargs=(data,recording))
        results=pool.map(_frame_worker,selected,chunksize=1)
    else:
        pool=None;context=_frame_context(data,recording)
        results=(_frame_check(context,index) for index in selected)
    try:
        for row,frame_failures in results:
            rows.append(row);failures.extend(frame_failures)
            print(json.dumps({k: row[k] for k in ['frame','max_body_penetration_mm','cloth_edge_body_hits','body_edge_cloth_hits','strict_self_intersections','tensor_pass','max_principal_strain_percent']}), flush=True)
    finally:
        if pool:pool.shutdown(wait=True,cancel_futures=True)
    require(recording['continuation_bit_exact'], 'Physical continuation mismatch')
    resume_path = directory/'resume-independent.json'
    if resume_path.exists():
        resume = json.loads(resume_path.read_bytes())
        require(resume.get('verdict') == 'PASS' and resume.get('input_sha256') == sha(raw_input)
                and resume.get('recording_sha256') == sha(raw_trajectory), 'Fresh-process physical continuation failed or stale')
        checks['fresh_process_continuation'] = {'verdict':resume.get('verdict'), 'report_sha256':sha(resume_path.read_bytes())}
    else:
        require(False, 'Fresh-process physical continuation not verified')
    require(len(recording['frames']) == data['config']['数值条件']['记录步数']+1
            and recording.get('recorded_physical_steps') == data['config']['数值条件']['记录步数'], 'Incomplete physical recording')
    complete = selected == list(range(len(recording['frames'])))
    require(complete, 'Only selected frames checked; full trajectory remains unverified')
    require(all(row['fold_pass'] is True for row in rows), 'Recorded fold fields missing/unverified')
    return dict(verdict='FAIL' if failures else 'PASS', case=data['case'], input_sha256=sha(raw_input), recording_sha256=sha(raw_trajectory),verifier_sha256=sha(Path(__file__).read_bytes()),
                checks=checks, frames=rows, frames_checked=len(rows), total_frames=len(recording['frames']), failures=failures, audit_workers=workers,
                material_calibration='NOT_RUN', physical_fit='NOT_RUN',
                scope='Discrete recorded geometry and synthetic material mathematics; no calibrated material or real-person fit claim.')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('directory', type=Path); p.add_argument('--frames')
    p.add_argument('--output', type=Path, required=True);p.add_argument('--workers',type=int,choices=range(1,5),default=1); args = p.parse_args()
    indices = list(map(int, args.frames.split(','))) if args.frames else None
    result = audit(args.directory, indices,args.workers); args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=lambda x: bool(x) if isinstance(x, np.bool_) else x)+'\n')
    print(json.dumps({'verdict': result['verdict'], 'frames_checked': result['frames_checked'], 'failures': len(result['failures'])}))
    raise SystemExit(0 if result['verdict'] == 'PASS' else 1)
