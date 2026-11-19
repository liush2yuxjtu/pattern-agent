mod geometry;
mod material;
mod pressure;
mod self_contact;

use geometry::{fold, Body, Hit, Node, V};
use material::Material;
use std::{collections::BTreeMap, ptr::addr_of_mut};

const MAXV: usize = 4096;
const MAXT: usize = 8192;
const MAXS: usize = 256;
const MAXB: usize = 8192;
const MAX_EDGE_STITCHES: usize = 4096;
const MAXBV: usize = 16000;
const MAXBF: usize = 30000;
const MAXNODE: usize = 10000;
const EMPTY_SPRING: (usize, usize, f32) = (0, 0, 0.0);
const EMPTY_SEAM: (usize, usize, bool) = (0, 0, false);
const DT: f32 = 1.0 / 120.0;
const MARGIN: f32 = 0.006;

struct Solver {
    x: [V; MAXV],
    previous: [V; MAXV],
    edge_stitches: [([usize; 4], [f32; 3]); MAX_EDGE_STITCHES],
    edge_stitch_count: usize,
    pins: [V; MAXV],
    uv: [[f32; 2]; MAXV],
    inverse_mass: [f32; MAXV],
    contact: [f32; MAXV],
    rest_area_at_vertex: [f32; MAXV],
    contact_area: [f32; MAXV],
    normal_lambda: [f32; MAXV + MAXT],
    pressure_force: [f32; MAXV],
    pressure_area: [f32; MAXV],
    pressure_pa: [f32; MAXV],
    distance: [f32; MAXV],
    faces: [[i32; 3]; MAXT],
    inverse_dm: [[f32; 4]; MAXT],
    area: [f32; MAXT],
    lambda: [[f32; 3]; MAXT],
    fields: [[f32; 8]; MAXT],
    folds: [f32; MAXV],
    parent: [usize; MAXV],
    bends: [(usize, usize, f32); MAXB],
    seams: [(usize, usize, bool); MAXS],
    hinges: Vec<[usize; 4]>,
    body: [V; MAXBV],
    body_normals: [V; MAXBV],
    body_faces: [[i32; 3]; MAXBF],
    order: [i32; MAXBF],
    nodes: [Node; MAXNODE],
    body_nv: usize,
    body_nf: usize,
    node_count: usize,
    nv: usize,
    nt: usize,
    ns: usize,
    nb: usize,
    cache_point: [V; MAXV + MAXT],
    cache_distance: [f32; MAXV + MAXT],
    material: Material,
    offset: f32,
    frame: i32,
    time: f32,
    collision: bool,
    self_contact: self_contact::SelfContact,
    cache: bool,
    stats: [f32; 16],
    probe: [f32; 16],
}

impl Solver {
    const fn new() -> Self {
        Self {
            x: [V::ZERO; MAXV],
            previous: [V::ZERO; MAXV],
            edge_stitches: [([0; 4], [0.0; 3]); MAX_EDGE_STITCHES],
            edge_stitch_count: 0,
            pins: [V::ZERO; MAXV],
            uv: [[0.0; 2]; MAXV],
            inverse_mass: [0.0; MAXV],
            contact: [0.0; MAXV],
            rest_area_at_vertex: [0.0; MAXV],
            contact_area: [0.0; MAXV],
            normal_lambda: [0.0; MAXV + MAXT],
            pressure_force: [0.0; MAXV],
            pressure_area: [0.0; MAXV],
            pressure_pa: [0.0; MAXV],
            distance: [0.0; MAXV],
            faces: [[0; 3]; MAXT],
            inverse_dm: [[0.0; 4]; MAXT],
            area: [0.0; MAXT],
            lambda: [[0.0; 3]; MAXT],
            fields: [[0.0; 8]; MAXT],
            folds: [0.0; MAXV],
            parent: [0; MAXV],
            bends: [EMPTY_SPRING; MAXB],
            seams: [EMPTY_SEAM; MAXS],
            hinges: Vec::new(),
            body: [V::ZERO; MAXBV],
            body_normals: [V::ZERO; MAXBV],
            body_faces: [[0; 3]; MAXBF],
            order: [0; MAXBF],
            nodes: [Node::EMPTY; MAXNODE],
            body_nv: 0,
            body_nf: 0,
            node_count: 0,
            nv: 0,
            nt: 0,
            ns: 0,
            nb: 0,
            cache_point: [V::ZERO; MAXV + MAXT],
            cache_distance: [-1e6; MAXV + MAXT],
            material: Material::WOVEN,
            offset: 0.0,
            frame: 0,
            time: 0.0,
            collision: true,
            self_contact: self_contact::SelfContact::new(),
            cache: true,
            stats: [0.0; 16],
            probe: [0.0; 16],
        }
    }

    fn vertex(&self, mut id: usize) -> usize {
        while self.parent[id] != id {
            id = self.parent[id];
        }
        id
    }
    fn sync_aliases(&mut self) {
        for i in 0..self.nv {
            let parent = self.parent[i];
            if parent != i {
                self.x[i] = self.x[parent];
                self.previous[i] = self.previous[parent];
            }
        }
    }
    fn nearest(&self, point: V) -> Hit {
        Body {
            vertices: &self.body[..self.body_nv],
            normals: &self.body_normals[..self.body_nv],
            faces: &self.body_faces[..self.body_nf],
            order: &self.order[..self.body_nf],
            nodes: &self.nodes[..self.node_count],
            offset: self.offset,
        }
        .nearest(point)
    }
    fn transform_body(&mut self, sx: f32, sy: f32, sz: f32) {
        if ![sx, sy, sz]
            .into_iter()
            .all(|v| v.is_finite() && (0.5..=1.5).contains(&v))
        {
            return;
        }
        for (v, n) in self.body[..self.body_nv]
            .iter_mut()
            .zip(self.body_normals.iter_mut())
        {
            *v = V(v.0 * sx, v.1 * sy, v.2 * sz);
            *n = V(n.0 / sx, n.1 / sy, n.2 / sz).unit();
        }
        self.nodes[..self.node_count]
            .iter_mut()
            .for_each(|node| node.scale(sx, sy, sz));
        self.cache_distance.fill(-1e6);
    }
    fn configure(&mut self, nv: usize, nt: usize) {
        self.configure_with_rest(nv, nt, false);
    }
    fn configure_with_rest(&mut self, nv: usize, nt: usize, use_placed_rest: bool) {
        assert!(nv <= MAXV && nt <= MAXT);
        self.nv = nv;
        self.nt = nt;
        self.ns = 0;
        self.nb = 0;
        self.edge_stitch_count = 0;
        self.frame = 0;
        self.time = 0.0;
        self.offset = 0.0;
        self.cache_distance.fill(-1e6);
        for i in 0..nv {
            self.parent[i] = i;
            self.previous[i] = self.x[i];
            self.pins[i] = self.x[i];
            self.contact[i] = 0.0;
            self.inverse_mass[i] = 0.0;
        }
        let mut edges: BTreeMap<(usize, usize), [usize; 3]> = BTreeMap::new();
        self.hinges.clear();
        self.rest_area_at_vertex[..nv].fill(0.0);
        self.normal_lambda.fill(0.0);
        self.contact_area[..nv].fill(0.0);
        for t in 0..nt {
            let [i, j, k] = self.faces[t].map(|i| i as usize);
            let [a, b, c, d] = if use_placed_rest {
                let e1 = self.x[j] - self.x[i];
                let e2 = self.x[k] - self.x[i];
                let along = e1.len();
                let across = e1.cross(e2).len() / along;
                [along, e1.dot(e2) / along, 0.0, across]
            } else {
                [
                    self.uv[j][0] - self.uv[i][0],
                    self.uv[k][0] - self.uv[i][0],
                    self.uv[j][1] - self.uv[i][1],
                    self.uv[k][1] - self.uv[i][1],
                ]
            };
            let det = a * d - b * c;
            assert!(det.is_finite() && det.abs() > 1e-12);
            self.inverse_dm[t] = [d / det, -b / det, -c / det, a / det];
            self.area[t] = det.abs() * 0.5;
            let mass = self.area[t] * self.material.density / 3.0;
            for v in [i, j, k] {
                self.inverse_mass[v] += mass;
                self.rest_area_at_vertex[v] += self.area[t] / 3.0;
            }
            for (a, b, c) in [(i, j, k), (j, k, i), (k, i, j)] {
                let edge = (a.min(b), a.max(b));
                if let Some([first, second, other]) = edges.remove(&edge) {
                    self.hinges.push([first, second, other, c]);
                } else {
                    edges.insert(edge, [a, b, c]);
                }
            }
        }
        self.inverse_mass[..nv]
            .iter_mut()
            .for_each(|m| *m = m.max(1e-9).recip());
    }
    fn finalize(&mut self) {
        for j in 0..self.ns {
            let (a, b, active) = self.seams[j];
            if active {
                let (a, b) = (self.vertex(a), self.vertex(b));
                if a != b {
                    self.parent[b] = a;
                }
            }
        }
        let mut mass = [0.0; MAXV];
        let mut fixed = [false; MAXV];
        self.contact_area[..self.nv].fill(0.0);
        for i in 0..self.nv {
            let parent = self.vertex(i);
            self.parent[i] = parent;
            self.contact_area[parent] += self.rest_area_at_vertex[i];
            if self.inverse_mass[i] == 0.0 {
                fixed[parent] = true;
            } else {
                mass[parent] += self.inverse_mass[i].recip();
            }
        }
        for i in 0..self.nv {
            self.inverse_mass[i] = if self.parent[i] != i || fixed[i] {
                0.0
            } else {
                mass[i].max(1e-9).recip()
            };
        }
        self.sync_aliases();
    }
    fn basis(&self, t: usize, ids: [usize; 3]) -> (V, V) {
        let [i, j, k] = ids;
        let [a, b, c, d] = self.inverse_dm[t];
        let (e1, e2) = (self.x[j] - self.x[i], self.x[k] - self.x[i]);
        (e1 * a + e2 * c, e1 * b + e2 * d)
    }
    fn membrane(&mut self, t: usize, component: usize) {
        let ids = self.faces[t].map(|i| self.vertex(i as usize));
        let [a, b, c, d] = self.inverse_dm[t];
        let (u, v) = self.basis(t, ids);
        let (q11, q22, q12) = self.material.moduli();
        let (residual, g1, g2, stiffness) = match component {
            0 => {
                let r = q12 / q11;
                (
                    0.5 * (u.dot(u) - 1.0) + r * 0.5 * (v.dot(v) - 1.0),
                    u * a + v * (r * b),
                    u * c + v * (r * d),
                    q11,
                )
            }
            1 => (0.5 * (v.dot(v) - 1.0), v * b, v * d, q22 - q12 * q12 / q11),
            _ => (u.dot(v), v * a + u * b, v * c + u * d, self.material.shear),
        };
        let gradients = [(g1 + g2) * -1.0, g1, g2];
        let weights = ids.map(|i| self.inverse_mass[i]);
        let alpha = (stiffness * self.material.thickness * self.area[t] * DT * DT).recip();
        let den = weights[0] * gradients[0].dot(gradients[0])
            + weights[1] * g1.dot(g1)
            + weights[2] * g2.dot(g2)
            + alpha;
        let l = &mut self.lambda[t][component];
        let delta = (-residual - alpha * *l) / den.max(1e-12);
        *l += delta;
        for i in 0..3 {
            self.x[ids[i]] = self.x[ids[i]] + gradients[i] * (delta * weights[i]);
        }
    }
    fn solve_distance(&mut self, a: usize, b: usize, rest: f32, alpha: f32) {
        let (a, b) = (self.vertex(a), self.vertex(b));
        let delta = self.x[b] - self.x[a];
        let len = delta.len();
        let (wa, wb) = (self.inverse_mass[a], self.inverse_mass[b]);
        if wa + wb < 1e-12 || len < 1e-10 {
            return;
        }
        let r = (len - rest) / (len * (wa + wb + alpha));
        self.x[a] = self.x[a] + delta * (r * wa);
        self.x[b] = self.x[b] - delta * (r * wb);
    }
    fn cached_nearest(&mut self, point: V, key: usize, envelope: f32) -> Option<Hit> {
        let local = point - V(self.offset, 0.0, 0.0);
        let delta = local - self.cache_point[key];
        let safe = self.cache_distance[key] - envelope;
        if self.cache && self.normal_lambda[key] == 0.0 && safe > 0.0 && delta.dot(delta) < safe * safe {
            return None;
        }
        let hit = self.nearest(point);
        self.cache_point[key] = local;
        self.cache_distance[key] = hit.distance;
        Some(hit)
    }
    fn contact_gradient(point: V, hit: Hit) -> V {
        if hit.distance.abs() < 1e-7 {
            hit.n
        } else {
            (point - hit.q).unit() * hit.distance.signum()
        }
    }
    fn collide_vertex(&mut self, i: usize) {
        let mass = self.inverse_mass[i];
        let area = self.contact_area[i];
        if mass == 0.0 || area <= 0.0 {
            return;
        }
        let point = self.x[i];
        if let Some(hit) = self.cached_nearest(point, i, MARGIN) {
            let change = pressure::project(&mut self.normal_lambda[i], hit.distance - MARGIN, mass, area);
            if change != 0.0 {
                self.x[i] = point + Self::contact_gradient(point, hit) * (change * mass);
            }
        }
    }
    fn collide_centroid(&mut self, t: usize) {
        let ids = self.faces[t].map(|i| self.vertex(i as usize));
        if ids[0] == ids[1] || ids[0] == ids[2] || ids[1] == ids[2] {
            return;
        }
        let [a, b, c] = ids;
        let sum = self.inverse_mass[a] + self.inverse_mass[b] + self.inverse_mass[c];
        if sum <= 1e-12 {
            return;
        }
        let p = (self.x[a] + (self.x[b] + self.x[c])) * (1.0 / 3.0);
        let slot = MAXV + t;
        let envelope = MARGIN * 0.5;
        if let Some(hit) = self.cached_nearest(p, slot, envelope) {
            let change = pressure::project(&mut self.normal_lambda[slot], hit.distance - envelope, sum / 9.0, 0.0);
            if change != 0.0 {
                let direction = Self::contact_gradient(p, hit);
                for i in ids {
                    self.x[i] = self.x[i] + direction * (change * self.inverse_mass[i] / 3.0);
                }
            }
        }
    }
    fn report_pressure(&mut self) {
        self.pressure_area[..self.nv].fill(0.0);
        self.pressure_force[..self.nv].fill(0.0);
        let mut merged_area = [0.0; MAXV];
        let to_newtons = (DT * DT).recip();
        for t in 0..self.nt {
            let [a,b,c] = self.faces[t].map(|i| i as usize);
            let area = (self.x[b] - self.x[a]).cross(self.x[c] - self.x[a]).len() / 6.0;
            let force = self.normal_lambda[MAXV + t] * to_newtons / 3.0;
            for i in [a,b,c] {
                self.pressure_area[i] += area;
                if self.collision { self.pressure_force[i] += force; }
            }
        }
        for i in 0..self.nv {
            merged_area[self.parent[i]] += self.pressure_area[i];
        }
        for i in 0..self.nv {
            let area = self.pressure_area[i];
            let root = self.parent[i];
            if self.collision && merged_area[root] > 0.0 {
                self.pressure_force[i] += self.normal_lambda[root] * to_newtons * area / merged_area[root];
            }
            self.pressure_pa[i] = if area > 0.0 { self.pressure_force[i] / area } else { 0.0 };
        }
    }
    fn sew(&mut self) {
        for j in 0..self.ns {
            let (a, b, active) = self.seams[j];
            if active {
                self.solve_distance(a, b, 0.0, 0.0);
            }
        }
    }
    // Couple different tessellations on opposite sides of a reference seam.
    fn sew_edges(&mut self) {
        for j in 0..self.edge_stitch_count {
            let (vertices, bary) = self.edge_stitches[j];
            let ids = vertices.map(|i| self.vertex(i));
            if ids[1..].contains(&ids[0]) {
                continue;
            }
            let weights = [1.0, -bary[0], -bary[1], -bary[2]];
            let mut den: f32 = 0.0;
            let mut max_gain: f32 = 0.0;
            let mut error = V(0.0, 0.0, 0.0);
            for k in 0..4 {
                let gain = weights[k] * self.inverse_mass[ids[k]];
                den += weights[k] * gain;
                max_gain = max_gain.max(gain.abs());
                error = error + self.x[ids[k]] * weights[k];
            }
            if den > 1e-12 {
                for k in 0..4 {
                    let id = ids[k];
                    self.x[id] = self.x[id] - error * (0.65 * weights[k] * self.inverse_mass[id] / den.max(max_gain));
                }
            }
        }
    }

    fn step(&mut self, wind: f32) {
        for i in 0..self.nv {
            if self.parent[i] != i {
                continue;
            }
            if self.inverse_mass[i] == 0.0 {
                self.x[i] = self.pins[i];
                self.previous[i] = self.x[i];
                continue;
            }
            let mut velocity = (self.x[i] - self.previous[i]) * 0.993;
            let speed = velocity.len();
            if speed > 0.025 {
                velocity = velocity * (0.025 / speed);
            }
            self.previous[i] = self.x[i];
            self.x[i] = self.x[i] + velocity + V(0.0, -9.81 * DT * DT, wind * DT * DT);
        }
        self.constrain_step();
    }
    fn solve_self_contact(&mut self) {
        self.self_contact.solve(
            &mut self.x[..self.nv], &self.previous[..self.nv],
            &self.inverse_mass[..self.nv], &self.parent[..self.nv],
        );
    }
    fn constrain_step(&mut self) {
        self.self_contact.step_hits = 0;
        self.contact[..self.nv].fill(0.0);
        self.normal_lambda[..self.nv].fill(0.0);
        self.normal_lambda[MAXV..MAXV + self.nt].fill(0.0);
        self.lambda[..self.nt].fill([0.0; 3]);
        for iteration in 0..24 {
            for j in 0..self.nt {
                let t = if iteration % 2 == 0 {
                    j
                } else {
                    self.nt - 1 - j
                };
                for component in 0..3 {
                    self.membrane(t, component);
                }
            }
            for j in 0..self.nb {
                let (a, b, rest) = self.bends[j];
                self.solve_distance(a, b, rest, (0.04 * DT * DT).recip());
            }
            self.sew();
            self.sew_edges();
            if self.self_contact.enabled && matches!(iteration, 12 | 23) {
                self.solve_self_contact();
            }
            if self.collision {
                for i in 0..self.nv {
                    self.collide_vertex(i);
                }
                if iteration >= 22 {
                    for t in 0..self.nt {
                        self.collide_centroid(t);
                    }
                }
            }
        }
        for _ in 0..3 {
            self.sew();
            self.sew_edges();
            if self.collision {
                for i in 0..self.nv {
                    self.collide_vertex(i);
                }
                for t in 0..self.nt {
                    self.collide_centroid(t);
                }
            }
        }
        for i in 0..self.nv {
            self.contact[i] = (self.normal_lambda[self.parent[i]] > 0.0) as u8 as f32;
        }
        self.sync_aliases();
        self.frame += 1;
        self.time += DT;
    }
    fn analyze(&mut self) {
        let (mut strain, mut stress, mut energy) = (-1.0_f32, 0.0_f32, 0.0);
        let (q11, q22, q12) = self.material.moduli();
        for t in 0..self.nt {
            let (u, v) = self.basis(t, self.faces[t].map(|i| i as usize));
            let fields = self.material.fields(u, v);
            self.fields[t] = fields;
            strain = strain.max(fields[0]);
            stress = stress.max(fields[3]);
            let [a, b, c] = [fields[5], fields[6], fields[7]];
            energy += (0.5 * q11 * a * a
                + q12 * a * b
                + 0.5 * q22 * b * b
                + 2.0 * self.material.shear * c * c)
                * self.area[t]
                * self.material.thickness;
        }
        let mut gap = 0.0_f32;
        for &(a, b, active) in &self.seams[..self.ns] {
            if active {
                gap = gap.max((self.x[a] - self.x[b]).len());
            }
        }
        let (mut penetration, mut clearance, mut contacts, mut finite) =
            (0.0_f32, 1e6_f32, 0, true);
        for i in 0..self.nv {
            let distance = self.nearest(self.x[i]).distance;
            self.distance[i] = distance;
            penetration = penetration.max(-distance);
            clearance = clearance.min(distance);
            contacts += usize::from(self.contact[i] > 0.0);
            finite &= self.x[i].finite();
        }
        self.folds[..self.nv].fill(0.0);
        let mut maximum_fold = 0.0_f32;
        for &[a, b, c, d] in &self.hinges {
            let angle = fold(self.x[a], self.x[b], self.x[c], self.x[d]);
            self.folds[a] = self.folds[a].max(angle);
            self.folds[b] = self.folds[b].max(angle);
            maximum_fold = maximum_fold.max(angle);
        }
        self.report_pressure();
        self.stats[12] = self.self_contact.step_hits as f32;
        self.stats[13] = self.self_contact.total_hits as f32;
        self.stats[14] = self.self_contact.enabled as u8 as f32;
        self.stats[..12].copy_from_slice(&[
            self.frame as f32,
            self.time,
            gap,
            penetration,
            clearance,
            strain,
            stress,
            contacts as f32,
            finite as u8 as f32,
            energy,
            self.collision as u8 as f32,
            maximum_fold,
        ]);
    }
}

// The fixed-buffer ABI is for one caller on one thread. Buffer views must not
// be accessed concurrently with calls. Pointers remain valid for module life.
static mut STATE: Solver = Solver::new();
fn state() -> &'static mut Solver {
    unsafe { &mut *addr_of_mut!(STATE) }
}

macro_rules! pointer {
    ($method:ident, $field:ident) => {
        #[no_mangle]
        pub unsafe extern "C" fn $method() -> usize {
            unsafe { addr_of_mut!(STATE.$field) as usize }
        }
    };
}
pointer!(position_ptr, x);
pointer!(previous_ptr, previous);
pointer!(pin_ptr, pins);
pointer!(uv_ptr, uv);
pointer!(face_ptr, faces);
pointer!(invmass_ptr, inverse_mass);
pointer!(field_ptr, fields);
pointer!(contacts_ptr, contact);
pointer!(pressure_ptr, pressure_pa);
pointer!(pressure_force_ptr, pressure_force);
pointer!(pressure_area_ptr, pressure_area);
pointer!(pressure_lambda_ptr, normal_lambda);
pointer!(parent_ptr, parent);
#[no_mangle]
pub extern "C" fn pressure_face_start() -> usize { MAXV }
pointer!(body_distance_ptr, distance);
pointer!(stats_ptr, stats);

#[no_mangle]
pub unsafe extern "C" fn finish_predicted_step() {
    state().constrain_step();
}
pointer!(probe_ptr, probe);
pointer!(fold_ptr, folds);
pointer!(body_ptr, body);
pointer!(body_normal_ptr, body_normals);
pointer!(body_face_ptr, body_faces);
pointer!(body_order_ptr, order);
pointer!(body_node_ptr, nodes);

#[no_mangle]
pub unsafe extern "C" fn configure_body(v: usize, f: usize, n: usize) {
    assert!(v <= MAXBV && f <= MAXBF && n <= MAXNODE);
    let s = state();
    (s.body_nv, s.body_nf, s.node_count) = (v, f, n);
    s.cache_distance.fill(-1e6);
}
#[no_mangle]
pub unsafe extern "C" fn transform_body(sx: f32, sy: f32, sz: f32) {
    state().transform_body(sx, sy, sz);
}
#[no_mangle]
pub unsafe extern "C" fn configure_cloth(v: usize, f: usize) {
    state().configure(v, f);
}
// Warm-start a previously assembled garment with its placed edge lengths as rest shape.
#[no_mangle]
pub unsafe extern "C" fn configure_placed_cloth(v: usize, f: usize) {
    state().configure_with_rest(v, f, true);
}
#[no_mangle]
pub unsafe extern "C" fn configure_material(
    eu: f32,
    ev: f32,
    shear: f32,
    poisson: f32,
    thickness: f32,
    density: f32,
) {
    state().material = Material {
        eu,
        ev,
        shear,
        poisson,
        thickness,
        density,
    };
}
#[no_mangle]
pub unsafe extern "C" fn add_edge_stitch(p: usize, a: usize, b: usize, t: f32) {
    let s = state();
    assert!(s.edge_stitch_count < MAX_EDGE_STITCHES);
    s.edge_stitches[s.edge_stitch_count] = ([p, a, b, b], [1.0 - t, t, 0.0]);
    s.edge_stitch_count += 1;
}
#[no_mangle]
pub unsafe extern "C" fn add_surface_stitch(p: usize, a: usize, b: usize, c: usize, u: f32, v: f32, w: f32) {
    let s = state();
    assert!(s.edge_stitch_count < MAX_EDGE_STITCHES);
    s.edge_stitches[s.edge_stitch_count] = ([p, a, b, c], [u, v, w]);
    s.edge_stitch_count += 1;
}
#[no_mangle]
pub unsafe extern "C" fn set_pin(i: usize) {
    state().inverse_mass[i] = 0.0;
}
#[no_mangle]
pub unsafe extern "C" fn add_seam(a: usize, b: usize, active: i32) {
    let s = state();
    if s.ns < MAXS {
        s.seams[s.ns] = (a, b, active != 0);
        s.ns += 1;
    }
}
#[no_mangle]
pub unsafe extern "C" fn add_bend(a: usize, b: usize, rest: f32) {
    let s = state();
    if s.nb < MAXB {
        s.bends[s.nb] = (a, b, rest);
        s.nb += 1;
    }
}
#[no_mangle]
pub unsafe extern "C" fn finalize_seams() {
    state().finalize();
}
#[no_mangle]
pub unsafe extern "C" fn set_self_collision(enabled: i32) {
    let s = state();
    s.self_contact.enabled = enabled != 0;
    s.self_contact.step_hits = 0;
    s.self_contact.total_hits = 0;
    if s.self_contact.enabled {
        s.self_contact.configure(&s.parent[..s.nv], &s.faces[..s.nt], &s.edge_stitches[..s.edge_stitch_count]);
    }
}

#[no_mangle]
pub unsafe extern "C" fn set_collision(enabled: i32) {
    state().collision = enabled != 0;
}
#[no_mangle]
pub unsafe extern "C" fn set_cache(enabled: i32) {
    state().cache = enabled != 0;
}
#[no_mangle]
pub unsafe extern "C" fn set_body_offset(offset: f32) {
    let s = state();
    let delta = offset - s.offset;
    s.offset = offset;
    for i in 0..s.nv {
        if s.parent[i] == i && s.inverse_mass[i] == 0.0 {
            s.pins[i].0 += delta;
            s.x[i] = s.pins[i];
            s.previous[i] = s.x[i];
        }
    }
    s.sync_aliases();
}
#[no_mangle]
pub unsafe extern "C" fn inject_vertex(i: usize, x: f32, y: f32, z: f32) {
    let s = state();
    let i = s.vertex(i);
    s.x[i] = V(x, y, z);
    s.previous[i] = s.x[i];
    s.sync_aliases();
}
#[no_mangle]
pub unsafe extern "C" fn material_probe(ux: f32, uy: f32, uz: f32, vx: f32, vy: f32, vz: f32) {
    let s = state();
    s.probe[..8].copy_from_slice(&s.material.fields(V(ux, uy, uz), V(vx, vy, vz)));
}
#[no_mangle]
pub unsafe extern "C" fn collision_probe(x: f32, y: f32, z: f32) {
    let s = state();
    let hit = s.nearest(V(x, y, z));
    s.probe[..7].copy_from_slice(&[
        hit.distance,
        hit.q.0,
        hit.q.1,
        hit.q.2,
        hit.n.0,
        hit.n.1,
        hit.n.2,
    ]);
}
#[no_mangle]
pub unsafe extern "C" fn step(count: i32, wind: f32) {
    let s = state();
    for _ in 0..count {
        s.step(wind);
    }
}
#[no_mangle]
pub unsafe extern "C" fn analyze() {
    state().analyze();
}
#[no_mangle]
pub unsafe extern "C" fn set_clock(frame: i32, time: f32) {
    let s = state();
    (s.frame, s.time) = (frame, time);
}
#[no_mangle]
pub unsafe extern "C" fn get_frame() -> i32 {
    state().frame
}
#[no_mangle]
pub unsafe extern "C" fn get_time() -> f32 {
    state().time
}

// 两片裙样的自动配边。每片以腰到下摆作为缝线方向。
#[no_mangle]
pub unsafe extern "C" fn skirt_seams(columns: usize, rows: usize, fault: i32) -> usize {
    let s = state();
    if columns == 0
        || rows == 0
        || columns >= MAXV
        || rows >= MAXS / 2
        || 2 * (columns + 1) * (rows + 1) != s.nv
    {
        return 0;
    }
    let panel = (columns + 1) * (rows + 1);
    for j in 0..=rows {
        let row = j * (columns + 1);
        let other = if fault == 2 {
            (rows - j) * (columns + 1)
        } else {
            row
        };
        s.seams[2 * j] = (row + columns, panel + row, true);
        s.seams[2 * j + 1] = (row, panel + other + columns, fault != 1);
    }
    s.ns = 2 * (rows + 1);
    s.ns
}
#[no_mangle]
pub unsafe extern "C" fn seam_vertex(pair: usize, end: usize) -> usize {
    let (a, b, _) = state().seams[pair];
    if end == 0 {
        a
    } else {
        b
    }
}
#[no_mangle]
pub unsafe extern "C" fn seam_active(pair: usize) -> i32 {
    state().seams[pair].2 as i32
}
#[no_mangle]
pub unsafe extern "C" fn seam_audit() -> i32 {
    let s = state();
    let mut flags = 0;
    let mut lengths = [0.0_f32; 2];
    for side in 0..2 {
        for j in (side..s.ns).step_by(2) {
            let (a, b, active) = s.seams[j];
            if !active {
                flags |= 1;
            }
            if j < 2 {
                continue;
            }
            let (c, d, _) = s.seams[j - 2];
            let left = s.uv[a][0] - s.uv[c][0];
            let right = s.uv[b][0] - s.uv[d][0];
            if left * right <= 0.0 {
                flags |= 2;
            }
            let len = |(a, b): (usize, usize)| {
                ((s.uv[a][0] - s.uv[b][0]).powi(2) + (s.uv[a][1] - s.uv[b][1]).powi(2)).sqrt()
            };
            lengths[side] += len((a, c)) - len((b, d));
        }
    }
    s.probe[0] = lengths[0].abs().max(lengths[1].abs()) * 1000.0;
    if s.ns == 0 {
        flags |= 1;
    }
    flags
}

// 纸样以毫米为界面单位，求解和材料坐标使用米。
#[no_mangle]
pub unsafe extern "C" fn configure_skirt(
    columns: usize,
    rows: usize,
    top_mm: f32,
    bottom_mm: f32,
    front_mm: f32,
    back_mm: f32,
    waist_height: f32,
) {
    assert!((1..=32).contains(&columns) && (1..=32).contains(&rows));
    assert!([top_mm, bottom_mm, front_mm, back_mm, waist_height]
        .iter()
        .all(|v| v.is_finite() && *v > 0.0));
    let s = state();
    let panel = (columns + 1) * (rows + 1);
    let idx = |p, i, j| p * panel + j * (columns + 1) + i;
    let ellipse = |i: usize| {
        let angle = std::f64::consts::TAU * i as f64 / 2048.0;
        (0.158 * angle.cos(), 0.108 * angle.sin())
    };
    let mut arc = [0.0; 2049];
    for i in 1..arc.len() {
        let ((x, z), (a, b)) = (ellipse(i), ellipse(i - 1));
        arc[i] = arc[i - 1] + (x - a).hypot(z - b);
    }
    let total = arc[2048];
    let scale = f64::from(top_mm) * 0.002 / total;
    let mut segment = 0;
    let mut ring = Vec::with_capacity(2 * columns + 1);
    for i in 0..=2 * columns {
        let distance = total * i as f64 / (2 * columns) as f64;
        while segment < 2047 && arc[segment + 1] < distance {
            segment += 1;
        }
        let t = (distance - arc[segment]) / (arc[segment + 1] - arc[segment]);
        let ((x, z), (a, b)) = (ellipse(segment), ellipse(segment + 1));
        ring.push((
            ((1.0 - t) * x + t * a) * scale,
            ((1.0 - t) * z + t * b) * scale,
        ));
    }
    let mut f = 0;
    for (p, length) in [front_mm, back_mm].into_iter().enumerate() {
        for j in 0..=rows {
            let ratio = j as f64 / rows as f64;
            let w = f64::from(top_mm) + f64::from(bottom_mm - top_mm) * ratio;
            let flaring = w / f64::from(top_mm);
            for i in 0..=columns {
                let k = idx(p, i, j);
                let (x, z) = ring[p * columns + i];
                s.x[k] = V(
                    (x * flaring) as f32,
                    (f64::from(waist_height) - ratio * f64::from(length) / 1000.0) as f32,
                    (0.06 + z * flaring) as f32,
                );
                s.uv[k] = [
                    (ratio * f64::from(length) / 1000.0) as f32,
                    ((i as f64 / columns as f64 - 0.5) * w / 1000.0) as f32,
                ];
                if i < columns && j < rows {
                    let a = k as i32;
                    let b = a + 1;
                    let c = a + columns as i32 + 1;
                    s.faces[f] = [a, b, c];
                    s.faces[f + 1] = [b, c + 1, c];
                    f += 2;
                }
            }
        }
    }
    // 腰口固定点先贴到人台外侧，避免改尺寸后把裁片固定在体内。
    s.offset = 0.0;
    for p in 0..2 {
        for i in 0..=columns {
            let k = idx(p, i, 0);
            let hit = s.nearest(s.x[k]);
            if hit.distance < MARGIN {
                s.x[k] = hit.q + hit.n * MARGIN;
            }
        }
    }
    s.configure(2 * panel, f);
    for p in 0..2 {
        for i in 0..=columns {
            s.inverse_mass[idx(p, i, 0)] = 0.0;
        }
        for j in 0..=rows {
            for i in 0..=columns {
                let k = idx(p, i, j);
                let candidates = [
                    (i + 2 <= columns).then(|| idx(p, i + 2, j)),
                    (j + 2 <= rows).then(|| idx(p, i, j + 2)),
                ];
                for end in candidates.into_iter().flatten() {
                    let rest = (s.uv[k][0] - s.uv[end][0]).hypot(s.uv[k][1] - s.uv[end][1]);
                    s.bends[s.nb] = (k, end, rest);
                    s.nb += 1;
                }
            }
        }
    }
}

static mut SNAPSHOT: [f32; MAXV * 10] = [0.0; MAXV * 10];

#[no_mangle]
pub unsafe extern "C" fn snapshot_ptr() -> usize {
    addr_of_mut!(SNAPSHOT) as usize
}

#[no_mangle]
pub unsafe extern "C" fn capture_state() -> usize {
    let s = state();
    let n = s.nv;
    let out = &mut *addr_of_mut!(SNAPSHOT);
    for i in 0..n {
        for (channel, v) in [s.x[i], s.previous[i], s.pins[i]].into_iter().enumerate() {
            let k = (channel * n + i) * 3;
            out[k..k + 3].copy_from_slice(&[v.0, v.1, v.2]);
        }
        out[n * 9 + i] = s.contact[i];
    }
    n * 10
}

#[no_mangle]
pub unsafe extern "C" fn restore_state(frame: i32, time: f32) {
    let s = state();
    let n = s.nv;
    let data = &*addr_of_mut!(SNAPSHOT);
    let read = |k| V(data[k], data[k + 1], data[k + 2]);
    for i in 0..n {
        s.x[i] = read(i * 3);
        s.previous[i] = read((n + i) * 3);
        s.pins[i] = read((2 * n + i) * 3);
        s.contact[i] = data[n * 9 + i];
    }
    s.frame = frame;
    s.time = time;
    s.cache_distance.fill(-1e6);
}

// 以三角形交线追踪闭合轮廓。取最大闭合截面，以排除同高度的手臂截面。
#[no_mangle]
pub unsafe extern "C" fn body_waist_mm(height: f32) -> f32 {
    if !height.is_finite() {
        return 0.0;
    }
    let s = state();
    let mut edges = BTreeMap::<(usize, usize), Vec<((usize, usize), f32)>>::new();
    for face in &s.body_faces[..s.body_nf] {
        let [a, b, c] = face.map(|i| i as usize);
        let mut crossings = [(0, 0, V::ZERO); 2];
        let mut n = 0;
        for (i, j) in [(a, b), (b, c), (c, a)] {
            let (p, q) = (s.body[i], s.body[j]);
            if (p.1 <= height) == (q.1 <= height) {
                continue;
            }
            let t = (height - p.1) / (q.1 - p.1);
            crossings[n] = (i.min(j), i.max(j), p + (q - p) * t);
            n += 1;
        }
        if let (2, [(a, b, p), (c, d, q)]) = (n, crossings) {
            let length = (p - q).len();
            edges.entry((a, b)).or_default().push(((c, d), length));
            edges.entry((c, d)).or_default().push(((a, b), length));
        }
    }
    let mut largest = 0.0_f32;
    while let Some((key, _)) = edges.first_key_value() {
        let mut next = vec![*key];
        let mut sum = 0.0;
        let mut closed = true;
        while let Some(key) = next.pop() {
            let Some(neighbors) = edges.remove(&key) else {
                continue;
            };
            closed &= neighbors.len() == 2;
            for (neighbor, length) in neighbors {
                sum += length;
                next.push(neighbor);
            }
        }
        if closed {
            largest = largest.max(sum * 0.5);
        }
    }
    largest * 1000.0
}
