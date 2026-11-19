import assert from 'node:assert/strict';import fs from 'node:fs';
import{segmentTriangle,triangleCross}from '../src/intersections.js';
import{buildConstraints}from '../src/constraints.js';import{createContactSystem}from '../src/collision.js';import{verdict}from '../src/debugger.js';
export function testCollision(test){
 const t=[[0,0,0],[1,0,0],[0,1,0]];
 test('collision: strict segment transverse hit',()=>assert.equal(segmentTriangle([.2,.2,-1],[.2,.2,1],t),true));
 test('collision: segment miss rejected',()=>assert.equal(segmentTriangle([2,2,-1],[2,2,1],t),false));
 test('collision: coplanar is not labeled a transverse hit',()=>assert.equal(segmentTriangle([.1,.1,0],[.2,.2,0],t),false));
 test('collision: two-way full triangle crossing',()=>assert.equal(triangleCross(t,[[.1,.1,-1],[.4,.1,1],[.1,.4,1]]),true));
 test('collision: face crossing prevents false overall PASS',()=>{const r=verdict({finite:true,penetratingVertices:0,penetratingSamples:0,fullCollision:true,bodyFaceCrossings:1,selfFaceCrossings:0,strainP95:0,strainMax:0},{status:'PASS',maxGapMm:0});assert.equal(r.geometry,'FAIL');});
 const path='evidence/history/gpu-before-face-fix.json';
 if(fs.existsSync(path)){
  const s=JSON.parse(fs.readFileSync(path)),d=s.project.document,m=buildConstraints(d),c=createContactSystem(s.project.body,m,d),r=c.inspect(Float32Array.from(s.positions),true);
  test('collision: detects six historical body crossings despite zero inside vertices',()=>{assert.equal(r.penetratingVertices,0);assert.equal(r.bodyFacePairs.pairs.length,6);});
  test('collision: 38 historical self crossings independently agree with NumPy',()=>assert.equal(r.selfFacePairs.pairs.length,38));
 }
}
