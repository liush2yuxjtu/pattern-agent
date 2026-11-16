#!/usr/bin/env python3
"""Compare supplied segmentation and actual mesh projection masks. Does not infer anatomy."""
import argparse
import json
from pathlib import Path
import cv2
import numpy as np


def binary_masks(reference, projected):
    masks = []
    for value in (reference, projected):
        mask = np.asarray(value)
        if mask.dtype.kind not in 'buif' or not np.isfinite(mask).all():
            raise ValueError('Masks must contain finite binary values (0 or 1).')
        if not np.isin(mask, (0, 1)).all():
            raise ValueError('Masks must contain binary values (0 or 1); threshold probabilities explicitly.')
        masks.append(mask.astype(bool))
    a, b = masks
    if a.ndim != 2 or a.shape != b.shape:
        raise ValueError('Masks must be same-size 2D arrays; do not silently resize evaluation masks.')
    return a, b


def compare(reference, projected):
    a, b = binary_masks(reference, projected)
    if not a.any() or not b.any():
        raise ValueError('Empty foreground mask: inspect segmentation/projection before evaluation.')
    intersection = np.count_nonzero(a & b)
    union = np.count_nonzero(a | b)
    boundaries = []
    for mask in (a, b):
        contours, _ = cv2.findContours(mask.astype('uint8'), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        edge = np.zeros(mask.shape, np.uint8)
        cv2.drawContours(edge, contours, -1, 1, 1)
        boundaries.append(edge)
    da = cv2.distanceTransform(1-boundaries[0], cv2.DIST_L2, cv2.DIST_MASK_PRECISE)
    db = cv2.distanceTransform(1-boundaries[1], cv2.DIST_L2, cv2.DIST_MASK_PRECISE)
    distance = np.r_[da[boundaries[1] > 0], db[boundaries[0] > 0]]
    return {'iou': float(intersection/union), 'dice': float(2*intersection/(a.sum()+b.sum())),
            'mean_symmetric_contour_distance_px': float(distance.mean()),
            'p95_symmetric_contour_distance_px': float(np.percentile(distance, 95)),
            'evaluation_size_px': [int(a.shape[1]), int(a.shape[0])],
            'interpretation': '2D silhouette agreement; not anatomical measurement accuracy'}


def overlay(photo_bgr, reference, projected):
    a, b = binary_masks(reference, projected)
    photo_bgr = np.asarray(photo_bgr)
    if photo_bgr.ndim != 3 or photo_bgr.shape[2] != 3:
        raise ValueError('Photo must be an H×W×3 BGR array.')
    if photo_bgr.dtype.kind not in 'buif' or not np.isfinite(photo_bgr).all():
        raise ValueError('Photo channels must contain finite numeric values in [0, 255].')
    if np.any(photo_bgr < 0) or np.any(photo_bgr > 255):
        raise ValueError('Photo channels must contain values in [0, 255].')
    if photo_bgr.shape[:2] != a.shape:
        raise ValueError('Photo and masks must have matching pixel coordinates.')
    image = photo_bgr.astype(float)
    # BGR colors: overlap green, reference-only pink, projected-only cyan.
    for mask, color in [(a & b, (125, 220, 55)), (a & ~b, (145, 65, 255)), (~a & b, (255, 205, 0))]:
        image[mask] = .45*image[mask] + .55*np.asarray(color)
    return image.astype('uint8')


def load_mask(path):
    value = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if value is None:
        raise ValueError(f'Cannot read mask: {path}')
    return value > 127


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--projected', type=Path, required=True)
    parser.add_argument('--photo', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    a, b = load_mask(args.reference), load_mask(args.projected)
    metrics = compare(a, b)
    metrics['inputs'] = {'reference_mask': str(args.reference), 'projected_mask': str(args.projected)}
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out/'metrics.json').write_text(json.dumps(metrics, indent=2), encoding='utf-8')
    if args.photo:
        photo = cv2.imread(str(args.photo))
        if photo is None:
            raise ValueError(f'Cannot read photo: {args.photo}')
        if not cv2.imwrite(str(args.out/'overlay.png'), overlay(photo, a, b)):
            raise OSError('Could not write overlay image')
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
