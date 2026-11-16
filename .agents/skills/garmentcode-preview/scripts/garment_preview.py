#!/usr/bin/env python3
"""Validate GarmentCode patterns, reuse upstream meshing/physics, export offline previews."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def resolve_pattern(path):
    p = Path(path).expanduser().resolve()
    if p.is_dir():
        candidates = sorted(p.glob('*_specification.json'))
        if len(candidates) != 1:
            raise ValueError(f'Expected one *_specification.json; found {len(candidates)}: '
                             + ', '.join(x.name for x in candidates))
        p = candidates[0]
    if not p.is_file():
        raise ValueError(f'Pattern does not exist: {p}')
    return p


def inspect_pattern(path):
    p = resolve_pattern(path)
    data = json.loads(p.read_text(encoding='utf-8'))
    pattern = data.get('pattern', {})
    panels = pattern.get('panels')
    if not isinstance(panels, dict) or not panels:
        raise ValueError('Expected nonempty pattern.panels dictionary, not an image or design YAML.')
    unit = data.get('properties', {}).get('units_in_meter', 100)
    if not isinstance(unit, (int, float)) or not math.isfinite(unit) or unit <= 0:
        raise ValueError('properties.units_in_meter must be a positive finite number.')
    for name, panel in panels.items():
        verts = panel.get('vertices', [])
        if len(verts) < 2:
            raise ValueError(f'{name}: fewer than two boundary vertices.')
        for v in verts:
            if len(v) != 2 or not all(isinstance(n, (float, int)) and math.isfinite(n) for n in v):
                raise ValueError(f'{name}: invalid or non-finite 2D vertex.')
        for field in ['translation', 'rotation']:
            v = panel.get(field)
            if not isinstance(v, list) or len(v) != 3 or not all(isinstance(n, (float, int)) and math.isfinite(n) for n in v):
                raise ValueError(f'{name}: {field} must contain three finite numbers.')
        edges = panel.get('edges', [])
        if len(edges) < 2:
            raise ValueError(f'{name}: fewer than two boundary edges.')
        for e in edges:
            ends = e.get('endpoints', [])
            if len(ends) != 2 or any(type(n) is not int or not 0 <= n < len(verts) for n in ends):
                raise ValueError(f'{name}: invalid edge endpoints.')
            if ends[0] == ends[1]:
                raise ValueError(f'{name}: edge endpoints must differ.')
    stitched = set()
    for i, stitch in enumerate(pattern.get('stitches', [])):
        if not isinstance(stitch, list) or len(stitch) not in (2, 3):
            raise ValueError(f'Stitch {i}: expected two edge references and optional right_wrong flag.')
        for side in stitch[:2]:
            if not isinstance(side, dict):
                raise ValueError(f'Stitch {i}: invalid reference.')
            name, edge = side.get('panel'), side.get('edge')
            if name not in panels or type(edge) is not int or not 0 <= edge < len(panels[name]['edges']):
                raise ValueError(f'Stitch {i}: invalid panel or edge reference.')
            key = (name, edge)
            if key in stitched:
                raise ValueError(f'Stitch {i}: edge {key} is stitched more than once.')
            stitched.add(key)
        if len(stitch) == 3 and stitch[2] != 'right_wrong':
            raise ValueError(f'Stitch {i}: unknown orientation flag.')
    return p, {'sha256': sha256(p), 'panels': len(panels),
               'stitches': len(pattern.get('stitches', [])), 'units_in_meter': unit}


def revision(repo):
    try:
        return subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'],
                                       stderr=subprocess.DEVNULL, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def doctor(repo):
    modules = ['numpy', 'scipy', 'yaml', 'trimesh', 'CGAL', 'igl', 'svgpathtools', 'cairosvg', 'warp']
    return {'python': sys.version.split()[0], 'repo_exists': (repo / 'pygarment').is_dir(),
            'garmentcode_commit': revision(repo),
            'modules': {m: importlib.util.find_spec(m) is not None for m in modules}}


def mesh_payload(vertices, faces):
    import numpy as np
    v, f = np.asarray(vertices), np.asarray(faces)
    if v.ndim != 2 or v.shape[1] != 3 or not np.isfinite(v).all() or not len(v):
        raise ValueError('Generated mesh has invalid vertices.')
    if f.ndim != 2 or f.shape[1] != 3 or not len(f) or f.min() < 0 or f.max() >= len(v):
        raise ValueError('Generated mesh has invalid triangles.')
    return {'vertices': np.round(v, 5).reshape(-1).tolist(), 'faces': f.reshape(-1).tolist()}


def export_glb(vertices, faces, path):
    import trimesh
    m = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
    m.visual.material = trimesh.visual.material.PBRMaterial(
        baseColorFactor=[49, 155, 145, 255], roughnessFactor=0.85,
        metallicFactor=0., doubleSided=True)
    m.export(str(path))


def find_measurements(p):
    exact = p.parent / 'body_measurements.yaml'
    if exact.exists():
        return exact
    stem = p.stem.removesuffix('_specification')
    exact = p.parent / f'{stem}_body_measurements.yaml'
    return exact if exact.exists() else None


def create_preview(out, initial, final, body, manifest):
    payload = {'initial': initial, 'final': final, 'body': body,
               'label': manifest['preview_label'], 'name': manifest['sample_name'],
               'source': manifest['source']}
    encoded = json.dumps(payload, ensure_ascii=False, separators=(',', ':'), allow_nan=False).replace('</', '<\\/')
    fragment = (ROOT / 'assets/viewer-fragment.html').read_text(encoding='utf-8').replace('__MESH_DATA__', encoded)
    (out / 'preview-fragment.html').write_text(fragment, encoding='utf-8')
    wrapper = '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>GarmentCode 三维预览</title><style>:root{--background:#f5f6f4;--foreground:#20332f;--muted:#e3e9e5;--muted-foreground:#56655e;--border:#c9d3cd;--viz-series-1:#238f83;--primary:#254d43;--primary-foreground:#fff;--card:#fff;--card-foreground:#20332f;--font-size-base:14px}body{margin:0;padding:24px;font:14px/1.5 system-ui,sans-serif;background:var(--background);color:var(--foreground)}h2{font-size:20px;font-weight:500;margin:0}.btn{font:inherit;padding:7px 13px;background:var(--card);color:var(--foreground);border:1px solid var(--border);border-radius:6px;cursor:pointer}.btn[aria-pressed="true"]{background:var(--primary);color:var(--primary-foreground)}.viz-controls,.viz-row{display:flex;flex-wrap:wrap;gap:12px;align-items:center}.form-check{display:inline-flex;gap:6px;align-items:center}.text-small{font-size:12px}.text-muted{color:var(--muted-foreground)}@media(max-width:500px){body{padding:12px}}</style></head><body>'
    (out / 'preview.html').write_text(wrapper + fragment + '</body></html>', encoding='utf-8')


def unrun_release():
    return {'upstream_threshold_check': 'NOT_RUN',
            'strict_zero_body_intersections': 'NOT_RUN',
            'strict_zero_self_intersections': 'NOT_RUN',
            'independent_full_geometry_audit': 'NOT_RUN', 'physical_fit': 'NOT_RUN'}


def build_existing(args):
    """Preview a supplied mesh without requiring or inventing its original pattern."""
    import numpy as np
    import trimesh

    if not args.existing_mesh or not args.existing_mesh.is_file():
        raise ValueError('existing mode requires --existing-mesh pointing to a local OBJ/PLY/GLB.')
    out = args.out.expanduser().resolve()
    if out.exists() and any(out.iterdir()):
        raise ValueError('Output directory is not empty; choose a new directory to preserve previous results.')
    mesh = trimesh.load_mesh(str(args.existing_mesh), process=False)
    if not isinstance(mesh, trimesh.Trimesh):
        raise ValueError('Expected one triangle mesh, not a multi-object scene.')
    scale = args.existing_scale
    if scale is None:
        scale = 1.0 if args.existing_mesh.suffix.lower() == '.glb' else .01
    vertices = np.asarray(mesh.vertices) * scale
    final = mesh_payload(vertices, mesh.faces)
    body = None
    if args.body_mesh:
        display = trimesh.load_mesh(str(args.body_mesh), process=False)
        body = mesh_payload(np.asarray(display.vertices) * args.body_scale, display.faces)
    out.mkdir(parents=True, exist_ok=True)
    manifest = {'schema_version': 2, 'sample_name': args.existing_mesh.stem,
                'source': args.source or str(args.existing_mesh), 'mode': 'existing',
                'input': {'file': str(args.existing_mesh), 'sha256': sha256(args.existing_mesh)},
                'existing_mesh': {'path': str(args.existing_mesh), 'sha256': sha256(args.existing_mesh),
                                  'scale_to_meters': scale},
                'mesh_generated_this_run': False,
                'mesh': {'vertices': len(vertices), 'triangles': len(mesh.faces)},
                'units': {'glb': 'meters'}, 'body': None,
                'simulation': {'executed': False}, 'release': unrun_release(),
                'preview_label': '已有网格 · 本次未重新生成或仿真'}
    if args.body_mesh:
        manifest['body'] = {'file': str(args.body_mesh), 'sha256': sha256(args.body_mesh),
                            'scale_to_meters': args.body_scale, 'usage': 'display_only'}
    export_glb(vertices, mesh.faces, out / 'garment.glb')
    create_preview(out, None, final, body, manifest)
    dump(out / 'manifest.json', manifest)
    print(json.dumps({'preview': str(out / 'preview.html'), 'manifest': manifest}, ensure_ascii=False, indent=2))
    return manifest


def build(args):
    if args.mode == 'existing':
        return build_existing(args)
    if not args.pattern or not args.repo:
        raise ValueError('mesh/simulate mode requires --pattern and --repo; existing mode only requires --existing-mesh.')
    import numpy as np
    import trimesh
    import yaml

    p, info = inspect_pattern(args.pattern)
    repo, out = args.repo.expanduser().resolve(), args.out.expanduser().resolve()
    if out.exists() and any(out.iterdir()):
        raise ValueError('Output directory is not empty; choose a new directory to preserve previous results.')
    out.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(repo))
    if not (repo / 'pygarment').is_dir():
        raise ValueError('Expected --repo to be a GarmentCode source checkout.')
    measurements = args.body_measurements or find_measurements(p)
    body_info = yaml.safe_load(Path(measurements).read_text()) if measurements else {}
    sample_id = body_info.get('body', {}).get('body_sample')
    random_sample = 'random_body' in p.parts or sample_id is not None
    if random_sample and (not args.body_mesh or not measurements):
        raise ValueError('Random-body sample requires its matching --body-mesh and body measurements; refusing neutral-body substitution.')
    if args.body_mesh and not measurements:
        raise ValueError('Custom --body-mesh requires --body-measurements for matching attachment levels.')
    body_path = Path(args.body_mesh).expanduser().resolve() if args.body_mesh else repo / 'assets/bodies/mean_all.obj'
    mes_path = Path(measurements).expanduser().resolve() if measurements else repo / 'assets/bodies/mean_all.yaml'
    if not body_path.is_file() or not mes_path.is_file():
        raise ValueError('Matching body mesh or measurements file is missing.')
    body_mesh = trimesh.load_mesh(str(body_path), process=False)
    body_verts = np.asarray(body_mesh.vertices) * args.body_scale
    # Display-only body decimation; never modify the collider supplied to the solver.
    display_v, display_f = body_verts, np.asarray(body_mesh.faces)
    if len(display_f) > 5000:
        import igl
        result = igl.decimate(display_v, display_f, 5000)
        # libigl 2.6 returns (V,F,J,I); older bindings prepend a success flag.
        if len(result) == 4:
            display_v, display_f = result[:2]
        elif result[0]:
            display_v, display_f = result[1:3]
    body_payload = mesh_payload(display_v, display_f)
    source = args.source or ('官方 GarmentCode 仓库示例（非下载的数据集条目）'
                            if sha256(p) == sha256(ROOT / 'assets/example-shirt_specification.json') else str(p))
    manifest = {'schema_version': 2, 'sample_name': p.stem.removesuffix('_specification'), 'source': source,
                'input': {'file': str(p), **info}, 'mode': args.mode,
                'garmentcode_commit': revision(repo), 'resolution_cm': args.resolution,
                'body': {'file': str(body_path), 'sha256': sha256(body_path),
                         'measurements': str(mes_path), 'measurements_sha256': sha256(mes_path),
                         'scale_to_meters': args.body_scale, 'sample_id': sample_id},
                'units': {'glb': 'meters', 'simulation_obj': 'centimeters'},
                'simulation': {'executed': False}, 'release': unrun_release(),
                'mesh_generated_this_run': True, 'preview_label': '初始缝合网格 · 未物理仿真'}
    dump(out / 'manifest.json', manifest)
    initial, final = None, None
    runtime = out / 'runtime'
    runtime.mkdir()
    staging = runtime / 'input'
    staging.mkdir()
    name = 'garment'
    shutil.copy2(p, staging / f'{name}_specification.json')
    shutil.copy2(mes_path, staging / 'body_measurements.yaml')
    for candidate in [p.parent / 'design_params.yaml', p.parent / f'{manifest["sample_name"]}_design_params.yaml']:
        if candidate.exists():
            shutil.copy2(candidate, staging / 'design_params.yaml')
            break
    system = {'output': str(out), 'datasets_path': str(runtime), 'datasets_sim': str(out),
              'sim_configs_path': str(repo / 'assets/Sim_props'),
              'bodies_default_path': str(repo / 'assets/bodies'), 'body_samples_path': str(runtime)}
    dump(runtime / 'system.json', system)
    old_cwd = Path.cwd()
    try:
        os.chdir(runtime)
        from pygarment.meshgen.boxmeshgen import BoxMesh, Edge
        from pygarment.meshgen.sim_config import PathCofig, SimConfig
        # A logging-only upstream bug for coarse edges references a missing Edge.name.
        if not hasattr(Edge, 'name'):
            Edge.name = 'boundary'
        paths = PathCofig(staging, out, name, out_name='mesh', body_name='mean_all', smpl_body=args.smpl)
        paths.in_body_obj, paths.in_body_mes = body_path, mes_path
        shutil.copy2(mes_path, paths.body_mes)
        mesh = BoxMesh(str(staging / f'{name}_specification.json'), args.resolution)
        mesh.load()
        mesh.serialize(paths, store_panels=False, uv_config={'dpi': 72, 'seam_width': 0.3})
        verts, faces = np.asarray(mesh.vertices), np.asarray(mesh.faces)
        initial = mesh_payload(verts * .01, faces)
        export_glb(verts * .01, faces, out / 'garment-initial.glb')
        manifest['mesh'] = {'vertices': len(verts), 'triangles': len(faces),
                            'bounds_m': (np.array([verts.min(0), verts.max(0)]) * .01).tolist()}
        create_preview(out, initial, None, body_payload, manifest)
        dump(out / 'manifest.json', manifest)
        print(f'Mesh ready: {len(verts)} vertices / {len(faces)} triangles', flush=True)
        if args.mode == 'simulate':
            import warp as wp
            wp.config.kernel_cache_dir = str(runtime / 'warp-cache')
            wp.init()
            from pygarment.meshgen.garment import Cloth
            from pygarment.meshgen.simulation import sim_frame_sequence
            if not hasattr(wp.sim.ModelBuilder, 'add_cloth_mesh_sewing_spring'):
                raise ValueError('Wrong Warp version: install NvidiaWarp-GarmentCode, not stock warp-lang.')
            if not wp.get_device().is_cuda and wp.context.runtime.llvm is None:
                raise ValueError('CPU simulation needs warp-clang runtime compiler; see references/setup.md.')
            config_path = args.sim_config or repo / 'assets/Sim_props/gui_sim_props.yaml'
            props = yaml.safe_load(Path(config_path).read_text())
            config_dict = props['sim']['config']
            config_dict.update(resolution_scale=args.resolution, max_sim_steps=args.max_frames,
                               max_sim_time=args.max_seconds, max_frame_time=None)
            (out / 'sim-config.yaml').write_text(yaml.safe_dump(props), encoding='utf-8')
            # Upstream Cloth multiplies body meters by 100; stage a converted mesh if needed.
            if args.body_scale != 1.0:
                body_mesh.vertices = body_verts
                body_mesh.export(str(runtime / 'body-meters.obj'))
                paths.in_body_obj = runtime / 'body-meters.obj'
            config = SimConfig(config_dict)
            start = time.monotonic()
            class SnapshotCloth(Cloth):
                def run_frame(self):
                    # CPU numpy() is a view; an even number of buffer swaps aliases
                    # last_verts and current_verts and falsely reports zero motion.
                    self.current_verts = np.array(self.current_verts, copy=True)
                    super().run_frame()

            cloth = SnapshotCloth(name, config, paths, caching=False)
            error = None
            try:
                sim_frame_sequence(cloth, config, store_usd=False, verbose=False)
            except BaseException as exc:
                if isinstance(exc, KeyboardInterrupt):
                    raise
                error = f'{type(exc).__name__}: {exc}'
            cloth.save_frame(save_v_norms=False)
            sim_v = np.asarray(cloth.current_verts)
            final = mesh_payload(sim_v * .01, faces)
            export_glb(sim_v * .01, faces, out / 'garment.glb')
            static, moving = cloth.is_static()
            body_contacts = cloth.count_body_intersections()
            self_contacts = cloth.count_self_intersections()
            passed = bool(not error and static and body_contacts <= config.max_body_collisions
                          and self_contacts <= config.max_self_collisions)
            manifest['simulation'] = {'executed': True, 'solver': 'GarmentCode Warp XPBD',
                'warp_version': wp.__version__, 'device': str(cloth.device),
                'warp_source_commit': revision(Path(wp.__file__).resolve().parents[1]),
                'frames': cloth.frame + 1, 'elapsed_seconds': round(time.monotonic() - start, 3),
                'cpu_static_check_snapshot_fix': True,
                'static': bool(static), 'moving_vertices': int(moving),
                'body_intersections': int(body_contacts), 'self_intersections': int(self_contacts),
                'max_body_intersections': config.max_body_collisions,
                'max_self_intersections': config.max_self_collisions,
                'upstream_threshold_passed': passed,
                'quality_passed': passed, 'quality_passed_scope': 'upstream_config_thresholds_only',
                'error': error, 'config_sha256': sha256(out / 'sim-config.yaml')}
            manifest['release'] = {
                'simulation_execution': 'FAIL' if error else 'PASS',
                'stability': 'PASS' if static and not error else 'FAIL',
                'upstream_threshold_check': 'PASS' if passed else 'FAIL',
                'strict_zero_body_intersections': 'PASS' if not error and static and body_contacts == 0 else 'FAIL',
                'strict_zero_self_intersections': 'PASS' if not error and static and self_contacts == 0 else 'FAIL',
                'independent_full_geometry_audit': 'NOT_RUN', 'physical_fit': 'NOT_RUN',
                'reason': 'Intersection counters are upstream diagnostics, not an independent garment or physical-fit certificate.'}
            if error:
                manifest['preview_label'] = '物理仿真未完成 · 部分结果，仅供排查'
            elif not static:
                manifest['preview_label'] = '物理仿真达到帧数上限 · 尚未稳定（研究预览）'
            elif body_contacts or self_contacts:
                manifest['preview_label'] = '物理仿真完成 · 零穿透检查未通过（研究预览）'
            else:
                manifest['preview_label'] = '物理仿真完成 · 上游零穿透计数通过，合身未验证'
    except Exception as exc:
        manifest['error'] = f'{type(exc).__name__}: {exc}'
        dump(out / 'manifest.json', manifest)
        if initial:
            create_preview(out, initial, None, body_payload, manifest)
        raise
    finally:
        os.chdir(old_cwd)
    dump(out / 'manifest.json', manifest)
    create_preview(out, initial, final, body_payload, manifest)
    print(json.dumps({'preview': str(out / 'preview.html'), 'manifest': manifest}, ensure_ascii=False, indent=2))
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    i = sub.add_parser('inspect')
    i.add_argument('--pattern', required=True)
    d = sub.add_parser('doctor')
    d.add_argument('--repo', type=Path, required=True)
    b = sub.add_parser('build')
    b.add_argument('--pattern')
    b.add_argument('--repo', type=Path)
    b.add_argument('--out', type=Path, required=True)
    b.add_argument('--mode', choices=['mesh', 'simulate', 'existing'], default='mesh')
    b.add_argument('--existing-mesh', type=Path)
    b.add_argument('--existing-scale', type=float, help='Existing mesh units to meters; default 1 for GLB, .01 for OBJ/PLY')
    b.add_argument('--body-mesh', type=Path)
    b.add_argument('--body-measurements', type=Path)
    b.add_argument('--body-scale', type=float, default=1., help='Body mesh units to meters')
    b.add_argument('--smpl', action='store_true')
    b.add_argument('--resolution', type=float, default=1., help='Target mesh spacing in cm; larger is coarser')
    b.add_argument('--sim-config', type=Path)
    b.add_argument('--max-frames', type=int, default=2400)
    b.add_argument('--max-seconds', type=int, default=600)
    b.add_argument('--source', help='Dataset URL or other provenance label')
    args = parser.parse_args()
    try:
        if args.command == 'inspect':
            p, info = inspect_pattern(args.pattern)
            print(json.dumps({'path': str(p), **info}, ensure_ascii=False, indent=2))
        elif args.command == 'doctor':
            print(json.dumps(doctor(args.repo.resolve()), indent=2))
        else:
            for key in ['resolution', 'body_scale', 'existing_scale', 'max_frames', 'max_seconds']:
                value = getattr(args, key)
                if value is not None and (not math.isfinite(value) or value <= 0):
                    raise ValueError(f'--{key.replace("_", "-")} must be finite and positive')
            # Resolve paths before changing cwd for upstream's system.json lookup.
            for key in ['body_mesh', 'body_measurements', 'sim_config', 'existing_mesh']:
                if getattr(args, key):
                    setattr(args, key, getattr(args, key).expanduser().resolve())
            result = build(args)
            if result.get('simulation', {}).get('error'):
                return 2
    except (Exception, SystemExit) as exc:
        if isinstance(exc, SystemExit):
            raise
        print(f'ERROR: {type(exc).__name__}: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
