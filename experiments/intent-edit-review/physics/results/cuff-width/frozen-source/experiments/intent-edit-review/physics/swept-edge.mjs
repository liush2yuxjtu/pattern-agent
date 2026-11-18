// Finite-thickness, linearly moving segment CCD without an endpoint-only gate.
//
// A null result is produced only after a swept-box or Lipschitz separation
// certificate. Budget/precision exhaustion returns an explicit uncertain
// candidate. This is floating-point conservative advancement, not an exact
// predicate or a certified interval-arithmetic geometry kernel.

const EPS=Number.EPSILON;
const clamp01=x=>Math.max(0,Math.min(1,x));
const sub=(a,b)=>[a[0]-b[0],a[1]-b[1],a[2]-b[2]];
const dot=(a,b)=>a[0]*b[0]+a[1]*b[1]+a[2]*b[2];
const cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
const norm=a=>Math.hypot(a[0],a[1],a[2]);
const lerp=(a,b,t)=>[a[0]+t*(b[0]-a[0]),a[1]+t*(b[1]-a[1]),a[2]+t*(b[2]-a[2])];

function requirePoint(p){
 if(!p||p.length!==3||!Array.from(p).every(Number.isFinite))throw new TypeError('A segment endpoint must contain three finite coordinates');
}
function normalized(p){const n=norm(p);return n>0&&Number.isFinite(n)?p.map(x=>x/n):[0,0,0];}
function numericScale(points){return Math.max(1,...points.flatMap(p=>Array.from(p,x=>Math.abs(x))));}
function tolerance(value,name){
 if(value===undefined)return 0;
 if(!Number.isFinite(value)||value<0)throw new RangeError(name+' must be finite and nonnegative');
 return value;
}

/**
 * Closest points of two closed 3D segments. u is on [a0,a1], v on [b0,b1].
 * `normal` points from B to A; it is zero when that normal is undefined.
 * Endpoint projections and a valid unconstrained interior minimum are compared.
 * A nearly parallel feature carries an explicit conservative distance allowance.
 */
export function segmentClosest(a0,a1,b0,b1,options={}){
 for(const p of [a0,a1,b0,b1])requirePoint(p);
 const e=sub(a1,a0),f=sub(b1,b0),le=norm(e),lf=norm(f);
 if(!Number.isFinite(le)||!Number.isFinite(lf))throw new RangeError('Segment coordinate differences exceed numeric range');
 const E=le>0?e.map(x=>x/le):[0,0,0],F=lf>0?f.map(x=>x/lf):[0,0,0];
 let best=null;
 function candidate(u,v){
  if(!Number.isFinite(u)||!Number.isFinite(v))return;
  u=clamp01(u);v=clamp01(v);
  const pointA=lerp(a0,a1,u),pointB=lerp(b0,b1,v),delta=sub(pointA,pointB),distance=norm(delta);
  if(!Number.isFinite(distance))throw new RangeError('Segment separation exceeds numeric range');
  if(best===null||distance<best.distance)best={u,v,pointA,pointB,delta,distance};
 }
 // Every constrained minimum is either an interior stationary point or lies on
 // the boundary of the [u,v] square. The four projections cover that boundary.
 candidate(0,lf>0?dot(sub(a0,b0),F)/lf:0);
 candidate(1,lf>0?dot(sub(a1,b0),F)/lf:0);
 candidate(le>0?dot(sub(b0,a0),E)/le:0,0);
 candidate(le>0?dot(sub(b1,a0),E)/le:0,1);
 const n=cross(E,F),sin=norm(n),den=dot(n,n);
 if(le>0&&lf>0&&den>0){
  const w=sub(b0,a0),u=dot(cross(w,F),n)/den/le,v=dot(cross(w,E),n)/den/lf;
  if(u>=0&&u<=1&&v>=0&&v<=1)candidate(u,v);
 }
 const scale=numericScale([a0,a1,b0,b1]);
 const roundoffPadding=Math.max(128*EPS*scale,tolerance(options.distanceTolerance,'distanceTolerance'));
 // Close-to-parallel line solves are ill-conditioned. Retaining an allowance
 // prevents their approximate closest pair from authorizing an unsafe advance.
 const parallelAllowance=sin>0&&sin<1e-6?4*Math.min(le,lf)*sin:0;
 const distanceUncertainty=roundoffPadding+parallelAllowance;
 return {...best,normal:best.distance>0?best.delta.map(x=>x/best.distance):[0,0,0],
  normalDefined:best.distance>0,distanceLowerBound:Math.max(0,best.distance-distanceUncertainty),
  distanceUncertainty,roundoffPadding,parallelAllowance};
}

function boxSeparation(p0,p1){
 let x=0,y=0,z=0;
 for(let k=0;k<3;k++){
  const alo=Math.min(p0[0][k],p0[1][k],p1[0][k],p1[1][k]);
  const ahi=Math.max(p0[0][k],p0[1][k],p1[0][k],p1[1][k]);
  const blo=Math.min(p0[2][k],p0[3][k],p1[2][k],p1[3][k]);
  const bhi=Math.max(p0[2][k],p0[3][k],p1[2][k],p1[3][k]);
  const gap=Math.max(0,alo-bhi,blo-ahi);
  if(k===0)x=gap;else if(k===1)y=gap;else z=gap;
 }
 return Math.hypot(x,y,z);
}

function relativeSpeedBound(velocities){
 // Subtracting a common translational velocity does not change segment
 // distance. Each candidate frame gives a valid Hausdorff/Lipschitz bound.
 const [a,b,c,d]=velocities;
 const separation=(p,q)=>Math.hypot(p[0]-q[0],p[1]-q[1],p[2]-q[2]);
 // The four endpoint frames use only six distinct symmetric norms rather than
 // sixteen freshly allocated vectors. Their candidate bounds are unchanged.
 const ab=separation(a,b),ac=separation(a,c),ad=separation(a,d),bc=separation(b,c),bd=separation(b,d),cd=separation(c,d);
 let bound=Math.min(ab+Math.max(ac,ad),ab+Math.max(bc,bd),Math.max(ac,bc)+cd,Math.max(ad,bd)+cd);
 function frame(x,y,z){
  const sa=Math.hypot(a[0]-x,a[1]-y,a[2]-z),sb=Math.hypot(b[0]-x,b[1]-y,b[2]-z);
  const sc=Math.hypot(c[0]-x,c[1]-y,c[2]-z),sd=Math.hypot(d[0]-x,d[1]-y,d[2]-z);
  bound=Math.min(bound,Math.max(sa,sb)+Math.max(sc,sd));
 }
 frame((a[0]+b[0])/2,(a[1]+b[1])/2,(a[2]+b[2])/2);
 frame((c[0]+d[0])/2,(c[1]+d[1])/2,(c[2]+d[2])/2);
 frame(((a[0]/4+b[0]/4)+c[0]/4)+d[0]/4,((a[1]/4+b[1]/4)+c[1]/4)+d[1]/4,((a[2]/4+b[2]/4)+c[2]/4)+d[2]/4);
 return bound;
}

// Same candidates, formula order and rounding allowance as segmentClosest,
// but with a caller-owned scalar record. No per-evaluation endpoint arrays,
// sub/cross arrays, point objects or repeated public-input validation.
function closestInto(a,b,c,d,padding,out){
 const ex=b[0]-a[0],ey=b[1]-a[1],ez=b[2]-a[2],fx=d[0]-c[0],fy=d[1]-c[1],fz=d[2]-c[2];
 const le=Math.hypot(ex,ey,ez),lf=Math.hypot(fx,fy,fz);
 if(!Number.isFinite(le)||!Number.isFinite(lf))throw new RangeError('Segment coordinate differences exceed numeric range');
 const Ex=le>0?ex/le:0,Ey=le>0?ey/le:0,Ez=le>0?ez/le:0;
 const Fx=lf>0?fx/lf:0,Fy=lf>0?fy/lf:0,Fz=lf>0?fz/lf:0;
 let best=Infinity;
 function candidate(u,v){
  if(!Number.isFinite(u)||!Number.isFinite(v))return;
  u=clamp01(u);v=clamp01(v);
  const ax=a[0]+u*ex,ay=a[1]+u*ey,az=a[2]+u*ez,bx=c[0]+v*fx,by=c[1]+v*fy,bz=c[2]+v*fz;
  const dx=ax-bx,dy=ay-by,dz=az-bz,distance=Math.hypot(dx,dy,dz);
  if(!Number.isFinite(distance))throw new RangeError('Segment separation exceeds numeric range');
  if(distance<best){best=distance;out.u=u;out.v=v;out.ax=ax;out.ay=ay;out.az=az;out.bx=bx;out.by=by;out.bz=bz;out.dx=dx;out.dy=dy;out.dz=dz;}
 }
 candidate(0,lf>0?((a[0]-c[0])*Fx+(a[1]-c[1])*Fy+(a[2]-c[2])*Fz)/lf:0);
 candidate(1,lf>0?((b[0]-c[0])*Fx+(b[1]-c[1])*Fy+(b[2]-c[2])*Fz)/lf:0);
 candidate(le>0?((c[0]-a[0])*Ex+(c[1]-a[1])*Ey+(c[2]-a[2])*Ez)/le:0,0);
 candidate(le>0?((d[0]-a[0])*Ex+(d[1]-a[1])*Ey+(d[2]-a[2])*Ez)/le:0,1);
 const nx=Ey*Fz-Ez*Fy,ny=Ez*Fx-Ex*Fz,nz=Ex*Fy-Ey*Fx,sin=Math.hypot(nx,ny,nz),den=nx*nx+ny*ny+nz*nz;
 if(le>0&&lf>0&&den>0){
  const wx=c[0]-a[0],wy=c[1]-a[1],wz=c[2]-a[2];
  const u=((wy*Fz-wz*Fy)*nx+(wz*Fx-wx*Fz)*ny+(wx*Fy-wy*Fx)*nz)/den/le;
  const v=((wy*Ez-wz*Ey)*nx+(wz*Ex-wx*Ez)*ny+(wx*Ey-wy*Ex)*nz)/den/lf;
  if(u>=0&&u<=1&&v>=0&&v<=1)candidate(u,v);
 }
 const scale=Math.max(1,Math.abs(a[0]),Math.abs(a[1]),Math.abs(a[2]),Math.abs(b[0]),Math.abs(b[1]),Math.abs(b[2]),
  Math.abs(c[0]),Math.abs(c[1]),Math.abs(c[2]),Math.abs(d[0]),Math.abs(d[1]),Math.abs(d[2]));
 out.distance=best;
 out.parallelAllowance=sin>0&&sin<1e-6?4*Math.min(le,lf)*sin:0;
 out.distanceUncertainty=Math.max(128*EPS*scale,padding)+out.parallelAllowance;
 out.distanceLowerBound=Math.max(0,best-out.distanceUncertainty);
 out.normalDefined=best>0;
 return out;
}

function queryWorkspace(){return {points:Array.from({length:4},()=>[0,0,0]),closest:{}};}

function motionQuery(starts,ends,velocities,thickness,maxIterations,timeTolerance,padding,scale,workspace){
 if(boxSeparation(starts,ends)>thickness+padding)return null;
 const rawSpeed=relativeSpeedBound(velocities);
 const speed=rawSpeed===0?0:rawSpeed+128*EPS*Math.max(scale,rawSpeed);
 let time=0,iterations=0,evaluations=0;
 const p=workspace.points;
 function at(t){
  for(let i=0;i<4;i++)for(let k=0;k<3;k++)p[i][k]=starts[i][k]+t*velocities[i][k];
  return p;
 }
 function evaluate(t){evaluations++;at(t);return closestInto(p[0],p[1],p[2],p[3],padding,workspace.closest);}
 let closest=evaluate(0);
 function result(status,reason){
  let normal=closest.normalDefined?[closest.dx/closest.distance,closest.dy/closest.distance,closest.dz/closest.distance]:[0,0,0],normalSource='current-separation';
  const oldA=lerp(starts[0],starts[1],closest.u),oldB=lerp(starts[2],starts[3],closest.v),oldDelta=sub(oldA,oldB);
  if(!closest.normalDefined){
   if(norm(oldDelta)>padding){normal=normalized(oldDelta);normalSource='historical-side';}
   else{
    const relative=velocities[0].map((_,k)=>
     (1-closest.u)*velocities[0][k]+closest.u*velocities[1][k]-(1-closest.v)*velocities[2][k]-closest.v*velocities[3][k]);
    if(norm(relative)>0){normal=normalized(relative.map(x=>-x));normalSource='opposite-relative-motion';}
    else{const p=at(time);normal=normalized(cross(sub(p[1],p[0]),sub(p[3],p[2])));normalSource='edge-cross-product';}
   }
  }
  if(norm(oldDelta)>padding&&dot(normal,oldDelta)<0)normal=normal.map(x=>-x);
  const normalDefined=norm(normal)>0;
  if(!normalDefined)normalSource='undefined-degenerate';
  return {time,u:closest.u,v:closest.v,normal,normalDefined,normalSource,
   distance:closest.distance,distanceLowerBound:closest.distanceLowerBound,
   distanceUncertainty:closest.distanceUncertainty,thickness,status,reason,
   contact:status==='contact',conservative:status==='conservative',uncertain:status==='uncertain',
   possibleInterval:[time,1],clearedUntil:time,iterations,evaluations,speedBound:speed,
   pointA:[closest.ax,closest.ay,closest.az],pointB:[closest.bx,closest.by,closest.bz]};
 }
 for(;;){
  if(closest.distance<=thickness)return result('contact','sample-within-thickness');
  if(closest.distanceLowerBound<=thickness){
   const status=closest.parallelAllowance>padding?'uncertain':'conservative';
   return result(status,status==='uncertain'?'closest-feature-conditioning':'distance-resolution');
  }
  if(speed===0)return null;
  const safeDuration=(closest.distanceLowerBound-thickness)/speed;
  const remaining=1-time;
  if(safeDuration>remaining)return null;
  if(boxSeparation(p,ends)>thickness+padding)return null;
  if(iterations>=maxIterations)return result('uncertain','iteration-budget-exhausted');
  const advance=0.9*safeDuration;
  if(advance<=timeTolerance||time+advance===time)return result('uncertain','time-resolution');
  const next=Math.min(1,time+advance);
  if(next===time)return result('uncertain','floating-point-stagnation');
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
 const maxIterations=options.maxIterations===undefined?128:options.maxIterations;
 if(!Number.isInteger(maxIterations)||maxIterations<0)throw new RangeError('maxIterations must be a nonnegative integer');
 return {maxIterations,timeTolerance:options.timeTolerance===undefined?1e-10:tolerance(options.timeTolerance,'timeTolerance'),
  distanceTolerance:tolerance(options.distanceTolerance,'distanceTolerance')};
}

function validateArrays(history,current){
 if(!history||!current||history.length!==current.length||history.length%3!==0)throw new TypeError('history/current must be equal-length flat xyz arrays');
}

/**
 * Finite-thickness continuous contact of linearly moving closed edges.
 *
 * history/current: equal-length flat xyz arrays; a,b,c,d: vertex indices.
 * thickness: the contact distance, in the arrays' unchanged length unit.
 * options: maxIterations (default 128), timeTolerance (default 1e-10),
 *          distanceTolerance (default IEEE-scale padding only).
 *
 * Non-null statuses:
 *  contact      -- a sampled closest pair is within thickness;
 *  conservative -- a candidate is within the reported distance uncertainty;
 *  uncertain    -- remaining motion cannot be certified clear within budget or
 *                  numeric resolution. It MUST NOT be silently treated as clear.
 *
 * `time` is the candidate after a certified-clear prefix, not an assertion of an
 * exact earliest root. `possibleInterval` retains the unresolved suffix. `u/v`
 * and `normal` describe the candidate at `time`, with normal oriented toward the
 * historical side where that side is defined. Callers must preserve status.
 */
export function sweptEdgeContact(history,current,a,b,c,d,thickness,options={}){
 validateArrays(history,current);
 if(!Number.isFinite(thickness)||thickness<0)throw new RangeError('thickness must be finite and nonnegative');
 const ids=[a,b,c,d],count=history.length/3;
 if(ids.some(i=>!Number.isInteger(i)||i<0||i>=count))throw new RangeError('Edge vertex index is out of bounds');
 const starts=ids.map(i=>Array.from(history.slice(i*3,i*3+3))),ends=ids.map(i=>Array.from(current.slice(i*3,i*3+3)));
 for(const p of [...starts,...ends])requirePoint(p);
 const settings=queryOptions(thickness,options),scale=numericScale([...starts,...ends]);
 const padding=Math.max(256*EPS*scale,settings.distanceTolerance),velocities=starts.map((p,i)=>sub(ends[i],p));
 if(velocities.some(p=>p.some(x=>!Number.isFinite(x))))throw new RangeError('Motion exceeds numeric range');
 return motionQuery(starts,ends,velocities,thickness,settings.maxIterations,settings.timeTolerance,padding,scale,queryWorkspace());
}

/**
 * Prepare many edge queries on one IMMUTABLE motion snapshot. The input arrays
 * are copied and validated once and per-vertex velocities are cached. Returned
 * query(a,b,c,d) has the same result/status and numerical settings as the public
 * single-query function; its workspace is reused only during synchronous calls.
 * Returned records own their point/normal arrays, so later queries cannot alter
 * earlier results. Reprepare after motion changes; no global or identity cache
 * silently reuses stale vertex positions.
 */
export function prepareSweptEdgeContacts(history,current,thickness,options={}){
 validateArrays(history,current);
 const settings=queryOptions(thickness,options),count=history.length/3;
 const starts=new Array(count),ends=new Array(count),velocities=new Array(count),scales=new Float64Array(count);
 for(let i=0;i<count;i++){
  const j=i*3,start=[history[j],history[j+1],history[j+2]],end=[current[j],current[j+1],current[j+2]];
  requirePoint(start);requirePoint(end);
  const velocity=[end[0]-start[0],end[1]-start[1],end[2]-start[2]];
  if(velocity.some(x=>!Number.isFinite(x)))throw new RangeError('Motion exceeds numeric range');
  starts[i]=start;ends[i]=end;velocities[i]=velocity;scales[i]=numericScale([start,end]);
 }
 const workspace=queryWorkspace();
 function query(a,b,c,d){
  if(!Number.isInteger(a)||!Number.isInteger(b)||!Number.isInteger(c)||!Number.isInteger(d)||a<0||b<0||c<0||d<0||a>=count||b>=count||c>=count||d>=count)throw new RangeError('Edge vertex index is out of bounds');
  const scale=Math.max(scales[a],scales[b],scales[c],scales[d]);
  return motionQuery([starts[a],starts[b],starts[c],starts[d]],[ends[a],ends[b],ends[c],ends[d]],
   [velocities[a],velocities[b],velocities[c],velocities[d]],thickness,settings.maxIterations,settings.timeTolerance,
   Math.max(256*EPS*scale,settings.distanceTolerance),scale,workspace);
 }
 query.vertexCount=count;
 return query;
}
