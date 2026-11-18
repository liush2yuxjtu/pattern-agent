import assert from 'node:assert/strict';
import {MeshContact} from './mesh-contact.mjs';

const receipts=[];
const movement=(a,b,id)=>Math.hypot(...[0,1,2].map(k=>a[id*3+k]-b[id*3+k]));
const triangleVisits=contact=>{
 let n=0;contact.tree.shapecast({intersectsBounds:()=>true,intersectsTriangle:()=>{n++;return false;}});return n;
};

// All supported index representations reach all faces in a multi-leaf BVH.
for(const Type of [Array,Uint8Array,Uint16Array,Uint32Array,Int32Array]){
 const faces=40,positions=new Float64Array(faces*9),indices=Type.from({length:faces*3},(_,i)=>i);
 for(let face=0;face<faces;face++)positions.set([face*2,0,0,face*2+1,0,0,face*2,.5,0],face*9);
 const solver=new MeshContact(positions,indices,.001);
 assert.equal(solver.geometry.index.count,faces*3);
 assert.equal(triangleVisits(solver),faces);
 assert.equal(solver.faceIndices.length,faces);
 receipts.push({indexType:Type.name,actualTriangles:triangleVisits(solver)});solver.dispose();
}

// Ten identical fixed queries affect the same movable face. Every proposal is
// computed on one snapshot and the complete pass, not each query, is capped.
const capped=[];
for(const Type of [Float32Array,Float64Array]){
 const positions=Type.from([-1,-1,0,1,-1,0,0,1,0,...Array(10).fill([0,0,0]).flat()]);
 const previous=positions.slice(),history=positions.slice(),historyBefore=history.slice(),before=positions.slice();
 const inv=Type.from([1,1,1,...Array(10).fill(0)]),cap=.0005;
 const solver=new MeshContact(positions,[0,1,2],.003,{maxVertexCorrection:cap});
 const contacts=solver.solve(positions,previous,inv,1,history);
 assert.equal(contacts,10);assert.equal(solver.lastProfile.vfConstraints,10);
 const maximum=Math.max(...[0,1,2].map(id=>movement(positions,before,id)));
 assert.ok(maximum>0&&maximum<=cap,`${Type.name}: whole-pass maximum ${maximum} exceeds cap ${cap}`);
 for(let id=3;id<13;id++){
  assert.equal(movement(positions,before,id),0,'Fixed query moved');
  assert.equal(movement(previous,before,id),0,'Fixed previous coordinate moved');
 }
 for(let id=0;id<3;id++)for(let k=0;k<3;k++)assert.ok(Math.abs(previous[id*3+k]-before[id*3+k]-.8*(positions[id*3+k]-before[id*3+k]))<5e-11);
 assert.deepEqual(history,historyBefore,'Caller-owned separate history changed');
 assert.deepEqual(Array.from(solver.vertices),Array.from(positions),'Final BVH geometry is stale');
 assert.ok(solver.lastPassMaxCorrections.every(x=>x<=cap));
 capped.push({positionType:Type.name,contacts,maximumPassMovement_m:maximum,cap_m:cap});solver.dispose();
}

// A known isolated VF constraint retains inverse-mass/barycentric weighting.
{
 const positions=new Float64Array([0,0,0,1,0,0,0,1,0,.25,.25,.0005]),before=positions.slice(),previous=positions.slice();
 const solver=new MeshContact(positions,[0,1,2],.001,{maxVertexCorrection:.01});
 assert.equal(solver.solve(positions,previous,new Float64Array([1,0,0,2]),1,before),1);
 const lambda=(.001-.0005)/(2+.5*.5);
 assert.ok(Math.abs(positions[11]-(before[11]+2*lambda))<1e-14);
 assert.ok(Math.abs(positions[2]-(before[2]-.5*lambda))<1e-14);
 for(const id of [1,2])assert.equal(movement(positions,before,id),0);
 receipts.push({inverseMassWeighting:'PASS',queryDisplacement_m:positions[11]-before[11],faceVertexDisplacement_m:positions[2]-before[2]});solver.dispose();
}

// Proximity and moving-plane crossing remain on the history side when budget
// permits. Fixed face vertices and the immutable history are not projected.
for(const finalZ of [.0005,-.004]){
 const p=new Float64Array([-1,-1,0,1,-1,0,0,1,0,0,0,finalZ]),previous=p.slice(),history=p.slice();history[11]=.01;
 const before=history.slice(),solver=new MeshContact(p,[0,1,2],.003,{maxVertexCorrection:.02});
 assert.ok(solver.solve(p,previous,new Float64Array([0,0,0,1]),1,history)>0);
 assert.ok(p[11]>=.003-1e-12);
 assert.deepEqual(history,before);
 assert.deepEqual(Array.from(p.slice(0,9)),[-1,-1,0,1,-1,0,0,1,0]);
 receipts.push({VFInitialCurrentZ_m:finalZ,historySideFinalZ_m:p[11]});solver.dispose();
}

// Each requery sees the previous pass's applied positions. Four .02m passes
// may cumulatively recover .043m; each complete pass is still individually capped.
{
 const p=new Float64Array([-1,-1,.04,1,-1,.04,0,1,.04,0,0,0]),history=p.slice();history[2]=history[5]=history[8]=-.04;
 const historyBefore=history.slice(),solver=new MeshContact(p,[0,1,2],.003,{maxVertexCorrection:.02});
 assert.ok(solver.solve(p,p.slice(),new Float64Array([0,0,0,1]),4,history)>0);
 assert.ok(p[11]>=.043-1e-10);
 assert.ok(solver.lastPassMaxCorrections.every(value=>value<=.02));
 assert.ok(solver.lastProfile.maxAccumulatedCorrection>.02);
 assert.deepEqual(history,historyBefore);
 receipts.push({movingFaceCrossingFinalZ_m:p[11],perPassMaxima_m:solver.lastPassMaxCorrections,totalTravel_m:solver.lastProfile.maxAccumulatedCorrection});solver.dispose();
}

// Do not suppress an entire material one-ring: only membership in the queried
// face is intrinsic VF adjacency. Legacy broad callbacks need explicit opt-in.
{
 const p=new Float64Array([.2,.2,.0005,0,0,0,1,0,0,0,1,0]),before=p.slice(),tri=[0,1,2,1,2,3];
 const solver=new MeshContact(p,tri,.001,{maxVertexCorrection:.01,excludeVertexFace:()=>true,excludeEdgePair:()=>true});
 assert.ok(solver.solve(p,p.slice(),new Float64Array([1,0,0,0]),1,before)>0);
 assert.ok(p[2]>=.001-1e-12,'A nonincident one-ring face was silently excluded');solver.dispose();
 const skipped=before.slice(),custom=new MeshContact(skipped,tri,.001,{useCustomExclusions:true,excludeVertexFace:()=>true,excludeEdgePair:()=>true});
 assert.equal(custom.solve(skipped,skipped.slice(),new Float64Array([1,0,0,0]),1,before),0);assert.deepEqual(skipped,before);custom.dispose();
 receipts.push({primitiveOnlyExclusions:'PASS',customExclusionOptIn:'PASS'});
}

// Swept EE candidates include disjoint final AABBs; primitive-shared endpoint
// pairs are excluded without suppressing other edges in the one-ring.
{
 const p=new Float64Array([-1,0,0,1,0,0,0,-1,-.004,0,1,-.004]),history=p.slice();history[8]=history[11]=.004;
 const historyBefore=history.slice(),solver=new MeshContact(p,[0,1,2],.001,{maxVertexCorrection:.02});solver.edges=[[0,1],[2,3]];
 assert.ok(solver.solveEdges(p,p.slice(),new Float64Array([0,0,1,1]),history)>0);
 assert.ok((p[8]+p[11])/2>=.001-1e-9);assert.deepEqual(history,historyBefore);
 receipts.push({EEThroughCrossingFinalZ_m:(p[8]+p[11])/2,candidates:solver.lastProfile.eeCandidates});solver.dispose();
 const iterative=new Float64Array([-1,0,0,1,0,0,0,-1,-.004,0,1,-.004]),iterativeHistory=iterative.slice();iterativeHistory[8]=iterativeHistory[11]=.004;
 const requery=new MeshContact(iterative,[0,1,2],.001,{maxVertexCorrection:.001});requery.edges=[[0,1],[2,3]];
 assert.ok(requery.solve(iterative,iterative.slice(),new Float64Array([0,0,1,1]),8,iterativeHistory)>0);
 assert.ok((iterative[8]+iterative[11])/2>=.001-1e-10);
 assert.ok(requery.lastPassMaxCorrections.every(x=>x<=.001));
 receipts.push({preparedEERefitRequery:'PASS',perPassMaxima_m:requery.lastPassMaxCorrections});requery.dispose();
 const cross=new Float64Array([-1,0,0,1,0,0,2,-1,0,2,1,0]),old=cross.slice();old[6]=old[9]=-2;
 const swept=new MeshContact(cross,[0,1,2],.001,{maxVertexCorrection:.02});swept.edges=[[0,1],[2,3]];
 const candidates=[];swept.forEachCandidate(cross,(a,b)=>candidates.push([a,b].sort((x,y)=>x-y)),old);assert.deepEqual(candidates,[[0,1]]);
 assert.ok(swept.solveEdges(cross,cross.slice(),new Float64Array([0,0,1,1]),old)>0,'Endpoint-disjoint swept EE was omitted');
 receipts.push({endpointDisjointEECandidate:'PASS',finalX_m:cross[6]});swept.dispose();
}

// All moving face endpoint boxes are present in the swept node unions.
{
 const count=40,p=new Float64Array(count*9),history=new Float64Array(count*9),indices=Array.from({length:count*3},(_,i)=>i);
 for(let i=0;i<p.length;i++){p[i]=Math.sin(i*3.17)*.5;history[i]=p[i]+Math.cos(i*2.31)*.07;}
 const solver=new MeshContact(p,indices,.003);solver.buildSweptBounds(history);let covered=0;
 for(let query=0;query<60;query++){
  const a=[0,1,2].map(k=>Math.sin((query*3+k)*1.13)*.6),b=a.map((v,k)=>v+Math.cos(query+k)*.06),lo=a.map((v,k)=>Math.min(v,b[k])-.003),hi=a.map((v,k)=>Math.max(v,b[k])+.003),actual=new Set();
  const overlaps=(l,h)=>[0,1,2].every(k=>lo[k]<=h[k]&&hi[k]>=l[k]);
  solver.tree.shapecast({intersectsBounds:(box,leaf,score,depth,node)=>{const v=solver.sweptNodes.get(node);assert.ok(v);return overlaps(v.slice(0,3),v.slice(3));},intersectsTriangle:(triangle,id)=>{actual.add(id);return false;}});
  for(let face=0;face<count;face++){
   const ids=indices.slice(face*3,face*3+3),low=[0,1,2].map(k=>Math.min(...ids.flatMap(id=>[p[id*3+k],history[id*3+k]]))),high=[0,1,2].map(k=>Math.max(...ids.flatMap(id=>[p[id*3+k],history[id*3+k]])));
   if(overlaps(low,high)){assert.ok(actual.has(face),'Swept BVH omitted a moving face');covered++;}
  }
 }
 solver.dispose();receipts.push({sweptFaceQueries:60,overlappingFaceBoundsRetained:covered});
}

console.log(JSON.stringify({verdict:'PASS',scope:'Jacobi VF+EE contact mechanics, per-pass correction cap and geometric controls; not garment physical acceptance or general VF CCD proof',coincidentQueryCaps:capped,checks:receipts},null,2));
