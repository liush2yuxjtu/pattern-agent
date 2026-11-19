import assert from 'node:assert/strict'
import {readFile} from 'node:fs/promises'

const binary=await readFile(new URL('rust/target/wasm32-unknown-unknown/release/cloth_lab_rust.wasm',import.meta.url))
async function coupon(cells,{distance=0.006,collision=true,steps=480}={}){
  const {instance:{exports:k}}=await WebAssembly.instantiate(binary)
  const floats=(ptr,n)=>new Float32Array(k.memory.buffer,k[ptr](),n)
  const ints=(ptr,n)=>new Int32Array(k.memory.buffer,k[ptr](),n)
  floats('body_ptr',12).set([-2,0,-2,-2,0,2,2,0,-2,2,0,2])
  floats('body_normal_ptr',12).set([0,1,0,0,1,0,0,1,0,0,1,0])
  ints('body_face_ptr',6).set([0,1,2,1,3,2])
  ints('body_order_ptr',2).set([0,1])
  floats('body_node_ptr',6).set([-2,0,-2,2,0,2])
  ints('body_node_ptr',10).set([-1,-1,0,2],6)
  k.configure_body(4,2,1)
  const nv=(cells+1)**2,nt=2*cells*cells
  const pos=floats('position_ptr',3*nv),rest=floats('uv_ptr',2*nv)
  const faces=[]
  for(let j=0;j<=cells;j++)for(let i=0;i<=cells;i++){
    const n=j*(cells+1)+i,x=(i/cells-.5)*.2,z=(j/cells-.5)*.2
    pos.set([x,distance,z],3*n)
    rest.set([x,z],2*n)
    if(i<cells&&j<cells)faces.push(n,n+cells+1,n+1,n+cells+1,n+cells+2,n+1)
  }
  ints('face_ptr',3*nt).set(faces)
  k.configure_material(550000,550000,90000,.22,.0013,.4)
  k.configure_cloth(nv,nt)
  k.finalize_seams()
  k.set_collision(Number(collision))
  k.step(steps,0)
  k.analyze()
  const forces=floats('pressure_force_ptr',nv)
  const area=floats('pressure_area_ptr',nv)
  const pressure=floats('pressure_ptr',nv)
  const total=forces.reduce((a,b)=>a+b,0)
  const mean=total/area.reduce((a,b)=>a+b,0)
  for(let i=0;i<nv;i++)assert.ok(Math.abs(pressure[i]*area[i]-forces[i])<1e-6)
  return {cells,steps,collision,total,mean}
}

const stationary=await Promise.all([coupon(3),coupon(6)])
for(const {total,mean} of stationary){
  assert.ok(Math.abs(mean-.4*9.81)<.025, 'gravity pressure: '+mean)
  assert.ok(Math.abs(total-.04*.4*9.81)<.001)
}
const separated=await coupon(3,{distance:.06,steps:3})
const off=await coupon(3,{collision:false,steps:10})
assert.equal(separated.total,0)
assert.equal(off.total,0)
console.log(JSON.stringify({verdict:'PASS',expectedPa:.4*9.81,stationary,separated,off},null,2))
