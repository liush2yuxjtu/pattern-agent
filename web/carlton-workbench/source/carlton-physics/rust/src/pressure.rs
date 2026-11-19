// Rust port of Pattern Agent web/cloth-lab/src/solver.c normal contact.
// Unilateral XPBD multiplier with an area-scaled virtual interface.
use crate::DT;

pub(crate) const NORMAL_STIFFNESS_PER_AREA: f32 = 1_000_000.0;

pub(crate) fn project(lambda: &mut f32, signed_gap: f32, inverse_mass: f32, area: f32) -> f32 {
    let compliance = if area > 0.0 {
        (NORMAL_STIFFNESS_PER_AREA * area * DT * DT).recip()
    } else {
        0.0
    };
    let old = *lambda;
    *lambda = (old + (-signed_gap - compliance * old) / (inverse_mass + compliance)).max(0.0);
    *lambda - old
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn normal_constraint_releases_and_matches_area_scaled_load() {
        let area = 0.02;
        let force = 2.0;
        let gap = -force / (area * NORMAL_STIFFNESS_PER_AREA);
        let mut lambda = force * DT * DT;
        assert!(project(&mut lambda, gap, 30.0, area).abs() < 1e-9);
        assert!((lambda / (DT * DT) / area - 100.0).abs() < 1e-4);
        assert!(project(&mut lambda, 0.01, 30.0, area) < 0.0);
        assert_eq!(lambda, 0.0);
        assert_eq!(project(&mut lambda, 0.01, 30.0, area), 0.0);
    }
}
