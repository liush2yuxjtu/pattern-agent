import assert from 'node:assert/strict';
import{initStrain,tensorFromF}from '../src/strain.js';
export async function testStrain(test){await initStrain();
 test('WASM: rigid rest',()=>{const r=tensorFromF([1,0,0],[0,1,0]);assert.equal(r.lmax,1);assert.equal(r.lmin,1);assert.equal(r.vonMises,0);});
 test('WASM: rigid rotation invariant',()=>{const r=tensorFromF([0,1,0],[-1,0,0]);assert.equal(r.lmax,1);assert.equal(r.vonMises,0);});
 test('WASM: 10% stretch tensor',()=>{const r=tensorFromF([1.1,0,0],[0,1,0]);assert.ok(Math.abs(r.lmax-1.1)<1e-12);assert.ok(Math.abs(r.lmin-1)<1e-12);assert.ok(Math.abs(r.ex-.105)<1e-12);assert.ok(Math.abs(r.sx-11538.4615384615)<1e-7);});
 test('WASM: extreme collapse 1e-9 retained',()=>{const r=tensorFromF([1,0,0],[0,1e-9,0]);assert.ok(Math.abs(r.lmin-1e-9)<1e-20);assert.equal(r.lmax,1);});
 test('WASM: degenerate finite',()=>{const r=tensorFromF([0,0,0],[0,0,0]);assert.equal(r.lmin,0);assert.equal(r.lmax,0);assert.ok(Number.isFinite(r.vonMises));});
 test('WASM: pure shear independent eigenvalues',()=>{const r=tensorFromF([1,0,0],[.2,1,0]);const hi=Math.sqrt((2.04+Math.sqrt(.04*.04+.16))/2);assert.ok(Math.abs(r.lmax-hi)<1e-12);assert.ok(Math.abs(r.lmin-1/hi)<1e-12);});
 test('WASM: material modulus changes stress only',()=>{const a=tensorFromF([1.1,0,0],[0,1,0],100000,.3),b=tensorFromF([1.1,0,0],[0,1,0],200000,.3);assert.equal(a.lmax,b.lmax);assert.equal(b.sx,2*a.sx);});
}
