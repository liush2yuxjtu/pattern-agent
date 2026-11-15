"""Measure causal controls on saved physical meshes, never just RNA properties."""
import argparse,hashlib,json
from pathlib import Path
import numpy as np


def main():
    p=argparse.ArgumentParser();p.add_argument('--baseline',type=Path,required=True);p.add_argument('--atlas',type=Path,required=True);p.add_argument('--short',type=Path,required=True);p.add_argument('--protocol',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    protocol=json.loads(a.protocol.read_text());paths=[a.baseline,a.atlas,a.short];reports=[json.loads((x/'drape-report.json').read_text()) for x in paths]
    inputs=[]
    for x in paths:
        with np.load(x/'input-metrics.npz') as f:inputs.append({k:f[k] for k in f.files})
    names=[[x.name for x in sorted((r/'frames').glob('*.npz'))] for r in paths]
    assert names[0]==names[1]==names[2] and len(names[0])==reports[0]['frame_count']
    rows=[];initial_deltas=[];topology_identical=True;no_flat_teleport=[]
    for name in names[0]:
        frames=[]
        for root in paths:
            with np.load(root/'frames'/name) as f:
                frames.append(f['cloth_vertices']);topology_identical &= np.array_equal(f['cloth_triangles'],inputs[0]['cloth_triangles'])
        deltas=[float(np.max(np.linalg.norm(frames[k]-frames[0],axis=1))) for k in (1,2)]
        if not rows:initial_deltas=deltas
        rows.append({'frame':int(name[6:10]),'atlas_max_vertex_delta_m':deltas[0],'short_max_vertex_delta_m':deltas[1]})
        no_flat_teleport.append([float(np.max(np.abs(frames[k]-inputs[k]['actual_key_coordinates']))) for k in range(3)])
    atlas=max(r['atlas_max_vertex_delta_m'] for r in rows);short=max(r['short_max_vertex_delta_m'] for r in rows)
    metric=float(np.max(abs(inputs[0]['rest_lengths']-inputs[1]['rest_lengths'])))
    factor=reports[2]['input']['left_grain_probe_initial_stretch_ratio']/reports[0]['input']['left_grain_probe_initial_stretch_ratio']
    checks={'same_initial3D':max(initial_deltas)<protocol['same_initial3D_max_delta_m'],
            'same_atlas_intrinsic_rest_lengths':metric<protocol['atlas_structural_rest_length_max_delta_m'],
            'atlas_trajectory_invariant':atlas<protocol['atlas_trajectory_max_delta_m'],
            'short_probe_expected_factor':abs(factor-protocol['left_grain_probe_expected_stretch_ratio_factor'])<protocol['grain_probe_factor_tolerance'],
            'short_response_isolated':short>.001 and short>=5*atlas,
            'topology_identical':bool(topology_identical),'all_runs_complete':all(r['execution_complete'] for r in reports)}
    result={'frame_count_each':len(rows),'protocol_sha256':hashlib.sha256(a.protocol.read_bytes()).hexdigest(),'checks':checks,
            'initial_deltas_m':initial_deltas,'atlas_intrinsic_edge_length_max_delta_m':metric,'atlas_max_vertex_delta_m':atlas,'short_max_vertex_delta_m':short,
            'short_to_atlas_response_ratio':short/atlas if atlas else None,'short_grain_probe_initial_stretch_factor':factor,
            'first_frame_diverging_atlas':next((r['frame'] for r in rows if r['atlas_max_vertex_delta_m']>protocol['atlas_trajectory_max_delta_m']),None),
            'rows':rows,'max_delta_from_flat_input_per_frame_m':no_flat_teleport,
            'verdict':'PASS_LIMITED_CAUSAL_CONTROLS' if all(checks.values()) else 'FAIL_CAUSAL_CONTROL',
            'scope':'Preplaced3D, frozen A pose, assumed mechanics. Not flat sewing, donning or fit.',
            'armhole_fit':'UNKNOWN','physical_fit':'NOT_RUN'}
    a.out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ('rows','max_delta_from_flat_input_per_frame_m')}));return 0 if all(checks.values()) else 2


if __name__=='__main__':raise SystemExit(main())
