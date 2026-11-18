#!/usr/bin/env python3
"""Actual-WASM controls for intersection-derived body contacts, not cloth fit.

Use the independent-audit environment (numpy/trimesh/scipy/rtree):
 work/intent-physics/venv/bin/python \
   experiments/intent-edit-review/physics/test_body_feature_contact.py \
   --wasm work/intent-physics/baseline-run30/solver.wasm \
   --input work/intent-physics/baseline-run27/input.json \
   --trajectory work/intent-physics/baseline-run27/trajectory.json

Analytic counterexamples were independently designed by the body reviewer:
interior box, off-midpoint edge box, connected nonconvex U, and historical side.
All legacy seven-point samples miss these transverse intersections. Real tests
use the saved failing forearm faces and the complete saved cloth mesh.
"""
import argparse, base64, hashlib, json, struct, subprocess
from pathlib import Path
import numpy as np
import trimesh


def pack(a,dtype='<f4'):
    return base64.b64encode(np.asarray(a,dtype=dtype).tobytes()).decode()


def unpack(value,width=3,dtype='<f4'):
    a=np.frombuffer(base64.b64decode(value),dtype=dtype).astype(float)
    return a.reshape(-1,width) if width>1 else a


def pack_body(mesh):
    # Synthetic fixture packaging only. Verification uses independent ray/mesh
    # queries; no production builder or contact implementation is imported.
    v=np.asarray(mesh.vertices,dtype=np.float32).astype(float);f=np.asarray(mesh.faces,int)
    p=v[f];cross=np.cross(p[:,1]-p[:,0],p[:,2]-p[:,0]);fn=cross/np.linalg.norm(cross,axis=1)[:,None]
    vn=np.zeros_like(v);en=np.zeros((len(f),3,3));edges={}
    for k in range(3):
        a=p[:,(k+1)%3]-p[:,k];b=p[:,(k+2)%3]-p[:,k]
        angle=np.arctan2(np.linalg.norm(np.cross(a,b),axis=1),np.einsum('ij,ij->i',a,b))
        np.add.at(vn,f[:,k],fn*angle[:,None])
    vn/=np.linalg.norm(vn,axis=1)[:,None]
    for i,face in enumerate(f):
        for k in range(3):edges.setdefault(tuple(sorted([int(face[k]),int(face[(k+1)%3])])),[]).append((i,k))
    for rows in edges.values():
        assert len(rows)==2
        n=fn[[i for i,k in rows]].sum(0);n/=np.linalg.norm(n)
        for i,k in rows:en[i,k]=n
    nodes=[];order=[];centers=p.mean(1)
    def split(ids):
        i=len(nodes);nodes.append(None);lo=p[ids].min((0,1));hi=p[ids].max((0,1))
        if len(ids)<=8:children=(-1,-1,len(order),len(ids));order.extend(ids.tolist())
        else:
            axis=np.argmax(np.ptp(centers[ids],axis=0));ids=ids[np.argsort(centers[ids,axis],kind='stable')];m=len(ids)//2
            children=(split(ids[:m]),split(ids[m:]),0,0)
        nodes[i]=struct.pack('<6f4i',*lo,*hi,*children);return i
    split(np.arange(len(f)))
    return dict(positions=pack(v),normals=pack(vn),edge_normals=pack(en),indices=pack(f,'<i4'),
                order=pack(order,'<i4'),nodes=base64.b64encode(b''.join(nodes)).decode(),
                vertices=len(v),triangles=len(f),nodeCount=len(nodes))


def u_body():
    grid=[[-12.,-8.,8.,12.],[-2.,2.],[-6.,-2.,2.]]
    occupied={(0,0,0),(1,0,0),(2,0,0),(0,0,1),(2,0,1)}
    side=[((-1,0,0),[(0,0,0),(0,0,1),(0,1,1),(0,1,0)]),
          ((1,0,0),[(1,0,0),(1,1,0),(1,1,1),(1,0,1)]),
          ((0,-1,0),[(0,0,0),(1,0,0),(1,0,1),(0,0,1)]),
          ((0,1,0),[(0,1,0),(0,1,1),(1,1,1),(1,1,0)]),
          ((0,0,-1),[(0,0,0),(0,1,0),(1,1,0),(1,0,0)]),
          ((0,0,1),[(0,0,1),(1,0,1),(1,1,1),(0,1,1)])]
    vertices=[];lookup={};faces=[]
    for cell in sorted(occupied):
        for direction,corners in side:
            if tuple(a+b for a,b in zip(cell,direction)) in occupied:continue
            q=[]
            for corner in corners:
                ix=tuple(a+b for a,b in zip(cell,corner))
                if ix not in lookup:lookup[ix]=len(vertices);vertices.append([grid[k][ix[k]]/1000 for k in range(3)])
                q.append(lookup[ix])
            faces.extend([[q[0],q[1],q[2]],[q[0],q[2],q[3]]])
    return trimesh.Trimesh(vertices,faces,process=False)


DRIVER=r"""
import fs from 'node:fs';
const req=JSON.parse(fs.readFileSync(0,'utf8')),module=new WebAssembly.Module(Buffer.from(req.wasm,'base64'));
const w=new WebAssembly.Instance(module,{}).exports;
for(const name of ['project_body_feature_contacts','body_feature_contact_scan','set_body_feature_cap','body_feature_stats_ptr'])
 if(typeof w[name]!=='function')throw Error('Missing actual WASM feature control: '+name);
const pack=a=>Buffer.from(a.buffer,a.byteOffset,a.byteLength).toString('base64');
function setup(c){
 const body=c.body||req.input.body,copy=(ptr,s)=>new Uint8Array(w.memory.buffer,ptr,Buffer.from(s,'base64').length).set(Buffer.from(s,'base64'));
 for(const [k,m] of [['positions','body_ptr'],['normals','body_normal_ptr'],['indices','body_face_ptr'],['order','body_order_ptr'],['nodes','body_node_ptr'],['edge_normals','body_edge_normal_ptr']])copy(w[m](),body[k]);
 w.configure_body(body.vertices,body.triangles,body.nodeCount);
 const nv=c.positions.length,nt=c.triangles.length,x=new Float32Array(w.memory.buffer,w.position_ptr(),nv*3),prev=new Float32Array(w.memory.buffer,w.previous_ptr(),nv*3);
 x.set(c.positions.flat());new Float32Array(w.memory.buffer,w.uv_ptr(),nv*2).set(c.uv.flat());new Int32Array(w.memory.buffer,w.face_ptr(),nt*3).set(c.triangles.flat());
 const m=req.input.material;w.configure_material(m.Eu,m.Ev,m.G,m.nu,m.thickness,m.density);w.configure_cloth(nv,nt);
 for(const [a,b] of c.seams||[])w.add_seam(a,b,1);if(c.seams?.length)w.finalize_seams();
 const inv=new Float32Array(w.memory.buffer,w.invmass_ptr(),nv);if(c.inverse_masses)inv.set(c.inverse_masses);
 if(c.saved){const b=Buffer.from(req.frame.positions,'base64');x.set(new Float32Array(b.buffer,b.byteOffset,b.byteLength/4));}
 prev.set(c.previous?c.previous.flat():x);w.set_contact_margin(.001);w.set_projection_cap(.002);w.set_body_feature_cap(.002);
 return {x,prev,inv,nv,nt,body};
}
const source=setup(req.input),sourceMass=Array.from(source.inv),rows=[];
for(const c of req.cases){
 if(c.source_face!==undefined){
  const f=req.input.triangles[c.source_face];c.positions=f.map(i=>req.saved_positions[i]);c.uv=f.map(i=>req.input.uv[i]);
  c.inverse_masses=f.map(i=>sourceMass[req.input.roots[i]]);
 }
 const v=setup(c);let oldSamplerMoved=false;
 if(c.name.startsWith('analytic.')){
  const before=v.x.slice();w.project_surface_contacts(1);
  oldSamplerMoved=v.x.some((value,i)=>value!==before[i]);
 }
 for(let k=0;k<(c.old_rounds||0);k++)w.project_surface_contacts(1);
 w.body_feature_contact_scan();
 const row={name:c.name,body:v.body,triangles:c.triangles,roots:c.roots||Array.from({length:v.nv},(_,i)=>i),inverse_masses:pack(v.inv),
  initial:pack(v.x),initial_previous:pack(v.prev),old_sampler_moved:oldSamplerMoved,
  initial_stats:Array.from(new Float64Array(w.memory.buffer,w.body_feature_stats_ptr(),16)),steps:[]};
 for(let k=0;k<c.rounds;k++){
  const before=pack(v.x),pb=pack(v.prev);w.project_body_feature_contacts(1);
  const stats=Array.from(new Float64Array(w.memory.buffer,w.body_feature_stats_ptr(),16));
  row.steps.push({before,previous_before:pb,after:pack(v.x),previous_after:pack(v.prev),stats,
    last:Array.from(new Float64Array(w.memory.buffer,w.body_feature_last_contact_ptr(),32))});
 }
 w.body_feature_contact_scan();row.final_stats=Array.from(new Float64Array(w.memory.buffer,w.body_feature_stats_ptr(),16));
 row.body_after={positions:pack(new Float32Array(w.memory.buffer,w.body_ptr(),v.body.vertices*3)),indices:pack(new Int32Array(w.memory.buffer,w.body_face_ptr(),v.body.triangles*3))};
 rows.push(row);
}
process.stdout.write(JSON.stringify(rows));
"""


def segment_hits(mesh,starts,ends):
    direction=ends-starts;length=np.linalg.norm(direction,axis=1);valid=length>1e-9
    direction=direction[valid]/length[valid,None];starts=starts[valid];length=length[valid]
    locations,rays,_=mesh.ray.intersects_location(starts,direction,multiple_hits=True)
    if not len(rays):return 0
    distance=np.einsum('ij,ij->i',locations-starts[rays],direction[rays])
    return int(np.sum((distance>1e-6)&(distance<length[rays]-1e-6)))


def gate(points,row):
    roots=np.asarray(row['roots']);faces=roots[np.asarray(row['triangles'])]
    cloth=trimesh.Trimesh(points,faces,process=False);edges=cloth.edges_unique
    body=trimesh.Trimesh(unpack(row['body']['positions']),unpack(row['body']['indices'],3,'<i4').astype(int),process=False)
    used=np.unique(faces);samples=np.concatenate([points[used],points[edges].mean(1),points[faces].mean(1)])
    be=body.edges_unique;bv=np.asarray(body.vertices);a,b=bv[be[:,0]],bv[be[:,1]]
    keep=np.all(np.minimum(a,b)<=points.max(0)+1e-5,axis=1)&np.all(np.maximum(a,b)>=points.min(0)-1e-5,axis=1)
    return dict(inside_samples=int(body.contains(samples).sum()),
                cloth_edge_body_hits=segment_hits(body,points[edges[:,0]],points[edges[:,1]]),
                body_edge_cloth_hits=segment_hits(cloth,a[keep],b[keep]))


def cases(source):
    cloth=np.array([[-.04,-.04,0],[.06,-.04,0],[-.04,.06,0]])
    boxes=[('analytic.interior_box',[0,0,0]),('analytic.off_midpoint_edge_box',[-.02,-.04,0])]
    rows=[]
    for name,center in boxes:
        mesh=trimesh.creation.box(extents=[.002]*3,transform=trimesh.transformations.translation_matrix(center))
        rows.append(dict(name=name,positions=cloth.tolist(),uv=cloth[:,:2].tolist(),triangles=[[0,1,2]],
                         inverse_masses=[1e5,2e5,1.5e5],body=pack_body(mesh),rounds=12))
    rows.append(dict(name='analytic.connected_U',positions=cloth.tolist(),uv=cloth[:,:2].tolist(),triangles=[[0,1,2]],
                     inverse_masses=[1e5,2e5,1.5e5],body=pack_body(u_body()),rounds=12))
    local=np.array([[.004,-.012,0],[.024,-.012,0],[.004,.012,0]])
    # Previous is outside the CURRENT right-arm region's -X support plane,
    # but crosses the other arm of the same connected U.  Local support alone
    # must not falsely certify that previous whole-face geometry as feasible.
    rows.append(dict(name='analytic.previous_crosses_other_U_arm',positions=local.tolist(),
                     previous=(local+[-.02,0,0]).tolist(),uv=local[:,:2].tolist(),triangles=[[0,1,2]],
                     inverse_masses=[1e5,2e5,1.5e5],body=pack_body(u_body()),rounds=12))
    history={**rows[0],'name':'analytic.history_outside_below_margin',
             'positions':(cloth+[0,0,-.0008]).tolist(),'previous':(cloth+[0,0,.0015]).tolist()}
    rows.append(history)
    rows.append({**rows[0],'name':'analytic.winding_response_reverse','triangles':[[0,2,1]]})
    rows.append({**rows[0],'name':'analytic.fixed_root','inverse_masses':[0,2e5,1.5e5]})
    rows.append({**rows[0],'name':'scope.swept_only_not_supported',
                 'positions':(cloth+[0,0,-.003]).tolist(),
                 'previous':(cloth+[0,0,.003]).tolist(),'rounds':1})
    # The real 6257 initial whole-face exit/support requires about 69 mm;
    # 24*2 mm cannot supply that path.  A fixed, bounded 64-round control keeps
    # the zero-intersection threshold and actual cap unchanged.  This is NOT
    # a claim that the coupled runtime's much smaller round budget converges.
    for face in [6257,6592]:rows.append(dict(name=f'real.forearm.face{face}',source_face=face,triangles=[[0,1,2]],rounds=64))
    for name,old in [('real.full_frame60',0),('real.legacy_sample_miss',32)]:
        rows.append(dict(name=name,**{k:source[k] for k in ['positions','uv','triangles','seams','roots']},saved=True,old_rounds=old,rounds=24))
    return rows


def verify(rows):
    reports=[];max_previous_error=0.;checked_exit_rays=0;max_exit_error=0.;cap=float(np.float32(.002))
    for row in rows:
        assert row['body_after']['positions']==row['body']['positions'], 'Body positions changed'
        assert row['body_after']['indices']==row['body']['indices'], 'Body topology changed'
        before=unpack(row['initial']);start=gate(before,row)
        if row['name']=='scope.swept_only_not_supported':
            middle=(before+unpack(row['initial_previous']))*.5;mid=gate(middle,row)
            assert start['cloth_edge_body_hits']==start['body_edge_cloth_hits']==0
            assert mid['cloth_edge_body_hits']+mid['body_edge_cloth_hits']>0
            assert row['initial_stats'][4]==0 and np.array_equal(before,unpack(row['steps'][-1]['after']))
            reports.append(dict(name=row['name'],endpoint=start,midpath=mid,continuous_collision_detection='NOT_SUPPORTED'))
            continue
        assert start['cloth_edge_body_hits']+start['body_edge_cloth_hits']>0, row['name']+' has no true regression intersection'
        assert row['initial_stats'][4]>0, row['name']+' actual feature detector missed crossings'
        if row['name'].startswith('analytic.') or row['name']=='real.legacy_sample_miss':
            assert start['inside_samples']==0, row['name']+' does not demonstrate legacy sample miss'
        if row['name'].startswith('analytic.'):
            assert not row['old_sampler_moved'], row['name']+' was already modified by the actual old sample projection'
        roots=np.asarray(row['roots']);wi=unpack(row['inverse_masses'],1);fixed=(roots==np.arange(len(roots)))&(wi==0)
        degree=np.bincount(roots[np.asarray(row['triangles'])].ravel(),minlength=len(roots))
        body=trimesh.Trimesh(unpack(row['body']['positions']),unpack(row['body']['indices'],3,'<i4').astype(int),process=False)
        for s in row['steps']:
            a,b=unpack(s['before']),unpack(s['after']);pa,pb=unpack(s['previous_before']),unpack(s['previous_after'])
            assert np.isfinite(b).all() and np.isfinite(pb).all(), row['name']+' nonfinite'
            actual=np.linalg.norm(b-a,axis=1)
            assert float(actual.max())<=cap, (row['name'],'actual f32 root motion exceeded cap',actual.max(),cap)
            assert s['stats'][7]<=cap, (row['name'],'actual accumulated path exceeded cap')
            assert s['stats'][6]==s['stats'][12]==0, (row['name'],'intersection-candidate/stack capacity overflow')
            assert np.array_equal(a[fixed],b[fixed]), 'Fixed root moved'
            assert np.array_equal(b,b[roots]) and np.array_equal(pb,pb[roots]), 'Weld alias separated'
            err=abs((pb-pa)-.8*(b-a));max_previous_error=max(max_previous_error,float(err.max()))
            ulp=np.abs(np.spacing(np.maximum(abs(pa),abs(pb)).astype(np.float32))).astype(float)
            assert np.all(err<=4*degree[:,None]*ulp+1e-12), (row['name'],'previous does not follow actual correction')
            if s['stats'][5]>0 and s['last'][25]>0:
                origin=np.array(s['last'][26:29]);normal=np.array(s['last'][7:10])
                assert body.contains(origin[None])[0], 'Claimed first-exit ray origin is not independently inside body'
                hits,_,_=body.ray.intersects_location(origin[None],normal[None],multiple_hits=True)
                distances=(hits-origin)@normal;distances=distances[distances>1e-8]
                assert len(distances), 'Actual C first-exit ray has no independent body hit'
                error=abs(float(distances.min())-s['last'][25]);max_exit_error=max(max_exit_error,error)
                assert error<=1e-6, (row['name'],'actual body ray exit mismatch',error)
                checked_exit_rays+=1
        after=gate(unpack(row['steps'][-1]['after']),row)
        if row['name'].startswith('analytic.') or row['name'].startswith('real.forearm.'):
            assert after['cloth_edge_body_hits']==after['body_edge_cloth_hits']==after['inside_samples']==0, (row['name'],'local fixture not separated',after)
        else:
            assert after['cloth_edge_body_hits']<start['cloth_edge_body_hits'], (row['name'],'cloth/body crossings did not decrease',start,after)
            assert after['body_edge_cloth_hits']<start['body_edge_cloth_hits'], (row['name'],'body/cloth crossings did not decrease',start,after)
        if row['name']=='analytic.history_outside_below_margin':
            assert (unpack(row['steps'][-1]['after'])[:,2]>0).all(), 'Exited the wrong historical side'
            assert any(s['stats'][15]>0 for s in row['steps']), 'Historical feasible side was not recognized'
        if row['name']=='analytic.previous_crosses_other_U_arm':
            old=gate(unpack(row['initial_previous']),row)
            assert old['cloth_edge_body_hits']+old['body_edge_cloth_hits']>0, 'Invalid-history fixture is not actually intersecting'
            assert row['steps'][0]['stats'][5]>0 and row['steps'][0]['last'][24]==0, 'Intersecting previous face was falsely certified feasible'
        if row['name']=='analytic.interior_box':
            assert (unpack(row['steps'][-1]['after'])[:,2]>0).all(), 'Outward positive winding repair side changed'
        if row['name']=='analytic.winding_response_reverse':
            assert (unpack(row['steps'][-1]['after'])[:,2]<0).all(), 'Response did not reflect reversed outward-side declaration'
        reports.append(dict(name=row['name'],before=start,after=after,rounds=len(row['steps']),
                            initial_intersecting_faces=row['initial_stats'][4],final_intersecting_faces=row['final_stats'][4],
                            maximum_total_vertex_displacement_mm=float(np.linalg.norm(unpack(row['steps'][-1]['after'])-before,axis=1).max()*1000)))
    return dict(verdict='PASS',cases=reports,maximum_previous_sync_error_m=max_previous_error,
                independently_checked_exit_rays=checked_exit_rays,maximum_first_exit_distance_error_m=max_exit_error,
                scope='Requires outward cloth winding. Discrete component controls only; swept-only CCD is NOT_SUPPORTED. Full coupled trajectory, cloth self-contact and real-person fit remain unverified.')


def main():
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--wasm',type=Path,required=True);p.add_argument('--input',type=Path,required=True)
    p.add_argument('--trajectory',type=Path,required=True);args=p.parse_args()
    raw=args.input.read_bytes();source=json.loads(raw);record=json.loads(args.trajectory.read_text());first={}
    source['roots']=[first.setdefault(gid,i) for i,gid in enumerate(source['global_ids'])]
    frame=record['frames'][60];binary=args.wasm.read_bytes()
    request=dict(wasm=base64.b64encode(binary).decode(),input=source,frame=frame,saved_positions=unpack(frame['positions']).tolist(),cases=cases(source))
    runtime=subprocess.run(['node','--input-type=module','-e',DRIVER],input=json.dumps(request),capture_output=True,text=True)
    if runtime.returncode:raise RuntimeError(runtime.stderr)
    report=verify(json.loads(runtime.stdout))
    report.update(wasm_sha256=hashlib.sha256(binary).hexdigest(),input_sha256=hashlib.sha256(raw).hexdigest(),
                  trajectory_sha256=hashlib.sha256(args.trajectory.read_bytes()).hexdigest(),
                  test_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  component_source_sha256=hashlib.sha256(Path(__file__).with_name('body-feature-contact.c').read_bytes()).hexdigest())
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
