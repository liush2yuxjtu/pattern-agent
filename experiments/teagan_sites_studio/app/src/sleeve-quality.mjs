// Geometric acceptance for this unstructured set-in sleeve preview, not an industry fit standard.
const sub=(a,b)=>a.map((x,k)=>x-b[k]);
const dot=(a,b)=>a.reduce((s,x,k)=>s+x*b[k],0);
const unit=a=>{const d=Math.hypot(...a);return a.map(x=>x/(d||1));};
const cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
const angle=(a,b,plane=false)=>Math.acos(Math.max(-1,Math.min(1,plane?Math.abs(dot(a,b)):dot(a,b))))*180/Math.PI;
const key=(a,b)=>a<b?a+':'+b:b+':'+a;
function closest(p,a,b){const v=sub(b,a),t=Math.max(0,Math.min(1,dot(sub(p,a),v)/(dot(v,v)||1))),q=a.map((x,k)=>x+t*v[k]);return{distance:Math.hypot(...sub(p,q)),t};}
export function sleeveApex(part){
 let from=null,best=null;const consider=p=>{if(!best||p.y<best.y)best={...p};};
 for(const s of part.seamOps){if(s.type==='move'){from=s.to;continue;}if(!s.to)continue;if(s.edge==='cap'){
  consider(from);consider(s.to);
  if(s.type==='curve'){const a=-from.y+3*s.cp1.y-3*s.cp2.y+s.to.y,b=2*(from.y-2*s.cp1.y+s.cp2.y),c=s.cp1.y-from.y,roots=[];
   if(Math.abs(a)<1e-14){if(Math.abs(b)>1e-14)roots.push(-c/b);}else{const d=b*b-4*a*c;if(d>=0)roots.push((-b+Math.sqrt(d))/(2*a),(-b-Math.sqrt(d))/(2*a));}
   for(const t of roots)if(t>0&&t<1){const u=1-t;consider({x:u**3*from.x+3*u*u*t*s.cp1.x+3*u*t*t*s.cp2.x+t**3*s.to.x,y:u**3*from.y+3*u*u*t*s.cp1.y+3*u*t*t*s.cp2.y+t**3*s.to.y});}
  }
 }from=s.to;}return best;
}
function boundaryFaces(p){
 const incident=new Map();for(const t of p.triangles)for(let k=0;k<3;k++){const id=key(t[k],t[(k+1)%3]);if(!incident.has(id))incident.set(id,[]);incident.get(id).push(t[(k+2)%3]);}
 return p.boundary.map(e=>{const opposite=incident.get(key(e.a,e.b));if(opposite?.length!==1)throw Error('袖山检查发现非边界配缝');const a=p.vertices[e.a],b=p.vertices[e.b],c=p.vertices[opposite[0]],axis=unit(sub(b,a)),mid=a.map((x,k)=>(x+b[k])/2),v=sub(c,mid),normal=unit(cross(sub(b,a),sub(c,a))),inward=unit(v.map((x,k)=>x-dot(v,axis)*axis[k]));return{...e,a3:a,b3:b,normal,inward,uvA:p.points2d[e.a],uvB:p.points2d[e.b]};});
}
const stats=values=>{const a=values.slice().sort((x,y)=>x-y);return{count:a.length,mean:a.reduce((s,x)=>s+x,0)/a.length,p95:a[Math.max(0,Math.ceil(a.length*.95)-1)],max:a.at(-1)};};
function sleeveInterior(p){
 const normal=p.triangles.map(t=>unit(cross(sub(p.vertices[t[1]],p.vertices[t[0]]),sub(p.vertices[t[2]],p.vertices[t[0]])))),edges=new Map();
 p.triangles.forEach((t,f)=>{for(let k=0;k<3;k++){const a=t[k],b=t[(k+1)%3],id=key(a,b);if(!edges.has(id))edges.set(id,{a,b,faces:[]});edges.get(id).faces.push(f);}});
 const underarm=p.boundary.filter(e=>e.edge.startsWith('underarm')).map(e=>[p.points2d[e.a],p.points2d[e.b]]),values=[];let excluded=0;
 for(const e of edges.values()){if(e.faces.length!==2)continue;const a=p.points2d[e.a],b=p.points2d[e.b],mid=[(a.x+b.x)/2,(a.y+b.y)/2],near=Math.min(...underarm.map(([a,b])=>closest(mid,[a.x,a.y],[b.x,b.y]).distance));if(near<15){excluded++;continue;}values.push(angle(normal[e.faces[0]],normal[e.faces[1]]));}
 return{...stats(values),excludedNearUnderarmEdges:excluded,underarmExclusionMm:15};
}
export function auditSleeveQuality(panels,pattern){
 const apex=sleeveApex(pattern.parts.sleeve),bs=panels.map(boundaryFaces),sides=[];
 for(const[i,sign]of[[2,1],[3,-1]]){
  const cap=bs[i].filter(e=>e.edge==='cap').map(e=>{const reverse=e.uvA.x<e.uvB.x,start=reverse?e.uvB:e.uvA,end=reverse?e.uvA:e.uvB;return{...e,reverse,start,end,length:Math.hypot(end.x-start.x,end.y-start.y)};}).sort((a,b)=>(b.start.x+b.end.x)-(a.start.x+a.end.x));
  const total=cap.reduce((s,e)=>s+e.length,0),samples=[];let j=0,start=0;
  for(let s=2.5;s<total;s+=5){while(j<cap.length-1&&s>start+cap[j].length){start+=cap[j].length;j++;}const e=cap[j],t=(s-start)/e.length,uv={x:e.start.x*(1-t)+e.end.x*t,y:e.start.y*(1-t)+e.end.y*t};if(uv.y>apex.y*.65)continue;
   const u=e.reverse?1-t:t,p=e.a3.map((x,k)=>x*(1-u)+e.b3[k]*u),part=uv.x>=apex.x?0:1,arms=bs[part].filter(a=>a.edge==='armhole'&&(a.uvA.x+a.uvB.x)*sign>0);let best;
   for(const a of arms){const h=closest(p,a.a3,a.b3);if(!best||h.distance<best.distance)best={...h,edge:a};}
   if(!best)throw Error('袖山找不到对应袖窿');samples.push({sourceArcMm:s,sourceX:uv.x,sourceY:uv.y,planeAngleDeg:angle(e.normal,best.edge.normal,true),inwardTurnDeg:180-angle(e.inward,best.edge.inward),gapMm:best.distance*1000});
  }
  sides.push({part:panels[i].partId,planeAngleDeg:stats(samples.map(x=>x.planeAngleDeg)),inwardTurnDeg:stats(samples.map(x=>x.inwardTurnDeg)),interiorFoldDeg:sleeveInterior(panels[i]),samples});
 }
 let mirrorMax=0;const right=panels[2],left=panels[3];if(right.vertices.length!==left.vertices.length)mirrorMax=Infinity;else for(let i=0;i<right.vertices.length;i++){const a=right.vertices[i],b=left.vertices[i];mirrorMax=Math.max(mirrorMax,Math.hypot(a[0]+b[0],a[1]-b[1],a[2]-b[2])*1000);}
 const limits={upperCapPlaneP95Deg:30,upperCapInwardTurnMaxDeg:45,sleeveMirrorMaxMm:.5,interiorFoldP95Deg:25,interiorFoldMaxDeg:45},pass=mirrorMax<=limits.sleeveMirrorMaxMm&&sides.every(s=>s.samples.length>=10&&s.planeAngleDeg.p95<=limits.upperCapPlaneP95Deg&&s.inwardTurnDeg.max<=limits.upperCapInwardTurnMaxDeg&&s.interiorFoldDeg.p95<=limits.interiorFoldP95Deg&&s.interiorFoldDeg.max<=limits.interiorFoldMaxDeg);
 return{schema:'set-in-sleeve-surface-quality/1',status:pass?'PASS':'FAIL',scopeZh:'本次无结构装袖预览的平顺性工程检查',sampling:'source cap arc 2.5+5k mm; upper normalized cap height >=0.65; no shading normals',apexMm:apex,limits,sleeveMirrorMaxMm:mirrorMax,sides};
}
