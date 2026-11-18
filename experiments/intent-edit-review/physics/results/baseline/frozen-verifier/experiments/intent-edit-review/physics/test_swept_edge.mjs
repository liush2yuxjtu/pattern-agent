import assert from 'node:assert/strict';
import {segmentClosest,sweptEdgeContact,prepareSweptEdgeContacts} from './swept-edge.mjs';

const near=(a,b,tolerance=1e-8)=>assert.ok(Math.abs(a-b)<=tolerance,`${a} != ${b}`);
const vsub=(a,b)=>a.map((x,k)=>x-b[k]);
const vdot=(a,b)=>a.reduce((s,x,k)=>s+x*b[k],0);
const lerp=(a,b,t)=>a.map((x,k)=>x+t*(b[k]-x));
const flat=p=>new Float64Array(p.flat());
const points=p=>Array.from({length:p.length/3},(_,i)=>Array.from(p.slice(i*3,i*3+3)));
let checks=0;
function check(name,fn){fn();checks++;console.log('PASS '+name);}

// Independent constrained quadratic minimization; no call to the CCD module's
// closest-point implementation or to any original contact solver.
function oracleDistance(A,B,C,D){
 const u=vsub(B,A),v=vsub(D,C),w=vsub(A,C),aa=vdot(u,u),bb=vdot(u,v),cc=vdot(v,v),dd=vdot(u,w),ee=vdot(v,w);
 const clamp=x=>Math.max(0,Math.min(1,x)),pairs=[];
 const add=(s,t)=>pairs.push(Math.hypot(...vsub(lerp(A,B,s),lerp(C,D,t))));
 add(0,cc>0?clamp(ee/cc):0);add(1,cc>0?clamp((bb+ee)/cc):0);
 add(aa>0?clamp(-dd/aa):0,0);add(aa>0?clamp((bb-dd)/aa):0,1);
 const det=aa*cc-bb*bb;
 if(det>1e-24){const s=(bb*ee-cc*dd)/det,t=(aa*ee-bb*dd)/det;if(s>=0&&s<=1&&t>=0&&t<=1)add(s,t);}
 return Math.min(...pairs);
}
function at(history,current,t){const old=points(history),next=points(current);return old.map((p,i)=>lerp(p,next[i],t));}
function hit(history,current,h,options={}){return sweptEdgeContact(history,current,0,1,2,3,h,options);}
const old=flat([[-.02,0,0],[.02,0,0],[0,-.02,.01],[0,.02,.01]]);
const next=flat([[-.02,0,0],[.02,0,0],[0,-.02,-.01],[0,.02,-.01]]);
const thickness=.003;

check('Interior edge crossing survives disjoint final separation of 10mm',()=>{
 assert.ok(oracleDistance(...points(next))>thickness);
 const c=hit(old,next,thickness);assert.ok(c);assert.ok(c.time<.5);near(c.time,.35,1e-8);near(c.u,.5);near(c.v,.5);
 assert.ok(c.normal[2]<-.999999);assert.ok(c.possibleInterval[0]<=.35);
 assert.ok(['contact','conservative','uncertain'].includes(c.status));
});
check('Actual two-triangle non-endpoint edges cross at t=.5',()=>{
 const h=flat([[-.02,0,0],[.02,0,0],[-.02,-.02,0],[0,-.02,.01],[0,.02,.01],[.02,.02,.01]]);
 const n=h.slice();n[11]=n[14]=n[17]=-.01;
 const c=sweptEdgeContact(h,n,0,1,3,4,thickness);assert.ok(c);near(c.time,.35,1e-8);near(c.u,.5);near(c.v,.5);
 near(oracleDistance(...at(h,n,.5).filter((_,i)=>[0,1,3,4].includes(i))),0);
});
check('Iteration exhaustion returns uncertain, never a silent miss',()=>{
 for(const maxIterations of [0,1,2]){const c=hit(old,next,thickness,{maxIterations});assert.ok(c);assert.equal(c.status,'uncertain');assert.equal(c.reason,'iteration-budget-exhausted');assert.equal(c.iterations,maxIterations);assert.ok(c.possibleInterval[0]<.35);}
});
check('Time-resolution exhaustion remains explicit uncertainty',()=>{
 const c=hit(old,next,thickness,{timeTolerance:1});assert.equal(c.status,'uncertain');assert.equal(c.reason,'time-resolution');
});
check('Finite-thickness grazing is retained',()=>{
 const h=flat([[0,0,0],[0,0,0],[-1,0,.003],[-1,0,.003]]);
 const n=flat([[0,0,0],[0,0,0],[1,0,.003],[1,0,.003]]);
 const c=hit(h,n,.003);assert.ok(c);assert.ok(c.time<=.5);assert.ok(c.possibleInterval[1]>=.5);
 near(oracleDistance(...at(h,n,.5)),.003,1e-12);
});
check('Stationary near, intersecting and far segments are distinguished',()=>{
 const nearP=flat([[-1,0,0],[1,0,0],[0,-1,.002],[0,1,.002]]);
 const nearC=hit(nearP,nearP,.003);assert.equal(nearC.status,'contact');assert.equal(nearC.time,0);
 const far=flat([[-1,0,0],[1,0,0],[0,-1,.01],[0,1,.01]]);assert.equal(hit(far,far,.003),null);
 const crossing=flat([[-1,0,0],[1,0,0],[0,-1,0],[0,1,0]]);const c=hit(crossing,crossing,.003);assert.ok(c.normalDefined);near(Math.hypot(...c.normal),1);
});
check('Degenerate edges and undefined coincident normals stay finite',()=>{
 const h=flat([[0,0,0],[0,0,0],[-1,0,0],[-1,0,0]]),n=h.slice();n[6]=n[9]=1;
 const c=hit(h,n,.001);assert.ok(c);near(c.time,.4995,1e-8);assert.ok(c.normal.every(Number.isFinite));
 const zero=flat([[0,0,0],[0,0,0],[0,0,0],[0,0,0]]),z=hit(zero,zero,0);assert.equal(z.status,'contact');assert.equal(z.normalDefined,false);assert.deepEqual(z.normal,[0,0,0]);
 const s=segmentClosest([0,0,0],[0,0,0],[-1,0,0],[1,0,0]);near(s.distance,0);near(s.v,.5);
});
check('Rotation and common translation preserve TOI and barycentrics',()=>{
 // This exact orthonormal Rodrigues matrix rotates about (0,.6,.8).
 const axis=[0,.6,.8],angle=.71,c=Math.cos(angle),s=Math.sin(angle);
 const R=p=>{const dot=vdot(p,axis),cross=[axis[1]*p[2]-axis[2]*p[1],axis[2]*p[0]-axis[0]*p[2],axis[0]*p[1]-axis[1]*p[0]];return p.map((x,k)=>c*x+s*cross[k]+(1-c)*dot*axis[k]);};
 const translation=[3.2,-7.4,11.8],transform=p=>R(p).map((x,k)=>x+translation[k]);
 const a=hit(old,next,thickness),b=hit(flat(points(old).map(transform)),flat(points(next).map(transform)),thickness);
 assert.ok(b);near(a.time,b.time,1e-8);near(a.u,b.u,1e-8);near(a.v,b.v,1e-8);R(a.normal).forEach((x,k)=>near(x,b.normal[k],1e-7));
});
check('Reversing an edge preserves geometry and complements u',()=>{
 const a=hit(old,next,thickness),b=sweptEdgeContact(old,next,1,0,2,3,thickness);near(a.time,b.time);near(1-a.u,b.u);near(a.v,b.v);
});
check('Splitting the same linear motion preserves the global first candidate',()=>{
 const midpoint=flat(at(old,next,.5)),a=hit(old,next,thickness),b=hit(old,midpoint,thickness);assert.ok(b);near(a.time,.5*b.time,1e-8);
});
check('Very narrow complete crossing is not missed by coarse final-state gates',()=>{
 const h=flat([[-1,0,0],[1,0,0],[0,-1,1],[0,1,1]]),n=h.slice();n[8]=n[11]=-1;
 const c=hit(h,n,1e-9);assert.ok(c);assert.ok(c.time<=.5);near(c.time,.5-5e-10,1e-8);
});
check('Near-parallel separation reports conditioning rather than false clearance',()=>{
 const h=flat([[0,0,0],[1,0,0],[0,1e-10,0],[1,-1e-10,0]]),c=hit(h,h,0);
 assert.ok(c);assert.ok(c.distance<=c.distanceUncertainty||c.status==='contact');
});
check('A grazing near-miss can be certified with sufficient iterations',()=>{
 const h=flat([[0,0,0],[0,0,0],[-1,0,.0035],[-1,0,.0035]]),n=h.slice();n[6]=n[9]=1;
 assert.equal(hit(h,n,.003,{maxIterations:4096}),null);
});
check('Rigid common translation of separated segments remains clear',()=>{
 const h=flat([[-1,0,0],[1,0,0],[0,-1,.01],[0,1,.01]]),n=Float64Array.from(h,(x,i)=>x+[2,-3,5][i%3]);
 assert.equal(hit(h,n,.003),null);
});
check('Finite huge-coordinate box distances do not overflow into false clearance',()=>{
 const h=flat([[0,0,0],[0,0,0],[1e200,0,0],[1e200,0,0]]);
 const c=hit(h,h,1e201);assert.ok(c);assert.equal(c.status,'contact');near(c.distance/1e200,1);
});
check('Invalid data or budgets are rejected explicitly',()=>{
 assert.throws(()=>hit(old,next,-1),RangeError);assert.throws(()=>hit(old,next,Infinity),RangeError);
 assert.throws(()=>hit(old,next,thickness,{maxIterations:-1}),RangeError);
 assert.throws(()=>hit(old,next,thickness,{timeTolerance:NaN}),RangeError);
 assert.throws(()=>sweptEdgeContact(old,next,0,1,2,99,thickness),RangeError);
 const broken=old.slice();broken[0]=NaN;assert.throws(()=>hit(broken,next,thickness),TypeError);
});
check('Prepared motion has identical results and owns immutable snapshots/results',()=>{
 const h=old.slice(),n=next.slice(),prepared=prepareSweptEdgeContacts(h,n,thickness);
 const reference=hit(h,n,thickness),actual=prepared(0,1,2,3),saved=structuredClone(actual);
 assert.deepEqual(actual,reference);assert.equal(prepared.vertexCount,4);
 prepared(1,0,3,2);assert.deepEqual(actual,saved);
 h.fill(10);n.fill(20);assert.deepEqual(prepared(0,1,2,3),reference);
 assert.throws(()=>prepared(-1,1,2,3),RangeError);
 const bad=old.slice();bad[0]=Infinity;assert.throws(()=>prepareSweptEdgeContacts(bad,next,thickness),TypeError);
});

let seed=0x4d395a21;
function random(){seed=(Math.imul(seed,1664525)+1013904223)>>>0;return seed/4294967296;}
check('Allocation-free closest kernel agrees exactly with the public feature routine',()=>{
 for(let trial=0;trial<600;trial++){
  const p=Array.from({length:4},()=>Array.from({length:3},()=>random()*2-1));
  if(trial%10===0)p[1]=p[0].slice();
  if(trial%13===0)p[3]=p[2].slice();
  if(trial%17===0){p[1]=[p[0][0]+1,p[0][1],p[0][2]];p[3]=[p[2][0]+1,p[2][1]+1e-10,p[2][2]];}
  const scale=Math.max(1,...p.flat().map(Math.abs)),padding=256*Number.EPSILON*scale;
  const classic=segmentClosest(...p,{distanceTolerance:padding}),data=flat(p),fast=hit(data,data,10);
  for(const key of ['u','v','distance','distanceLowerBound','distanceUncertainty','pointA','pointB'])assert.deepEqual(fast[key],classic[key],`Closest candidate ${trial}: ${key}`);
 }
});
// Keep the pre-optimization dense-time corpus unchanged when adding controls.
seed=0x4d395a21;
let sampledContacts=0,clearCases=0,uncertain=0,totalSamples=0;
check('Independent dense-time oracle detects no false-negative CCD results',()=>{
 for(let trial=0;trial<180;trial++){
  const h=flat(Array.from({length:4},()=>Array.from({length:3},()=>random()*2-1)));
  const n=Float64Array.from(h,x=>x+(random()*2-1)*1.2),radius=.08+(trial%5)*.02;
  let sampledMinimum=Infinity;
  for(let i=0;i<=2400;i++){sampledMinimum=Math.min(sampledMinimum,oracleDistance(...at(h,n,i/2400)));totalSamples++;}
  const c=hit(h,n,radius);
  assert.deepEqual(prepareSweptEdgeContacts(h,n,radius)(0,1,2,3),c,'Prepared and direct query disagree');
  if(sampledMinimum<=radius-1e-8){sampledContacts++;assert.ok(c,`False negative on trial ${trial}, min=${sampledMinimum}`);}
  if(c===null){clearCases++;assert.ok(sampledMinimum>radius-1e-8);}
  else{
   assert.ok(c.time>=0&&c.time<=1&&c.u>=0&&c.u<=1&&c.v>=0&&c.v<=1);
   assert.ok(c.normal.every(Number.isFinite));
   if(c.status==='contact')assert.ok(oracleDistance(...at(h,n,c.time))<=radius+1e-8);
   if(c.status==='uncertain')uncertain++;
  }
 }
 assert.ok(sampledContacts>10);assert.ok(clearCases>10);
});
console.log(JSON.stringify({verdict:'PASS',checks,independentTimeSamples:totalSamples,sampledContactCases:sampledContacts,certifiedClearCases:clearCases,explicitUncertainCases:uncertain,
 scope:'Pure arithmetic linear edge-edge CCD controls; no original solver, material, body or threshold changes. Uncertainty is retained, not counted as exact impact certification.'}));
