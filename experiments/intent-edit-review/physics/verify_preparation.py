#!/usr/bin/env python3
"""Independent geometry gate BEFORE an initial state can be called ready.

Uses the saved float32 checkpoint, actual body triangles and strict all-face
oracle. It imports no native solver or contact-response implementation.
"""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
import trimesh

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools/cloth_lab'))
sys.path.insert(0,str(ROOT/'experiments/oneshot_control'))
from oracle import segment_hits
from independent_oracle_v2 import intersect_pairs,mesh_audit
from exact_body_oracle import closest_body
from arm_wear_oracle import check_arm_wear
def sha(raw):return hashlib.sha256(raw).hexdigest()

def verify(directory):
    raw=(directory/'input.json').read_bytes();data=json.loads(raw)
    positions_raw=(directory/'preparation-final.bin').read_bytes()
    points=np.frombuffer(positions_raw,dtype='<f4').reshape(-1,3).astype(float)
    if points.shape!=np.asarray(data['positions']).shape or not np.isfinite(points).all():
        raise ValueError('Invalid actual preparation checkpoint')
    ids=np.asarray(data['global_ids']);_,first,inverse=np.unique(ids,return_index=True,return_inverse=True)
    x=points[first];faces=inverse[np.asarray(data['triangles'])];pairs=np.asarray(data['seams'])
    gap=float(np.linalg.norm(points[pairs[:,0]]-points[pairs[:,1]],axis=1).max()*1000)
    body_data=data['body'];decode=lambda name,dtype:np.frombuffer(base64.b64decode(body_data[name],validate=True),dtype).reshape(-1,3)
    body=trimesh.Trimesh(decode('positions','<f4'),decode('indices','<i4'),process=False)
    cloth=trimesh.Trimesh(x,faces,process=False);edges=cloth.edges_unique
    samples=np.concatenate([x,x[edges].mean(1),x[faces].mean(1)])
    inside=body.contains(samples)
    penetration=float(closest_body(body,samples[inside])[1].max()*1000) if inside.any() else 0.
    forward=segment_hits(body,x[edges[:,0]],x[edges[:,1]])
    be=body.edges_unique;bv=body.vertices;a,b=bv[be[:,0]],bv[be[:,1]]
    keep=np.all(np.minimum(a,b)<=x.max(0)+1e-5,axis=1)&np.all(np.maximum(a,b)>=x.min(0)-1e-5,axis=1)
    reverse=segment_hits(cloth,a[keep],b[keep]);self_pairs=intersect_pairs(x,faces,epsilon_m=1e-6)
    topology=mesh_audit(x,faces);failures=[]
    if gap>2:failures.append('Positional seam gap exceeds 2mm')
    if penetration>.2 or forward or reverse:failures.append('Actual body penetration or triangle crossing')
    if self_pairs:failures.append('Strict all-triangle self intersections')
    arm_wear=None
    if data.get('initialization',{}).get('actual_arm_seed') is not None:
        arm_wear=check_arm_wear(data,points)
        if not arm_wear['both_arms_threaded']:failures.append('Digital arm routing failed or inconclusive')
    invalid=[key for key in ['nonmanifold_edges','winding_conflicts','degenerate_triangles','duplicate_faces','orphan_vertices','boundary_branch_vertices'] if topology[key]]
    if invalid or topology['connected_components']!=1 or topology['boundary_cycles']!=4:failures.append('Invalid sewn topology: '+str(invalid))
    source_path=directory/'source-independent.json'
    if not source_path.exists():failures.append('Independent source reference missing')
    else:
        source=json.loads(source_path.read_bytes())
        if source['verdict']!='PASS' or source.get('experiment_input_sha256')!=sha(raw):failures.append('Source reference failed or stale')
    report={'verdict':'FAIL' if failures else 'PASS','phase':'initialization gate, before physical replay',
        'input_sha256':sha(raw),'positions_sha256':sha(positions_raw),'wasm_sha256':sha((directory/'solver.wasm').read_bytes()),
        'verifier_sha256':sha(Path(__file__).read_bytes()),'max_seam_gap_mm':gap,
        'sampled_points':len(samples),'inside_samples':int(inside.sum()),'max_body_penetration_mm':penetration,
        'cloth_edge_body_hits':forward,'body_edge_cloth_hits':reverse,'strict_self_intersections':len(self_pairs),
        'intersection_examples':self_pairs[:12],'topology':topology,'failures':failures,
        'arm_wear':arm_wear,
        'physical_fit':'NOT_RUN','material_calibration':'NOT_RUN'}
    (directory/'preparation-gate.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ['topology','intersection_examples','arm_wear']}),flush=True)
    return not failures

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('directory',type=Path)
    raise SystemExit(0 if verify(p.parse_args().directory) else 2)
