/** Signed dihedral: flat = 0, positive/negative preserve the oriented edge's
 * mountain/valley convention. Curvature is theta divided by dual-face spacing.
 * This is a geometric wrinkle indicator, not a permanent-crease material law.
 */
export function buildHinges(triangles,uvs){
 const pending=new Map(),hinges=[];
 for(let t=0;t<triangles.length/3;t++)for(let j=0;j<3;j++){
  const ids=triangles.slice(t*3,t*3+3),a=ids[j],b=ids[(j+1)%3],c=ids[(j+2)%3],key=[Math.min(a,b),Math.max(a,b)].join(':');
  const uv=k=>uvs.slice(t*6+k*2,t*6+k*2+2),p=uv(j),q=uv((j+1)%3),r=uv((j+2)%3);
  const length=Math.hypot(q[0]-p[0],q[1]-p[1]),height=Math.abs((q[0]-p[0])*(r[1]-p[1])-(q[1]-p[1])*(r[0]-p[0]))/length;
  if(pending.has(key)){
   const h=pending.get(key);if(h.a!==b||h.b!==a)throw new Error('Inconsistent oriented hinge');
   hinges.push({a:h.a,b:h.b,c:h.c,d:c,left:h.t,right:t,dualLength_m:(h.height+height)/3,restAngle_rad:0});pending.delete(key);
  }else pending.set(key,{a,b,c,t,height});
 }
 return hinges;
}
export function foldFields(positions,triangles,hinges){
 const angle=new Float64Array(hinges.length),curvature=new Float64Array(hinges.length),dualLength=new Float64Array(hinges.length),triangleAngle=new Float64Array(triangles.length/3),triangleCurvature=new Float64Array(triangles.length/3);
 for(let i=0;i<hinges.length;i++){
  const h=hinges[i],a=h.a*3,b=h.b*3,c=h.c*3,d=h.d*3;
  const ex=positions[b]-positions[a],ey=positions[b+1]-positions[a+1],ez=positions[b+2]-positions[a+2],el=Math.hypot(ex,ey,ez);
  const ux=positions[c]-positions[a],uy=positions[c+1]-positions[a+1],uz=positions[c+2]-positions[a+2],vx=positions[d]-positions[a],vy=positions[d+1]-positions[a+1],vz=positions[d+2]-positions[a+2];
  let nx=ey*uz-ez*uy,ny=ez*ux-ex*uz,nz=ex*uy-ey*ux,mx=vy*ez-vz*ey,my=vz*ex-vx*ez,mz=vx*ey-vy*ex;
  const nl=Math.hypot(nx,ny,nz),ml=Math.hypot(mx,my,mz);if(Math.min(el,nl,ml)<1e-14)throw new Error('Degenerate hinge geometry');
  nx/=nl;ny/=nl;nz/=nl;mx/=ml;my/=ml;mz/=ml;
  const sin=((ny*mz-nz*my)*ex+(nz*mx-nx*mz)*ey+(nx*my-ny*mx)*ez)/el;
  const theta=Math.atan2(sin,Math.max(-1,Math.min(1,nx*mx+ny*my+nz*mz))),degrees=theta*180/Math.PI,dual=(nl+ml)/(3*el),k=theta/dual;
  angle[i]=theta;curvature[i]=k;dualLength[i]=dual;
  for(const t of [h.left,h.right]){
   if(Math.abs(degrees)>Math.abs(triangleAngle[t]))triangleAngle[t]=degrees;
   if(Math.abs(k)>Math.abs(triangleCurvature[t]))triangleCurvature[t]=k;
  }
 }
 return {angle_rad:angle,curvature_per_m:curvature,currentDualLength_m:dualLength,triangleAngle_deg:triangleAngle,triangleCurvature_per_m:triangleCurvature};
}
