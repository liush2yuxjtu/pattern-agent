use std::ops::{Add, Mul, Sub};

#[repr(C)]
#[derive(Clone, Copy, Default, Debug)]
pub(crate) struct V(pub f32, pub f32, pub f32);

impl V {
    pub const ZERO: Self = Self(0.0, 0.0, 0.0);
    pub fn dot(self, rhs: Self) -> f32 {
        self.0 * rhs.0 + self.1 * rhs.1 + self.2 * rhs.2
    }
    pub fn cross(self, rhs: Self) -> Self {
        Self(
            self.1 * rhs.2 - self.2 * rhs.1,
            self.2 * rhs.0 - self.0 * rhs.2,
            self.0 * rhs.1 - self.1 * rhs.0,
        )
    }
    pub fn len(self) -> f32 {
        self.dot(self).sqrt()
    }
    pub fn unit(self) -> Self {
        self * self.len().max(1e-12).recip()
    }
    pub fn finite(self) -> bool {
        self.0.is_finite() && self.1.is_finite() && self.2.is_finite()
    }
}

impl Add for V {
    type Output = Self;
    fn add(self, rhs: Self) -> Self {
        Self(self.0 + rhs.0, self.1 + rhs.1, self.2 + rhs.2)
    }
}
impl Sub for V {
    type Output = Self;
    fn sub(self, rhs: Self) -> Self {
        Self(self.0 - rhs.0, self.1 - rhs.1, self.2 - rhs.2)
    }
}
impl Mul<f32> for V {
    type Output = Self;
    fn mul(self, s: f32) -> Self {
        Self(self.0 * s, self.1 * s, self.2 * s)
    }
}

#[repr(C)]
#[derive(Clone, Copy)]
pub(crate) struct Node {
    lo: [f32; 3],
    hi: [f32; 3],
    left: i32,
    right: i32,
    start: i32,
    count: i32,
}

impl Node {
    pub const EMPTY: Self = Self {
        lo: [0.0; 3],
        hi: [0.0; 3],
        left: 0,
        right: 0,
        start: 0,
        count: 0,
    };
    fn distance(self, p: V) -> f32 {
        [p.0, p.1, p.2]
            .into_iter()
            .enumerate()
            .map(|(i, x)| {
                let d = 0.0_f32.max((self.lo[i] - x).max(x - self.hi[i]));
                d * d
            })
            .sum()
    }
    pub fn scale(&mut self, sx: f32, sy: f32, sz: f32) {
        for (i, scale) in [sx, sy, sz].into_iter().enumerate() {
            self.lo[i] *= scale;
            self.hi[i] *= scale;
        }
    }
}

#[derive(Clone, Copy)]
pub(crate) struct Hit {
    pub q: V,
    pub n: V,
    pub distance: f32,
}

// 最近点与重心坐标采用 Ericson 的三角形区域测试。
pub(crate) fn closest(p: V, a: V, b: V, c: V) -> (V, f32, f32) {
    let ab = b - a;
    let ac = c - a;
    let ap = p - a;
    let d1 = ab.dot(ap);
    let d2 = ac.dot(ap);
    if d1 <= 0.0 && d2 <= 0.0 {
        return (a, 0.0, 0.0);
    }
    let bp = p - b;
    let d3 = ab.dot(bp);
    let d4 = ac.dot(bp);
    if d3 >= 0.0 && d4 <= d3 {
        return (b, 1.0, 0.0);
    }
    let vc = d1 * d4 - d3 * d2;
    if vc <= 0.0 && d1 >= 0.0 && d3 <= 0.0 {
        let u = d1 / (d1 - d3);
        return (a + ab * u, u, 0.0);
    }
    let cp = p - c;
    let d5 = ab.dot(cp);
    let d6 = ac.dot(cp);
    if d6 >= 0.0 && d5 <= d6 {
        return (c, 0.0, 1.0);
    }
    let vb = d5 * d2 - d1 * d6;
    if vb <= 0.0 && d2 >= 0.0 && d6 <= 0.0 {
        let v = d2 / (d2 - d6);
        return (a + ac * v, 0.0, v);
    }
    let va = d3 * d6 - d5 * d4;
    if va <= 0.0 && d4 >= d3 && d5 >= d6 {
        let v = (d4 - d3) / ((d4 - d3) + (d5 - d6));
        return (b + (c - b) * v, 1.0 - v, v);
    }
    let inv = (va + vb + vc).recip();
    let (u, v) = (vb * inv, vc * inv);
    (a + (ab * u + ac * v), u, v)
}

pub(crate) struct Body<'a> {
    pub vertices: &'a [V],
    pub normals: &'a [V],
    pub faces: &'a [[i32; 3]],
    pub order: &'a [i32],
    pub nodes: &'a [Node],
    pub offset: f32,
}

impl Body<'_> {
    pub fn nearest(&self, p: V) -> Hit {
        if self.nodes.is_empty() || self.faces.is_empty() {
            return Hit {
                q: p,
                n: V::ZERO,
                distance: 1e6,
            };
        }
        let p = p - V(self.offset, 0.0, 0.0);
        let mut best = f32::INFINITY;
        let mut found = (0, V::ZERO, 0.0, 0.0);
        let mut stack = [0; 64];
        let mut depth = 1;
        while depth > 0 {
            depth -= 1;
            let node = self.nodes[stack[depth]];
            if node.distance(p) > best {
                continue;
            }
            if node.count > 0 {
                for &index in &self.order[node.start as usize..(node.start + node.count) as usize] {
                    let face = self.faces[index as usize].map(|v| self.vertices[v as usize]);
                    let (q, u, v) = closest(p, face[0], face[1], face[2]);
                    let delta = p - q;
                    let d = delta.dot(delta);
                    if d < best {
                        best = d;
                        found = (index as usize, q, u, v);
                    }
                }
            } else {
                let a = node.left as usize;
                let b = node.right as usize;
                let da = self.nodes[a].distance(p);
                let db = self.nodes[b].distance(p);
                let ordered = if da < db {
                    [(b, db), (a, da)]
                } else {
                    [(a, da), (b, db)]
                };
                for (child, d) in ordered {
                    if d <= best {
                        stack[depth] = child;
                        depth += 1;
                    }
                }
            }
        }
        let (face, q, u, v) = found;
        let [a, b, c] = self.faces[face].map(|i| self.normals[i as usize]);
        let normal = (a * (1.0 - u - v) + (b * u + c * v)).unit();
        let sign = if (p - q).dot(normal) < 0.0 { -1.0 } else { 1.0 };
        Hit {
            q: q + V(self.offset, 0.0, 0.0),
            n: normal,
            distance: best.sqrt() * sign,
        }
    }
}

pub(crate) fn fold(a: V, b: V, c: V, d: V) -> f32 {
    let edge = b - a;
    let n1 = edge.cross(c - a);
    let n2 = (d - a).cross(edge);
    if n1.len().min(n2.len()) < 1e-12 {
        return 0.0;
    }
    n1.cross(n2).len().atan2(n1.dot(n2)).to_degrees()
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn fold_flat_and_right_angle() {
        let a = V::ZERO;
        let b = V(1.0, 0.0, 0.0);
        let c = V(0.0, 1.0, 0.0);
        assert_eq!(fold(a, b, c, V(0.0, -1.0, 0.0)), 0.0);
        assert!((fold(a, b, c, V(0.0, 0.0, 1.0)) - 90.0).abs() < 1e-5);
    }
    #[test]
    fn body_signed_distances() {
        let body = Body {
            vertices: &[V::ZERO, V(1.0, 0.0, 0.0), V(0.0, 1.0, 0.0)],
            normals: &[V(0.0, 0.0, 1.0); 3],
            faces: &[[0, 1, 2]],
            order: &[0],
            nodes: &[Node {
                count: 1,
                ..Node::EMPTY
            }],
            offset: 2.0,
        };
        let outside = body.nearest(V(2.25, 0.25, 0.4));
        let inside = body.nearest(V(2.25, 0.25, -0.4));
        assert!((outside.distance - 0.4).abs() < 1e-6);
        assert!((inside.distance + 0.4).abs() < 1e-6);
        assert!((inside.q.0 - 2.25).abs() < 1e-6);
    }
}
