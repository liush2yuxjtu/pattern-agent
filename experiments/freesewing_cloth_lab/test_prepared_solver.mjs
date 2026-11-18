import assert from 'node:assert/strict';
import fs from 'node:fs';
const bytes=new Uint8Array(JSON.parse(fs.readFileSync(new URL('./source/solver-bytes.json',import.meta.url),'utf8')));
const instances=await Promise.all([WebAssembly.instantiate(bytes,{}),WebAssembly.instantiate(bytes,{})]);
const kernels=instances.map(x=>x.instance.exports),n=32,edges=31,old=768,mass=1536,records=1792,prepared=records+edges*32,dt=1/120;
for(const w of kernels){
 const x=new Float64Array(w.memory.buffer,0,n*3),previous=new Float64Array(w.memory.buffer,old,n*3),inv=new Float64Array(w.memory.buffer,mass,n),view=new DataView(w.memory.buffer);
 for(let i=0;i<n;i++){x.set([i*.03,1+Math.sin(i)*.005,Math.cos(i)*.01],i*3);inv[i]=i<2?0:(i%5+1)*.7;}
 previous.set(x);
 for(let i=0;i<edges;i++){const r=records+i*32;view.setInt32(r,i,true);view.setInt32(r+4,i+1,true);view.setFloat64(r+8,.025,true);view.setFloat64(r+16,i%3?1e-7:0,true);view.setFloat64(r+24,0,true);}
}
kernels[1].prepare(edges,0,mass,records,prepared,dt*dt);
for(let frame=0;frame<5;frame++){
 for(const w of kernels)w.integrate(n,0,old,mass,dt,2.5);
 const view=new DataView(kernels[0].memory.buffer);
 for(let i=0;i<edges;i++)view.setFloat64(records+i*32+24,0,true);
 for(let iteration=0;iteration<120;iteration++)kernels[0].solve(edges,0,mass,records,dt*dt);
 kernels[1].solve_prepared(edges,prepared,120);
 assert.deepEqual(new Uint8Array(kernels[1].memory.buffer,0,n*3*8),new Uint8Array(kernels[0].memory.buffer,0,n*3*8));
 assert.deepEqual(new Uint8Array(kernels[1].memory.buffer,old,n*3*8),new Uint8Array(kernels[0].memory.buffer,old,n*3*8));
}
console.log(JSON.stringify({verdict:'PASS',frames:5,constraints:edges,iterations:120,positionsAndPreviousBitExact:true,nonzeroCompliance:true,unequalMasses:true,pinnedPoints:true}));
