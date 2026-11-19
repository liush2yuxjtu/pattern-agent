use crate::geometry::{closest, V};

const CELL: f32 = 0.045;
const BUCKETS: usize = 8192;
const THICKNESS: f32 = 0.0026;
const SWEEP: f32 = 0.012;
const NO_VERTEX: usize = usize::MAX;

pub(crate) struct SelfContact {
    pub enabled: bool,
    pub step_hits: u32,
    pub total_hits: u32,
    triangles: Vec<[usize; 3]>,
    neighbors: Vec<Vec<usize>>,
    heads: Vec<usize>,
    links: Vec<usize>,
    cells: Vec<[i32; 3]>,
    budget: Vec<f32>,
}

impl SelfContact {
    pub const fn new() -> Self {
        Self {
            enabled: false,
            step_hits: 0,
            total_hits: 0,
            triangles: Vec::new(),
            neighbors: Vec::new(),
            heads: Vec::new(),
            links: Vec::new(),
            cells: Vec::new(),
            budget: Vec::new(),
        }
    }

    pub fn configure(&mut self, parent: &[usize], faces: &[[i32; 3]], stitches: &[([usize; 4], [f32; 3])]) {
        self.triangles.clear();
        self.neighbors.clear();
        self.neighbors.resize_with(parent.len(), Vec::new);
        for face in faces {
            let ids = face.map(|i| parent[i as usize]);
            if ids[0] == ids[1] || ids[0] == ids[2] || ids[1] == ids[2] {
                continue;
            }
            self.triangles.push(ids);
            for j in 0..3 {
                self.neighbors[ids[j]].push(ids[(j + 1) % 3]);
                self.neighbors[ids[j]].push(ids[(j + 2) % 3]);
            }
        }
        for &(ids, _) in stitches {
            let [p, a, b, c] = ids.map(|i| parent[i]);
            self.neighbors[p].extend([a, b, c]);
            for i in [a, b, c] {
                self.neighbors[i].push(p);
            }
        }
        for neighbors in &mut self.neighbors {
            neighbors.sort_unstable();
            neighbors.dedup();
        }
        self.heads.resize(BUCKETS, NO_VERTEX);
        self.links.resize(parent.len(), NO_VERTEX);
        self.cells.resize(parent.len(), [0; 3]);
        self.budget.resize(parent.len(), 0.0);
        self.step_hits = 0;
        self.total_hits = 0;
    }

    pub fn solve(&mut self, x: &mut [V], previous: &[V], mass: &[f32], parent: &[usize]) {
        self.heads.fill(NO_VERTEX);
        self.budget.fill(0.004);
        for i in 0..x.len() {
            if parent[i] != i || !x[i].finite() {
                continue;
            }
            let cell = cell(x[i]);
            let slot = hash(cell);
            self.cells[i] = cell;
            self.links[i] = self.heads[slot];
            self.heads[slot] = i;
        }
        for &face in &self.triangles {
            let [a, b, c] = face.map(|i| x[i]);
            if !(a.finite() && b.finite() && c.finite()) {
                continue;
            }
            let bounds = [
                (a.0.min(b.0).min(c.0) - SWEEP, a.0.max(b.0).max(c.0) + SWEEP),
                (a.1.min(b.1).min(c.1) - SWEEP, a.1.max(b.1).max(c.1) + SWEEP),
                (a.2.min(b.2).min(c.2) - SWEEP, a.2.max(b.2).max(c.2) + SWEEP),
            ];
            let [(lo_x, hi_x), (lo_y, hi_y), (lo_z, hi_z)] =
                bounds.map(|(lo, hi)| (cell_axis(lo), cell_axis(hi)));
            // An invalid stretched face may span an unbounded number of buckets.
            if [hi_x.saturating_sub(lo_x), hi_y.saturating_sub(lo_y), hi_z.saturating_sub(lo_z)]
                .into_iter().any(|span| span > 24) {
                continue;
            }
            for ix in lo_x..=hi_x {
                for iy in lo_y..=hi_y {
                    for iz in lo_z..=hi_z {
                        let bin = [ix, iy, iz];
                        let mut vertex = self.heads[hash(bin)];
                        while vertex != NO_VERTEX {
                            let p = vertex;
                            vertex = self.links[p];
                            if self.cells[p] != bin || face.contains(&p)
                                || face.iter().any(|v| self.neighbors[p].binary_search(v).is_ok()) {
                                continue;
                            }
                            if [x[p].0, x[p].1, x[p].2].into_iter().zip(bounds)
                                .any(|(v, (lo, hi))| v < lo || v > hi) {
                                continue;
                            }
                            if resolve(x, previous, mass, &mut self.budget, p, face) {
                                self.step_hits += 1;
                                self.total_hits += 1;
                            }
                        }
                    }
                }
            }
        }
    }
}

fn cell_axis(x: f32) -> i32 {
    (x / CELL).floor() as i32
}

fn cell(v: V) -> [i32; 3] {
    [v.0, v.1, v.2].map(cell_axis)
}

fn hash([a, b, c]: [i32; 3]) -> usize {
    ((a.wrapping_mul(73856093) ^ b.wrapping_mul(19349663) ^ c.wrapping_mul(83492791)) as usize)
        & (BUCKETS - 1)
}

fn resolve(x: &mut [V], previous: &[V], mass: &[f32], budget: &mut [f32], p: usize, face: [usize; 3]) -> bool {
    let [a, b, c] = face.map(|i| x[i]);
    let cross = (b - a).cross(c - a);
    let size = cross.len();
    if size < 1e-8 {
        return false;
    }
    let (q, u, v) = closest(x[p], a, b, c);
    let delta = x[p] - q;
    let distance = delta.len();
    if distance > SWEEP {
        return false;
    }
    let normal = cross * size.recip();
    let bary = [1.0 - u - v, u, v];
    let old = face.map(|i| previous[i]);
    let old_normal = (old[1] - old[0]).cross(old[2] - old[0]).unit();
    let old_point = old[0] * bary[0] + old[1] * bary[1] + old[2] * bary[2];
    let old_side = (previous[p] - old_point).dot(old_normal);
    let side = delta.dot(normal);
    let crossed = old_side.abs() > THICKNESS * 0.5 && old_side.abs() < SWEEP * 2.0
        && side * old_side < 0.0 && bary.into_iter().all(|w| w > 0.015);
    let (direction, correction) = if crossed {
        (normal * old_side.signum(), THICKNESS + side.abs())
    } else if distance < THICKNESS {
        let direction = if distance > 1e-6 { delta * distance.recip() }
            else { normal * if old_side < 0.0 { -1.0 } else { 1.0 } };
        (direction, THICKNESS - distance)
    } else {
        return false;
    };
    let ids = [p, face[0], face[1], face[2]];
    let gradients = [1.0, -bary[0], -bary[1], -bary[2]];
    let gains = std::array::from_fn::<_, 4, _>(|i| {
        if budget[ids[i]] > 1e-6 { mass[ids[i]] * gradients[i] } else { 0.0 }
    });
    let weight = gains.into_iter().zip(gradients).map(|(a, b)| a * b).sum::<f32>();
    let max_gain = gains.into_iter().map(f32::abs).fold(0.0, f32::max);
    if weight <= 1e-12 {
        return false;
    }
    // Tiny barycentric weights on light vertices must not amplify the move
    // beyond the contact depth, even when all other vertices are pinned.
    let scale = 0.85 * correction / weight.max(max_gain);
    for (id, gain) in ids.into_iter().zip(gains) {
        let move_by = (gain * scale).clamp(-budget[id], budget[id]);
        x[id] = x[id] + direction * move_by;
        budget[id] -= move_by.abs();
    }
    true
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn layers_separate_and_crossing_returns_to_previous_side() {
        for z in [0.001, -0.003] {
            let mut x = [V::ZERO, V(0.03, 0., 0.), V(0., 0.03, 0.), V(0.01, 0.01, z)];
            let mut previous = x;
            previous[3].2 = 0.004;
            let mut collision = SelfContact::new();
            let parent = [0, 1, 2, 3];
            collision.configure(&parent, &[[0, 1, 2]], &[]);
            for _ in 0..4 {
                collision.solve(&mut x, &previous, &[0., 0., 0., 1.], &parent);
            }
            assert!(collision.total_hits > 0);
            assert!(x[3].2 >= THICKNESS - 0.00002);
        }
    }

    #[test]
    fn sewn_neighbors_are_excluded_from_contact() {
        let mut x = [V::ZERO, V(0.03, 0., 0.), V(0., 0.03, 0.), V(0.01, 0.01, 0.001)];
        let previous = x;
        let parent = [0, 1, 2, 3];
        let mut collision = SelfContact::new();
        collision.configure(&parent, &[[0, 1, 2]], &[([3, 0, 1, 1], [0.5, 0.5, 0.0])]);
        collision.solve(&mut x, &previous, &[1.; 4], &parent);
        assert_eq!(collision.total_hits, 0);
    }
}
