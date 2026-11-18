#!/usr/bin/env python3
"""Exercise the ACTUAL compiled solveMembrane through its direct WASM control.

After prepare_experiment.py incorporates membrane-stable.c, run:
  python experiments/intent-edit-review/physics/test_membrane_projection.py \
    --wasm work/intent-physics/YOUR-RUN/solver.wasm \
    --input work/intent-physics/baseline-run25/input.json

Requires Python/numpy and Node; no simulation, generator or shared recomputation
helper is imported.  The recorded run25 fixtures below include actual native
welded inverse masses.  --input optionally checks their original CAD UV/xyz
binding.  It is not necessary for replaying the self-contained fixtures.

This checks nonlinear residual descent, stored x/lambda coupling, pinning,
momentum, covariance and finite results.  A PASS is not a cloth/collision/fit PASS.
"""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np


BASELINE_INPUT_SHA256 = 'ca3b1c3df74a5052b771dab4e0c2b48ca3008416cba97a07c890e972e25ef0d1'
MATERIAL = dict(Eu=120000., Ev=200000., G=30000., nu=.2,
                thickness=.0005, density=.155)
DT = float(np.float32(1/120))
REAL_FIXTURES = [
    dict(name='run25.face5778', face=5778, vertex_ids=[3615, 3538, 3537],
         positions=[[.15893437621328993, 1.3688140578390189, .07839325769353181],
                    [.1587624920982932, 1.3706987035082676, .06586295510363993],
                    [.1586845164196294, 1.369234924294475, .07632968465970613]],
         uv=[[.16555935963947555, .5846001787429831],
             [.15974143601501778, .5923745359758146],
             [.1646551714236093, .5915450397272479]],
         inverse_masses=[127154.859375, 140164.015625, 173366.828125]),
    dict(name='run25.face4491', face=4491, vertex_ids=[2811, 2848, 2386],
         positions=[[-.1598802024114833, 1.3702973153600626, .038284741975113654],
                    [-.15942301617885737, 1.3709357655032008, .062318159062964486],
                    [-.15877113742395044, 1.3708609957538804, .04418869041686859]],
         uv=[[.1477238076442644, .5810348064749375],
             [.15631917517494953, .5839634914731315],
             [.1498703410283433, .5930741519245293]],
         inverse_masses=[40871.578125, 63057.52734375, 122158.8515625]),
]

# The driver only configures memory and invokes the compiled function.  All
# numerical assertions are independently evaluated below in Python/float64.
NODE_DRIVER = r"""
import fs from 'node:fs';
const request=JSON.parse(fs.readFileSync(0,'utf8'));
const bytes=Buffer.from(request.wasm_base64,'base64');
const w=new WebAssembly.Instance(new WebAssembly.Module(bytes),{}).exports;
for(const name of ['membrane_projection_probe','membrane_lambda_ptr',
 'membrane_inverse_dm_ptr','membrane_area_ptr','configure_material',
 'configure_cloth','position_ptr','uv_ptr','face_ptr','invmass_ptr']){
 if(typeof w[name]!=='function')throw Error('Compiled WASM is missing actual control: '+name);
}
const x=new Float32Array(w.memory.buffer,w.position_ptr(),9);
const uv=new Float32Array(w.memory.buffer,w.uv_ptr(),6);
const face=new Int32Array(w.memory.buffer,w.face_ptr(),3);
const mass=new Float32Array(w.memory.buffer,w.invmass_ptr(),3);
const lambda=new Float32Array(w.memory.buffer,w.membrane_lambda_ptr(),3);
const results=[];
for(const c of request.cases){
 const m=request.material;
 w.configure_material(m.Eu,m.Ev,m.G,m.nu,m.thickness,m.density);
 x.set(c.positions.flat());uv.set(c.uv.flat());face.set([0,1,2]);
 w.configure_cloth(3,1);mass.set(c.inverse_masses);lambda.set(c.initial_lambdas||[0,0,0]);
 const row={name:c.name,uv:Array.from(uv),inverse_masses:Array.from(mass),
  inverse_dm:Array.from(new Float32Array(w.memory.buffer,w.membrane_inverse_dm_ptr(),4)),
  area:new Float32Array(w.memory.buffer,w.membrane_area_ptr(),1)[0],steps:[]};
 for(const component of c.components){
  const s={component,before:Array.from(x),lambda_before:Array.from(lambda)};
  w.membrane_projection_probe(0,component,request.dt);
  s.after=Array.from(x);s.lambda_after=Array.from(lambda);row.steps.push(s);
 }
 results.push(row);
}
process.stdout.write(JSON.stringify({results}));
"""


def make_cases():
    rng = np.random.default_rng(20261118)
    cases = []
    for fixture in REAL_FIXTURES:
        cases.append({**fixture, 'components': [1]+[0, 1, 2]*4})
    uv = np.array([[0., 0.], [.02, 0.], [.004, .017]])
    # A range of actual deformations, rather than root-formula mirror tests.
    modes = [('rest', 1., 1., 0.), ('stretch', 4., 2., .3),
             ('compression', .08, .03, 0.), ('shear', 1., 1., 3.),
             ('near_flat', 1., 1e-5, .4), ('near_point', 1e-6, 1e-6, 0.)]
    for name, su, sv, shear in modes:
        F = np.array([[su, shear], [0., sv], [0., 0.]])
        for placement in [0, 1]:
            points = uv@F.T + placement*np.array([.15, 1.37, -.06])
            cases.append(dict(name=f'{name}.placement{placement}', positions=points.tolist(),
                              uv=uv.tolist(), inverse_masses=[1e5, 9e4, 1.4e5],
                              components=[0, 1, 2]*6))
    # Deliberate exact collapse is a stationary point of StVK, not a valid
    # garment: require finite arithmetic, never pretend this test untangles it.
    cases.append(dict(name='exact_collapse.finite_only', positions=[[0., 0., 0.]]*3,
                      uv=uv.tolist(), inverse_masses=[1e5]*3, components=[0, 1, 2]*3))
    for i in range(96):
        L = rng.uniform(.006, .03)
        rest = np.array([[0., 0.], [L, 0.], [L*rng.uniform(-.4, .8), L*rng.uniform(.6, 1.8)]])
        rotation, _ = np.linalg.qr(rng.normal(size=(3, 3)))
        if np.linalg.det(rotation) < 0:
            rotation[:, 0] *= -1
        deform = np.array([[10**rng.uniform(-4, .75), rng.uniform(-3, 3)],
                           [0., 10**rng.uniform(-4, .75)], [0., 0.]])
        points = rest@(rotation@deform).T + (np.array([.15, 1.37, -.06]) if i % 2 else 0)
        mass = 10**rng.uniform(4, 6, size=3)
        if i % 11 == 0:
            mass[i % 3] = 0
        cases.append(dict(name=f'random.{i:02}', positions=points.tolist(),
                          uv=(rest + ([.17, .58] if i % 3 else [0, 0])).tolist(),
                          inverse_masses=mass.tolist(),
                          initial_lambdas=rng.uniform(-1e-7, 1e-7, size=3).tolist(),
                          components=[0, 1, 2]*4))
    base = uv@np.array([[1.5, .4], [.1, .45], [.1, -.07]]).T
    R, _ = np.linalg.qr(np.array([[.3, -.7, .2], [.6, .1, .8], [-.1, .9, .5]]))
    translation = np.array([.23, 1.4, -.07])
    for name, points in [('covariance.base', base), ('covariance.transformed', base@R.T+translation)]:
        cases.append(dict(name=name, positions=points.tolist(), uv=uv.tolist(),
                          inverse_masses=[1e5, 9e4, 1.4e5], components=[0, 1, 2]*3))
    return cases, R, translation


def constants():
    # Reproduce the public f32 MATERIAL inputs and native constitutive constants;
    # no solver helper or implementation under test is imported.
    f = np.float32
    Eu, Ev, G, nu, thickness = [f(MATERIAL[k]) for k in ['Eu', 'Ev', 'G', 'nu', 'thickness']]
    den = f(f(1)-f(f(f(nu*nu)*Ev)/Eu))
    q11, q22, q12 = f(Eu/den), f(Ev/den), f(f(nu*Ev)/den)
    return float(f(q12/q11)), [float(q11), float(f(q22-f(f(q12*q12)/q11))), float(G)], float(thickness)


def independent_constraint(points, inverse_dm, component, r):
    # Matrix calculus in material coordinates: F=Ds*Dm^-1.  This is independent
    # of the implementation's quadratic-root and line-search arithmetic.
    D = np.column_stack([points[1]-points[0], points[2]-points[0]])
    F = D@inverse_dm
    if component == 0:
        C = .5*(F[:, 0]@F[:, 0]-1)+r*.5*(F[:, 1]@F[:, 1]-1)
        dCdF = F@np.diag([1., r])
    elif component == 1:
        C = .5*(F[:, 1]@F[:, 1]-1)
        dCdF = F@np.diag([0., 1.])
    else:
        C = F[:, 0]@F[:, 1]
        dCdF = F@np.array([[0., 1.], [1., 0.]])
    edge_gradient = dCdF@inverse_dm.T
    gradient = np.stack([-edge_gradient.sum(axis=1), edge_gradient[:, 0], edge_gradient[:, 1]])
    return float(C), gradient


def check_binding(path):
    if path is None:
        return None
    raw = path.read_bytes(); data = json.loads(raw)
    for fixture in REAL_FIXTURES:
        assert data['triangles'][fixture['face']] == fixture['vertex_ids'], 'Real fixture vertex mapping changed'
        ids = fixture['vertex_ids']
        assert np.array_equal(np.asarray(data['positions'])[ids], fixture['positions']), 'Real fixture xyz changed'
        assert np.array_equal(np.asarray(data['uv'])[ids], fixture['uv']), 'Real fixture material UV changed'
    for key, value in MATERIAL.items():
        assert data['material'][key] == value, f'Material changed: {key}'
    return hashlib.sha256(raw).hexdigest()


def verify(results, R, translation):
    r, stiffness, thickness = constants()
    counters = dict(cases=len(results), actual_wasm_projections=0, reduced=0, stagnant=0)
    regressions = []; max_direction_error = 0.; by_name = {}
    for row in results:
        by_name[row['name']] = row
        inv = np.asarray(row['inverse_dm']).reshape(2, 2)
        mass = np.asarray(row['inverse_masses'])
        assert row['area'] > 0 and np.isfinite(inv).all()
        for index, step in enumerate(row['steps']):
            counters['actual_wasm_projections'] += 1
            component = step['component']
            before = np.asarray(step['before']).reshape(3, 3)
            after = np.asarray(step['after']).reshape(3, 3)
            lb, la = np.asarray(step['lambda_before']), np.asarray(step['lambda_after'])
            assert np.isfinite(after).all() and np.isfinite(la).all(), row['name']+' nonfinite'
            alpha = 1/(stiffness[component]*thickness*row['area']*DT*DT)
            C0, gradient = independent_constraint(before, inv, component, r)
            C1, _ = independent_constraint(after, inv, component, r)
            R0, R1 = C0+alpha*lb[component], C1+alpha*la[component]
            tolerance = 2e-10*(1+abs(C0)+abs(alpha*lb[component]))
            assert abs(R1) <= abs(R0)+tolerance, (row['name'], index, 'residual increased', R0, R1)
            other = [i for i in range(3) if i != component]
            assert np.array_equal(lb[other], la[other]), 'Unselected multiplier changed'
            assert np.array_equal(before[mass == 0], after[mass == 0]), 'Pinned vertex moved'
            delta_lambda = la[component]-lb[component]
            if delta_lambda == 0:
                counters['stagnant'] += 1
                assert np.array_equal(before, after), 'Position changed without stored multiplier increment'
            else:
                counters['reduced'] += 1
            ideal = before+mass[:, None]*gradient*delta_lambda
            ulp = np.abs(np.spacing(np.maximum(abs(before), abs(ideal)).astype(np.float32)).astype(float))
            error = abs(after-ideal)
            max_direction_error = max(max_direction_error, float(error.max()))
            assert np.all(error <= 2*ulp+1e-15), (row['name'], 'Stored x/lambda updates disagree', error.max())
            # Enforce progress above the representational floor, not below f32
            # coordinate precision.  No production acceptance tolerance changes.
            storage_floor = float((abs(gradient)*ulp).sum()+alpha*abs(np.spacing(np.float32(lb[component]))))
            if abs(R0) > max(1e-8, 64*storage_floor):
                assert abs(R1) < abs(R0), (row['name'], index, 'No progress above storage floor')
            if (mass > 0).all():
                drift = ((after-before)/mass[:, None]).sum(axis=0)
                bound = (2*ulp/mass[:, None]).sum(axis=0)+1e-16
                assert np.all(abs(drift) <= bound), (row['name'], 'Internal projection added net momentum')
            if row['name'].startswith('run25.') and index == 0:
                # Establish that the real fixture would trigger the old bug.
                dl = -R0/(np.sum(mass[:, None]*gradient**2)+alpha)
                old_candidate = before+mass[:, None]*gradient*dl
                old_C, _ = independent_constraint(old_candidate, inv, component, r)
                old_R = old_C+alpha*(lb[component]+dl)
                old_move = float(np.linalg.norm(old_candidate-before, axis=1).max())
                new_move = float(np.linalg.norm(after-before, axis=1).max())
                assert abs(old_R) > 10*abs(R0), 'Regression no longer exercises nonlinear overshoot'
                assert abs(R1) < .01*abs(R0), 'Real compressed fixture did not converge'
                assert new_move < .25*old_move, 'Real compressed fixture retained the unsafe large step'
                regressions.append(dict(name=row['name'], old_residual=R0,
                    legacy_full_step_residual=old_R, actual_new_residual=R1,
                    legacy_max_move_mm=old_move*1000, actual_max_move_mm=new_move*1000))
    covariance_error = 0.
    for a, b in zip(by_name['covariance.base']['steps'], by_name['covariance.transformed']['steps']):
        expected = np.asarray(a['after']).reshape(3, 3)@R.T+translation
        actual = np.asarray(b['after']).reshape(3, 3)
        covariance_error = max(covariance_error, float(abs(actual-expected).max()))
    covariance_bound = 64*np.finfo(np.float32).eps*max(1., np.abs(translation).max())
    assert covariance_error <= covariance_bound, ('Rigid covariance failed', covariance_error, covariance_bound)
    return dict(verdict='PASS', **counters, real_regressions=regressions,
                max_stored_direction_rounding_error_m=max_direction_error,
                rigid_covariance_error_m=covariance_error,
                scope='Actual compiled per-constraint nonlinear projection only; full dynamics, collisions and physical fit remain unverified.')


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--wasm', type=Path, required=True)
    p.add_argument('--input', type=Path)
    args = p.parse_args()
    binding = check_binding(args.input)
    cases, R, translation = make_cases()
    binary = args.wasm.read_bytes()
    request = dict(wasm_base64=base64.b64encode(binary).decode(), material=MATERIAL, dt=DT, cases=cases)
    runtime = subprocess.run(['node', '--input-type=module', '-e', NODE_DRIVER],
                             input=json.dumps(request), text=True, capture_output=True, check=False)
    if runtime.returncode:
        raise RuntimeError('Actual WASM control failed:\n'+runtime.stderr)
    data = json.loads(runtime.stdout)
    report = verify(data['results'], R, translation)
    report.update(wasm_sha256=hashlib.sha256(binary).hexdigest(),
                  real_fixture_input_sha256=BASELINE_INPUT_SHA256, checked_input_sha256=binding,
                  test_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
