import assert from 'node:assert/strict';import{checkSeams}from '../src/seams.js';import{buildConstraints,expandPositions}from '../src/constraints.js';
export function testSeams(test,doc){const m=buildConstraints(doc),p=expandPositions(m,m.initial);
 test('seams: all ten pairs present',()=>assert.equal(doc.seams.length,10));
 test('seams: valid edge references and matching lengths',()=>assert.equal(checkSeams(doc,p).status,'PASS'));
 test('seams: equality constraint groups give exact zero gap',()=>assert.equal(checkSeams(doc,p).maxGapMm,0));
 test('seams: broken seam is rejected',()=>{const q=p.slice(),a=doc.seams[0].pairs[2][0];q[a*3]+=.02;assert.equal(checkSeams(doc,q).status,'FAIL');});
 test('seams: duplicate boundary is rejected',()=>{const d=structuredClone(doc);d.seams.push(d.seams[0]);assert.equal(checkSeams(d,p).status,'FAIL');});
 test('seams: reversed pairing is rejected',()=>{const d=structuredClone(doc);d.seams[0].pairs.reverse();assert.equal(checkSeams(d,p).status,'FAIL');});
 test('seams: invalid piece edge is rejected',()=>{const d=structuredClone(doc);d.seams[0].a.edge='missing';assert.equal(checkSeams(d,p).status,'FAIL');});
 test('seams: stale length metadata is rejected',()=>{const d=structuredClone(doc);d.seams[0].lengthAmm+=10;assert.equal(checkSeams(d,p).status,'FAIL');});
 test('GPU constraints: no shared write in a dispatch color',()=>{for(const group of m.colors){const used=new Set();for(const e of group){assert.ok(!used.has(e.a)&&!used.has(e.b));used.add(e.a);used.add(e.b);}}});
 test('GPU constraints: rest distances from independent 2D UV',()=>{for(const e of doc.mesh.edges){const [a,b]=[doc.mesh.restUV[e.a],doc.mesh.restUV[e.b]];assert.ok(Math.abs(e.restMm-Math.hypot(a[0]-b[0],a[1]-b[1]))<1e-9);}});
 test('GPU constraints: no artificial seam-distance springs',()=>{assert.equal(m.edges.length,doc.mesh.edges.length);assert.ok(m.groups.some(g=>g.length>1));});
 return m;
}
