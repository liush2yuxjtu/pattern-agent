import assert from 'node:assert/strict';
import {createSelfContact} from './create-self-contact.mjs';

const count=40,positions=new Float32Array(count*9),history=new Float32Array(count*9),indices=Array.from({length:count*3},(_,i)=>i);
for(let i=0;i<positions.length;i++){positions[i]=Math.sin(i*3.17)*.5;history[i]=positions[i]+Math.cos(i*2.31)*.07;}
const solver=createSelfContact(positions,indices,.003);solver.buildSweptBounds(history);
let checks=0,visited=0;
for(let q=0;q<100;q++){
 const a=[0,1,2].map(k=>Math.sin((q*3+k)*1.13)*.6),b=a.map((v,k)=>v+Math.cos(q+k)*.06);
 const lo=a.map((v,k)=>Math.min(v,b[k])-.003),hi=a.map((v,k)=>Math.max(v,b[k])+.003),actual=new Set();
 const overlap=(l,h)=>[0,1,2].every(k=>lo[k]<=h[k]&&hi[k]>=l[k]);
 solver.tree.shapecast({intersectsBounds:(box,leaf,score,depth,node)=>{const v=solver.sweptNodes.get(node);return overlap(v.slice(0,3),v.slice(3));},intersectsTriangle:(triangle,id)=>{actual.add(id);visited++;return false;}});
 for(let t=0;t<count;t++){
  const ids=indices.slice(t*3,t*3+3),low=[0,1,2].map(k=>Math.min(...ids.flatMap(i=>[positions[i*3+k],history[i*3+k]]))),high=[0,1,2].map(k=>Math.max(...ids.flatMap(i=>[positions[i*3+k],history[i*3+k]])));
  if(overlap(low,high)){assert.ok(actual.has(t),'Swept broad phase dropped a possible moving triangle');checks++;}
 }
}
solver.dispose();
// A stationary point and a translating triangle collide although their current
// AABBs are disjoint. The swept hierarchy must retain the whole motion.
const p=new Float32Array([-1,-1,.04,1,-1,.04,0,1,.04,0,0,0]),old=p.slice();old[2]=old[5]=old[8]=-.04;
const moving=createSelfContact(p,[0,1,2],.003,{maxVertexCorrection:.02});const contacts=moving.solve(p,p.slice(),new Float32Array([0,0,0,1]),4,old);
assert.ok(contacts>0);assert.ok(p[11]>=.043-1e-7);moving.dispose();
const edges=new Float32Array([-1,0,0,1,0,0,0,-1,0,0,1,0]),edgeHistory=edges.slice();edgeHistory[8]=edgeHistory[11]=.01;
const edgeSolver=createSelfContact(edges,[0,1,2],.003,{maxVertexCorrection:.02});edgeSolver.edges=[[0,1],[2,3]];
assert.ok(edgeSolver.solveEdges(edges,edges.slice(),new Float32Array([0,0,1,1]),edgeHistory)>0);
assert.ok((edges[8]+edges[11])/2>=.003-1e-7);edgeSolver.dispose();
console.log(JSON.stringify({verdict:'PASS',denseSweptAABBFeaturesRetained:checks,queries:100,actualTriangleCallbacks:visited,
 movingTriangleStationaryPoint:{contacts,finalZ:p[11]},exactCrossingEdgesSeparated:true}));
