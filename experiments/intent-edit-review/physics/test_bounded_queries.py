#!/usr/bin/env python3
"""Sequential old-vs-bounded query equivalence; no audit or physics changes.

 work/intent-physics/venv/bin/python experiments/intent-edit-review/physics/test_bounded_queries.py \
   --case work/intent-physics/baseline-run37 --case work/intent-physics/cuff-run37 \
   --output work/intent-physics/bounded-query-controls37.json

The first four real checks are frame0/frame30 across both cases. Frame60 follows.
Process RSS high-water measurements are cumulative, NOT per-query peak claims.
"""
import argparse
import base64
import hashlib
import inspect
import json
from pathlib import Path
import resource
import sys
import time

import numpy as np
import trimesh

from bounded_queries import contains_points_batched, segment_hits_batched

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools/cloth_lab'))
from oracle import segment_hits as old_segment_hits


def sha(raw):return hashlib.sha256(raw).hexdigest()
def unpack(value,width=3,dtype='<f4'):
    a=np.frombuffer(base64.b64decode(value,validate=True),dtype=dtype).astype(float)
    return a.reshape(-1,width)


def memory():
    data={'process_peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
    try:
        for line in Path('/proc/self/status').read_text().splitlines():
            if line.startswith('VmRSS:'):data['current_rss_kib']=int(line.split()[1]);break
    except OSError:pass
    return data


def measured(call):
    before=memory();started=time.perf_counter();value=call()
    return value,dict(seconds=time.perf_counter()-started,memory_before=before,memory_after=memory())


def same_rng(a,b):
    return a[0]==b[0] and np.array_equal(a[1],b[1]) and a[2:]==b[2:]


def compare_contains(mesh,points,batch_size,trace=False):
    original=mesh.ray.intersects_location
    observed=[]
    def recording(origins,directions,**kwargs):
        observed.append((np.array(origins,copy=True),np.array(directions,copy=True)))
        return original(origins,directions,**kwargs)
    if trace:mesh.ray.intersects_location=recording
    try:
        np.random.seed(20261118);rng=np.random.get_state()
        old,old_perf=measured(lambda:mesh.contains(points));old_rng=np.random.get_state()
        old_stream=observed[:];observed.clear();stats={}
        np.random.set_state(rng)
        bounded,bounded_perf=measured(lambda:contains_points_batched(mesh,points,batch_size,stats=stats))
        bounded_rng=np.random.get_state()
        assert np.array_equal(old,bounded), 'Inside mask differs at indices '+str(np.flatnonzero(old!=bounded)[:20].tolist())
        assert same_rng(old_rng,bounded_rng), 'Contains random retry direction/RNG consumption changed'
        assert old.dtype==bounded.dtype==np.dtype(bool) and len(bounded)==len(points)
        assert stats['points']==len(points) and stats.get('max_backend_rays',0)<=batch_size
        if trace:
            for axis in [0,1]:
                before=np.concatenate([r[axis] for r in old_stream]) if old_stream else np.empty((0,3))
                after=np.concatenate([r[axis] for r in observed]) if observed else np.empty((0,3))
                assert np.array_equal(before,after), 'Original ray origins/directions changed'
        return dict(points=len(points),inside=int(old.sum()),mismatches=0,inside_mask_sha256=sha(old.tobytes()),
                    random_state_exact=True,ray_stream_exact=True if trace else 'covered by analytic controls',
                    old=old_perf,bounded=bounded_perf,backend=stats)
    finally:
        if trace:mesh.ray.intersects_location=original


def compare_segments(mesh,starts,ends,batch_size):
    old,old_perf=measured(lambda:old_segment_hits(mesh,starts,ends));stats={}
    new,new_perf=measured(lambda:segment_hits_batched(mesh,starts,ends,batch_size,stats=stats))
    assert old==new, f'Segment hit count differs: {old} vs {new}'
    assert stats['segments']==len(starts) and stats.get('max_backend_rays',0)<=batch_size
    expected=int((np.linalg.norm(ends-starts,axis=1)>1e-9).sum())
    assert stats.get('valid_segments',0)==expected and stats.get('rays_queried',0)==expected, 'A real valid edge was skipped'
    return dict(segments=len(starts),valid_segments=expected,hits=old,old=old_perf,bounded=new_perf,backend=stats)


def analytic():
    box=trimesh.creation.box(extents=[2.,2.,2.]);rows=[]
    # Surface classification is undefined physically; require exact old/new
    # semantics without claiming these points are a valid containment oracle.
    points=np.vstack([[[0,0,0],[2,0,0],[-2,0,0]],box.vertices,box.triangles_center])
    for size in [1,2,7,512,1024]:
        row=compare_contains(box,points,size,trace=True)
        rows.append(dict(name='inside_outside_surface',batch_size=size,contains=row))
    # Real ray backend, intentionally non-watertight negative: two forward
    # planes and one backward plane force nonzero conflicting parity. Trimesh
    # must choose ONE shared random retry direction for the logical query.
    vertices=[];faces=[]
    for x in [-1.,.5,1.]:
        n=len(vertices);vertices.extend([[x,-5,-5],[x,5,-5],[x,5,5],[x,-5,5]])
        faces.extend([[n,n+1,n+2],[n,n+2,n+3]])
    open_planes=trimesh.Trimesh(vertices,faces,process=False)
    for size in [1,2,512]:
        row=compare_contains(open_planes,np.array([[0,0,0],[0,.1,.1],[0,-.2,.1]],float),size,trace=True)
        assert row['backend'].get('logical_ray_queries',0)>=2, 'Random retry control was not exercised'
        rows.append(dict(name='nonwatertight_conflicting_parity_global_random_retry',batch_size=size,contains=row))
    empty=np.empty((0,3),dtype=float)
    rows.append(dict(name='empty',contains=compare_contains(box,empty,3,trace=True),segments=compare_segments(box,empty,empty,3)))
    starts=np.array([[-2,0,0],[-1,0,0],[-1-.5e-6,0,0],[0,0,0],[0,0,0],[-2,0,0]],float)
    ends=np.array([[2,0,0],[0,0,0],[0,0,0],[0,0,0],[.5e-9,0,0],[-1+.5e-6,0,0]],float)
    for size in [1,2,512,1024]:
        row=compare_segments(box,starts,ends,size);assert row['hits']==2
        rows.append(dict(name='true_crossing_empty_short_endpoint_tolerances',batch_size=size,segments=row))
    outer=trimesh.creation.box(extents=[2.,2.,2.]);inner=trimesh.creation.box(extents=[.6,.6,.6]);inner.invert()
    cavity=trimesh.util.concatenate([outer,inner]);p=np.array([[0,0,0],[.7,0,0],[2,0,0]],float)
    row=compare_contains(cavity,p,2,trace=True);assert np.array_equal(cavity.contains(p),[False,True,False])
    crossing=compare_segments(cavity,np.array([[-2,0,0.]],float),np.array([[2,0,0.]],float),1);assert crossing['hits']==4
    rows.append(dict(name='closed_cavity_multiple_hits',contains=row,segments=crossing))
    return rows


def load_case(directory):
    raw=(directory/'input.json').read_bytes();recording_raw=(directory/'trajectory.json').read_bytes()
    data=json.loads(raw);recording=json.loads(recording_raw)
    assert recording['input_sha256']==sha(raw), 'Recording/input digest mismatch'
    vertices=unpack(data['body']['positions']);faces=unpack(data['body']['indices'],dtype='<i4').astype(int)
    body=trimesh.Trimesh(vertices,faces,process=False)
    ids=np.asarray(data['global_ids']);_,first,inverse=np.unique(ids,return_index=True,return_inverse=True)
    return dict(data=data,recording=recording,body=body,first=first,faces=inverse[np.asarray(data['triangles'],int)],
                binding=dict(directory=str(directory),input_sha256=sha(raw),recording_sha256=sha(recording_raw),
                             source_dxf_sha256=data['source_dxf_sha256'],source_spec_sha256=data['source_spec_sha256'],
                             body_positions_sha256=sha(base64.b64decode(data['body']['positions'])),body_indices_sha256=sha(base64.b64decode(data['body']['indices']))))


def real_frame(context,index,size):
    frame=context['recording']['frames'][index];points=unpack(frame['positions'])[context['first']]
    faces=context['faces'];body=context['body'];cloth=trimesh.Trimesh(points,faces,process=False);edges=cloth.edges_unique
    samples=np.concatenate([points,points[edges].mean(1),points[faces].mean(1)])
    body_before=sha(body.vertices.tobytes()+body.faces.tobytes())
    contains=compare_contains(body,samples,size)
    forward=compare_segments(body,points[edges[:,0]],points[edges[:,1]],size)
    be=body.edges_unique;bv=body.vertices;a,b=bv[be[:,0]],bv[be[:,1]]
    keep=np.all(np.minimum(a,b)<=points.max(0)+1e-5,axis=1)&np.all(np.maximum(a,b)>=points.min(0)-1e-5,axis=1)
    reverse=compare_segments(cloth,a[keep],b[keep],size)
    assert body_before==sha(body.vertices.tobytes()+body.faces.tobytes()), 'Actual body geometry changed'
    return dict(verdict='PASS',**context['binding'],frame=index,positions_sha256=sha(base64.b64decode(frame['positions'])),
                contains=contains,cloth_edges_into_body=forward,body_edges_into_cloth=reverse)


def main():
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--case',type=Path,action='append',default=[]);p.add_argument('--frames',default='0,30,60')
    p.add_argument('--batch-size',type=int,default=512);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--analytic-only',action='store_true');args=p.parse_args()
    here=Path(__file__);module=here.with_name('bounded_queries.py')
    report=dict(verdict='RUNNING',scope='Query equivalence/resource controls only; no geometry/dynamics/fit acceptance.',
                batch_size=args.batch_size,python=sys.executable,trimesh_version=trimesh.__version__,
                test_sha256=sha(here.read_bytes()),bounded_module_sha256=sha(module.read_bytes()),
                original_oracle_sha256=sha(Path(inspect.getsourcefile(old_segment_hits)).read_bytes()),
                memory_scope='RSS high-water values are cumulative for this one sequential process, not isolated per-call peaks.',
                analytic=[],real_frames=[],failures=[])
    args.output.parent.mkdir(parents=True,exist_ok=True)
    def save():args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    started=time.perf_counter();save()
    try:
        report['analytic']=analytic();print(json.dumps({'phase':'analytic','verdict':'PASS','controls':len(report['analytic'])}),flush=True);save()
        if not args.analytic_only:
            assert args.case, '--case is required for real-frame equivalence'
            contexts=[load_case(case.resolve()) for case in args.case]
            for index in [int(x) for x in args.frames.split(',')]:
                for context in contexts:
                    print(json.dumps({'phase':'real-start','directory':context['binding']['directory'],'frame':index}),flush=True)
                    row=real_frame(context,index,args.batch_size);report['real_frames'].append(row);save()
                    print(json.dumps({'phase':'real-complete','directory':row['directory'],'frame':index,'verdict':'PASS',
                                      'inside':row['contains']['inside'],'forward':row['cloth_edges_into_body']['hits'],
                                      'reverse':row['body_edges_into_cloth']['hits']}),flush=True)
        report['verdict']='PASS'
    except Exception as error:
        report['verdict']='FAIL';report['failures'].append(repr(error));raise
    finally:
        report['total_seconds']=time.perf_counter()-started;report['memory_final']=memory();save()
    print(json.dumps({'verdict':report['verdict'],'analytic_controls':len(report['analytic']),
                      'real_frames':len(report['real_frames']),'total_seconds':report['total_seconds'],
                      'process_peak_rss_kib':report['memory_final']['process_peak_rss_kib'],'report':str(args.output)}),flush=True)


if __name__=='__main__':main()
