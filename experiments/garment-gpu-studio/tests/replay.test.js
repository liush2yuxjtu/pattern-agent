import assert from 'node:assert/strict';import{Replay}from '../src/replay.js';
export function testReplay(test){
 test('replay: stores a copy, not live positions',()=>{const r=new Replay(),p=new Float32Array([1,2,3]);r.reset('a');r.record(p,1,1/120,{});p[0]=9;assert.equal(r.seek(0,'a').positions[0],1);});
 test('replay: seeking does not run physics',()=>{const r=new Replay();r.reset('a');r.record([1,2,3],12,1/120,{});r.record([2,3,4],24,1/120,{});r.seek(0,'a');assert.equal(r.frames[0].id,12);assert.equal(r.frames.length,2);assert.equal(r.frames[0].time,.1);});
 test('replay: stale input rejected',()=>{const r=new Replay();r.reset('a');r.record([1],0,.1,{});assert.throws(()=>r.seek(0,'b'),/STALE/);});
 test('replay: bounded storage keeps first/latest',()=>{const r=new Replay(3);r.reset('a');for(let i=0;i<10;i++)r.record([i],i,.1,{});assert.equal(r.frames.length,3);assert.equal(r.frames[0].id,0);assert.equal(r.frames.at(-1).id,9);});
}
