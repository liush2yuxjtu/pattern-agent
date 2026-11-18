import {SelfContact} from '../../freesewing_cloth_lab/source/self-contact.js';

// A finite DISCRETE accepted-step safeguard. It never untangles an invalid
// reference, certifies a swept interval, or approves body contact/dynamics.
const EPSILON=1e-6,NUMERICAL=Math.max(EPSILON*1e-4,1e-12);
const sub=(a,b)=>[a[0]-b[0],a[1]-b[1],a[2]-b[2]];
const dot=(a,b)=>a[0]*b[0]+a[1]*b[1]+a[2]*b[2];
const cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
const norm=v=>Math.hypot(v[0],v[1],v[2]);
const area2=polygon=>polygon.reduce((sum,p,i)=>{const q=polygon[(i+1)%polygon.length];return sum+p[0]*q[1]-p[1]*q[0];},0)/2;

function coplanarArea(a,b,normal){
 let drop=0;for(let i=1;i<3;i++)if(Math.abs(normal[i])>Math.abs(normal[drop]))drop=i;
 const axes=[0,1,2].filter(i=>i!==drop),clip=b.map(p=>axes.map(i=>p[i])),orientation=Math.sign(area2(clip));
 if(!orientation)return 0;let polygon=a.map(p=>axes.map(i=>p[i]));
 for(let i=0;i<3&&polygon.length;i++){
  const p=clip[i],q=clip[(i+1)%3],side=x=>orientation*((q[0]-p[0])*(x[1]-p[1])-(q[1]-p[1])*(x[0]-p[0])),next=[];
  let old=polygon.at(-1),oldDistance=side(old);
  for(const current of polygon){
   const distance=side(current);
   if((oldDistance>=0)!==(distance>=0)){const t=oldDistance/(oldDistance-distance);next.push([old[0]+t*(current[0]-old[0]),old[1]+t*(current[1]-old[1])]);}
   if(distance>=0)next.push(current);old=current;oldDistance=distance;
  }
  polygon=next;
 }
 // The existing independent gate measures this projected area, with epsilon².
 return polygon.length>=3?Math.abs(area2(polygon)):0;
}

function triangleData(positions,ids){
 const points=ids.map(id=>[positions[id*3],positions[id*3+1],positions[id*3+2]]),edges=points.map((p,i)=>sub(points[(i+1)%3],p)),rawNormal=cross(edges[0],edges[1]),doubleArea=norm(rawNormal);
 return {ids,points,edges,rawNormal,doubleArea,normal:doubleArea>0?rawNormal.map(x=>x/doubleArea):[0,0,0],degenerate:doubleArea<=EPSILON**2,
  lo:[0,1,2].map(k=>Math.min(...points.map(p=>p[k]))),hi:[0,1,2].map(k=>Math.max(...points.map(p=>p[k])))};
}
function actualOverlap(a,b){
 if(a.degenerate||b.degenerate)return null;
 const da=a.points.map(p=>dot(sub(p,b.points[0]),b.normal)),db=b.points.map(p=>dot(sub(p,a.points[0]),a.normal));
 const parallel=norm(cross(a.normal,b.normal))<=1e-10;
 if(parallel){
  if(Math.max(...da.map(Math.abs))>NUMERICAL)return null;
  const area=coplanarArea(a.points,b.points,a.normal);return area>EPSILON**2?{coplanar:true}:null;
 }
 // Proper crossings straddle BOTH planes. A shared point, shared edge or edge
 // resting on another face is a boundary contact, not a proper intersection.
 if(!(Math.min(...da)<-EPSILON&&Math.max(...da)>EPSILON&&Math.min(...db)<-EPSILON&&Math.max(...db)>EPSILON))return null;
 const axes=[a.rawNormal,b.rawNormal,...a.edges.flatMap(e=>b.edges.map(f=>cross(e,f)))],origin=a.points[0];
 for(const axis of axes){
  const length=norm(axis);if(length<=1e-14)continue;
  const n=axis.map(x=>x/length),pa=a.points.map(p=>dot(sub(p,origin),n)),pb=b.points.map(p=>dot(sub(p,origin),n));
  const amin=Math.min(...pa),amax=Math.max(...pa),bmin=Math.min(...pb),bmax=Math.max(...pb),overlap=Math.min(amax,bmax)-Math.max(amin,bmin);
  if(overlap<-NUMERICAL)return null;
  if(amax-amin>NUMERICAL&&bmax-bmin>NUMERICAL&&overlap<=NUMERICAL)return null;
 }
 return {coplanar:false};
}

function flatIndices(triangles,count){
 if(!triangles||!triangles.length)throw new TypeError('A nonempty complete triangle index array is required');
 const flat=typeof triangles[0]==='number'?Array.from(triangles):Array.from(triangles,t=>Array.from(t)).flat();
 if(flat.length%3||flat.some(id=>!Number.isInteger(id)||id<0||id>=count))throw new RangeError('Triangle indices are invalid or out of range');
 return flat;
}
function positions32(value,name,length){
 if(!value||!Number.isSafeInteger(value.length)||value.length===0||value.length%3||length!==undefined&&value.length!==length)throw new TypeError(name+' must be a compatible nonempty flat xyz array');
 const result=new Float32Array(value.length);
 for(let i=0;i<value.length;i++){if(!Number.isFinite(value[i]))throw new TypeError(name+' contains a nonfinite coordinate');result[i]=value[i];if(!Number.isFinite(result[i]))throw new RangeError(name+' exceeds Float32 coordinate range');}
 return result;
}
function overlapBuffers(a,b){
 if(!a||!b)return false;if(a===b)return true;
 return ArrayBuffer.isView(a)&&ArrayBuffer.isView(b)&&a.buffer===b.buffer&&a.byteOffset<b.byteOffset+b.byteLength&&b.byteOffset<a.byteOffset+a.byteLength;
}

// Keep only leaf membership/hierarchy from the supplied BVH. All coordinates
// and node bounds are rebuilt from EACH actual Float32 trial; no supplied
// geometry, native bounds, triangle order, or tree state is written/refitted.
function topology(tree,flat,count){
 const geometry=tree?.geometry,index=geometry?.index;
 if(!geometry||geometry.getAttribute('position')?.count!==count||!index||index.count!==flat.length||flat.some((id,i)=>index.array[i]!==id))throw new TypeError('BVH does not contain the complete matching mesh');
 const records=[],roots=[],stack=[],seen=new Uint8Array(flat.length/3);
 tree.traverse((depth,leaf,bounds,offset,size)=>{
  const node={children:[],faces:[],lo:[0,0,0],hi:[0,0,0]};records.push(node);
  if(depth)stack[depth-1].children.push(node);else roots.push(node);stack[depth]=node;
  if(leaf)for(let i=offset;i<offset+size;i++){
   const face=tree.resolveTriangleIndex(i);if(!Number.isInteger(face)||face<0||face>=seen.length||seen[face])throw new TypeError('BVH leaf membership is incomplete or duplicated');
   seen[face]=1;node.faces.push(face);
  }
 });
 if(seen.some(x=>x!==1))throw new TypeError('BVH omits actual triangles');
 return {records,roots,triangleCount:seen.length};
}
function inspect(positions,ids,hierarchy){
 const triangles=ids.map(face=>triangleData(positions,face)),degenerateTriangleIndices=[];
 for(let i=0;i<triangles.length;i++)if(triangles[i].degenerate)degenerateTriangleIndices.push(i);
 for(let i=hierarchy.records.length-1;i>=0;i--){
  const node=hierarchy.records[i];node.lo.fill(Infinity);node.hi.fill(-Infinity);
  for(const face of node.faces)for(let k=0;k<3;k++){node.lo[k]=Math.min(node.lo[k],triangles[face].lo[k]);node.hi[k]=Math.max(node.hi[k],triangles[face].hi[k]);}
  for(const child of node.children)for(let k=0;k<3;k++){node.lo[k]=Math.min(node.lo[k],child.lo[k]);node.hi[k]=Math.max(node.hi[k],child.hi[k]);}
 }
 const pairs=[];let shared0=0,shared1=0,unsupportedShared2=0,unsupportedShared3=0,coplanarPairs=0;
 for(let a=0;a<triangles.length;a++){
  const left=triangles[a],stack=hierarchy.roots.slice();
  while(stack.length){
   const node=stack.pop();if([0,1,2].some(k=>left.lo[k]-EPSILON>node.hi[k]||left.hi[k]+EPSILON<node.lo[k]))continue;
   if(node.children.length){stack.push(...node.children);continue;}
   for(const b of node.faces){
    if(b<=a)continue;const right=triangles[b],hit=actualOverlap(left,right);if(!hit)continue;
    const shared=left.ids.filter(id=>right.ids.includes(id)).length;pairs.push([a,b]);if(hit.coplanar)coplanarPairs++;
    if(shared===0)shared0++;else if(shared===1)shared1++;else if(shared===2)unsupportedShared2++;else unsupportedShared3++;
   }
  }
 }
 pairs.sort((a,b)=>a[0]-b[0]||a[1]-b[1]);
 return {pairCount:pairs.length,pairs,shared0,shared1,unsupportedShared2,unsupportedShared3,coplanarPairs,degenerateTriangles:degenerateTriangleIndices.length,degenerateTriangleIndices,triangleCount:triangles.length,bvhTriangleCount:hierarchy.triangleCount};
}
const valid=report=>report.pairCount===0&&report.degenerateTriangles===0;
function displacement(a,b){let squared=0,maximum=0;for(let i=0;i<a.length;i+=3){const distance=Math.hypot(a[i]-b[i],a[i+1]-b[i+1],a[i+2]-b[i+2]);squared+=distance*distance;maximum=Math.max(maximum,distance);}return {norm:Math.sqrt(squared),maximum};}

export class InvalidSelfStepReferenceError extends Error{
 constructor(report){super(`Self-step reference is invalid: ${report.pairCount} overlapping pairs, ${report.degenerateTriangles} degenerate triangles`);this.name='InvalidSelfStepReferenceError';this.code='INVALID_REFERENCE';this.referenceReport=report;}
}

/**
 * guardSelfStep(candidate,reference,previous,inverseMass,triangles,tree?,options?)
 *
 * Pure by default: all inputs, including any supplied BVH, remain unchanged.
 * Positions are converted to owned Float32 trials before ANY geometry decision.
 * previous may be null. Its returned copy keeps Float32 precision when the
 * supplied previous is Float32; otherwise Float64. Correction uses exactly
 * previous += .8*(acceptedFloat32-candidateFloat32).
 *
 * Reference overlap/degeneracy throws InvalidSelfStepReferenceError. A fixed
 * node (inverseMass=0) must already be identical and Float32-representable in
 * candidate/reference; mismatches throw rather than moving the fixed node.
 * Trials use one alpha for ALL movable vertices: 1,1/2,1/4,...; no faces/vertices
 * are deleted. Degenerate trials and shared2/shared3 overlaps are rejected.
 *
 * maxBacktracks defaults to32. Budget exhaustion returns the verified reference
 * with alpha0/fallbackToReference=true. A nonzero proposed Float32 displacement
 * with zero stored progress is status='stalled',accepted=false, even at alpha>0.
 * Geometric safety of that returned reference is not acceptance of a physical
 * step or permission to advance its clock.
 *
 * options.inPlace=true writes only candidate and optional previous, after all
 * validation/selection. Aliasing with reference/metadata/tree or each other is
 * rejected. In-place also writes an explicit stalled rollback; callers must
 * stop/reject the physical step when accepted=false. Body contact, arm routing,
 * seam/material conditions and swept collisions require separate validation.
 */
export function guardSelfStep(candidate,reference,previous,inverseMass,triangles,tree=null,options={}){
 const current=positions32(candidate,'candidate'),origin=positions32(reference,'reference',current.length),count=current.length/3,flat=flatIndices(triangles,count),ids=Array.from({length:flat.length/3},(_,i)=>flat.slice(i*3,i*3+3));
 if(!inverseMass||inverseMass.length!==count||Array.from(inverseMass).some(w=>!Number.isFinite(w)||w<0))throw new TypeError('Inverse masses must be compatible, finite and nonnegative');
 if(previous!==null&&previous!==undefined&&(!previous||previous.length!==current.length||Array.from(previous).some(x=>!Number.isFinite(x))))throw new TypeError('previous must be null or compatible finite coordinates');
 const maxBacktracks=options.maxBacktracks===undefined?32:options.maxBacktracks,inPlace=options.inPlace===true;
 if(!Number.isSafeInteger(maxBacktracks)||maxBacktracks<0||maxBacktracks>1022)throw new RangeError('maxBacktracks must be an integer between0 and1022');
 if(options.inPlace!==undefined&&typeof options.inPlace!=='boolean')throw new TypeError('inPlace must be boolean');
 if(options.intersectionEpsilon!==undefined&&options.intersectionEpsilon!==EPSILON)throw new RangeError('The self-step guard uses the unchanged1e-6m intersection epsilon');
 let fixedVertexCount=0;
 for(let id=0;id<count;id++)if(inverseMass[id]===0){
  fixedVertexCount++;
  for(let k=0;k<3;k++){const i=id*3+k;if(!Object.is(candidate[i],current[i])||!Object.is(reference[i],origin[i])||!Object.is(current[i],origin[i]))throw new RangeError('Fixed nodes must be unchanged Float32 coordinates in candidate and reference');}
 }
 if(inPlace){
  const metadata=[reference,inverseMass,triangles,...(typeof triangles[0]==='number'?[]:Array.from(triangles)),tree?.geometry?.getAttribute('position')?.array,tree?.geometry?.index?.array];
  if(metadata.some(value=>overlapBuffers(candidate,value)||previous&&overlapBuffers(previous,value))||previous&&overlapBuffers(candidate,previous))throw new TypeError('In-place output aliases reference, previous or protected mesh data');
 }
 let owner=null;
 try{
  if(!tree){owner=new SelfContact(origin,flat,0);tree=owner.tree;}
  const hierarchy=topology(tree,flat,count),referenceReport=inspect(origin,ids,hierarchy);let geometryEvaluations=1;
  if(!valid(referenceReport))throw new InvalidSelfStepReferenceError(referenceReport);
  const rejected=[];let alpha=1,iterations=0,positions=current.slice(),report=inspect(positions,ids,hierarchy),fallbackToReference=false;geometryEvaluations++;
  while(!valid(report)){
   rejected.push({alpha,...report});
   if(iterations>=maxBacktracks){positions=origin.slice();report=referenceReport;alpha=0;fallbackToReference=true;break;}
   iterations++;alpha=2**(-iterations);positions=new Float32Array(current.length);
   for(let id=0;id<count;id++)for(let k=0;k<3;k++){const i=id*3+k;positions[i]=inverseMass[id]===0?current[i]:Math.fround(origin[i]+alpha*(current[i]-origin[i]));}
   report=inspect(positions,ids,hierarchy);geometryEvaluations++;
  }
  const proposed=displacement(current,origin),accepted=displacement(positions,origin),rollback=displacement(positions,current),zeroStoredProgress=accepted.norm===0,stalled=proposed.norm>0&&zeroStoredProgress;
  let updatedPrevious=null;
  if(previous!==null&&previous!==undefined){
   updatedPrevious=previous instanceof Float32Array?previous.slice():Float64Array.from(previous);
   for(let i=0;i<updatedPrevious.length;i++){const rollback=positions[i]-current[i];if(rollback!==0)updatedPrevious[i]+=.8*rollback;if(!Number.isFinite(updatedPrevious[i]))throw new RangeError('Rollback previous-coordinate synchronization exceeded numeric range');}
  }
  if(inPlace){for(let i=0;i<positions.length;i++)candidate[i]=positions[i];if(updatedPrevious)for(let i=0;i<updatedPrevious.length;i++)previous[i]=updatedPrevious[i];}
  return {accepted:!stalled,status:stalled?'stalled':alpha===1?'accepted':'backtracked',positions,previous:updatedPrevious,alpha,iterations,geometryEvaluations,
   rejectedCandidates:rejected.length,rejectedPairCounts:rejected.map(row=>row.pairCount),rejected,referenceReport,acceptedReport:report,
   globalRollbackNorm:rollback.norm,maxVertexRollback:rollback.maximum,acceptedDisplacementNorm:accepted.norm,proposedDisplacementNorm:proposed.norm,
   fallbackToReference,zeroStoredProgress,fixedVertexCount,triangleCount:ids.length,bvhTriangleCount:hierarchy.triangleCount,inPlace,
   intersectionEpsilon:EPSILON,continuousCollisionDetection:false,physicalAcceptance:'NOT_EVALUATED'};
 }finally{owner?.dispose();}
}
