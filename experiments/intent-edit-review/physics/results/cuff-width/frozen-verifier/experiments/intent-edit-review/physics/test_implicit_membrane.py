#!/usr/bin/env python3
"""Independent controls of the actual compiled global implicit membrane solver.

Example (all local; no generator or solver recomputation helper is imported):
 python experiments/intent-edit-review/physics/test_implicit_membrane.py \
   --wasm work/intent-physics/baseline-run27/solver.wasm \
   --input work/intent-physics/baseline-run25/input.json \
   --legacy-wasm work/intent-physics/baseline-run25/solver.wasm \
   --legacy-wasm work/intent-physics/baseline-run26/solver.wasm

The native full-step comparison disables body, self contact and hinges solely
to isolate membrane mechanics.  Its PASS is not a full garment/fit verdict.
"""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np


DT = float(np.float32(1/120))
DRIVER = r"""
import fs from 'node:fs';
const req=JSON.parse(fs.readFileSync(0,'utf8'));
const module=new WebAssembly.Module(Buffer.from(req.wasm,'base64'));
const pack=a=>Buffer.from(a.buffer,a.byteOffset,a.byteLength).toString('base64');
const make=mod=>new WebAssembly.Instance(mod,{}).exports;
const w=make(module);
for(const name of ['implicit_membrane_probe_begin','implicit_membrane_probe_iteration',
 'implicit_membrane_probe_objective','implicit_membrane_probe_gradient',
 'implicit_membrane_prediction_ptr','implicit_membrane_gradient_ptr','implicit_membrane_stats_ptr']){
 if(typeof w[name]!=='function')throw Error('Missing actual global WASM control: '+name);
}
function setup(w,c){
 const nv=c.positions.length,nt=c.triangles.length;
 const x=new Float32Array(w.memory.buffer,w.position_ptr(),nv*3);
 const uv=new Float32Array(w.memory.buffer,w.uv_ptr(),nv*2);
 const faces=new Int32Array(w.memory.buffer,w.face_ptr(),nt*3);
 x.set(c.positions.flat());uv.set(c.uv.flat());faces.set(c.triangles.flat());
 const m=req.input.material;
 w.configure_material(m.Eu,m.Ev,m.G,m.nu,m.thickness,m.density);w.configure_cloth(nv,nt);
 for(const [a,b] of c.seams||[])w.add_seam(a,b,1);
 if(c.seams?.length)w.finalize_seams();
 const inv=new Float32Array(w.memory.buffer,w.invmass_ptr(),nv);
 if(c.inverse_masses)inv.set(c.inverse_masses);
 w.set_collision(0);
 return {nv,nt,x,uv,faces,inv};
}
function context(w,c,v,dt){
 const dmPtr=w.implicit_membrane_inverse_dm_ptr||w.membrane_inverse_dm_ptr;
 const areaPtr=w.implicit_membrane_area_ptr||w.membrane_area_ptr;
 if(!dmPtr||!areaPtr)throw Error('Missing actual rest-cache read controls');
 return {nv:v.nv,nt:v.nt,dt,roots:c.roots||Array.from({length:v.nv},(_,i)=>i),
  uv:pack(v.uv),faces:pack(v.faces),inverse_masses:pack(v.inv),
  inverse_dm:pack(new Float32Array(w.memory.buffer,dmPtr(),v.nt*4)),
  areas:pack(new Float32Array(w.memory.buffer,areaPtr(),v.nt)),
  predicted:pack(new Float32Array(w.memory.buffer,w.implicit_membrane_prediction_ptr(),v.nv*3))};
}
const rows=[];
const full=setup(w,req.input),fullMass=Array.from(full.inv);
for(const c of req.cases){
 if(c.source_face!==undefined){
  const local=req.input.triangles[c.source_face],roots=req.input.roots;
  c.positions=local.map(i=>req.input.positions[i]);c.uv=local.map(i=>req.input.uv[i]);
  c.inverse_masses=local.map(i=>fullMass[roots[i]]);
 }
 const v=setup(w,c),dt=c.dt||req.dt;
 w.implicit_membrane_probe_begin(dt);
 if(c.start)v.x.set(c.start.flat());
 const ctx=context(w,c,v,dt);
 const initialObjective=w.implicit_membrane_probe_gradient(dt);
 const row={name:c.name,context:ctx,initial:{positions:pack(v.x),objective:initialObjective,
  gradient:pack(new Float64Array(w.memory.buffer,w.implicit_membrane_gradient_ptr(),v.nv*3))},steps:[]};
 for(let k=0;k<c.iterations;k++){
  const injected=Boolean(c.inject&&k===c.inject.iteration);
  if(injected)v.x[c.inject.vertex*3+c.inject.axis]+=c.inject.delta;
  const before=pack(v.x),J0=w.implicit_membrane_probe_objective(dt);
  const accepted=w.implicit_membrane_probe_iteration(dt),J1=w.implicit_membrane_probe_objective(dt);
  row.steps.push({before,after:pack(v.x),J0,J1,accepted,injected,
    stats:Array.from(new Float64Array(w.memory.buffer,w.implicit_membrane_stats_ptr(),14))});
 }
 row.predicted_after=pack(new Float32Array(w.memory.buffer,w.implicit_membrane_prediction_ptr(),v.nv*3));
 rows.push(row);
}
const nativeSetup=setup(w,req.input),initial=pack(nativeSetup.x);
w.step(1,0);
const native={context:context(w,req.input,nativeSetup,req.dt),initial,
 after:pack(nativeSetup.x),objective:w.implicit_membrane_probe_objective(req.dt),
 stats:Array.from(new Float64Array(w.memory.buffer,w.implicit_membrane_stats_ptr(),14))};
const legacy=[];
for(const c of req.legacy){
 const lw=make(new WebAssembly.Module(Buffer.from(c.bytes,'base64'))),v=setup(lw,req.input);
 lw.step(1,0);legacy.push({name:c.name,after:pack(v.x),inverse_masses:pack(v.inv),uv:pack(v.uv)});
}
process.stdout.write(JSON.stringify({rows,native,legacy}));
"""


def unpack(value, width=1, dtype='<f4'):
    v = np.frombuffer(base64.b64decode(value, validate=True), dtype=dtype).astype(float)
    return v.reshape(-1, width) if width > 1 else v


def make_cases(data):
    rng = np.random.default_rng(20261119)
    tri = [[0, 1, 2]]; uv = np.array([[0., 0.], [.02, 0.], [.004, .017]])
    cases = [dict(name=f'real.face{face}', source_face=face, triangles=tri, iterations=20)
             for face in [5778, 4491]]
    for i in range(30):
        R, _ = np.linalg.qr(rng.normal(size=(3, 3)))
        F = R@np.array([[10**rng.uniform(-4, .7), rng.uniform(-2, 2)],
                        [0., 10**rng.uniform(-4, .7)], [0., 0.]])
        p = uv@F.T + (np.array([.15, 1.37, -.06]) if i % 2 else 0)
        mass = 10**rng.uniform(4, 6, size=3)
        if i % 9 == 0:
            mass[0] = 0
        cases.append(dict(name=f'random.{i:02}', positions=p.tolist(), uv=uv.tolist(),
                          triangles=tri, inverse_masses=mass.tolist(), iterations=12))
    base = uv@np.array([[1.5, .4], [.1, .45], [.1, -.07]]).T
    R, _ = np.linalg.qr(np.array([[.3, -.7, .2], [.6, .1, .8], [-.1, .9, .5]]))
    translation = np.array([.23, 1.4, -.07])
    for name, points in [('covariance.base', base), ('covariance.transformed', base@R.T+translation)]:
        cases.append(dict(name=name, positions=points.tolist(), uv=uv.tolist(), triangles=tri,
                          inverse_masses=[1e5, 9e4, 1.4e5], iterations=8))
    for scale in [.5, 1., 2.]:
        # Deliberately visible inertial energy for the wrong-mass/wrong-dt
        # fault controls, rather than a displacement at the matching floor.
        displaced = base+10*np.array([[.001, -.002, .0004], [-.001, .0003, .0001], [.0002, .001, -.0002]])
        cases.append(dict(name=f'inertia.dt{scale}', positions=base.tolist(), start=displaced.tolist(),
                          uv=uv.tolist(), triangles=tri, inverse_masses=[1e5, 9e4, 1.4e5],
                          dt=float(np.float32(DT*scale)), iterations=12))
    cases.append(dict(name='external_projection', positions=base.tolist(), uv=uv.tolist(), triangles=tri,
                      inverse_masses=[1e5, 9e4, 1.4e5], iterations=12,
                      inject=dict(iteration=4, vertex=0, axis=2, delta=.002)))
    cases.append(dict(name='full_source_probe', **{k:data[k] for k in ['positions','uv','triangles','seams','roots']}, iterations=24))
    return cases, R, translation


def material_constants(material):
    f = np.float32
    Eu, Ev, G, nu, thickness = [f(material[k]) for k in ['Eu','Ev','G','nu','thickness']]
    den = f(f(1)-f(f(f(nu*nu)*Ev)/Eu))
    return float(f(Eu/den)), float(f(Ev/den)), float(f(f(nu*Ev)/den)), float(G), float(thickness)


def objective(points, ctx, material, gradient=False, dt_override=None, mass_scale=1.):
    faces = unpack(ctx['faces'], 3, '<i4').astype(int)
    roots = np.asarray(ctx['roots'], int); faces = roots[faces]
    inv = unpack(ctx['inverse_dm']).reshape(-1, 2, 2)
    areas = unpack(ctx['areas']); wi = unpack(ctx['inverse_masses'])
    predicted = unpack(ctx['predicted'], 3)
    free = (roots == np.arange(len(roots))) & (wi > 0)
    masses = np.zeros(len(roots)); masses[free] = mass_scale/wi[free]
    dt = ctx['dt'] if dt_override is None else dt_override
    D = np.stack([points[faces[:, 1]]-points[faces[:, 0]], points[faces[:, 2]]-points[faces[:, 0]]], axis=2)
    F = D@inv; C = np.einsum('tji,tjk->tik', F, F); E = (C-np.eye(2))/2
    q11, q22, q12, G, thickness = material_constants(material)
    W = .5*q11*E[:,0,0]**2+q12*E[:,0,0]*E[:,1,1]+.5*q22*E[:,1,1]**2+2*G*E[:,0,1]**2
    elastic = float(np.sum(areas*thickness*W))
    delta = points-predicted
    inertia = float(.5*np.sum(masses[:,None]*delta**2)/dt**2)
    result = dict(objective=elastic+inertia, elastic=elastic, inertia=inertia)
    if gradient:
        S = np.zeros((len(faces),2,2))
        S[:,0,0]=q11*E[:,0,0]+q12*E[:,1,1]
        S[:,1,1]=q12*E[:,0,0]+q22*E[:,1,1]
        S[:,0,1]=S[:,1,0]=2*G*E[:,0,1]
        force = (F@S)@inv.transpose(0,2,1)*(areas*thickness)[:,None,None]
        grad = masses[:,None]*delta/dt**2
        np.add.at(grad, faces[:,0], -force.sum(axis=2))
        np.add.at(grad, faces[:,1], force[:,:,0]); np.add.at(grad, faces[:,2], force[:,:,1])
        grad[~free] = 0
        result['gradient'] = grad
    return result


def strain(points, ctx):
    roots = np.asarray(ctx['roots'], int); faces = roots[unpack(ctx['faces'],3,'<i4').astype(int)]
    inv = unpack(ctx['inverse_dm']).reshape(-1,2,2)
    F = np.stack([points[faces[:,1]]-points[faces[:,0]], points[faces[:,2]]-points[faces[:,0]]],axis=2)@inv
    s = np.linalg.svd(F,compute_uv=False)
    return dict(max_principal_strain_percent=float((s[:,0].max()-1)*100),
                p95_principal_strain_percent=float(np.percentile(s[:,0]-1,95)*100),
                min_area_ratio=float(np.prod(s,axis=1).min()))


def check_rest_cache(ctx):
    """Bind native caches to actual per-panel material coordinates, not claims."""
    uv=unpack(ctx['uv'],2);faces=unpack(ctx['faces'],3,'<i4').astype(int)
    Dm=np.stack([uv[faces[:,1]]-uv[faces[:,0]],uv[faces[:,2]]-uv[faces[:,0]]],axis=2)
    expected_inverse=np.linalg.inv(Dm);expected_area=abs(np.linalg.det(Dm))/2
    assert np.allclose(unpack(ctx['inverse_dm']).reshape(-1,2,2),expected_inverse,
                       rtol=2e-6,atol=1e-6), 'Native rest inverse differs from input UV'
    assert np.allclose(unpack(ctx['areas']),expected_area,rtol=2e-6,atol=1e-12), 'Native area differs from input UV'


def verify(data, source, R, translation):
    material=source['material']; accepted=0; checked=0; max_gradient_error=0.; summary=[]; rows={}
    for row in data['rows']:
        rows[row['name']]=row;ctx=row['context'];x=unpack(row['initial']['positions'],3)
        check_rest_cache(ctx)
        ref=objective(x,ctx,material,gradient=True)
        native_gradient=unpack(row['initial']['gradient'],3,'<f8')
        assert np.isfinite(native_gradient).all(), row['name']+' nonfinite gradient'
        err=float(abs(native_gradient-ref['gradient']).max());max_gradient_error=max(max_gradient_error,err)
        assert np.allclose(native_gradient,ref['gradient'],rtol=2e-8,atol=2e-9), (row['name'],'material/mass/dt gradient mismatch',err)
        assert np.isclose(row['initial']['objective'],ref['objective'],rtol=2e-10,atol=2e-12), (row['name'],'initial objective mismatch')
        if ctx['nv']<=3:
            # Independent finite difference of total StVK + inertia, including
            # real nonzero prediction displacement; no analytic solver helper.
            roots=np.asarray(ctx['roots']);wi=unpack(ctx['inverse_masses'])
            h=2e-7
            for i in range(ctx['nv']):
                if wi[i]==0 or roots[i]!=i:continue
                for axis in range(3):
                    a=x.copy();b=x.copy();a[i,axis]+=h;b[i,axis]-=h
                    fd=(objective(a,ctx,material)['objective']-objective(b,ctx,material)['objective'])/(2*h)
                    assert np.isclose(fd,native_gradient[i,axis],rtol=2e-5,atol=2e-6), (row['name'],'finite difference',i,axis,fd,native_gradient[i,axis])
        initial_objective=ref['objective'];curve=[]
        for step in row['steps']:
            checked+=1;a=unpack(step['before'],3);b=unpack(step['after'],3)
            assert np.isfinite(b).all(), row['name']+' nonfinite positions'
            before=objective(a,ctx,material);after=objective(b,ctx,material)
            assert np.isclose(step['J0'],before['objective'],rtol=2e-10,atol=2e-12), row['name']+' before mismatch'
            assert np.isclose(step['J1'],after['objective'],rtol=2e-10,atol=2e-12), row['name']+' after mismatch'
            tolerance=3e-10*(1+before['objective'])
            assert after['objective']<=before['objective']+tolerance, (row['name'],'global objective increased')
            if step['accepted']:
                accepted+=1
                assert after['objective']<before['objective'], row['name']+' accepted non-descent'
            else:
                assert np.array_equal(a,b), row['name']+' rejected step modified x'
            wi=unpack(ctx['inverse_masses']);roots=np.asarray(ctx['roots'])
            pinned=(wi==0)&(roots==np.arange(len(roots)))
            assert np.array_equal(a[pinned],b[pinned]), 'Fixed root moved'
            assert np.array_equal(b,b[roots]), 'Weld alias separated'
            curve.append(after['objective'])
        assert row['predicted_after']==ctx['predicted'], 'External projection rewrote physical prediction'
        if row['name']=='external_projection':
            assert row['steps'][4]['stats'][7]>=1, 'External projection did not invalidate history'
        summary.append(dict(name=row['name'],initial_objective=initial_objective,final_objective=curve[-1],accepted=sum(s['accepted'] for s in row['steps'])))
    # Deliberately wrong mass and dt must not match the actual inertial objective.
    inertia_row=rows['inertia.dt1.0'];ctx=inertia_row['context'];x=unpack(inertia_row['initial']['positions'],3)
    good=objective(x,ctx,material)['objective']
    for bad in [objective(x,ctx,material,mass_scale=.5)['objective'],objective(x,ctx,material,dt_override=2*ctx['dt'])['objective']]:
        assert abs(bad-good)>1e-6, 'Mass/dt fault control is insensitive'
    covariance_error=0.
    for a,b in zip(rows['covariance.base']['steps'],rows['covariance.transformed']['steps']):
        error=abs(unpack(b['after'],3)-(unpack(a['after'],3)@R.T+translation)).max()
        covariance_error=max(covariance_error,float(error))
    assert covariance_error<=256*np.finfo(np.float32).eps*max(1.,abs(translation).max()), ('Rigid covariance',covariance_error)
    full=data['native'];ctx=full['context'];initial=unpack(full['initial'],3);final=unpack(full['after'],3);pred=unpack(ctx['predicted'],3)
    check_rest_cache(ctx)
    assert np.array_equal(unpack(ctx['uv'],2),np.asarray(source['uv'],dtype=np.float32).astype(float)), 'Production material UV changed'
    assert np.array_equal(unpack(ctx['faces'],3,'<i4').astype(int),source['triangles']), 'Production topology changed'
    assert np.array_equal(initial,np.asarray(source['positions'],dtype=np.float32).astype(float)), 'Production initial positions changed'
    roots=np.asarray(ctx['roots']);faces=unpack(ctx['faces'],3,'<i4').astype(int)
    expected_mass=np.zeros(ctx['nv']);areas=unpack(ctx['areas'])
    for k in range(3):np.add.at(expected_mass,roots[faces[:,k]],areas*float(np.float32(material['density']))/3)
    wi=unpack(ctx['inverse_masses']);is_root=roots==np.arange(ctx['nv'])
    assert (wi[is_root]>0).all() and (wi[~is_root]==0).all(), 'Production roots were pinned or alias masses changed'
    assert np.allclose(1/wi[is_root],expected_mass[is_root],rtol=2e-6,atol=1e-12), 'Production mass differs from input density/area/welds'
    # Verify the real native prediction used the unchanged 1/120 s and gravity,
    # rather than minimizing around a silently relocated/reshaped target.
    expected=initial.astype(np.float32).copy();g=np.float32(-9.81)*np.float32(np.float32(DT)*np.float32(DT))
    expected[:,1]=np.float32(expected[:,1]+g)
    expected=expected[np.asarray(ctx['roots'])]
    assert np.array_equal(pred,expected.astype(float)), 'Native prediction/dt/gravity changed'
    original=objective(pred,ctx,material);after=objective(final,ctx,material)
    assert np.isclose(full['objective'],after['objective'],rtol=2e-10,atol=2e-12), 'Native full-step J mismatch'
    assert after['objective']<original['objective'] and after['elastic']<original['elastic'], 'Real first-step energy did not decrease'
    assert full['stats'][8]==24 and full['stats'][7]==0, 'Wrong native iteration integration or unexpected projection'
    native_report=dict(initial=original,after=after,**strain(final,ctx),
                       max_vertex_move_mm=float(np.linalg.norm(final-initial,axis=1).max()*1000),
                       actual_iterations=full['stats'][8],accepted_iterations=full['stats'][6])
    legacy=[]
    for old in data['legacy']:
        assert old['inverse_masses']==ctx['inverse_masses'], 'Comparison mass changed'
        assert old['uv']==ctx['uv'], 'Comparison rest UV changed'
        p=unpack(old['after'],3);values=objective(p,ctx,material)
        assert values['elastic']>original['elastic'], 'Legacy comparison no longer demonstrates first-step regression'
        legacy.append(dict(name=old['name'],**values,**strain(p,ctx),max_vertex_move_mm=float(np.linalg.norm(p-initial,axis=1).max()*1000)))
    return dict(verdict='PASS',cases=len(summary),actual_global_iterations=checked,accepted_iterations=accepted,
                maximum_gradient_absolute_error=max_gradient_error,rigid_covariance_error_m=covariance_error,
                mass_dt_fault_controls='PASS',cases_summary=summary,native_first_step=native_report,legacy_first_steps=legacy,
                scope='Unchanged orthotropic StVK + actual mass/dt inertia; collision/hinge projections excluded. Full cloth collision safety and real-person fit are NOT validated.')


def main():
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--wasm',type=Path,required=True);p.add_argument('--input',type=Path,required=True)
    p.add_argument('--legacy-wasm',type=Path,action='append',default=[]);args=p.parse_args()
    raw=args.input.read_bytes();source=json.loads(raw);gids=source['global_ids'];first={}
    source['roots']=[first.setdefault(gid,i) for i,gid in enumerate(gids)]
    cases,R,translation=make_cases(source);binary=args.wasm.read_bytes()
    request=dict(wasm=base64.b64encode(binary).decode(),input=source,cases=cases,dt=DT,
                 legacy=[dict(name=str(path),bytes=base64.b64encode(path.read_bytes()).decode()) for path in args.legacy_wasm])
    runtime=subprocess.run(['node','--input-type=module','-e',DRIVER],input=json.dumps(request),capture_output=True,text=True)
    if runtime.returncode:raise RuntimeError(runtime.stderr)
    report=verify(json.loads(runtime.stdout),source,R,translation)
    report.update(wasm_sha256=hashlib.sha256(binary).hexdigest(),input_sha256=hashlib.sha256(raw).hexdigest(),
                  test_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  implicit_source_sha256=hashlib.sha256(Path(__file__).with_name('implicit-membrane.c').read_bytes()).hexdigest())
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
