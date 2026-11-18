#!/usr/bin/env python3
"""Prepare source-bound experimental cloth input; all assumptions stay explicit."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
import sys
import numpy as np
import trimesh
import yaml
import triangle as triangle_lib
from scipy.interpolate import PchipInterpolator

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'services/dxf-preview'))
from converter.core import parse_dxf
from converter.sewn import Builder, build, harmonic
from initial_placement import improve_initial_placement
from arm_placement import retarget_sleeves


def sha(raw): return hashlib.sha256(raw).hexdigest()
def encode(array, dtype): return base64.b64encode(np.asarray(array, dtype=dtype).tobytes()).decode()


class PhysicsBuilder(Builder):
    """Uniform shared boundary samples avoid microscopic union-of-knots slivers.

    The CAD curves and sewing processes are retained. This is a separate physics
    mesh; the legacy static exporter keeps its original Builder and exact output.
    """
    boundary_step_mm = 5.0
    def add(self, name, *args, **kwargs):
        super().add(name, *args, **kwargs)
        segment = self.segments[name]
        segment['q'] = np.linspace(0, 1, max(3, int(np.ceil(segment['processed_length_mm']/self.boundary_step_mm))+1))
    def bind(self, name, a, b):
        super().bind(name, a, b)
        count = max(3, int(np.ceil(max(self.segments[k]['processed_length_mm'] for k in [a, b])/self.boundary_step_mm))+1)
        self.segments[a]['q'] = self.segments[b]['q'] = np.linspace(0, 1, count)


def quality_triangulate(boundary, spacing):
    segments = np.column_stack([np.arange(len(boundary)), np.roll(np.arange(len(boundary)), -1)])
    mesh = triangle_lib.triangulate({'vertices': boundary, 'segments': segments}, f'pYq22a{spacing*spacing/2:.9f}')
    points, faces = np.asarray(mesh['vertices']), np.asarray(mesh['triangles'], int)
    if not np.array_equal(points[:len(boundary)], boundary):
        raise ValueError('Physics mesher changed the synchronized seam boundary samples')
    edges = np.unique(np.sort(np.vstack([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]]), axis=1), axis=0)
    return points, faces, edges


def body_asset(path):
    raw = path.read_bytes(); data = json.loads(raw)
    points = np.asarray(data['positions']).reshape(-1, 3)
    faces = np.asarray(data['triangles'], dtype=int).reshape(-1, 3)
    mesh = trimesh.Trimesh(points, faces, process=False)
    if not mesh.is_watertight or not mesh.is_winding_consistent or mesh.volume <= 0:
        raise ValueError('The actual body must be closed and consistently outward oriented')
    triangles = points[faces]; normals = np.zeros_like(points)
    crosses = np.cross(triangles[:, 1]-triangles[:, 0], triangles[:, 2]-triangles[:, 0])
    face_normals = crosses/np.linalg.norm(crosses,axis=1)[:,None]
    for k in range(3):
        a=triangles[:,(k+1)%3]-triangles[:,k];b=triangles[:,(k+2)%3]-triangles[:,k]
        angle=np.arctan2(np.linalg.norm(np.cross(a,b),axis=1),np.sum(a*b,axis=1))
        np.add.at(normals,faces[:,k],face_normals*angle[:,None])
    normals /= np.maximum(np.linalg.norm(normals, axis=1)[:, None], 1e-15)
    edge_faces={}
    for i,face in enumerate(faces):
        for k in range(3):edge_faces.setdefault(tuple(sorted([int(face[k]),int(face[(k+1)%3])])),[]).append((i,k))
    edge_normals=np.empty((len(faces),3,3))
    for rows in edge_faces.values():
        if len(rows)!=2:raise ValueError('Body edge pseudonormal requires a closed two-manifold')
        normal=face_normals[[i for i,k in rows]].sum(axis=0);normal/=np.linalg.norm(normal)
        for i,k in rows:edge_normals[i,k]=normal
    mesh.vertex_normals = normals
    centers = triangles.mean(1); nodes = []; order = []
    def partition(ids):
        index = len(nodes); nodes.append(None)
        lo, hi = triangles[ids].min((0, 1)), triangles[ids].max((0, 1))
        if len(ids) <= 8:
            children = (-1, -1, len(order), len(ids)); order.extend(ids.tolist())
        else:
            axis = np.argmax(np.ptp(centers[ids], axis=0)); ids = ids[np.argsort(centers[ids, axis], kind='stable')]
            half = len(ids)//2; children = (partition(ids[:half]), partition(ids[half:]), 0, 0)
        nodes[index] = struct.pack('<6f4i', *lo, *hi, *children)
        return index
    partition(np.arange(len(faces)))
    packed = {'positions': encode(points, '<f4'), 'normals': encode(normals, '<f4'), 'edge_normals':encode(edge_normals,'<f4'),
              'indices': encode(faces, '<i4'), 'order': encode(order, '<i4'),
              'nodes': base64.b64encode(b''.join(nodes)).decode(), 'vertices': len(points),
              'triangles': len(faces), 'nodeCount': len(nodes), 'source_sha256': sha(raw),
              'source': str(path.relative_to(ROOT)), 'landmarks': data['landmarks']}
    return mesh, packed


def retarget_sleeve(builder, patch, side, body, translation, original):
    """Place the unchanged material mesh along the actual proxy arm, before solving."""
    boundary = []
    for key, reverse in builder.loops['sleeve.'+side]:
        segment = builder.segments[key]; domain = segment['domain'](segment['q'])
        if reverse: domain = domain[::-1]
        boundary.extend(domain[:-1])
    points = np.asarray(patch['flat_points']); faces = np.asarray(patch['local_faces'], int)
    edges = np.unique(np.sort(np.vstack([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]]), axis=1), axis=0)
    domain, _ = harmonic(points, faces, edges, np.asarray(boundary))
    u, angle = domain.T; grid = np.linspace(0, 1, 257); tube = builder.targets['tube.'+side]
    convert = lambda a: np.asarray(a)[:, [0, 2, 1]] * [1, 1, -1] + translation
    center = (convert(tube(grid, np.zeros(len(grid))))+convert(tube(grid, np.full(len(grid), np.pi))))/2
    targets = [center[0].copy()]
    # Follow horizontal sections down the actual arm. Sections in X can jump
    # between upper arm, forearm and hand where the bent limb folds back in X.
    for y in np.linspace(1.275, 1.025, 11):
        candidates = body.vertices[(abs(body.vertices[:, 1]-y) < .018) & (body.vertices[:, 0] > .20)]
        if not len(candidates): raise ValueError('Proxy arm cannot be located from its actual vertices')
        point = np.median(candidates, axis=0); point[0] *= -1 if side == 'left' else 1
        point[1] = y; targets.append(point)
    targets = np.asarray(targets)
    cumulative = np.r_[0, np.cumsum(np.linalg.norm(np.diff(targets, axis=0), axis=1))]
    target = PchipInterpolator(cumulative/cumulative[-1], targets, axis=0)(grid)
    blend = np.clip((grid-.22)/.35, 0, 1); blend = blend*blend*(3-2*blend)
    center_new = center*(1-blend[:, None])+target*blend[:, None]
    tangent = np.gradient(center_new, grid, axis=0); tangent /= np.linalg.norm(tangent, axis=1)[:, None]
    front = np.tile([0., 0., 1.], (len(grid), 1)); front -= tangent*np.sum(front*tangent, axis=1)[:, None]
    front /= np.linalg.norm(front, axis=1)[:, None]
    radial = np.cross(front, tangent) * (-1 if side == 'left' else 1)
    sample = lambda a: np.column_stack([np.interp(u, grid, a[:, k]) for k in range(3)])
    old_radial = convert(tube(grid, np.zeros(len(grid))))-center
    old_radial /= np.linalg.norm(old_radial, axis=1)[:, None]
    old_tangent = np.gradient(center, grid, axis=0)
    old_tangent /= np.linalg.norm(old_tangent, axis=1)[:, None]
    relative = original-sample(center)
    # Transport the actual accepted surface, including its exact cap boundary.
    # Recreating an ellipse from domain angles discards the separately defined
    # front/back cap curves and can fold the sleeve before physics even starts.
    placed = sample(center_new)
    placed += sample(radial)*np.sum(relative*sample(old_radial), axis=1)[:, None]
    placed += sample(tangent)*np.sum(relative*sample(old_tangent), axis=1)[:, None]
    placed += sample(front)*relative[:, 2, None]
    return placed


def prepare(args):
    out = args.output.resolve(); out.mkdir(parents=True, exist_ok=True)
    cfg = yaml.safe_load(Path(__file__).with_name('experiment-config.yaml').read_text())
    if args.boundary_step is not None:
        cfg['数值条件']['边界采样间距_U'] = args.boundary_step
    if args.preparation_iterations is not None:
        cfg['数值条件']['穿着初始位置松弛迭代'] = args.preparation_iterations
    PhysicsBuilder.boundary_step_mm = cfg['数值条件'].get('边界采样间距_U', 5.0)
    if cfg['单位']['每U毫米数'] != 1.0:
        raise ValueError('This initial experiment supports only its declared 1U=1mm hypothesis; another scale needs a newly checked placement and mesh')
    page = (ROOT/'web/intent-edit-review/index.html').read_text()
    data = json.loads(re.search(r'<script[^>]*id="app-data"[^>]*>(.*?)</script>', page, re.S)[1])
    entry = next(e for e in [data['baseline'], *data['cases']] if e['id'] == args.case)
    dxf = (ROOT/entry['files']['dxf']['path']).read_bytes()
    spec = (ROOT/entry['files']['yaml']['path']).read_bytes()
    if sha(dxf) != entry['files']['dxf']['sha256'] or sha(spec) != entry['files']['yaml']['sha256']:
        raise ValueError('The selected case differs from the independently audited source package')
    P, _ = parse_dxf(dxf)
    if len(P) != 126: raise ValueError('Only these exact case-specific 126-line sources are supported')
    spacing = cfg['数值条件']['网格采样间距_U']
    welded, welded_faces, certificate = build(P, spacing=spacing, builder_class=PhysicsBuilder, triangulator=quality_triangulate)
    builder = PhysicsBuilder(P, spacing=spacing)
    body, packed_body = body_asset(ROOT/cfg['人体']['文件'])
    shoulder = certificate['segments']['front.shoulder.left']['vertices']
    translation = np.array([0., packed_body['landmarks']['shoulderY']-welded[shoulder, 2].max(), packed_body['landmarks']['neck'][2]])
    xyz = []; uv = []; faces = []; global_ids = []; panels = []; offset = 0
    for name, patch in certificate['patches'].items():
        ids = np.asarray(patch['global_vertices'], int); points = np.asarray(patch['flat_points'])/1000
        positions = welded[ids][:, [0, 2, 1]] * [1, 1, -1] + translation
        if name.startswith('sleeve.') and cfg['数值条件']['袖子预变形']:
            positions = retarget_sleeve(builder, patch, name.split('.')[1], body, translation, positions)
        local = np.asarray(patch['local_faces'], int)
        origin = points.min(axis=0)
        panels.append({'name': name, 'start': offset, 'vertices': len(ids), 'face_start': len(faces), 'faces': len(local), 'uv_origin_m': origin.tolist()})
        xyz.extend(positions.tolist()); uv.extend((points-origin).tolist()); faces.extend((local+offset).tolist()); global_ids.extend(ids.tolist()); offset += len(ids)
    xyz, uv, faces, global_ids = np.asarray(xyz), np.asarray(uv), np.asarray(faces), np.asarray(global_ids)
    arm_blend = np.clip((np.abs(xyz[:, 0])-.25)/.20, 0, 1)
    arm_blend = arm_blend*arm_blend*(3-2*arm_blend)
    placement_depth = {'scale': cfg['数值条件']['初始深度放大'],
                       'offset_m': cfg['数值条件']['初始深度平移_毫米']/1000,
                       'arm_offset_m': cfg['数值条件']['前臂初始向前位移上限_毫米']/1000}
    xyz[:, 2] = xyz[:, 2]*placement_depth['scale']+placement_depth['offset_m']+placement_depth['arm_offset_m']*arm_blend
    first = {}; seams = []
    for i, gid in enumerate(global_ids):
        if int(gid) in first: seams.append([first[int(gid)], i])
        else: first[int(gid)] = i
    initial = xyz.copy()
    fem_seed = None
    if cfg['数值条件'].get('使用材料坐标FEM初始化', False):
        xyz, fem_seed = improve_initial_placement(certificate, xyz, panels, global_ids, builder, translation, placement_depth)
    arm_seed = None
    if cfg['数值条件'].get('按标准人体骨架定位袖子', False):
        if fem_seed is None:raise ValueError('Actual-arm placement requires its independently checked UV-FEM seed')
        xyz, arm_seed = retarget_sleeves(xyz,certificate,panels,global_ids,builder,translation,placement_depth,packed_body)
    roots = np.array(list(first.values()), int)
    nearest, distance, tri = trimesh.proximity.closest_point(body, xyz[roots]); inside = body.contains(xyz[roots])
    margin = cfg['数值条件']['接触间距_毫米']/1000
    move = inside | (distance < margin)
    bary = trimesh.triangles.points_to_barycentric(body.triangles[tri], nearest)
    normals = np.sum(body.vertex_normals[body.faces[tri]]*bary[:, :, None], axis=1)
    normals /= np.linalg.norm(normals, axis=1)[:, None]
    nonzero = distance > 1e-10
    normals[nonzero] = (xyz[roots[nonzero]]-nearest[nonzero])/distance[nonzero, None] * np.where(inside[nonzero], -1, 1)[:, None]
    if cfg['数值条件']['初始顶点接触投影']:
        xyz[roots[move]] = nearest[move]+normals[move]*margin
    for a, b in seams: xyz[b] = xyz[a]
    edge_faces = {}
    for fi, face in enumerate(faces):
        for j in range(3):
            a, b, opposite = face[j], face[(j+1)%3], face[(j+2)%3]
            oriented = (int(a), int(b))
            key = tuple(sorted([int(global_ids[a]), int(global_ids[b])]))
            if global_ids[a] != key[0]: a, b = b, a
            ab = uv[b]-uv[a]; delta = uv[opposite]-uv[a]; length = np.linalg.norm(ab)
            along = float(delta@ab/length); height = float(np.sqrt(max(0., delta@delta-along*along)))
            edge_faces.setdefault(key, []).append((int(opposite), along, height, length, *oriented))
    bends = []; hinges = []
    for rows in edge_faces.values():
        if len(rows) == 2:
            a, b = rows; common = (a[3]+b[3])/2
            # Distinct cut panels meet through a flexible sewn joint. Their
            # disconnected 2D material frames do not define a flat rest hinge.
            # Do not invent an across-seam bending law from unrelated UVs.
            if set(a[4:6]) != set(b[4:6]): continue
            rest = np.hypot(a[1]/a[3]*common-b[1]/b[3]*common, a[2]+b[2])
            bends.append([a[0], b[0], float(rest)])
            hinges.append([a[4], a[5], a[0], b[0], float(common/((a[2]+b[2])/3))])
    if not cfg['弯曲'].get('启用展开距离弯曲约束',True):bends=[]
    capacities = {'MAXV': 8192, 'MAXT': 8192, 'MAXS': 2048, 'MAXB': 16384}
    if any(count > capacities[key] for key, count in
           zip(['MAXV', 'MAXT', 'MAXS', 'MAXB'], [len(xyz), len(faces), len(seams), len(bends)])):
        raise ValueError('Native capacity exceeded; no constraints may be silently omitted')
    material = cfg['面料']; result = {'format': 'intent-physics-experiment/1', 'case': args.case,
        'source_dxf_sha256': sha(dxf), 'source_spec_sha256': sha(spec), 'config': cfg,
        'positions': xyz.tolist(), 'placement_before_contact': initial.tolist(), 'source_reference_positions':initial.tolist(), 'uv': uv.tolist(),
        'triangles': faces.tolist(), 'global_ids': global_ids.tolist(), 'seams': seams, 'bends': bends, 'hinges': hinges,
        'panels': panels, 'source_sewing': certificate, 'body': packed_body,
        'material': {'Eu': material['图面横向模量_Pa'], 'Ev': material['图面纵向模量_Pa'], 'G': material['图面剪切模量_Pa'],
                     'nu': material['泊松比'], 'thickness': material['厚度_米'], 'density': material['面密度_千克每平方米'], 'calibration': 'synthetic-not-measured'},
        'initialization': {'translation_m': translation.tolist(), 'depth_placement': placement_depth,
                           'material_metric_seed':fem_seed,
                           'actual_arm_seed':arm_seed,
                           'contact_projected_roots': int(move.sum()) if cfg['数值条件']['初始顶点接触投影'] else 0,
                           'interior_roots_before_contact': int(inside.sum()), 'max_placement_move_m': float(np.linalg.norm(xyz-initial, axis=1).max())},
        'physical_fit': 'NOT_RUN', 'units_status': 'assumed 1U=1mm; original uncalibrated status preserved'}
    result['native_capacities'] = capacities
    result['solver_features'] = {'surface_contacts': True, 'self_contacts': True,'body_feature_contacts': True,
        'self_step_guard': bool(args.self_step_guard),
        'preparation_contact_start_m': cfg['数值条件']['初始化接触距离起点_毫米']/1000,
        'placement_relaxation_iterations': cfg['数值条件']['穿着初始位置松弛迭代']}
    result['source_hashes'] = {str(path.relative_to(ROOT)): sha(path.read_bytes()) for path in
        [Path(__file__), Path(__file__).with_name('experiment-config.yaml'),
         Path(__file__).with_name('contact-extension.c'), Path(__file__).with_name('body-feature-contact.c'), Path(__file__).with_name('hinge-extension.c'), Path(__file__).with_name('closest64.c'), Path(__file__).with_name('membrane-stable.c'), Path(__file__).with_name('implicit-membrane.c'), Path(__file__).with_name('initial_placement.py'), Path(__file__).with_name('arm_placement.py'), Path(__file__).with_name('proxy-arm-joints.json'), ROOT/'services/dxf-preview/converter/sewn.py',
         ROOT/'web/cloth-lab/src/solver.c']}
    for path in [Path(__file__).with_name('arm_wear_oracle.py'),
                 ROOT/'experiments/teagan_sites_studio/app/dist/models/makehuman-base.obj',
                 ROOT/'web/human-studio/assets/human.json',ROOT/'web/human-studio/assets/provenance.json',
                 ROOT/'experiments/oneshot_control/independent_oracle_v2.py']:
        result['source_hashes'][str(path.relative_to(ROOT))]=sha(path.read_bytes())
    (out/'input.json').write_text(json.dumps(result, ensure_ascii=False, separators=(',', ':'), default=lambda value: value.tolist()))
    source = (ROOT/'web/cloth-lab/src/solver.c').read_text()
    native_source = source
    begin=native_source.index('static void solveMembrane(');end=native_source.index('static void solveDistance(',begin)
    native_source=native_source[:begin]+Path(__file__).with_name('membrane-stable.c').read_text()+'\n'+native_source[end:]
    begin=native_source.index('static V closest(');end=native_source.index('typedef struct {V q,n;float signedDistance',begin)
    native_source=native_source[:begin]+Path(__file__).with_name('closest64.c').read_text()+'\n'+native_source[end:]
    for key, old in {'MAXV': 4096, 'MAXT': 8192, 'MAXS': 256, 'MAXB': 8192}.items():
        declaration = f'#define {key} {old}'
        if native_source.count(declaration) != 1:
            raise ValueError('Native source capacity declaration changed')
        native_source = native_source.replace(declaration, f'#define {key} {capacities[key]}')
    marker='typedef struct {V q,n;float signedDistance'
    if native_source.count(marker)!=1:raise ValueError('Native closest-feature structure changed')
    native_source=native_source.replace(marker,'static V feature_normal(int face,float u,float v);\nstatic float bounded_normal_delta(int slot,float change,float coefficient);\n'+marker)
    before='const float change = unilateralDelta(i, hit.signedDistance - margin, invMass[i], contactArea[i]);'
    if native_source.count(before)!=1:raise ValueError('Native vertex contact changed')
    native_source=native_source.replace(before,'float change = unilateralDelta(i, hit.signedDistance - margin, invMass[i], contactArea[i]);change=bounded_normal_delta(i,change,invMass[i]);')
    before='const float change = unilateralDelta(slot, hit.signedDistance - margin * .5f, inverseEffectiveMass, 0);'
    if native_source.count(before)!=1:raise ValueError('Native centroid contact changed')
    native_source=native_source.replace(before,'float change = unilateralDelta(slot, hit.signedDistance - margin * .5f, inverseEffectiveMass, 0);change=bounded_normal_delta(slot,change,maxf(invMass[a],maxf(invMass[b],invMass[c]))/3);')
    old_normal='V normal=unit(add(mul(bodyNormals[ia],1-bu-bv),add(mul(bodyNormals[ib],bu),mul(bodyNormals[ic],bv))));'
    if native_source.count(old_normal)!=1:raise ValueError('Native nearest-normal expression changed')
    native_source=native_source.replace(old_normal,'V normal=feature_normal(bestFace,bu,bv);')
    old_gradient = 'float sd=root(best);if(dot(sub(p,q),normal)<0)sd=-sd;q.x+=offsetX;'
    if native_source.count(old_gradient) != 1: raise ValueError('Native distance-gradient implementation changed')
    native_source = native_source.replace(old_gradient,
        'float sd=root(best);int inside=dot(sub(p,q),normal)<0;'
        'if(sd>1e-10f)normal=mul(sub(p,q),(inside?-1.f:1.f)/sd);'
        'if(inside)sd=-sd;q.x+=offsetX;')
    native_source = 'static void solve_hinges(float dt);static void reset_hinge_lambdas();\n'+native_source
    before = 'for(int i=0;i<nt*3;i++)lambda[i]=0;'
    if native_source.count(before) != 1: raise ValueError('Native iteration structure changed')
    native_source = native_source.replace(before, before+'reset_hinge_lambdas();')
    before = 'for(int j=0;j<nb;j++)solveDistance(bends[j].a,bends[j].b,bends[j].rest,1/(.04f*dt*dt));'
    if native_source.count(before) != 1: raise ValueError('Native bending loop changed')
    native_source = native_source.replace(before, before+'solve_hinges(dt);')
    marker='__attribute__((export_name("step"))) void step('
    if native_source.count(marker)!=1:raise ValueError('Native step entrypoint changed')
    native_source=native_source.replace(marker,Path(__file__).with_name('implicit-membrane.c').read_text()+'\n'+marker)
    before='for(int it=0;it<24;it++){'
    if native_source.count(before)!=1:raise ValueError('Native main iteration count changed')
    native_source=native_source.replace(before,'implicit_membrane_begin(dt);'+before)
    before='for(int j=0;j<nt;j++){int t=it%2?nt-1-j:j;for(int c=0;c<3;c++)solveMembrane(t,c,dt);}'
    if native_source.count(before)!=1:raise ValueError('Native membrane sweep changed')
    native_source=native_source.replace(before,'implicit_membrane_iteration(dt);')
    native_source += '\n' + Path(__file__).with_name('contact-extension.c').read_text()
    native_source += '\n' + Path(__file__).with_name('body-feature-contact.c').read_text()
    native_source += '\n' + Path(__file__).with_name('hinge-extension.c').read_text()
    (out/'solver-capacity.c').write_text(native_source)
    subprocess.run([args.zig, 'cc', '-target', 'wasm32-freestanding', '-O3', '-nostdlib', '-Wl,--no-entry', '-rdynamic',
        '-Wl,--initial-memory=16777216', '-Wl,--max-memory=16777216', '-Wl,-z,stack-size=262144',
        str(out/'solver-capacity.c'), '-o', str(out/'solver.wasm')], check=True,
        env={**__import__('os').environ, 'ZIG_GLOBAL_CACHE_DIR': str(out/'zig-cache'), 'ZIG_LOCAL_CACHE_DIR': str(out/'zig-local-cache')})
    print(json.dumps({'case': args.case, 'vertices': len(xyz), 'triangles': len(faces), 'seam_constraints': len(seams),
        'bend_constraints': len(bends), 'initialization': result['initialization'], 'units_status': result['units_status']}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--case', default='baseline')
    parser.add_argument('--boundary-step',type=float)
    parser.add_argument('--preparation-iterations',type=int)
    parser.add_argument('--self-step-guard',action='store_true',help='Reject discrete self-intersecting proposals; independent body/physical gates still apply')
    parser.add_argument('--output', type=Path, required=True); parser.add_argument('--zig', required=True)
    prepare(parser.parse_args())
