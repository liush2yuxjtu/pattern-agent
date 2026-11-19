import wasmBytes from './wasm-binary.js';
let kernel=null;
export async function initStrain(){kernel=(await WebAssembly.instantiate(wasmBytes)).instance.exports;return Object.keys(kernel);}
export function tensorFromF(u,v,E=100000,nu=.3){
  if(!kernel)throw new Error('WASM not initialized');
  const dot=(a,b)=>a.reduce((s,x,i)=>s+x*b[i],0),a=dot(u,u),b=dot(u,v),c=dot(v,v);
  const cr=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]],det=dot(cr,cr);
  const lmax=kernel.principal_max(a,b,c),lmin=kernel.principal_min(a,b,c,det);
  const ex=kernel.green_normal(a),ey=kernel.green_normal(c),gamma=b;
  const sx=kernel.plane_stress(ex,ey,E,nu),sy=kernel.plane_stress(ey,ex,E,nu),tau=kernel.shear_stress(gamma,E,nu);
  return {lmax,lmin,ex,ey,gamma,sx,sy,tau,vonMises:Math.sqrt(Math.max(0,sx*sx-sx*sy+sy*sy+3*tau*tau))};
}
export function strainField(doc,p,material){
  const uv=doc.mesh.restUV,t=doc.mesh.triangles,values=[],stress=[],perVertex=new Float32Array(p.length/3),vertexStress=new Float32Array(p.length/3),weights=new Uint16Array(p.length/3);
  for(let f=0;f<t.length;f+=3){const [i,j,k]=t.slice(f,f+3),u0=(uv[j][0]-uv[i][0])/1000,v0=(uv[j][1]-uv[i][1])/1000,u1=(uv[k][0]-uv[i][0])/1000,v1=(uv[k][1]-uv[i][1])/1000,det=u0*v1-u1*v0;
    if(Math.abs(det)<1e-14)throw new Error(`Degenerate rest triangle ${f/3}`);
    const e1=[0,1,2].map(a=>p[j*3+a]-p[i*3+a]),e2=[0,1,2].map(a=>p[k*3+a]-p[i*3+a]);
    const F0=e1.map((x,a)=>(x*v1-e2[a]*v0)/det),F1=e1.map((x,a)=>(e2[a]*u0-x*u1)/det);
    const r=tensorFromF(F0,F1,material.E,material.nu),strain=Math.max(Math.abs(r.lmax-1),Math.abs(r.lmin-1));
    values.push(strain);stress.push(r.vonMises);for(const id of [i,j,k]){perVertex[id]+=strain;vertexStress[id]+=r.vonMises;weights[id]++;}
  }
  for(let i=0;i<weights.length;i++){perVertex[i]/=weights[i]||1;vertexStress[i]/=weights[i]||1;}
  const sorted=values.slice().sort((a,b)=>a-b),q=.95*(sorted.length-1),i=Math.floor(q),p95=sorted[i]+(sorted[Math.min(i+1,sorted.length-1)]-sorted[i])*(q-i);
  return {values,stress,perVertex,vertexStress,p95,max:sorted.at(-1),maxStressPa:Math.max(...stress),model:'Green-Lagrange strain; isotropic plane stress StVK diagnostic. ASSUMED E/nu; not calibrated cloth stress.'};
}
