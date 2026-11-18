import assert from 'node:assert/strict';
import {SelfContact} from './source/self-contact.js';

function vertexTriangle(z){
 const p=new Float64Array([-1,-1,0,1,-1,0,0,1,0,0,0,z]);
 const history=new Float64Array(p);history[11]=.01;
 const previous=new Float64Array(history),inverseMass=new Float64Array([0,0,0,1]);
 const solver=new SelfContact(p,[0,1,2],.003);
 const contacts=solver.solve(p,previous,inverseMass,1,history);
 assert.ok(contacts>0,'the actual contact solver must activate');
 assert.ok(p[11]>=.003-1e-9,'the free point must return to its original side with clearance');
 assert.deepEqual(Array.from(p.slice(0,9)),Array.from(history.slice(0,9)),'pinned triangle must stay fixed');
 assert.equal(history[11],.01,'the pre-step history must remain immutable');
 solver.dispose();return {contacts,finalZ:p[11]};
}

const proximity=vertexTriangle(.001);
const crossed=vertexTriangle(-.004);
const p=new Float64Array([-1,0,0,1,0,0,0,-1,.001,0,1,.001]);
const history=new Float64Array(p);history[8]=history[11]=.01;
const previous=new Float64Array(history),inverseMass=new Float64Array([0,0,1,1]);
const solver=new SelfContact(p,[0,1,2],.003);solver.edges=[[0,1],[2,3]];
const edgeContacts=solver.solveEdges(p,previous,inverseMass,history);
assert.ok(edgeContacts>0,'disjoint crossing edges must receive a contact correction');
assert.ok((p[8]+p[11])/2>=.003-1e-9,'edge midpoint must reach the thickness boundary');
assert.deepEqual(Array.from(p.slice(0,6)),Array.from(history.slice(0,6)));
solver.dispose();
// The optimized sweep must enumerate the complete same AABB candidate set as
// an independent all-pairs check, with no duplicate callbacks.
const sample=new Float64Array(60);
for(let i=0;i<sample.length;i++)sample[i]=Math.sin(i*2.31)*.025;
const broad=new SelfContact(sample,[0,1,2],.003);
broad.edges=Array.from({length:10},(_,i)=>[i*2,i*2+1]);
const actual=new Set();let calls=0;
broad.forEachCandidate(sample,(a,b)=>{calls++;actual.add([Math.min(a,b),Math.max(a,b)].join(':'));});
const expected=new Set();
for(let i=0;i<broad.edges.length;i++)for(let j=i+1;j<broad.edges.length;j++){
 const [a,b]=broad.edges[i],[c,d]=broad.edges[j];
 const overlap=[0,1,2].every(k=>Math.max(Math.min(sample[a*3+k],sample[b*3+k])-.003,Math.min(sample[c*3+k],sample[d*3+k])-.003)<=Math.min(Math.max(sample[a*3+k],sample[b*3+k])+.003,Math.max(sample[c*3+k],sample[d*3+k])+.003));
 if(overlap)expected.add(i+':'+j);
}
assert.deepEqual(actual,expected);assert.equal(calls,actual.size);broad.dispose();
console.log(JSON.stringify({verdict:'PASS',vertexTriangleProximity:proximity,sweptVertexTriangle:crossed,edgeEdge:{contacts:edgeContacts,midpointZ:(p[8]+p[11])/2},completeUniqueBroadPhase:{candidates:calls,matchedDenseOracle:true}},null,2));
