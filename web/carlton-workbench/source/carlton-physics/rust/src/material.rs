use crate::geometry::V;

#[derive(Clone, Copy)]
pub(crate) struct Material {
    pub eu: f32,
    pub ev: f32,
    pub shear: f32,
    pub poisson: f32,
    pub thickness: f32,
    pub density: f32,
}

impl Material {
    pub const WOVEN: Self = Self {
        eu: 200000.0,
        ev: 120000.0,
        shear: 30000.0,
        poisson: 0.2,
        thickness: 0.0005,
        density: 0.22,
    };
    pub fn moduli(self) -> (f32, f32, f32) {
        let den = 1.0 - self.poisson * self.poisson * self.ev / self.eu;
        (self.eu / den, self.ev / den, self.poisson * self.ev / den)
    }
    pub fn fields(self, u: V, v: V) -> [f32; 8] {
        let (c00, c11, c01) = (u.dot(u), v.dot(v), u.dot(v));
        let (e0, e1, e2) = ((c00 - 1.0) * 0.5, (c11 - 1.0) * 0.5, c01 * 0.5);
        let (q11, q22, q12) = self.moduli();
        let (s0, s1, s2) = (
            q11 * e0 + q12 * e1,
            q12 * e0 + q22 * e1,
            2.0 * self.shear * e2,
        );
        let jac = (c00 * c11 - c01 * c01).max(0.0).sqrt().max(1e-8);
        let tr = (s0 * c00 + s1 * c11 + 2.0 * s2 * c01) / jac;
        let disc = (tr * tr - 4.0 * (s0 * s1 - s2 * s2)).max(0.0).sqrt();
        let (p1, p2) = ((tr + disc) * 0.5, (tr - disc) * 0.5);
        let principal =
            ((c00 + c11 + ((c00 - c11).powi(2) + 4.0 * c01 * c01).sqrt()) * 0.5).sqrt() - 1.0;
        [
            principal,
            c00.sqrt() - 1.0,
            c11.sqrt() - 1.0,
            p1,
            (p1 * p1 + p2 * p2 - p1 * p2).max(0.0).sqrt(),
            e0,
            e1,
            e2,
        ]
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn rest_and_known_extension() {
        let material = Material::WOVEN;
        let v = V(0.0, 1.0, 0.0);
        assert_eq!(material.fields(V(1.0, 0.0, 0.0), v), [0.0; 8]);
        let result = material.fields(V(1.1, 0.0, 0.0), v);
        assert!((result[0] - 0.1).abs() < 1e-6);
        assert!((result[5] - 0.105).abs() < 1e-6);
        let reference = 1.1 * 200000.0 / (1.0 - 0.2 * 0.2 * 0.6) * 0.105;
        assert!((result[3] - reference).abs() < 0.05);
    }
}
