// Finite-thickness point / linearly moving closed triangle CCD.
// A null result needs a swept-AABB or Lipschitz clearance certificate. A finite
// budget, poor feature conditioning or floating-point resolution cannot silently
// certify clearance. This is floating-point conservative advancement, not an
// exact-predicate or certified interval-arithmetic CCD kernel.
const EPS=Number.EPSILON;
const clamp01=x=>Math.max(0,Math.min(1,x));
const sub=(a,b)=>[a[0]-b[0],a[1]-b[1],a[2]-b[2]];
const dot=(a,b)=>a[0]*b[0]+a[1]*b[1]+a[2]*b[2];
const cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
const norm=a=>Math.hypot(a[0],a[1],a[2]);
const unit=a=>{const n=norm(a);return n>0&&Number.isFinite(n)?a.map(x=>x/n):[0,0,0];};
const scaleOf=points=>Math.max(1,...points.flatMap(p=>Array.from(p,Math.abs)));
function requirePoint(point){if(!point||point.length!==3||!Array.from(point).every(Number.isFinite))throw new TypeError('A point must contain three finite coordinates');}
function tolerance(value,name){if(value===undefined)return 0;if(!Number.isFinite(value)||value<0)throw new RangeError(name+' must be finite and nonnegative');return value;}

// Compare each of the three boundary segment projections and the admissible
// plane projection. Degenerate closed triangles reduce to their boundary hull.
// The face solve uses normalized edges, avoiding a squared area determinant
// formed from raw metre coordinates and its cancellation near collinearity.
function closestInto(point,a,b,c,padding,out){
 const vertices=[a,b,c],e=sub(b,a),f=sub(c,a),le=norm(e),lf=norm(f),lc=norm(sub(c,b));
 if(![le,lf,lc].every(Number.isFinite))throw new RangeError('Triangle coordinate differences exceed numeric range');
 let best=Infinity;
 function candidate(wa,wb,wc,feature){
  if(![wa,wb,wc].every(Number.isFinite)||wa<0||wb<0||wc<0)return;
  const q=[a[0]+wb*e[0]+wc*f[0],a[1]+wb*e[1]+wc*f[1],a[2]+wb*e[2]+wc*f[2]],delta=sub(point,q),distance=norm(delta);
  if(!Number.isFinite(distance))throw new RangeError('Point/triangle separation exceeds numeric range');
  if(distance<best){best=distance;out.wa=wa;out.wb=wb;out.wc=wc;out.qx=q[0];out.qy=q[1];out.qz=q[2];out.dx=delta[0];out.dy=delta[1];out.dz=delta[2];out.feature=feature;}
 }
 for(let i=0;i<3;i++){
  const j=(i+1)%3,edge=sub(vertices[j],vertices[i]),length=norm(edge),relative=sub(point,vertices[i]);
  const direction=length>0?edge.map(x=>x/length):[0,0,0],t=length>0?clamp01(dot(relative,direction)/length):0,weights=[0,0,0];
  weights[i]=1-t;weights[j]=t;candidate(...weights,t===0||t===1?'vertex':'edge');
 }
 const E=le>0?e.map(x=>x/le):[0,0,0],F=lf>0?f.map(x=>x/lf):[0,0,0],n=cross(E,F),sin=norm(n),N=sin>0?n.map(x=>x/sin):[0,0,0];
 if(le>0&&lf>0&&sin>0){
  const w=sub(point,a),coordinateScale=Math.max(le,lf,norm(w)),W=w.map(x=>x/coordinateScale);
  const wb=dot(cross(W,F),N)/sin/(le/coordinateScale),wc=dot(cross(E,W),N)/sin/(lf/coordinateScale),wa=1-wb-wc;
  if(wa>=0&&wb>=0&&wc>=0)candidate(wa,wb,wc,'face');
 }
 const scale=scaleOf([point,a,b,c]),roundoffPadding=Math.max(128*EPS*scale,padding);
 // When the normalized area is tiny the face classification is ill-conditioned.
 // Boundary distance overestimates the true triangle distance by at most its
 // smallest altitude. Retaining twice that width (plus roundoff) prevents a
 // missed interior candidate from authorizing an unsafe conservative advance.
 const longest=Math.max(le,lf,lc),altitude=longest>0?Math.min(le,lf)*(Math.max(le,lf)/longest)*sin:0;
 const conditioningAllowance=sin>0&&sin<1e-6?2*altitude:0;
 out.distance=best;out.roundoffPadding=roundoffPadding;out.conditioningAllowance=conditioningAllowance;
 out.distanceUncertainty=roundoffPadding+conditioningAllowance;out.distanceLowerBound=Math.max(0,best-out.distanceUncertainty);
 out.normalDefined=best>0;out.nx=N[0];out.ny=N[1];out.nz=N[2];out.faceNormalDefined=sin>0;
 return out;
}

/** Closest point on the entire closed triangle, including edges/vertices. */
export function pointTriangleClosest(point,a,b,c,options={}){
 for(const p of [point,a,b,c])requirePoint(p);
 const closest=closestInto(point,a,b,c,tolerance(options.distanceTolerance,'distanceTolerance'),{}),barycentric=[closest.wa,closest.wb,closest.wc];
 return {barycentric,weights:barycentric.slice(),point:Array.from(point),pointTriangle:[closest.qx,closest.qy,closest.qz],
  normal:closest.normalDefined?[closest.dx/closest.distance,closest.dy/closest.distance,closest.dz/closest.distance]:[0,0,0],
  normalDefined:closest.normalDefined,faceNormal:[closest.nx,closest.ny,closest.nz],faceNormalDefined:closest.faceNormalDefined,
  distance:closest.distance,distanceLowerBound:closest.distanceLowerBound,distanceUncertainty:closest.distanceUncertainty,
  roundoffPadding:closest.roundoffPadding,conditioningAllowance:closest.conditioningAllowance,feature:closest.feature};
}

function boxSeparation(starts,ends){
 const gap=[0,0,0];
 for(let k=0;k<3;k++){
  const pointLow=Math.min(starts[0][k],ends[0][k]),pointHigh=Math.max(starts[0][k],ends[0][k]);
  const triangleLow=Math.min(starts[1][k],starts[2][k],starts[3][k],ends[1][k],ends[2][k],ends[3][k]);
  const triangleHigh=Math.max(starts[1][k],starts[2][k],starts[3][k],ends[1][k],ends[2][k],ends[3][k]);
  gap[k]=Math.max(0,pointLow-triangleHigh,triangleLow-pointHigh);
 }
 return Math.hypot(...gap);
}
function speedBound(velocities){
 // Move to the query point's translational frame. Every triangle material point
 // has a convex combination of the three relative vertex velocities, hence
 // ||vp-vtri|| <= max_i ||vp-vi||. The same bound controls Hausdorff motion of
 // the triangle and the scalar closest distance, even at feature changes or
 // degenerate intermediate triangles. A common translation cancels exactly in
 // the mathematical bound; absolute world position is not part of this speed.
 const raw=Math.max(...velocities.slice(1).map(v=>norm(sub(v,velocities[0]))));
 if(!Number.isFinite(raw))throw new RangeError('Relative point/triangle motion exceeds numeric range');
 return raw===0?0:raw*(1+256*EPS);
}
function workspace(){return {points:Array.from({length:4},()=>[0,0,0]),closest:{}};}

function motionQuery(starts,ends,velocities,thickness,settings,scale,scratch){
 const padding=Math.max(256*EPS*scale,settings.distanceTolerance);
 if(boxSeparation(starts,ends)>thickness+padding)return null;
 const speed=speedBound(velocities),p=scratch.points;
 let time=0,iterations=0,evaluations=0;
 function at(t){for(let i=0;i<4;i++)for(let k=0;k<3;k++)p[i][k]=starts[i][k]+t*velocities[i][k];return p;}
 function evaluate(t){evaluations++;at(t);return closestInto(p[0],p[1],p[2],p[3],padding,scratch.closest);}
 let closest=evaluate(0);
 function result(status,reason){
  const weights=[closest.wa,closest.wb,closest.wc],oldDelta=[0,1,2].map(k=>starts[0][k]-weights.reduce((sum,w,i)=>sum+w*starts[i+1][k],0));
  let normal=closest.normalDefined?[closest.dx/closest.distance,closest.dy/closest.distance,closest.dz/closest.distance]:[0,0,0],normalSource='current-separation';
  if(!closest.normalDefined){
   if(norm(oldDelta)>padding){normal=unit(oldDelta);normalSource='historical-side';}
   else if(closest.faceNormalDefined){normal=[closest.nx,closest.ny,closest.nz];normalSource='face-normal';}
   else{
    const relative=[0,1,2].map(k=>velocities[0][k]-weights.reduce((sum,w,i)=>sum+w*velocities[i+1][k],0));
    normal=unit(relative.map(x=>-x));normalSource='opposite-relative-motion';
   }
  }
  if(norm(oldDelta)>padding&&dot(normal,oldDelta)<0)normal=normal.map(x=>-x);
  const normalDefined=norm(normal)>0;if(!normalDefined)normalSource='undefined-degenerate';
  return {time,barycentric:weights,weights:weights.slice(),normal,normalDefined,normalSource,
   point:[...p[0]],pointTriangle:[closest.qx,closest.qy,closest.qz],feature:closest.feature,
   faceNormal:[closest.nx,closest.ny,closest.nz],faceNormalDefined:closest.faceNormalDefined,
   distance:closest.distance,distanceLowerBound:closest.distanceLowerBound,distanceUncertainty:closest.distanceUncertainty,
   conditioningAllowance:closest.conditioningAllowance,thickness,status,reason,
   contact:status==='contact',conservative:status==='conservative',uncertain:status==='uncertain',
   possibleInterval:[time,1],clearedUntil:time,iterations,evaluations,speedBound:speed};
 }
 for(;;){
  if(closest.distance<=thickness)return result('contact','sample-within-thickness');
  if(closest.distanceLowerBound<=thickness){
   const conditioned=closest.conditioningAllowance>padding;
   return result(conditioned?'uncertain':'conservative',conditioned?'closest-feature-conditioning':'distance-resolution');
  }
  if(speed===0)return null;
  const safeDuration=(closest.distanceLowerBound-thickness)/speed,remaining=1-time;
  if(safeDuration>remaining)return null;
  if(boxSeparation(p,ends)>thickness+padding)return null;
  if(iterations>=settings.maxIterations)return result('uncertain','iteration-budget-exhausted');
  const advance=.9*safeDuration;
  if(advance<=settings.timeTolerance||time+advance===time)return result('uncertain','time-resolution');
  const next=Math.min(1,time+advance);if(next===time)return result('uncertain','floating-point-stagnation');
  time=next;iterations++;closest=evaluate(time);
  if(time===1){
   if(closest.distance<=thickness)return result('contact','endpoint-within-thickness');
   if(closest.distanceLowerBound<=thickness)return result('conservative','endpoint-distance-resolution');
   return null;
  }
 }
}
function queryOptions(thickness,options){
 if(!Number.isFinite(thickness)||thickness<0)throw new RangeError('thickness must be finite and nonnegative');
 const maxIterations=options.maxIterations===undefined?128:options.maxIterations;if(!Number.isInteger(maxIterations)||maxIterations<0)throw new RangeError('maxIterations must be a nonnegative integer');
 return {maxIterations,timeTolerance:options.timeTolerance===undefined?1e-10:tolerance(options.timeTolerance,'timeTolerance'),distanceTolerance:tolerance(options.distanceTolerance,'distanceTolerance')};
}
function validateArrays(history,current){if(!history||!current||history.length!==current.length||history.length%3)throw new TypeError('history/current must be equal-length flat xyz arrays');}
function validIndices(ids,count){if(ids.some(id=>!Number.isInteger(id)||id<0||id>=count))throw new RangeError('Point/triangle vertex index is out of bounds');}

/**
 * Vertex versus moving closed triangle, all four endpoints linear in time.
 * time is the candidate AFTER a floating-point cleared prefix, not an exact
 * impact root. contact: sampled distance<=h; conservative: distance uncertainty;
 * uncertain: unresolved suffix due to conditioning/iteration/time resolution.
 * null is returned only through separation certificates, never a budget exit.
 * barycentric and normal describe the true closest candidate at the given time;
 * normal keeps the historical side when defined. options match swept-edge:
 * maxIterations=128, timeTolerance=1e-10, distanceTolerance=IEEE padding only.
 * Primitive membership/adjacency exclusion remains the caller's responsibility.
 */
export function sweptVertexContact(history,current,v,a,b,c,thickness,options={}){
 validateArrays(history,current);const settings=queryOptions(thickness,options),ids=[v,a,b,c];validIndices(ids,history.length/3);
 const starts=ids.map(i=>Array.from(history.slice(i*3,i*3+3))),ends=ids.map(i=>Array.from(current.slice(i*3,i*3+3)));
 for(const p of [...starts,...ends])requirePoint(p);
 const velocities=starts.map((p,i)=>sub(ends[i],p));if(velocities.some(v=>v.some(x=>!Number.isFinite(x))))throw new RangeError('Motion exceeds numeric range');
 return motionQuery(starts,ends,velocities,thickness,settings,scaleOf([...starts,...ends]),workspace());
}

/**
 * Prepare repeated synchronous queries on one owned immutable motion snapshot.
 * Reprepare after motion changes. No global or array-identity state is cached;
 * query results own their arrays and cannot be overwritten by another query.
 */
export function prepareSweptVertexContacts(history,current,thickness,options={}){
 validateArrays(history,current);const settings=queryOptions(thickness,options),count=history.length/3;
 const starts=new Array(count),ends=new Array(count),velocities=new Array(count),scales=new Float64Array(count);
 for(let i=0;i<count;i++){
  const start=[history[i*3],history[i*3+1],history[i*3+2]],end=[current[i*3],current[i*3+1],current[i*3+2]];requirePoint(start);requirePoint(end);
  const velocity=sub(end,start);if(velocity.some(x=>!Number.isFinite(x)))throw new RangeError('Motion exceeds numeric range');
  starts[i]=start;ends[i]=end;velocities[i]=velocity;scales[i]=scaleOf([start,end]);
 }
 const scratch=workspace();
 function query(v,a,b,c){
  const ids=[v,a,b,c];validIndices(ids,count);
  return motionQuery(ids.map(i=>starts[i]),ids.map(i=>ends[i]),ids.map(i=>velocities[i]),thickness,settings,Math.max(...ids.map(i=>scales[i])),scratch);
 }
 query.vertexCount=count;return query;
}
