// Independent CPU reference for the colored PBD equations in solver-gpu.js.
// Used to examine numerical behavior, never reported as a WebGPU execution.
import {expandPositions}from '../src/constraints.js';
export class ReferenceSolver{
 constructor(model,contact,{iterations=16,gravity=9.81}={}){Object.assign(this,{model,contact,iterations,gravity});this.p=model.initial.slice();this.previous=this.p.slice();this.steps=0;}
 step(){const p=this.p,planes=this.contact.planes(p),dt=1/120;
  for(let i=0;i<this.model.nodeCount;i++){const at=i*4;for(let a=0;a<3;a++){const x=p[at+a];p[at+a]=x+(x-this.previous[at+a])*.96+(a===1?-this.gravity*dt*dt:0);this.previous[at+a]=x;}}
  for(let iteration=0;iteration<this.iterations;iteration++){
   for(const group of this.model.colors)for(const e of group){const ia=e.a*4,ib=e.b*4,d=[0,1,2].map(a=>p[ia+a]-p[ib+a]),l=Math.hypot(...d);if(l<1e-8)continue;const scale=(l-e.rest)/(l*(2+e.compliance*14400));for(let a=0;a<3;a++){p[ia+a]-=d[a]*scale;p[ib+a]+=d[a]*scale;}}
   for(let i=0;i<this.model.nodeCount;i++){const at=i*4;for(let j=0;j<8;j++){const slot=(j+1)%8,q=(i*8+slot)*8;if(!planes[q+3])continue;const d=[0,1,2].reduce((s,a)=>s+(p[at+a]-planes[q+4+a])*planes[q+a],0);if(d<0)for(let a=0;a<3;a++)p[at+a]-=Math.max(d,slot===0?-100:-.002)*planes[q+a];}}
  }
  this.steps++;return expandPositions(this.model,p);
 }
}
