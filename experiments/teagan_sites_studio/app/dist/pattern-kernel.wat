(module
 (func (export "deform") (param $v f64) (param $base f64) (param $target f64) (result f64)
  local.get $v local.get $target f64.mul local.get $base f64.div)
 (func (export "delta") (param $target f64) (param $base f64) (result f64)
  local.get $target local.get $base f64.sub)
 (func (export "lerp") (param $a f64) (param $b f64) (param $t f64) (result f64)
  local.get $a local.get $b local.get $a f64.sub local.get $t f64.mul f64.add)
 (func $root (param $a f64) (param $b f64) (param $c f64) (result f64)
  local.get $a local.get $c f64.sub
  local.get $a local.get $c f64.sub f64.mul
  f64.const 4 local.get $b local.get $b f64.mul f64.mul f64.add f64.sqrt)
 (func (export "principal_max") (param $a f64) (param $b f64) (param $c f64) (result f64)
  f64.const 0 local.get $a local.get $c f64.add
  local.get $a local.get $b local.get $c call $root f64.add f64.const 2 f64.div f64.max f64.sqrt)
 (func (export "principal_min") (param $a f64) (param $b f64) (param $c f64) (result f64)
  f64.const 0 local.get $a local.get $c f64.add
  local.get $a local.get $b local.get $c call $root f64.sub f64.const 2 f64.div f64.max f64.sqrt)
)
