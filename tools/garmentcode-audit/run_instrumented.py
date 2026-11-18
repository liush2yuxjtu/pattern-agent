#!/usr/bin/env python3
"""Run the pinned GarmentCode pipeline and retain real solver checkpoints.

This is a research adapter. It does not replace the upstream solver, change the
material, or certify fit. Substep/iteration changes are explicit in run.json.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import sys
import time

import numpy as np


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--pattern', type=Path)
    parser.add_argument('--substeps', type=int, default=10)
    parser.add_argument('--iterations', type=int, default=1)
    parser.add_argument('--contact-radius-cm', type=float)
    parser.add_argument('--min-frames', type=int, default=300)
    parser.add_argument('--max-frames', type=int, default=600)
    parser.add_argument('--sample-every', type=int, default=30)
    args = parser.parse_args()
    if min(args.substeps, args.iterations, args.min_frames, args.sample_every) < 1:
        parser.error('frame and solver settings must be positive')
    if args.min_frames > args.max_frames:
        parser.error('--min-frames exceeds --max-frames')
    if args.contact_radius_cm is not None and (not np.isfinite(args.contact_radius_cm) or args.contact_radius_cm <= 0):
        parser.error('--contact-radius-cm must be finite and positive')
    root = Path(__file__).resolve().parents[2]
    repo, out = args.repo.resolve(), args.out.resolve()
    if out.exists():
        parser.error('output already exists; preserve earlier evidence')
    sys.path.insert(0, str(repo))
    from pygarment.meshgen import sim_config
    original_config = sim_config.SimConfig

    class ResearchConfig(original_config):
        def __init__(self, values):
            super().__init__(values)
            self.sim_substeps = args.substeps
            self.min_sim_steps = args.min_frames - 1
            if args.contact_radius_cm is not None:
                self.garment_radius = args.contact_radius_cm

        def update_min_steps(self):
            super().update_min_steps()
            # Cloth may disable missing attachment labels and call this again.
            self.min_sim_steps = max(self.min_sim_steps, args.min_frames - 1)

    sim_config.SimConfig = ResearchConfig
    from pygarment.meshgen import garment
    original_cloth = garment.Cloth
    checkpoints, frame_ids, timings, counters = [], [], [], []
    context = {}

    class RecordedCloth(original_cloth):
        def __init__(self, *a, **kw):
            super().__init__(*a, **kw)
            self.integrator.iterations = args.iterations
            context.update(body_vertices_m=np.array(self.v_body) * .01,
                           body_faces=np.array(self.f_body),
                           faces=np.array(self.f_cloth),
                           initial_positions_m=np.array(self.current_verts) * .01)
            if self.config.min_sim_steps < args.min_frames - 1:
                raise ValueError('upstream reset the requested minimum simulation length')

        def run_frame(self):
            # The production adapter also copies this CPU shared view. Keeping
            # the copy here makes the recorder valid outside that adapter too.
            self.current_verts = np.array(self.current_verts, copy=True)
            start = time.perf_counter()
            super().run_frame()
            timings.append(time.perf_counter() - start)
            if self.frame == 0 or (self.frame + 1) % args.sample_every == 0:
                save(self)
            context['last_cloth'] = self

    def save(cloth):
        if frame_ids and frame_ids[-1] == cloth.frame + 1:
            return
        frame_ids.append(cloth.frame + 1)
        checkpoints.append(np.array(cloth.current_verts) * .01)
        counters.append({'frame': cloth.frame + 1,
                         'body_edges': cloth.count_body_intersections(),
                         'self_edges': cloth.count_self_intersections()})
        print(json.dumps({'checkpoint': frame_ids[-1], **counters[-1]}), flush=True)

    garment.Cloth = RecordedCloth
    script = root / '.agents/skills/garmentcode-preview/scripts/garment_preview.py'
    spec = importlib.util.spec_from_file_location('production_preview', script)
    preview = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(preview)
    pattern = (args.pattern or root / '.agents/skills/garmentcode-preview/assets/example-shirt_specification.json').resolve()
    build_args = argparse.Namespace(mode='simulate', pattern=pattern, repo=repo,
        out=out, body_measurements=None, body_mesh=None, body_scale=1., source=None,
        resolution=1.5, smpl=False, sim_config=None, max_frames=args.max_frames,
        max_seconds=1200)
    start = time.perf_counter()
    try:
        manifest = preview.build(build_args)
    finally:
        cloth = context.pop('last_cloth', None)
        if cloth is not None:
            save(cloth)
        if checkpoints:
            np.savez_compressed(out / 'checkpoints.npz',
                positions_m=np.array(checkpoints), frame_ids=np.array(frame_ids), **context)
            result = {'schema_version': 1, 'substeps': args.substeps,
                'iterations': args.iterations, 'min_frames': args.min_frames,
                'contact_radius_cm_override': args.contact_radius_cm,
                'sample_every': args.sample_every, 'frame_ids': frame_ids,
                'nominal_dt': 1 / 60 / args.substeps,
                'frame_times_s': timings, 'upstream_counters': counters,
                'wall_seconds': time.perf_counter() - start,
                'gravity_unit_chain': 'UNVALIDATED: upstream positions cm, gravity vector magnitude 9.81',
                'material': 'UNCHANGED upstream GUI research parameters; uncalibrated',
                'continuous_collision': 'NOT_VALIDATED', 'physical_fit': 'NOT_RUN'}
            (out / 'run.json').write_text(json.dumps(result, indent=2) + '\n')
    return 2 if manifest.get('simulation', {}).get('error') else 0


if __name__ == '__main__':
    raise SystemExit(main())
