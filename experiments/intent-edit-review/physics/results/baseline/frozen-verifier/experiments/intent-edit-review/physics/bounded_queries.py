"""Bound ray-query working sets without dropping any point or segment.

contains_points_batched intentionally does NOT call mesh.contains per point
chunk. Trimesh 4.12's original contains_points uses one common random retry
direction for all ambiguous rays in a logical query. Splitting that outer call
would change the directions and RNG consumption. Instead a nonmutating proxy
batches only the original algorithm's low-level intersects_location calls.

The original mesh, direction vectors, parity/retry algorithm and tolerances are
retained. Optional stats describe actual backend calls, never skipped samples.
"""
import operator

import numpy as np
from trimesh import constants
from trimesh.ray.ray_util import contains_points as _original_contains_points


def _batch_size(value):
    if isinstance(value, (bool, np.bool_)):
        raise TypeError('batch_size must be a positive integer')
    try:
        size = operator.index(value)
    except TypeError as exc:
        raise TypeError('batch_size must be a positive integer') from exc
    if size < 1:
        raise ValueError('batch_size must be a positive integer')
    return size


def _note(stats, count):
    if stats is not None:
        stats['backend_calls'] = stats.get('backend_calls', 0)+1
        stats['rays_queried'] = stats.get('rays_queried', 0)+count
        stats['max_backend_rays'] = max(stats.get('max_backend_rays', 0), count)


class _BoundedIntersector:
    """Preserve one contains call, remapping ray IDs across backend chunks."""
    def __init__(self, intersector, size, stats):
        self.mesh = intersector.mesh
        self._intersector = intersector
        self._size = size
        self._stats = stats

    def intersects_location(self, ray_origins, ray_directions, **kwargs):
        origins = np.asanyarray(ray_origins)
        directions = np.asanyarray(ray_directions)
        if self._stats is not None:
            self._stats['logical_ray_queries'] = self._stats.get('logical_ray_queries', 0)+1
        locations_parts = []; ray_parts = []; triangle_parts = []
        for start in range(0, len(origins), self._size):
            end = min(start+self._size, len(origins))
            locations, rays, triangles = self._intersector.intersects_location(
                origins[start:end], directions[start:end], **kwargs)
            _note(self._stats, end-start)
            if len(rays):
                locations_parts.append(locations)
                ray_parts.append(np.asarray(rays)+start)
                triangle_parts.append(triangles)
        if not ray_parts:
            return (np.empty((0, 3), dtype=np.float64), np.empty(0, dtype=np.int64),
                    np.empty(0, dtype=np.int64))
        return (np.concatenate(locations_parts), np.concatenate(ray_parts),
                np.concatenate(triangle_parts))


def contains_points_batched(mesh, points, batch_size=512, *, stats=None):
    """Return the original Trimesh inside mask with bounded backend ray batches.

    Every point retains its original index. ``batch_size`` bounds actual backend
    rays, including the original forward/backward and possible random retries.
    No mesh/intersector method is monkey-patched and no RNG seed is changed.
    """
    size = _batch_size(batch_size)
    points = np.asanyarray(points)
    if points.ndim != 2 or points.shape[1] != 3:
        raise ValueError('points must be (n,3)')
    if stats is not None:
        stats['points'] = stats.get('points', 0)+len(points)
    # Match Trimesh.contains's warning while retaining its existing ray/parity
    # implementation as a SINGLE logical query, including random fallback.
    if not mesh.is_watertight:
        constants.log.warning('Mesh is non-watertight for contained point query!')
    return _original_contains_points(_BoundedIntersector(mesh.ray, size, stats), points)


def segment_hits_batched(mesh, starts, ends, batch_size=512, *, stats=None):
    """Exact count of oracle.segment_hits, evaluated over all bounded chunks.

    Same direction normalization, length>1e-9 filter, multiple_hits=True, and
    endpoint distances strictly >1e-6 and <length-1e-6. Counts add across chunks.
    """
    size = _batch_size(batch_size)
    starts = np.asanyarray(starts); ends = np.asanyarray(ends)
    if starts.ndim != 2 or starts.shape[1] != 3 or starts.shape != ends.shape:
        raise ValueError('starts and ends must be matching (n,3) arrays')
    if stats is not None:
        stats['segments'] = stats.get('segments', 0)+len(starts)
    total = 0
    for left in range(0, len(starts), size):
        right = min(left+size, len(starts))
        a, b = starts[left:right], ends[left:right]
        direction = b-a
        lengths = np.linalg.norm(direction, axis=1)
        valid = lengths > 1e-9
        a, direction, lengths = a[valid], direction[valid], lengths[valid]
        if stats is not None:
            stats['valid_segments'] = stats.get('valid_segments', 0)+len(a)
        if not len(a):
            continue
        direction /= lengths[:, None]
        locations, rays, _ = mesh.ray.intersects_location(a, direction, multiple_hits=True)
        _note(stats, len(a))
        if len(rays):
            distances = np.einsum('ij,ij->i', locations-a[rays], direction[rays])
            total += int(np.sum((distances > 1e-6) & (distances < lengths[rays]-1e-6)))
    return total
