import assert from 'node:assert/strict';
import {pointTriangleClosest,sweptVertexContact,prepareSweptVertexContacts} from './swept-vertex.mjs';
const near=(a,b,tolerance=1e-8)=>assert.ok(Math.abs(a-b)<=tolerance,`${a} != ${b}`);
const sub=(a,b)=>a.map((x,k)=>x-b[k]),dot=(a,b)=>a.reduce((sum,x,k)=>sum+x*b[k],0),cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
const lerp=(a,b,t)=>a.map((x,k)=>x+t*(b[k]-x)),flat=points=>Float64Array.from(points.flat()),points=data=>Array.from({length:data.length/3},(_,id)=>Array.from(data.slice(id*3,id*3+3)));
const at=(history,current,t)=>points(history).map((p,i)=>lerp(p,points(current)[i],t));
let checks=0;const check=(name,fn)=>{fn();checks++;console.log('PASS '+name);};

// Independent Ericson Voronoi-region construction. The CCD module instead
// enumerates boundary projections and an admissible normalized plane solve.
// This oracle does not import any production closest-point or contact code.
function oracleClosest(p,a,b,c){
 const ab=sub(b,a),ac=sub(c,a),ap=sub(p,a),n=cross(ab,ac);
 if(Math.hypot(...n)<1e-20){
  const candidates=[];for(const [u,v] of [[a,b],[b,c],[c,a]]){const e=sub(v,u),den=dot(e,e),t=den>0?Math.max(0,Math.min(1,dot(sub(p,u),e)/den)):0;candidates.push(lerp(u,v,t));}
  candidates.sort((x,y)=>Math.hypot(...sub(p,x))-Math.hypot(...sub(p,y)));return candidates[0];
 }
 const d1=dot(ab,ap),d2=dot(ac,ap);if(d1<=0&&d2<=0)return a;
 const bp=sub(p,b),d3=dot(ab,bp),d4=dot(ac,bp);if(d3>=0&&d4<=d3)return b;
 const vc=d1*d4-d3*d2;if(vc<=0&&d1>=0&&d3<=0)return lerp(a,b,d1/(d1-d3));
 const cp=sub(p,c),d5=dot(ab,cp),d6=dot(ac,cp);if(d6>=0&&d5<=d6)return c;
 const vb=d5*d2-d1*d6;if(vb<=0&&d2>=0&&d6<=0)return lerp(a,c,d2/(d2-d6));
 const va=d3*d6-d5*d4;if(va<=0&&(d4-d3)>=0&&(d5-d6)>=0)return lerp(b,c,(d4-d3)/((d4-d3)+(d5-d6)));
 const denominator=1/(va+vb+vc),v=vb*denominator,w=vc*denominator;return a.map((x,k)=>x+v*ab[k]+w*ac[k]);
}
const oracleDistance=(...p)=>Math.hypot(...sub(p[0],oracleClosest(...p)));
const hit=(history,current,h,options={})=>sweptVertexContact(history,current,0,1,2,3,h,options);
const triangle=[[-.02,-.02,0],[.02,-.02,0],[0,.02,0]],h=.001;
const history=flat([[0,0,.01],...triangle]),current=flat([[0,0,-.01],...triangle]);
function oldPlaneCandidate(old,next){
 const A=points(old),B=points(next),normal=t=>{const n=cross(sub(t[2],t[1]),sub(t[3],t[1])),length=Math.hypot(...n);return n.map(x=>x/length);};
 const n0=normal(A),n1=normal(B),d0=dot(sub(A[0],A[1]),n0),d1=dot(sub(B[0],B[1]),n1);if(!(d0*d1<0&&Math.abs(d0)>1e-6&&Math.abs(d1)>1e-6))return null;
 const time=d0/(d0-d1),p=at(old,next,time),u=sub(p[2],p[1]),v=sub(p[3],p[1]),w=sub(p[0],p[1]),uu=dot(u,u),uv=dot(u,v),vv=dot(v,v),wu=dot(w,u),wv=dot(w,v),den=uu*vv-uv*uv;
 if(!(Math.abs(den)>1e-30))return null;
 const beta=(vv*wu-uv*wv)/den,gamma=(uu*wv-uv*wu)/den,barycentric=[1-beta-gamma,beta,gamma];
 return Math.min(...barycentric)>=-1e-4?{time,barycentric,d0,d1}:null;
}

check('Closest closed triangle includes face, edge and vertex regions',()=>{
 const face=pointTriangleClosest([0,0,.01],...triangle);near(face.distance,.01,1e-14);face.barycentric.forEach((x,i)=>near(x,[.25,.25,.5][i],1e-14));assert.equal(face.feature,'face');
 const edge=pointTriangleClosest([0,-.03,.01],...triangle);near(edge.distance,Math.SQRT2*.01,1e-14);assert.equal(edge.feature,'edge');near(edge.barycentric[2],0);
 const vertex=pointTriangleClosest([.03,-.02,.01],...triangle);near(vertex.distance,Math.SQRT2*.01,1e-14);assert.equal(vertex.feature,'vertex');assert.deepEqual(vertex.barycentric,[0,1,0]);
});
check('Moving point crossing survives disjoint final separation',()=>{
 assert.ok(oracleDistance(...points(current))>h);
 const candidate=hit(history,current,h);assert.ok(candidate);near(candidate.time,.45,1e-8);assert.ok(candidate.time<=.45);candidate.barycentric.forEach((x,i)=>near(x,[.25,.25,.5][i]));assert.ok(candidate.normal[2]>.999999);
 assert.ok(['contact','conservative','uncertain'].includes(candidate.status));assert.ok(candidate.possibleInterval[0]<=.45&&candidate.possibleInterval[1]>=.45);
});
check('Stationary query and translating moving face use relative motion',()=>{
 const old=flat([[0,0,0],...triangle.map(p=>[p[0],p[1],.01])]),next=flat([[0,0,0],...triangle.map(p=>[p[0],p[1],-.01])]);
 const candidate=hit(old,next,h);assert.ok(candidate);near(candidate.time,.45,1e-8);assert.ok(candidate.normal[2]<-.999999);near(candidate.speedBound,.02,1e-12);
});
const rotatingOld=flat([[.008817055542021989,-.055213719920720904,-.03174084203783423],[-.05,-.04,0],[.06,-.04,0],[-.01,.07,0]]);
const rotatingNext=flat([[.008817055542021989,-.055213719920720904,-.03174084203783423],[.05271196444241748,-.08336831998158956,-.016846143650741927],[-.04055192237700857,-.036714991086920376,.018158346323818637],[.019590891453291417,.0006222748808677389,-.09133489782678875]]);
let rotatingDenseMinimum=Infinity;
check('Rotating plane linear-root false positive is rejected geometrically',()=>{
 const old=oldPlaneCandidate(rotatingOld,rotatingNext);assert.ok(old);near(old.time,.7231723204886334,1e-12);
 assert.ok(oracleDistance(...at(rotatingOld,rotatingNext,old.time))>.015);
 for(let sample=0;sample<=10000;sample++)rotatingDenseMinimum=Math.min(rotatingDenseMinimum,oracleDistance(...at(rotatingOld,rotatingNext,sample/10000)));
 assert.ok(rotatingDenseMinimum>.012);assert.equal(hit(rotatingOld,rotatingNext,h),null);
});
check('A plane crossing outside the actual triangle remains clear',()=>{
 const old=history.slice(),next=current.slice();old[0]=next[0]=.2;old[1]=next[1]=.2;
 assert.equal(oldPlaneCandidate(old,next),null);assert.equal(hit(old,next,h),null);
});
let actual31DenseMinimum=Infinity;
check('Actual run31 old accepted VF root is a reproducible false constraint',()=>{
 // Frozen run31 step5/cycle1, welded IDs [2466,2585,2586,2593].
 const old=flat([[-.2987572252750397,1.1799238920211792,.06192060559988022],[-.2989208400249481,1.1677119731903076,.06053758040070534],[-.2946036756038666,1.1649284362792969,.05957407504320145],[-.31425657868385315,1.182337760925293,.061802174896001816]]);
 const next=flat([[-.2986937463283539,1.179694652557373,.061936695128679276],[-.297883003950119,1.1701725721359253,.057530030608177185],[-.2930229902267456,1.1633292436599731,.06344223022460938],[-.31262263655662537,1.1813430786132812,.062375035136938095]]);
 const root=oldPlaneCandidate(old,next);assert.ok(root);near(root.time,.43340629852844414,1e-12);assert.ok(oracleDistance(...at(old,next,root.time))>.0083);
 for(let sample=0;sample<=10000;sample++)actual31DenseMinimum=Math.min(actual31DenseMinimum,oracleDistance(...at(old,next,sample/10000)));
 assert.ok(actual31DenseMinimum>.0075);assert.equal(hit(old,next,h),null);
});
check('Finite-thickness edge and vertex approaches retain true barycentrics',()=>{
 const edgeOld=flat([[0,-.04,.0005],...triangle]),edgeNext=flat([[0,0,.0005],...triangle]),edge=hit(edgeOld,edgeNext,h);
 const edgeTime=(.02-Math.sqrt(h*h-.0005**2))/.04;assert.ok(edge);near(edge.time,edgeTime,1e-8);assert.equal(edge.feature,'edge');near(edge.barycentric[0],.5);near(edge.barycentric[1],.5);near(edge.barycentric[2],0);
 const vertexOld=flat([[-.04,-.02,.0005],...triangle]),vertexNext=flat([[-.015,-.02,.0005],...triangle]),vertex=hit(vertexOld,vertexNext,h);
 assert.ok(vertex);near(vertex.time,(.02-Math.sqrt(h*h-.0005**2))/.025,1e-8);assert.equal(vertex.feature,'vertex');assert.deepEqual(vertex.barycentric,[1,0,0]);
});
check('Tangent finite-thickness contact is retained as unresolved or contact',()=>{
 const d=h/Math.SQRT2,tri=[[0,0,0],[.02,0,0],[0,.02,0]],old=flat([[-.02-d,.02-d,0],...tri]),next=flat([[.02-d,-.02-d,0],...tri]);
 near(oracleDistance(...at(old,next,.5)),h,1e-12);const candidate=hit(old,next,h);assert.ok(candidate);assert.ok(candidate.time<=.5);assert.ok(candidate.possibleInterval[1]>=.5);
});
check('Degenerate triangles and zero-distance normal fallbacks stay finite',()=>{
 const old=flat([[-.01,0,0],[0,0,0],[0,0,0],[0,0,0]]),next=old.slice();next[0]=.01;
 const candidate=hit(old,next,h);assert.ok(candidate);near(candidate.time,.45,1e-8);assert.ok(candidate.normal.every(Number.isFinite));assert.equal(candidate.faceNormalDefined,false);
 const line=pointTriangleClosest([.5,.01,0],[0,0,0],[1,0,0],[2,0,0]);near(line.distance,.01);near(line.pointTriangle[0],.5);
 const onFace=flat([[0,0,0],...triangle]),face=hit(onFace,onFace,0);assert.equal(face.status,'contact');assert.equal(face.normalSource,'face-normal');assert.ok(face.normal[2]>.999999);
 const zero=flat(Array(4).fill([0,0,0])),undefinedNormal=hit(zero,zero,0);assert.equal(undefinedNormal.status,'contact');assert.equal(undefinedNormal.normalDefined,false);assert.deepEqual(undefinedNormal.normal,[0,0,0]);
});
check('Face collapse during the interval cannot authorize false clearance',()=>{
 const old=flat([[0,0,0],[-.02,-.02,.01],[.02,-.02,.01],[0,.02,.01]]),next=flat([[0,0,0],[.02,.02,-.01],[-.02,.02,-.01],[0,-.02,-.01]]);
 near(oracleDistance(...at(old,next,.5)),0,1e-12);const candidate=hit(old,next,h);assert.ok(candidate);assert.ok(candidate.time<=.5);
});
check('Iteration/time exhaustion is explicit, never a silent miss',()=>{
 for(const maxIterations of [0,1,2]){const candidate=hit(history,current,h,{maxIterations});assert.ok(candidate);assert.equal(candidate.status,'uncertain');assert.equal(candidate.reason,'iteration-budget-exhausted');assert.equal(candidate.iterations,maxIterations);}
 const resolution=hit(history,current,h,{timeTolerance:1});assert.equal(resolution.status,'uncertain');assert.equal(resolution.reason,'time-resolution');
});
check('Stationary near/far geometry and common rigid translation are distinguished',()=>{
 const nearData=history.slice();nearData[2]=.0005;assert.equal(hit(nearData,nearData,h).status,'contact');assert.equal(hit(history,history,h),null);
 const translated=Float64Array.from(history,(x,i)=>x+[2,-3,5][i%3]);assert.equal(hit(history,translated,h),null);
});
check('Narrow crossing is retained without endpoint distance gating',()=>{
 const old=history.slice(),next=current.slice();old[2]=1;next[2]=-1;const candidate=hit(old,next,1e-9);assert.ok(candidate);assert.ok(candidate.time<=.5);near(candidate.time,.5-5e-10,1e-8);
});
check('Rigid frame transforms and consistent length scales preserve geometry',()=>{
 const axis=[0,.6,.8],angle=.71,co=Math.cos(angle),si=Math.sin(angle),R=p=>{const n=cross(axis,p),d=dot(axis,p);return p.map((x,k)=>co*x+si*n[k]+(1-co)*d*axis[k]);};
 const translated=p=>R(p).map((x,k)=>x+[3.2,-7.4,11.8][k]),base=hit(history,current,h),transformed=hit(flat(points(history).map(translated)),flat(points(current).map(translated)),h);
 assert.ok(transformed);near(base.time,transformed.time,1e-8);base.barycentric.forEach((x,i)=>near(x,transformed.barycentric[i],1e-8));R(base.normal).forEach((x,k)=>near(x,transformed.normal[k],1e-7));
 const scaled=hit(Float64Array.from(history,x=>x*1000),Float64Array.from(current,x=>x*1000),h*1000);near(base.time,scaled.time,1e-8);near(base.speedBound*1000,scaled.speedBound,1e-10);
 const commonVelocity=[.7,-1.3,2.1],moving=Float64Array.from(current,(x,i)=>x+commonVelocity[i%3]),relative=hit(history,moving,h);near(base.time,relative.time,1e-8);near(base.speedBound,relative.speedBound,1e-12);
});
check('Triangle permutations and split linear intervals preserve candidates',()=>{
 const a=hit(history,current,h),b=sweptVertexContact(history,current,0,3,2,1,h);near(a.time,b.time);a.barycentric.forEach((x,i)=>near(x,b.barycentric[2-i]));
 const midpoint=flat(at(history,current,.5)),half=hit(history,midpoint,h);near(a.time,.5*half.time,1e-8);
});
check('Near-degenerate feature conditioning remains explicit uncertainty',()=>{
 const A=[0,0,0],B=[1,1,1],C=[.5+1e-10,.5-1e-10,.5],N=cross(sub(B,A),sub(C,A)),length=Math.hypot(...N),unit=N.map(x=>x/length),center=A.map((_,k)=>(A[k]+B[k]+C[k])/3),P=center.map((x,k)=>x+unit[k]*(h+5e-11)),data=flat([P,A,B,C]);
 const closest=pointTriangleClosest(P,A,B,C);assert.ok(closest.conditioningAllowance>0);const candidate=hit(data,data,h);assert.ok(candidate);assert.equal(candidate.status,'uncertain');assert.equal(candidate.reason,'closest-feature-conditioning');
});
check('Huge finite distances stay finite and invalid input is rejected',()=>{
 const huge=flat([[1e200,0,0],[0,0,0],[0,0,0],[0,0,0]]),candidate=hit(huge,huge,1e201);assert.equal(candidate.status,'contact');near(candidate.distance/1e200,1);
 assert.throws(()=>hit(history,current,-1),RangeError);assert.throws(()=>hit(history,current,Infinity),RangeError);assert.throws(()=>hit(history,current,h,{maxIterations:-1}),RangeError);assert.throws(()=>hit(history,current,h,{maxIterations:null}),RangeError);assert.throws(()=>hit(history,current,h,{timeTolerance:NaN}),RangeError);
 assert.throws(()=>sweptVertexContact(history,current,99,1,2,3,h),RangeError);const broken=history.slice();broken[0]=NaN;assert.throws(()=>hit(broken,current,h),TypeError);
});
check('Prepared queries own immutable snapshots and independent result records',()=>{
 const old=history.slice(),next=current.slice(),query=prepareSweptVertexContacts(old,next,h),reference=hit(old,next,h),candidate=query(0,1,2,3),saved=structuredClone(candidate);
 assert.deepEqual(candidate,reference);assert.equal(query.vertexCount,4);query(0,3,2,1);assert.deepEqual(candidate,saved);old.fill(10);next.fill(20);assert.deepEqual(query(0,1,2,3),reference);
 assert.throws(()=>query(-1,1,2,3),RangeError);const bad=history.slice();bad[0]=Infinity;assert.throws(()=>prepareSweptVertexContacts(bad,current,h),TypeError);
});
let seed=0x519bc270;const random=()=>((seed=(Math.imul(seed,1664525)+1013904223)>>>0)/4294967296);
check('Closest kernel agrees with independent region oracle on static geometry',()=>{
 for(let trial=0;trial<600;trial++){
  const p=Array.from({length:4},()=>Array.from({length:3},()=>random()*2-1));if(trial%11===0)p[2]=p[1].slice();if(trial%17===0)p[3]=p[1].slice();
  const value=pointTriangleClosest(...p),reference=oracleClosest(...p);near(value.distance,oracleDistance(...p),1e-11);value.pointTriangle.forEach((x,k)=>near(x,reference[k],1e-10));
  const data=flat(p),padding=256*Number.EPSILON*Math.max(1,...data.map(Math.abs)),publicValue=pointTriangleClosest(...p,{distanceTolerance:padding}),prepared=hit(data,data,10);
  for(const key of ['barycentric','weights','point','pointTriangle','distance','distanceLowerBound','distanceUncertainty','feature','faceNormal'])assert.deepEqual(prepared[key],publicValue[key],`${trial}:${key}`);
 }
});
let sampledContacts=0,clearCases=0,uncertain=0,samples=0;
check('Independent dense-time sampling observes no false-negative CCD result',()=>{
 for(let trial=0;trial<180;trial++){
  const old=flat(Array.from({length:4},()=>Array.from({length:3},()=>random()*2-1))),next=Float64Array.from(old,x=>x+(random()*2-1)*1.2),radius=.08+(trial%5)*.02;
  const candidate=hit(old,next,radius);assert.deepEqual(prepareSweptVertexContacts(old,next,radius)(0,1,2,3),candidate);
  let minimum=Infinity,firstContactSample=Infinity;
  for(let i=0;i<=2400;i++){const value=oracleDistance(...at(old,next,i/2400));samples++;minimum=Math.min(minimum,value);if(value<=radius-1e-8)firstContactSample=Math.min(firstContactSample,i/2400);}
  if(minimum<=radius-1e-8){sampledContacts++;assert.ok(candidate,`False negative ${trial}: ${minimum}`);assert.ok(candidate.time<=firstContactSample+1e-8,'Candidate follows an independently sampled earlier contact');}
  if(candidate===null){clearCases++;assert.ok(minimum>radius-1e-8);}else{
   assert.ok(candidate.time>=0&&candidate.time<=1);assert.ok(candidate.barycentric.every(w=>w>=0&&w<=1));near(candidate.barycentric.reduce((a,b)=>a+b,0),1,1e-12);assert.ok(candidate.normal.every(Number.isFinite));
   if(candidate.status==='contact')assert.ok(oracleDistance(...at(old,next,candidate.time))<=radius+1e-8);if(candidate.status==='uncertain')uncertain++;
   const p=at(old,next,candidate.time),q=[0,1,2].map(k=>candidate.barycentric.reduce((sum,w,j)=>sum+w*p[j+1][k],0));q.forEach((x,k)=>near(x,candidate.pointTriangle[k],1e-10));
  }
 }
 assert.ok(sampledContacts>10);assert.ok(clearCases>10);
});
console.log(JSON.stringify({verdict:'PASS',checks,independentTimeSamples:samples,sampledContactCases:sampledContacts,certifiedClearCases:clearCases,explicitUncertainCases:uncertain,rotatingFalsePlaneMinimum_m:rotatingDenseMinimum,actual31FalsePlaneMinimum_m:actual31DenseMinimum,scope:'Pure floating-point linear vertex/triangle CCD controls. Dense sampling is not a general proof; conservative/uncertain results are not exact impact certification. No solver/material/body/acceptance threshold changed.'}));
