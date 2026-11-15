"""Report measured cuff, hem, and collar motion from exported Blender frames.

Pure NumPy CLI (ordinary Python is sufficient):
  python verification/motion_diagnostic.py --run evidence/RUN
  python verification/motion_diagnostic.py --run evidence/RUN --all-frames

These observations do not introduce a comfort/stall acceptance threshold. The
reference is saved frame 1, not an idealized target pose. Dimensions are metres
in the inputs and explicitly named millimetres/degrees/percent in the output.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np


def _perimeter(vertices, indices):
    loop = vertices[indices]
    return float(np.linalg.norm(loop - np.roll(loop, -1, axis=0), axis=1).sum())


def measure_motion(arrays, topology, reference_vertices):
    vertices = arrays['cloth_vertices']
    rest = np.asarray(topology['rest_vertices'])
    hem = np.flatnonzero(rest[:, 2] < rest[:, 2].min() + 1e-5)
    pins = topology.get('collar_pinned_vertices', [])
    if len(hem) < 3:
        raise ValueError('assembled rest mesh does not have a recoverable bottom hem ring')
    row = dict(hem_centroid=vertices[hem].mean(axis=0).tolist(),
               hem_rise_mm=float((vertices[hem].mean(axis=0)[2] - reference_vertices[hem].mean(axis=0)[2]) * 1000),
               cloth_centroid=vertices.mean(axis=0).tolist(), collar_pinned_count=len(pins),
               collar_max_motion_mm=(float(np.linalg.norm(vertices[pins] - reference_vertices[pins], axis=1).max() * 1000)
                                     if pins else None), sleeves={})
    for side in ('L', 'R'):
        armhole, cuff = topology['armholes'][side], topology['cuffs'][side]
        armhole_centre, cuff_centre = vertices[armhole].mean(axis=0), vertices[cuff].mean(axis=0)
        path = arrays['path_' + side]
        axis = path[-1] - path[0]
        axis /= np.linalg.norm(axis)
        sleeve_axis = cuff_centre - armhole_centre
        sleeve_axis /= np.linalg.norm(sleeve_axis)
        # Distance is relative to the saved path's first point. Do not assume
        # a particular skeleton origin or a hard-coded shoulder offset.
        projection_from_path_start = float(np.dot(cuff_centre - path[0], axis))
        centreline_point = path[0] + axis * projection_from_path_start
        initial_perimeter = _perimeter(reference_vertices, armhole)
        row['sleeves'][side] = dict(
            arm_angle_deg=float(np.degrees(np.arctan2(axis[2], abs(axis[0])))),
            sleeve_axis_angle_deg=float(np.degrees(np.arctan2(sleeve_axis[2], abs(sleeve_axis[0])))),
            axis_misalignment_deg=float(np.degrees(np.arccos(np.clip(np.dot(axis, sleeve_axis), -1., 1.)))),
            cuff_centre=cuff_centre.tolist(), armhole_centre=armhole_centre.tolist(),
            cuff_rise_mm=float((cuff_centre[2] - reference_vertices[cuff].mean(axis=0)[2]) * 1000),
            cuff_arm_centerline_offset_mm=float(np.linalg.norm(cuff_centre - centreline_point) * 1000),
            cuff_projection_from_path_start_mm=projection_from_path_start * 1000,
            armhole_perimeter_change_pct=(_perimeter(vertices, armhole) / initial_perimeter - 1.) * 100)
    return row


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', required=True, type=Path)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--frames', nargs='+', type=int, default=[1, 21, 81, 141, 221, 241])
    parser.add_argument('--all-frames', action='store_true')
    args = parser.parse_args(argv)
    topology = json.loads((args.run / 'topology.json').read_text())
    with np.load(args.run / 'frames' / 'frame-0001.npz') as data:
        reference = data['cloth_vertices'].copy()
    files = sorted((args.run / 'frames').glob('frame-*.npz'))
    selected = set(args.frames)
    rows = []
    for file in files:
        frame = int(file.stem.rsplit('-', 1)[-1])
        if not args.all_frames and frame not in selected:
            continue
        with np.load(file) as data:
            row = measure_motion(dict(data), topology, reference)
        row['frame'] = frame
        row['source_frame_file'] = file.name
        rows.append(row)
    result = dict(schema_version=1, reference_frame=1, selected_frame_count=len(rows), frames=rows,
                  limits=['Geometric motion observations only; no calibrated comfort or stall threshold.',
                          'Hem vertices are inferred from the lowest assembled-rest ring of this fixture.',
                          'Centreline projection assumes the exported arm path is straight; bent paths require local projection.',
                          'Welded zero seam gap does not imply zero seam deformation or real seam strength.'])
    output = args.out or args.run / 'verification' / 'motion-checkpoints.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, allow_nan=False))
    print(json.dumps(dict(output=str(output), selected_frame_count=len(rows), reference_frame=1)))


if __name__ == '__main__':
    main()
