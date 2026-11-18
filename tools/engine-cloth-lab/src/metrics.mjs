// Dimensionless geometric measurements. These are not a constitutive stress model.
export function triangleStretch(uv, xyz) {
  const [u0,u1,u2]=uv, [p0,p1,p2]=xyz;
  const a=u1[0]-u0[0], b=u2[0]-u0[0], c=u1[1]-u0[1], d=u2[1]-u0[1];
  const determinant=(a*d-b*c)*1e-6;
  if(!Number.isFinite(determinant)||Math.abs(determinant)<1e-16) return {valid:false};
  const inv=[d*.001/determinant,-b*.001/determinant,-c*.001/determinant,a*.001/determinant];
  const e=p1.map((x,k)=>x-p0[k]), f=p2.map((x,k)=>x-p0[k]);
  const x=e.map((v,k)=>v*inv[0]+f[k]*inv[2]), y=e.map((v,k)=>v*inv[1]+f[k]*inv[3]);
  const dot=(v,w)=>v.reduce((s,t,k)=>s+t*w[k],0), xx=dot(x,x), yy=dot(y,y), xy=dot(x,y);
  const max=Math.sqrt(Math.max(0,(xx+yy+Math.hypot(xx-yy,2*xy))/2));
  const cross=[x[1]*y[2]-x[2]*y[1],x[2]*y[0]-x[0]*y[2],x[0]*y[1]-x[1]*y[0]];
  const areaRatio=Math.hypot(...cross), min=max>0?areaRatio/max:0;
  return {valid:[max,min,areaRatio].every(Number.isFinite),max,min,areaRatio,restAreaM2:Math.abs(determinant)/2};
}

export function measure(mesh,positions) {
  const p=i=>Array.from(positions.slice(i*3,i*3+3));
  const triangles=mesh.triangles.map((ids,index)=>({index,panel:mesh.panelOfVertex[ids[0]],...triangleStretch(ids.map(i=>mesh.restXY[i]),ids.map(p))}));
  const valid=triangles.filter(t=>t.valid), area=valid.reduce((s,t)=>s+t.restAreaM2,0);
  const seams=mesh.seams.map(s=>{
    const gaps=s.pairs.map(([a,b])=>Math.hypot(...p(a).map((v,k)=>v-p(b)[k]))*1000).sort((a,b)=>a-b);
    return {id:s.id,pairs:gaps.length,maxMM:Math.max(0,...gaps),p95MM:gaps[Math.floor((gaps.length-1)*.95)]??0};
  });
  return {units:{position:'m',rest:'mm',strain:'dimensionless',gap:'mm'},finite:Array.from(positions).every(Number.isFinite),triangles,
    maxStretch:Math.max(0,...valid.map(t=>t.max)),minStretch:Math.min(Infinity,...valid.map(t=>t.min)),
    areaOver20Percent:area?valid.filter(t=>t.max>1.2).reduce((s,t)=>s+t.restAreaM2,0)/area:null,
    invalidTriangleCount:triangles.length-valid.length,seams,maxSeamGapMM:Math.max(0,...seams.map(s=>s.maxMM)),
    physicalStress:{status:'UNKNOWN',reason:'No calibrated anisotropic constitutive law or material parameters.'},
    pressure:{status:'UNKNOWN',reason:'No calibrated contact-pressure reconstruction.'}};
}

export function foldAngles(mesh,positions) {
  const edgeMap=new Map(),normals=mesh.triangles.map(ids=>{
    const p=ids.map(i=>Array.from(positions.slice(i*3,i*3+3))),a=p[1].map((v,k)=>v-p[0][k]),b=p[2].map((v,k)=>v-p[0][k]);
    const n=[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]],d=Math.hypot(...n);
    return n.map(x=>d?x/d:0);
  }),values=new Float32Array(normals.length);
  mesh.triangles.forEach((ids,t)=>{for(let k=0;k<3;k++){
    const key=[ids[k],ids[(k+1)%3]].sort((a,b)=>a-b).join(':');
    if(edgeMap.has(key)){const o=edgeMap.get(key),a=normals[o],b=normals[t];const deg=Math.acos(Math.max(-1,Math.min(1,a.reduce((s,x,k)=>s+x*b[k],0))))*180/Math.PI;values[t]=Math.max(values[t],deg);values[o]=Math.max(values[o],deg);}else edgeMap.set(key,t);
  }});
  return {values:Array.from(values),unit:'degree',meaning:'Adjacent-triangle angle, geometric fold proxy; mesh-dependent, not a fabric quality grade.'};
}
