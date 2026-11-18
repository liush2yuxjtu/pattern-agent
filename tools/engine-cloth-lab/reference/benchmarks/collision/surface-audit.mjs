const sub=(a,b)=>[a[0]-b[0],a[1]-b[1],a[2]-b[2]];
const addScaled=(a,b,t)=>a.map((v,k)=>v+b[k]*t);
const dot=(a,b)=>a[0]*b[0]+a[1]*b[1]+a[2]*b[2];
const cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
const length=a=>Math.hypot(...a);
const distance=(a,b)=>length(sub(a,b));
const boundsOf=p=>[0,1,2].map(k=>Math.min(...p.map(v=>v[k]))).concat([0,1,2].map(k=>Math.max(...p.map(v=>v[k]))));
const boxOverlap=(a,b,e)=>a[0]<=b[3]+e&&a[3]+e>=b[0]&&a[1]<=b[4]+e&&a[4]+e>=b[1]&&a[2]<=b[5]+e&&a[5]+e>=b[2];
const unique=(points,e)=>points.filter((p,i)=>!points.slice(0,i).some(q=>distance(p,q)<=e));
function topology(triangles){
  const edges=new Map();
  for(const {ids} of triangles)for(let i=0;i<3;i++){
    const a=ids[i],b=ids[(i+1)%3],key=a<b?`${a}:${b}`:`${b}:${a}`,v=edges.get(key)||{count:0,orientation:0};
    v.count++;v.orientation+=a<b?1:-1;edges.set(key,v);
  }
  const values=[...edges.values()],boundaryEdges=values.filter(e=>e.count===1).length,nonManifoldEdges=values.filter(e=>e.count>2).length,inconsistentWindingEdges=values.filter(e=>e.count===2&&e.orientation!==0).length;
  return {closedManifold:boundaryEdges===0&&nonManifoldEdges===0&&inconsistentWindingEdges===0,boundaryEdges,nonManifoldEdges,inconsistentWindingEdges};
}

function meshTriangles(mesh,areaToleranceM2){
  const {positions:p,triangles:t}=mesh;
  if(!p?.length||p.length%3||!t?.length||t.length%3)throw new Error('Mesh requires xyz coordinates and triangle indices');
  if(!Array.from(p).every(Number.isFinite))throw new Error('Mesh positions must be finite');
  if(!Array.from(t).every(i=>Number.isInteger(i)&&i>=0&&i<p.length/3))throw new Error('Triangle index out of range');
  return Array.from({length:t.length/3},(_,index)=>{
    const ids=Array.from(t.slice(index*3,index*3+3)),points=ids.map(i=>Array.from(p.slice(i*3,i*3+3)));
    const n=cross(sub(points[1],points[0]),sub(points[2],points[0])),twiceArea=length(n);
    return {index,ids,points,bounds:boundsOf(points),normal:twiceArea?n.map(v=>v/twiceArea):[0,0,0],degenerate:twiceArea<=2*areaToleranceM2};
  });
}
function buildBVH(triangles,ids=triangles.map((_,i)=>i)){
  const bounds=[Infinity,Infinity,Infinity,-Infinity,-Infinity,-Infinity];
  for(const id of ids)for(let k=0;k<3;k++){bounds[k]=Math.min(bounds[k],triangles[id].bounds[k]);bounds[k+3]=Math.max(bounds[k+3],triangles[id].bounds[k+3]);}
  if(ids.length<=8)return {bounds,ids};
  const axis=[0,1,2].sort((a,b)=>(bounds[b+3]-bounds[b])-(bounds[a+3]-bounds[a]))[0];
  ids.sort((a,b)=>(triangles[a].bounds[axis]+triangles[a].bounds[axis+3])-(triangles[b].bounds[axis]+triangles[b].bounds[axis+3]));
  const mid=ids.length>>1;
  return {bounds,left:buildBVH(triangles,ids.slice(0,mid)),right:buildBVH(triangles,ids.slice(mid))};
}
function queryBVH(node,bounds,e,visit,counts){
  counts.bvhNodeVisits++;
  if(!boxOverlap(node.bounds,bounds,e))return;
  if(node.ids)for(const id of node.ids)visit(id);
  else{queryBVH(node.left,bounds,e,visit,counts);queryBVH(node.right,bounds,e,visit,counts);}
}
function barycentric(point,t){
  const e0=sub(t.points[1],t.points[0]),e1=sub(t.points[2],t.points[0]),v=sub(point,t.points[0]);
  const aa=dot(e0,e0),ab=dot(e0,e1),bb=dot(e1,e1),av=dot(e0,v),bv=dot(e1,v),den=aa*bb-ab*ab;
  if(den<=0)return null;
  const u=(bb*av-ab*bv)/den,w=(aa*bv-ab*av)/den;
  return [1-u-w,u,w];
}
function cutPlane(t,distances,e){
  const p=[];
  for(let i=0;i<3;i++){
    const j=(i+1)%3,a=distances[i],b=distances[j];
    if(Math.abs(a)<=e)p.push(t.points[i]);
    if(a>e&&b< -e||a< -e&&b>e)p.push(addScaled(t.points[i],sub(t.points[j],t.points[i]),a/(a-b)));
  }
  return unique(p,e);
}
const orient2=(a,b,c)=>(b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]);
function coplanarIntersection(a,b,e,areaToleranceM2){
  const drop=[0,1,2].sort((i,j)=>Math.abs(a.normal[j])-Math.abs(a.normal[i]))[0],axes=[0,1,2].filter(i=>i!==drop);
  const project=p=>axes.map(k=>p[k]);
  const clip=b.points.map(project),sign=Math.sign(orient2(...clip))||1;
  let poly=a.points.map(project);
  for(let i=0;i<3&&poly.length;i++){
    const c=clip[i],d=clip[(i+1)%3],out=[],edgeLength=Math.hypot(d[0]-c[0],d[1]-c[1]);
    for(let j=0;j<poly.length;j++){
      const s=poly[j],t=poly[(j+1)%poly.length],ds=sign*orient2(c,d,s)/edgeLength,dt=sign*orient2(c,d,t)/edgeLength;
      const si=ds>=-e,ti=dt>=-e;
      if(si)out.push(s);
      if(si!==ti){const f=ds/(ds-dt);out.push([s[0]+(t[0]-s[0])*f,s[1]+(t[1]-s[1])*f]);}
    }
    poly=out;
  }
  if(!poly.length)return {type:'none',points:[]};
  const areaProjected=Math.abs(poly.reduce((s,p,i)=>s+p[0]*poly[(i+1)%poly.length][1]-p[1]*poly[(i+1)%poly.length][0],0))/2;
  const areaM2=areaProjected/Math.abs(a.normal[drop]);
  const points=unique(poly.map(p=>{const q=[0,0,0];q[axes[0]]=p[0];q[axes[1]]=p[1];q[drop]=a.points[0][drop]-(a.normal[axes[0]]*(q[axes[0]]-a.points[0][axes[0]])+a.normal[axes[1]]*(q[axes[1]]-a.points[0][axes[1]]))/a.normal[drop];return q;}),e);
  return {type:areaM2>areaToleranceM2?'coplanar_overlap':'contact',points,overlapAreaM2:areaM2};
}
export function triangleIntersection(a,b,{linearToleranceM=1e-8,areaToleranceM2=1e-14}={}){
  const e=linearToleranceM;
  if(a.degenerate||b.degenerate)return {type:'degenerate',points:[]};
  const da=a.points.map(p=>dot(sub(p,b.points[0]),b.normal)),db=b.points.map(p=>dot(sub(p,a.points[0]),a.normal));
  if(da.every(d=>d>e)||da.every(d=>d< -e)||db.every(d=>d>e)||db.every(d=>d< -e))return {type:'none',points:[]};
  const direction=cross(a.normal,b.normal),norm=length(direction);
  if(norm<1e-12){
    if(da.every(d=>Math.abs(d)<=e)&&db.every(d=>Math.abs(d)<=e))return coplanarIntersection(a,b,e,areaToleranceM2);
    return {type:'uncertain_parallel',points:[]};
  }
  const pa=cutPlane(a,da,e),pb=cutPlane(b,db,e);
  if(!pa.length||!pb.length)return {type:'none',points:[]};
  const axis=[0,1,2].sort((i,j)=>Math.abs(direction[j])-Math.abs(direction[i]))[0];
  pa.sort((p,q)=>p[axis]-q[axis]);pb.sort((p,q)=>p[axis]-q[axis]);
  const lo=Math.max(pa[0][axis],pb[0][axis]),hi=Math.min(pa.at(-1)[axis],pb.at(-1)[axis]);
  const axisTolerance=e*Math.abs(direction[axis])/norm;
  if(hi<lo-axisTolerance)return {type:'none',points:[]};
  const source=pa.at(-1)[axis]-pa[0][axis]>axisTolerance?pa:pb;
  const den=source.at(-1)[axis]-source[0][axis];
  const at=x=>den?addScaled(source[0],sub(source.at(-1),source[0]),(x-source[0][axis])/den):source[0];
  const points=unique([at(lo),at(hi)],e),midpoint=at((lo+hi)/2);
  const ba=barycentric(midpoint,a),bb=barycentric(midpoint,b);
  const interior=ba&&bb&&ba.every(v=>v>1e-9)&&bb.every(v=>v>1e-9);
  return {type:points.length>1&&distance(points[0],points.at(-1))>e&&interior?'crossing':'contact',points,midpoint};
}
function pointSegmentDistance(p,a,b){const v=sub(b,a),den=dot(v,v),t=den?Math.max(0,Math.min(1,dot(sub(p,a),v)/den)):0;return distance(p,addScaled(a,v,t));}
function seamRoots(cloth,seams,e){
  const roots=Array.from({length:cloth.positions.length/3},(_,i)=>i);
  const find=i=>{while(roots[i]!==i){roots[i]=roots[roots[i]];i=roots[i];}return i;};
  let coincidentPairs=0;
  for(const [a,b] of seams||[]){if(!Number.isInteger(a)||!Number.isInteger(b)||a<0||b<0||a>=roots.length||b>=roots.length)throw new Error('Seam index out of range');if(distance(Array.from(cloth.positions.slice(a*3,a*3+3)),Array.from(cloth.positions.slice(b*3,b*3+3)))<=e){roots[find(b)]=find(a);coincidentPairs++;}}
  return {roots:roots.map((_,i)=>find(i)),coincidentPairs};
}
function localAdjacencyContact(a,b,result,roots,e){
  if(result.type!=='contact'||!result.points.length)return false;
  const shared=a.ids.filter(id=>b.ids.some(other=>roots[id]===roots[other]));
  if(!shared.length)return false;
  const points=shared.map(id=>a.points[a.ids.indexOf(id)]);
  return result.points.every(p=>points.some(q=>distance(p,q)<=e*5)||points.length>=2&&pointSegmentDistance(p,points[0],points[1])<=e*5);
}
function pairAudit(left,right,bvh,kind,e,areaToleranceM2,counts,{self=false,roots=null,maxExamples=64}={}){
  const crossings=[],contacts=[],coplanarOverlaps=[],uncertain=[],allCrossingPairs=[];
  let crossingCount=0,contactCount=0,coplanarOverlapCount=0,uncertainCount=0,excludedLocalContacts=0;
  for(const a of left)queryBVH(bvh,a.bounds,e,index=>{
    const b=right[index];if(self&&b.index<=a.index)return;
    counts.leafCandidates++;
    if(!boxOverlap(a.bounds,b.bounds,e))return;
    counts.trianglePairTests++;
    const r=triangleIntersection(a,b,{linearToleranceM:e,areaToleranceM2});
    if(r.type==='none'||r.type==='degenerate')return;
    if(self&&localAdjacencyContact(a,b,r,roots,e)){excludedLocalContacts++;return;}
    const pair=kind==='body'?{clothTriangle:a.index,bodyTriangle:b.index}:{triangleA:a.index,triangleB:b.index};
    const record={...pair,pointsM:r.points,...(r.midpoint?{midpointM:r.midpoint}:{}),...(r.overlapAreaM2!==undefined?{overlapAreaM2:r.overlapAreaM2}:{})};
    if(r.type==='crossing'){crossingCount++;allCrossingPairs.push(kind==='body'?[a.index,b.index]:[a.index,b.index]);if(crossings.length<maxExamples)crossings.push(record);}
    else if(r.type==='coplanar_overlap'){coplanarOverlapCount++;if(coplanarOverlaps.length<maxExamples)coplanarOverlaps.push(record);}
    else if(r.type==='uncertain_parallel'){uncertainCount++;if(uncertain.length<maxExamples)uncertain.push(record);}
    else{contactCount++;if(contacts.length<maxExamples)contacts.push(record);}
  },counts);
  return {status:crossingCount?'FAIL':coplanarOverlapCount||contactCount||uncertainCount?'REVIEW':'PASS',strictCrossingPairs:crossingCount,boundaryContactPairs:contactCount,coplanarOverlapPairs:coplanarOverlapCount,uncertainPairs:uncertainCount,excludedLocalAdjacencyContacts:excludedLocalContacts,allCrossingPairs,examples:{crossings,contacts,coplanarOverlaps,uncertain}};
}
export function auditSurfaceCollisions({cloth,body,bodyCollider=null,seams=[],selfCollision=true,linearToleranceM=1e-8,areaToleranceM2=1e-14,maxExamples=64}){
  if(!Number.isFinite(linearToleranceM)||!Number.isFinite(areaToleranceM2)||!(linearToleranceM>0)||!(areaToleranceM2>0))throw new Error('Finite positive tolerances required');
  if(!Number.isInteger(maxExamples)||maxExamples<0)throw new Error('maxExamples must be a nonnegative integer');
  const c=meshTriangles(cloth,areaToleranceM2),b=meshTriangles(body,areaToleranceM2),bodyBVH=buildBVH(b),bodyTopology=topology(b);
  const canTestInside=!!bodyCollider&&bodyTopology.closedManifold&&!b.some(t=>t.degenerate);
  const workCounts={clothVertices:cloth.positions.length/3,clothTriangles:c.length,bodyTriangles:b.length,vertexQueries:0,body:{bvhNodeVisits:0,leafCandidates:0,trianglePairTests:0},self:{bvhNodeVisits:0,leafCandidates:0,trianglePairTests:0}};
  const invalid={clothTriangles:c.filter(t=>t.degenerate).map(t=>t.index),bodyTriangles:b.filter(t=>t.degenerate).map(t=>t.index)};
  let insideCount=0,maxDepthM=0,minSignedDistanceM=Infinity;const insideExamples=[];
  if(canTestInside)for(let i=0;i<cloth.positions.length;i+=3){const p=cloth.positions.slice(i,i+3),q=bodyCollider.query(...p);workCounts.vertexQueries++;if(!Number.isFinite(q.signedDistance))throw new Error('Invalid body distance');minSignedDistanceM=Math.min(minSignedDistanceM,q.signedDistance);if(q.signedDistance< -linearToleranceM){insideCount++;maxDepthM=Math.max(maxDepthM,-q.signedDistance);if(insideExamples.length<maxExamples)insideExamples.push({vertex:i/3,positionM:Array.from(p),signedDistanceM:q.signedDistance,bodyTriangle:q.triangle});}}
  const vertexInside={status:canTestInside?(insideCount?'FAIL':'PASS'):'UNKNOWN',checked:workCounts.vertexQueries,count:canTestInside?insideCount:null,maxDepthM:canTestInside?maxDepthM:null,minSignedDistanceM:canTestInside?minSignedDistanceM:null,examples:insideExamples,...(!canTestInside?{reason:'Point-inside audit requires a supplied collider and a closed nondegenerate consistently oriented body mesh.'}:{})};
  const bodySurface=pairAudit(c,b,bodyBVH,'body',linearToleranceM,areaToleranceM2,workCounts.body,{maxExamples});
  const root=seamRoots(cloth,seams,linearToleranceM);
  const selfSurface=selfCollision?pairAudit(c,c,buildBVH(c),'self',linearToleranceM,areaToleranceM2,workCounts.self,{self:true,roots:root.roots,maxExamples}):{status:'UNKNOWN',reason:'Self surface audit disabled'};
  if(invalid.clothTriangles.length||invalid.bodyTriangles.length){if(bodySurface.status!=='FAIL')bodySurface.status='UNKNOWN';if(selfSurface.status!=='FAIL')selfSurface.status='UNKNOWN';}
  const statuses=[vertexInside.status,bodySurface.status,selfSurface.status];
  return {schema:'pattern-lab-surface-audit-1',units:'m',tolerances:{linearM:linearToleranceM,areaM2:areaToleranceM2},summary:{status:statuses.includes('FAIL')?'FAIL':statuses.includes('UNKNOWN')?'UNKNOWN':statuses.includes('REVIEW')?'REVIEW':'LIMITED_DISCRETE_CHECKS_PASS'},vertexInside,bodyTopology,bodySurface,selfSurface,invalidTriangles:invalid,coincidentSeamPairs:root.coincidentPairs,continuousCollision:{status:'UNKNOWN',reason:'Only the supplied instantaneous triangle surfaces are tested; no swept volumes or cloth thickness.'},workCounts,method:'BVH AABB candidates, triangle-plane intersection interval overlap, 2D coplanar clipping; strictly transverse interior crossings separated from contact and coplanar overlap.',limits:['A discrete surface audit does not certify continuous collision or finite-thickness clearance.','Only contacts confined to geometrically coincident shared vertices or shared edges are excluded. Crossings away from shared vertices remain tested.','Coplanar overlaps and nonlocal boundary contacts require review rather than being silently accepted.','Point-inside distances use the supplied body collider and require a closed body mesh.']};
}
