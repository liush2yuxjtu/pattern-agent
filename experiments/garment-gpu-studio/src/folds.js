const minus=(a,b)=>a.map((x,i)=>x-b[i]),cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]],dot=(a,b)=>a.reduce((s,x,i)=>s+x*b[i],0),unit=a=>{let n=Math.hypot(...a)||1;return a.map(x=>x/n);};
export function dihedral(a,b,c,d){const axis=unit(minus(b,a)),n1=unit(cross(minus(b,a),minus(c,a))),n2=unit(cross(minus(a,b),minus(d,b)));return Math.atan2(dot(axis,cross(n1,n2)),Math.max(-1,Math.min(1,dot(n1,n2))))*180/Math.PI;}
export function foldField(doc,model,p){
  const edges=new Map(),records=[],perVertex=new Float32Array(p.length/3);
  const t=doc.mesh.triangles,point=i=>Array.from(p.slice(i*3,i*3+3));
  for(let f=0;f<t.length;f+=3)for(let e=0;e<3;e++){
    const a=t[f+e],b=t[f+(e+1)%3],c=t[f+(e+2)%3],ka=model.map[a],kb=model.map[b],key=[ka,kb].sort((a,b)=>a-b).join(',');
    if(edges.has(key)){const prev=edges.get(key),angle=dihedral(point(prev.a),point(prev.b),point(prev.c),point(c));const r={a:prev.a,b:prev.b,c:prev.c,d:c,angleDeg:angle,triangleA:prev.f,triangleB:f/3};records.push(r);for(const id of [a,b,prev.a,prev.b])perVertex[id]=Math.max(perVertex[id],Math.abs(angle));}
    else edges.set(key,{a,b,c,f:f/3});
  }
  return {records,perVertex,maxDeg:Math.max(0,...records.map(r=>Math.abs(r.angleDeg))),definition:'Signed dihedral between neighboring triangle normals, flat = 0 degrees.'};
}
