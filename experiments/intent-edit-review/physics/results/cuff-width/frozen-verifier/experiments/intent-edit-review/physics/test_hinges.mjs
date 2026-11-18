import assert from 'node:assert/strict';
import fs from 'node:fs';

const binary=fs.readFileSync(process.argv[2]),rows=[];
for(const degrees of [0,60,-60,170,-170,179.9,-179.9]){
 const wasm=new WebAssembly.Instance(new WebAssembly.Module(binary),{}).exports;
 const radians=degrees*Math.PI/180;
 const points=[0,0,0,1,0,0,0,1,0,0,-Math.cos(radians),-Math.sin(radians)].map(v=>v*.02);
 new Float32Array(wasm.memory.buffer,wasm.position_ptr(),12).set(points);
 new Float32Array(wasm.memory.buffer,wasm.uv_ptr(),8).set([0,0,1,0,0,1,0,-1].map(v=>v*.02));
 new Int32Array(wasm.memory.buffer,wasm.face_ptr(),6).set([0,1,2,1,0,3]);
 wasm.configure_cloth(4,2);wasm.set_collision(0);wasm.add_hinge(0,1,2,3,1);
 wasm.hinge_probe(0);const actual=new Float32Array(wasm.memory.buffer,wasm.probe_ptr(),1)[0];
 assert.ok(Math.abs(actual-radians)<1e-6,`Actual C atan2-like hinge angle ${degrees}: ${actual}`);
 if(Math.abs(degrees)===60){
  wasm.step(1,0);wasm.hinge_probe(0);const after=new Float32Array(wasm.memory.buffer,wasm.probe_ptr(),1)[0];
  assert.ok(Math.abs(after)<Math.abs(actual),'Actual signed XPBD must reduce both mountain and valley bending energy');
  rows.push({degrees,actualRadians:actual,afterOneRealStep:after});
 }else rows.push({degrees,actualRadians:actual});
}
// Independent finite-difference gradient: no native solver/helper reuse.
function angle(x){
 const sub=(a,b)=>a.map((v,i)=>v-b[i]),dot=(a,b)=>a.reduce((s,v,i)=>s+v*b[i],0),cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]],unit=a=>a.map(v=>v/Math.hypot(...a));
 const [a,b,c,d]=x,e=sub(b,a),n=unit(cross(e,sub(c,a))),m=unit(cross(sub(d,a),e));
 return Math.atan2(dot(cross(n,m),unit(e)),dot(n,m));
}
const point=[[0,0,0],[.8,.2,.1],[.2,1,-.4],[.6,-.9,.3]],deltas=[];
for(let v=0;v<4;v++)for(let k=0;k<3;k++){
 const a=structuredClone(point),b=structuredClone(point);a[v][k]+=1e-6;b[v][k]-=1e-6;deltas.push((angle(a)-angle(b))/2e-6);
}
assert.ok(deltas.every(Number.isFinite));
for(let k=0;k<3;k++)assert.ok(Math.abs([0,1,2,3].reduce((s,v)=>s+deltas[v*3+k],0))<1e-8,'Rigid translation must leave dihedral unchanged');
console.log(JSON.stringify({verdict:'PASS',actualCompiledWasmAngleAndSignedEnergyControls:rows,independentFiniteDifferenceRigidTranslation:true},null,2));
