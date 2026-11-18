#!/usr/bin/env python3
"""Register an illustrative generated guide to unchanged source photo pixels.

Similarity alignment is image correspondence, not detection or joint truth.
Optional manually reviewed markers retain semantic kind and visibility.
"""
import argparse
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def register(reference, guide, output, markers=None):
    reference, guide, output = Path(reference), Path(guide), Path(output)
    if output.exists():
        raise ValueError('Choose a new registration directory; do not overwrite history')
    a, b = cv2.imread(str(guide)), cv2.imread(str(reference))
    if a is None or b is None:
        raise ValueError('Reference and guide must be real readable images')
    cv2.setRNGSeed(0)
    hsv = cv2.cvtColor(a, cv2.COLOR_BGR2HSV)
    neon = ((hsv[:, :, 1] > 150) & (hsv[:, :, 2] > 170) & (hsv[:, :, 0] > 15) & (hsv[:, :, 0] < 170)).astype('uint8') * 255
    feature_mask = 255 - cv2.dilate(neon, np.ones((19, 19), 'uint8'))
    sift = cv2.SIFT_create(nfeatures=7000)
    ka, da = sift.detectAndCompute(a, feature_mask)
    kb, db = sift.detectAndCompute(b, None)
    if da is None or db is None:
        raise ValueError('Insufficient real image features for registration')
    matches = cv2.BFMatcher().knnMatch(da, db, k=2)
    good = [pair[0] for pair in matches if len(pair) == 2 and pair[0].distance < .72 * pair[1].distance]
    if len(good) < 10:
        raise ValueError('Fewer than10 supported feature matches; review guide before fitting')
    x = np.float32([ka[m.queryIdx].pt for m in good])
    y = np.float32([kb[m.trainIdx].pt for m in good])
    matrix, mask = cv2.estimateAffinePartial2D(x, y, method=cv2.RANSAC, ransacReprojThreshold=4, maxIters=10000, confidence=.999)
    if matrix is None or not np.isfinite(matrix).all() or mask.sum() < 10:
        raise ValueError('Registration did not produce a supported finite similarity transform')
    errors = np.linalg.norm(x @ matrix[:, :2].T + matrix[:, 2] - y, axis=1)
    inliers = mask.ravel() > 0
    annotations = []
    if markers:
        for marker in json.loads(Path(markers).read_text())['markers']:
            if marker['kind'] not in {'joint', 'surface', 'garment', 'contact'} or 'visibility' not in marker:
                raise ValueError('Each marker needs explicit kind and visibility; labels are not anatomy evidence')
            row = dict(marker)
            point = row.get('native_xy')
            if point is None:
                row['raw_xy'] = None
            else:
                xy = np.asarray(point, float)
                if xy.shape != (2,) or not np.isfinite(xy).all():
                    raise ValueError('Marker must be null or two finite guide-pixel coordinates')
                row['raw_xy'] = (matrix @ np.r_[xy, 1]).tolist()
            annotations.append(row)
    output.mkdir(parents=True)
    report = dict(schema='illustrative-pose-registration-v1', method='SIFT Lowe0.72 + similarity RANSAC4px; exclude neon overlay19px',
                  matrix_native_to_raw=matrix.tolist(), matches=len(good), inliers=int(inliers.sum()),
                  inlier_mean_error_px=float(errors[inliers].mean()), inlier_p95_error_px=float(np.percentile(errors[inliers], 95)),
                  inputs=dict(reference=dict(path=str(reference.resolve()), sha256=digest(reference), pixels=list(b.shape[1::-1])),
                              guide=dict(path=str(guide.resolve()), sha256=digest(guide), pixels=list(a.shape[1::-1]))),
                  markers=annotations, anatomical_truth=False,
                  limitations='Similarity image alignment does not verify anatomy, occlusion, hidden3D or centimetres. Original photo pixels are not warped. Markers are manually reviewed illustrative constraints, not detector output.')
    (output / 'registration.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    overlay = b.copy()
    for marker in annotations:
        if marker['raw_xy'] is None:
            continue
        point = tuple(np.rint(marker['raw_xy']).astype(int))
        cv2.circle(overlay, point, 5, (0, 240, 200), 2)
        cv2.putText(overlay, marker['id'] + ' / ' + marker['kind'], (point[0] + 6, point[1] - 5), 0, .35, (20, 20, 20), 1)
    cv2.imwrite(str(output / 'source-marker-preview.png'), overlay)
    cv2.imwrite(str(output / 'guide-registered.png'), cv2.warpAffine(a, matrix, (b.shape[1], b.shape[0])))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--guide', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--markers', type=Path)
    args = parser.parse_args()
    result = register(args.reference, args.guide, args.out, args.markers)
    print(json.dumps({k: result[k] for k in ['matches', 'inliers', 'inlier_mean_error_px', 'inlier_p95_error_px']}))
