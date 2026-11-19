import assert from 'node:assert/strict';import{makeBody,BASE_SIZE,section}from '../src/body.js';import{createBodyCollider}from '../src/body-contact.js';
export function testBody(test){
 const base=makeBody(BASE_SIZE),wide=makeBody({...BASE_SIZE,chestMm:935,waistMm:740,hipMm:1030,heightCm:176});
 test('body: full anatomical topology retained',()=>{assert.equal(base.positions.length/3,4002);assert.equal(base.triangles.length/3,8000);assert.deepEqual(base.triangles,wide.triangles);});
 test('body: dimensions remeasured after morph, < 1 mm error',()=>{for(const v of Object.values(wide.measurementErrorMm))assert.ok(Math.abs(v)<1,`size residual ${v} mm`);});
 test('body: height matches requested cm',()=>assert.ok(Math.abs(Math.max(...wide.positions.filter((_,i)=>i%3===1))-1.76)<1e-8));
 test('body: render/collision share morphed geometry',()=>{assert.notDeepEqual(base.positions,wide.positions);assert.equal(wide.collision.geometry,'positions+triangles');});
 test('body: rebuilt BVH contains every child',()=>{const n=wide.collision.bvh.nodes;for(let at=0;at<n.length;at+=10)if(!n[at+9])for(const child of [n[at+6],n[at+7]])for(let a=0;a<3;a++){assert.ok(n[at+a]<=n[child*10+a]+1e-10);assert.ok(n[at+3+a]>=n[child*10+3+a]-1e-10);}});
 test('body: chest cross-section independently closed',()=>{const s=section(wide,wide.measurements.chest.height);assert.ok(Math.abs(s.circumference-.935)<.001);});
 test('body: inside negative/outside positive control',()=>{const c=createBodyCollider(base);assert.ok(c.closestPoint(0,1.1,.02).signedDistance<0);assert.ok(c.closestPoint(2,1.1,.02).signedDistance>1);});
 test('body: invalid dimensions rejected',()=>assert.throws(()=>makeBody({...BASE_SIZE,chestMm:NaN})));
 return {base,wide};
}
