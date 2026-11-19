(module
  (func (export "principal_max") (param f64 f64 f64) (result f64) (f64.sqrt (f64.max (f64.const 0) (f64.mul (f64.const 0.5) (f64.add (f64.add (local.get 0) (local.get 2)) (f64.sqrt (f64.add (f64.mul (f64.sub (local.get 0) (local.get 2)) (f64.sub (local.get 0) (local.get 2))) (f64.mul (f64.const 4) (f64.mul (local.get 1) (local.get 1))))))))))
  (func (export "principal_min") (param f64 f64 f64 f64) (result f64) (f64.sqrt (f64.max (f64.const 0) (f64.div (local.get 3) (f64.max (f64.const 1e-300) (f64.mul (f64.const 0.5) (f64.add (f64.add (local.get 0) (local.get 2)) (f64.sqrt (f64.add (f64.mul (f64.sub (local.get 0) (local.get 2)) (f64.sub (local.get 0) (local.get 2))) (f64.mul (f64.const 4) (f64.mul (local.get 1) (local.get 1))))))))))))
  (func (export "green_normal") (param f64) (result f64) (f64.mul (f64.const 0.5) (f64.sub (local.get 0) (f64.const 1))))
  (func (export "plane_stress") (param f64 f64 f64 f64) (result f64) (f64.mul (f64.div (local.get 2) (f64.sub (f64.const 1) (f64.mul (local.get 3) (local.get 3)))) (f64.add (local.get 0) (f64.mul (local.get 3) (local.get 1)))))
  (func (export "shear_stress") (param f64 f64 f64) (result f64) (f64.mul (f64.div (local.get 1) (f64.add (f64.const 1) (local.get 2))) (local.get 0)))
)
