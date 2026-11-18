import assert from 'node:assert/strict';
import {WaistRing} from './source/waist-ring.js';
const n=32,rest=new Float64Array(n*3),inv=new Float64Array(n);
for(let i=0;i<n;i++){const a=2*Math.PI*i/n;rest.set([.13*Math.cos(a),.3,.09*Math.sin(a)],i*3);inv[i]=2+i*.13;}
let length=0;for(let i=0;i<n;i++){const j=(i+1)%n;length+=Math.hypot(...[0,1,2].map(k=>rest[i*3+k]-rest[j*3+k]));}
const ring=new WaistRing(rest,inv,n,length);
// Non-axis-aligned rotation with an arbitrary translation: no world pose target.
const axis=[1,2,3].map(x=>x/Math.sqrt(14)),angle=1.1,c=Math.cos(angle),s=Math.sin(angle),[x,y,z]=axis;
const r=[c+x*x*(1-c),x*y*(1-c)-z*s,x*z*(1-c)+y*s,y*x*(1-c)+z*s,c+y*y*(1-c),y*z*(1-c)-x*s,z*x*(1-c)-y*s,z*y*(1-c)+x*s,c+z*z*(1-c)];
const rigid=new Float64Array(n*3);for(let i=0;i<n;i++)for(let k=0;k<3;k++)rigid[i*3+k]=[2,-3,7][k]+r[k*3]*rest[i*3]+r[k*3+1]*rest[i*3+1]+r[k*3+2]*rest[i*3+2];
const before=rigid.slice();ring.solve(rigid);const poseError=Math.max(...rigid.map((v,i)=>Math.abs(v-before[i])));assert(poseError<1e-11);
rigid[4]+=.025;rigid[19]-=.03;const deformed=rigid.slice(),center=ring.center(deformed);ring.solve(rigid);const centroidError=Math.max(...ring.center(rigid).map((v,i)=>Math.abs(v-center[i])));assert(centroidError<1e-12);
const force=[0,0,0],torque=[0,0,0];for(let i=0;i<n;i++){const p=[0,1,2].map(k=>deformed[i*3+k]-center[k]),d=[0,1,2].map(k=>(rigid[i*3+k]-deformed[i*3+k])/inv[i]);for(let k=0;k<3;k++)force[k]+=d[k];torque[0]+=p[1]*d[2]-p[2]*d[1];torque[1]+=p[2]*d[0]-p[0]*d[2];torque[2]+=p[0]*d[1]-p[1]*d[0];}
assert(Math.hypot(...force)<1e-12);assert(Math.hypot(...torque)<1e-12);
let distances=0;for(let i=0;i<n;i++)for(let j=0;j<n;j++){const dist=p=>Math.hypot(...[0,1,2].map(k=>p[i*3+k]-p[j*3+k]));distances=Math.max(distances,Math.abs(dist(rest)-dist(rigid)));}assert(distances<1e-11);
const broken=inv.slice();broken[0]=0;assert.throws(()=>new WaistRing(rest,broken,n,length),/no pins/);
console.log(JSON.stringify({verdict:'PASS',nonAxisRigidMotionError_m:poseError,massCentroidError_m:centroidError,netInternalPositionImpulse:force,netInternalTorque:torque,pairDistanceError_m:distances,zeroInverseMassRejected:true}));
