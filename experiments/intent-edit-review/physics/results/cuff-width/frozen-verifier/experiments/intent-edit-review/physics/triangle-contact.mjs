// Current triangle-crossing response for the research Jacobi contact backend.
// This is not CCD, a global untangling proof, or a garment acceptance test.
const sub=(a,b)=>[a[0]-b[0],a[1]-b[1],a[2]-b[2]];
const dot=(a,b)=>a[0]*b[0]+a[1]*b[1]+a[2]*b[2];
const cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
const length=a=>Math.hypot(...a);
const lerp=(a,b,t)=>a.map((x,k)=>x+t*(b[k]-x));
const centroid=t=>[0,1,2].map(k=>(t[0][k]+t[1][k]+t[2][k])/3);
const normal=t=>{const n=cross(sub(t[1],t[0]),sub(t[2],t[0])),l=length(n);return l>1e-20?n.map(x=>x/l):null;};
const signedArea=p=>p.reduce((s,a,i)=>{const b=p[(i+1)%p.length];return s+a[0]*b[1]-a[1]*b[0];},0)/2;

function clippedArea(a,b,n){
 let drop=0;for(let k=1;k<3;k++)if(Math.abs(n[k])>Math.abs(n[drop]))drop=k;
 const axes=[0,1,2].filter(k=>k!==drop),project=p=>axes.map(k=>p[k]),clip=b.map(project),orientation=Math.sign(signedArea(clip));
 if(!orientation)return 0;
 let polygon=a.map(project);
 for(let i=0;i<3&&polygon.length;i++){
  const x=clip[i],y=clip[(i+1)%3],edge=[y[0]-x[0],y[1]-x[1]],side=p=>orientation*(edge[0]*(p[1]-x[1])-edge[1]*(p[0]-x[0])),next=[];
  let previous=polygon.at(-1),d0=side(previous);
  for(const current of polygon){
   const d1=side(current);
   if((d0>=0)!==(d1>=0)){const t=d0/(d0-d1);next.push([previous[0]+t*(current[0]-previous[0]),previous[1]+t*(current[1]-previous[1])]);}
   if(d1>=0)next.push(current);
   previous=current;d0=d1;
  }
  polygon=next;
 }
 return polygon.length>=3?Math.abs(signedArea(polygon))/Math.abs(n[drop]):0;
}

function planeSlice(triangle,distances,roundoff){
 const points=[];
 for(let i=0;i<3;i++){
  if(Math.abs(distances[i])<=roundoff)points.push(triangle[i]);
  const j=(i+1)%3;
  if(distances[i]*distances[j]<0)points.push(lerp(triangle[i],triangle[j],distances[i]/(distances[i]-distances[j])));
 }
 return points;
}

function overlap(a,b,na,nb,epsilon){
 if(!na||!nb)return null;
 const scale=Math.max(1,...a.flat().map(Math.abs),...b.flat().map(Math.abs)),roundoff=128*Number.EPSILON*scale;
 const da=a.map(p=>dot(sub(p,b[0]),nb)),db=b.map(p=>dot(sub(p,a[0]),na));
 if(Math.min(...da)>roundoff||Math.max(...da)<-roundoff||Math.min(...db)>roundoff||Math.max(...db)<-roundoff)return null;
 const line=cross(na,nb),lineLength=length(line);
 if(lineLength<=128*Number.EPSILON){
  if(Math.max(...da.map(Math.abs),...db.map(Math.abs))>roundoff)return null;
  const area=clippedArea(a,b,nb);
  return area>epsilon*epsilon?{coplanar:true,area_m2:area}:null;
 }
 const sa=planeSlice(a,da,roundoff),sb=planeSlice(b,db,roundoff);
 if(sa.length<2||sb.length<2)return null;
 const direction=line.map(x=>x/lineLength),pa=sa.map(p=>dot(p,direction)),pb=sb.map(p=>dot(p,direction));
 const interval=Math.min(Math.max(...pa),Math.max(...pb))-Math.max(Math.min(...pa),Math.min(...pb));
 if(interval<=epsilon)return null;
 // An edge lying on the interior of the other face is still a boundary-only
 // contact. Proper noncoplanar crossings straddle BOTH planes by the fixed
 // intersection epsilon; topology alone never decides this predicate.
 const crosses=d=>Math.min(...d)<-epsilon&&Math.max(...d)>epsilon;
 if(!crosses(da)||!crosses(db))return null;
 return {coplanar:false,intersectionLength_m:interval};
}

/** Current triangle geometry, with a fixed numerical intersection epsilon. */
export function trianglePairOverlap(a,b,epsilon=1e-6){
 if(!(epsilon>0)||!Number.isFinite(epsilon))throw Error('Intersection epsilon must be positive and finite');
 for(const tri of [a,b])if(tri.length!==3||tri.some(p=>p.length!==3||!p.every(Number.isFinite)))throw Error('A triangle must have three finite 3D points');
 return overlap(a,b,normal(a),normal(b),epsilon);
}

function flatIndices(triangles){
 const flat=triangles.length&&typeof triangles[0]!=='number'?Array.from(triangles,t=>Array.from(t)).flat():Array.from(triangles);
 if(flat.length%3||flat.some(x=>!Number.isInteger(x)||x<0))throw Error('Invalid triangle indices');
 return flat;
}

function historicalSide(history,a,b,shared,epsilon){
 const nb=normal(b.map(id=>[history[id*3],history[id*3+1],history[id*3+2]]));if(!nb)return null;
 const origin=shared.length?[history[shared[0]*3],history[shared[0]*3+1],history[shared[0]*3+2]]:centroid(b.map(id=>[history[id*3],history[id*3+1],history[id*3+2]]));
 const distances=a.filter(id=>!shared.includes(id)).map(id=>dot(sub([history[id*3],history[id*3+1],history[id*3+2]],origin),nb));
 if(distances.length&&Math.min(...distances)>epsilon)return 1;
 if(distances.length&&Math.max(...distances)<-epsilon)return -1;
 return null;
}

function snapshotNodeBounds(tree,points){
 if(!tree)return null;
 const records=[],stack=[],seen=new Uint8Array(points.length);
 tree.traverse((depth,isLeaf,bounds,offset,count)=>{
  const row={key:bounds.byteOffset/4,bounds:[Infinity,Infinity,Infinity,-Infinity,-Infinity,-Infinity],children:[]};
  if(depth)stack[depth-1].children.push(row);stack[depth]=row;records.push(row);
  if(isLeaf)for(let i=offset;i<offset+count;i++){
   const face=tree.resolveTriangleIndex(i);if(face<0||face>=points.length||seen[face])throw Error('Triangle contact BVH does not cover each face exactly once');
   seen[face]=1;
   for(const p of points[face])for(let k=0;k<3;k++){row.bounds[k]=Math.min(row.bounds[k],p[k]);row.bounds[k+3]=Math.max(row.bounds[k+3],p[k]);}
  }
 });
 if(seen.some(x=>x!==1))throw Error('Triangle contact BVH omits faces');
 const result=new Map();
 for(let i=records.length-1;i>=0;i--){const row=records[i];for(const child of row.children)for(let k=0;k<3;k++){
  row.bounds[k]=Math.min(row.bounds[k],child.bounds[k]);row.bounds[k+3]=Math.max(row.bounds[k+3],child.bounds[k+3]);
 }result.set(row.key,row.bounds);}
 return result;
}

/**
 * Gather on the SAME immutable snapshot used to refit tree. Never writes any
 * input coordinates. `add` is the parent's inverse-mass-weighted Jacobi proposal
 * callback (ids,coefficients,normal,residual,limit) -> accepted boolean.
 * Stable roles are A=lower face index, B=higher. A historically feasible sheet
 * side is preserved; an already-intersected history explicitly chooses +B normal.
 * There is no hidden module, tree-identity or across-solve side cache.
 */
export function gatherTriangleContacts(snapshot,history,inverseMass,triangles,tree,thickness,add,options={}){
 const count=snapshot.length/3,flat=flatIndices(triangles),nf=flat.length/3,epsilon=options.intersectionEpsilon??1e-6,limit=options.constraintLimit??.02;
 if(!Number.isInteger(count)||history.length!==snapshot.length||inverseMass.length!==count)throw Error('Incompatible triangle contact arrays');
 if(!Array.from(snapshot).every(Number.isFinite)||!Array.from(history).every(Number.isFinite)||Array.from(inverseMass).some(w=>!Number.isFinite(w)||w<0))throw Error('Triangle contact coordinates/masses must be finite with nonnegative inverse masses');
 if(!(thickness>0)||!(epsilon>0)||!(limit>0)||![thickness,epsilon,limit].every(Number.isFinite))throw Error('Invalid triangle contact distance/limit');
 if(flat.some(id=>id>=count))throw Error('Triangle vertex out of range');
 const geometry=tree?.geometry?.getAttribute('position');
 if(tree&&options.verifySnapshot!==false){
  if(!geometry||geometry.count!==count)throw Error('Triangle contact BVH has incompatible vertices');
  const index=tree.geometry.index;
  if(!index||index.count!==flat.length||flat.some((id,i)=>index.array[i]!==id))throw Error('Triangle contact BVH has incompatible triangle indices');
  for(let i=0;i<snapshot.length;i++)if(geometry.array[i]!==snapshot[i])throw Error('Triangle contact BVH is stale relative to immutable snapshot');
 }
 const ids=Array.from({length:nf},(_,i)=>flat.slice(i*3,i*3+3)),points=ids.map(face=>face.map(id=>[snapshot[id*3],snapshot[id*3+1],snapshot[id*3+2]])),normals=points.map(normal);
 // MeshBVH node storage is Float32. Reconstruct conservative current-snapshot
 // bounds from its exact leaf membership, rather than relying on rounded node
 // bounds for close intersections or large coordinates. This is pass-local.
 const nodeBounds=snapshotNodeBounds(tree,points);
 const profile={contacts:0,candidatePairs:0,intersectingPairs:0,shared0:0,shared1:0,unsupportedShared2:0,unsupportedShared3:0,coplanarPairs:0,historicalSides:0,initialPositiveBSides:0,fixedUnresolvedPairs:0,degenerateTriangles:normals.filter(n=>!n).length,triangleCount:nf,bvhTriangleCount:tree?nf:null};
 const pairs=[];
 for(let fa=0;fa<nf;fa++){
  if(!normals[fa])continue;
  const lo=[0,1,2].map(k=>Math.min(...points[fa].map(p=>p[k]))-epsilon),hi=[0,1,2].map(k=>Math.max(...points[fa].map(p=>p[k]))+epsilon),candidates=[];
  if(tree)tree.shapecast({intersectsBounds:(box,isLeaf,score,depth,node)=>{const bounds=nodeBounds.get(node);if(!bounds)throw Error('Triangle contact BVH node is missing');return lo[0]<=bounds[3]&&hi[0]>=bounds[0]&&lo[1]<=bounds[4]&&hi[1]>=bounds[1]&&lo[2]<=bounds[5]&&hi[2]>=bounds[2];},
   intersectsTriangle:(triangle,fb)=>{if(fb>fa)candidates.push(fb);return false;}});
  else for(let fb=fa+1;fb<nf;fb++)candidates.push(fb);
  candidates.sort((a,b)=>a-b);
  for(const fb of candidates){
   if(!normals[fb])continue;profile.candidatePairs++;
   const shared=ids[fa].filter(id=>ids[fb].includes(id));
   // Noncoplanar incident faces meet only along their shared edge, rather than
   // crossing interiors. Coplanar positive-area fold-over is tested below.
   if(shared.length>=2&&length(cross(normals[fa],normals[fb]))>128*Number.EPSILON)continue;
   const hit=overlap(points[fa],points[fb],normals[fa],normals[fb],epsilon);if(!hit)continue;
   profile.intersectingPairs++;if(hit.coplanar)profile.coplanarPairs++;
   if(shared.length>=2){profile[shared.length===2?'unsupportedShared2':'unsupportedShared3']++;pairs.push({faces:[fa,fb],shared:shared.length,supported:false,...hit});continue;}
   profile[shared.length===0?'shared0':'shared1']++;
   const prior=historicalSide(history,ids[fa],ids[fb],shared,epsilon),side=prior??1;
   if(prior===null)profile.initialPositiveBSides++;else profile.historicalSides++;
   const n=normals[fb].map(v=>v*side),origin=shared.length?points[fb][ids[fb].indexOf(shared[0])]:centroid(points[fb]);
   let accepted=false;
   // Freeze the selected plane and its support within this Jacobi batch. This
   // is a crossing-recovery constraint, not the gradient of exact triangle
   // distance. It stops generating once the proper current crossing is gone;
   // proximity constraints must enforce the remaining thickness separately.
   for(let i=0;i<3;i++){
    const vertex=ids[fa][i];if(shared.includes(vertex))continue;
    const residual=thickness-dot(sub(points[fa][i],origin),n);if(!(residual>0))continue;
    const supportIds=shared.length?[vertex,shared[0]]:[vertex,...ids[fb]],coefficients=shared.length?[1,-1]:[1,-1/3,-1/3,-1/3];
    if(!supportIds.some((id,j)=>inverseMass[id]>0&&coefficients[j]!==0))continue;
    if(add(supportIds,coefficients,n,residual,limit)){profile.contacts++;accepted=true;}
   }
   if(!accepted)profile.fixedUnresolvedPairs++;
   pairs.push({faces:[fa,fb],shared:shared.length,supported:true,side,sideSource:prior===null?'initial-positive-B-normal':'feasible-history',...hit});
  }
 }
 profile.pairs=pairs;profile.examples=pairs.slice(0,8);return profile;
}
