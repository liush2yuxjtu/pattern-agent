export function improveTriangles(positions,triangles){
 const cross=(a,b,c)=>(b.x-a.x)*(c.y-a.y)-(b.y-a.y)*(c.x-a.x);
 const orient=t=>cross(...t.map(i=>positions[i]))>0?t:[t[0],t[2],t[1]];
 const angle=t=>{let value=Infinity;for(let i=0;i<3;i++){const a=positions[t[i]],b=positions[t[(i+1)%3]],c=positions[t[(i+2)%3]],ux=b.x-a.x,uy=b.y-a.y,vx=c.x-a.x,vy=c.y-a.y;value=Math.min(value,Math.atan2(Math.abs(ux*vy-uy*vx),ux*vx+uy*vy));}return value;};
 const ts=triangles.map(orient);let total=0,rounds=0;
 for(;rounds<64;rounds++){
  const edges=new Map(),changed=new Set();let flips=0;
  for(let f=0;f<ts.length;f++)for(let i=0;i<3;i++){const a=ts[f][i],b=ts[f][(i+1)%3],key=a<b?a+':'+b:b+':'+a;if(!edges.has(key))edges.set(key,[]);edges.get(key).push({f,a,b,c:ts[f][(i+2)%3]});}
  for(const pair of edges.values()){
   if(pair.length!==2)continue;const [u,v]=pair;if(changed.has(u.f)||changed.has(v.f))continue;
   const a=positions[u.a],b=positions[u.b],c=positions[u.c],d=positions[v.c];
   if(cross(a,b,c)*cross(a,b,d)>=-1e-16||cross(c,d,a)*cross(c,d,b)>=-1e-16)continue;
   const next=[orient([u.c,v.c,u.a]),orient([v.c,u.c,u.b])],old=Math.min(angle(ts[u.f]),angle(ts[v.f])),fresh=Math.min(angle(next[0]),angle(next[1]));
   if(fresh<=old+1e-9)continue;ts[u.f]=next[0];ts[v.f]=next[1];changed.add(u.f);changed.add(v.f);flips++;
  }
  total+=flips;if(!flips)break;
 }
 return {triangles:ts,flips:total,rounds};
}
