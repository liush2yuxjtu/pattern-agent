import {SelfContact} from '../../freesewing_cloth_lab/source/self-contact.js';
import {prepareSweptEdgeContacts} from './swept-edge.mjs';
import {prepareSweptVertexContacts} from './swept-vertex.mjs';

// Research backend: every VF and EE query in a Jacobi batch sees the same
// immutable coordinates. It is not a proof of collision-free dynamics. In
// particular, conservative floating-point candidates retain explicit uncertainty.
export class MeshContact extends SelfContact {
 constructor(positions,triangles,thickness=.003,options={}){
  if(!(thickness>0)||!Number.isFinite(thickness))throw Error('Contact thickness must be positive and finite');
  const cap=options.maxVertexCorrection??.0005;
  if(!(cap>=0)||!Number.isFinite(cap))throw Error('Contact correction cap must be nonnegative and finite');
  // BufferGeometry.setIndex does not accept an unwrapped Uint32Array.
  super(positions,Array.from(triangles),thickness,options);
  this.useSweptBounds=options.sweptBounds!==false;
  this.maxVertexCorrection=cap;
  // The old topology helper rejects a whole one-ring. Only primitive incidence
  // is excluded by default. A caller may opt into a separately reviewed hook.
  this.useCustomExclusions=options.useCustomExclusions===true;
  this.edgeOptions=options.sweptEdgeOptions??{};this.vertexOptions=options.sweptVertexOptions??{};
  this.order=Array.from({length:this.edges.length},(_,i)=>i);
  // Keep the exact batch snapshot in the BVH geometry as well. Its internal
  // float32 node bounds are replaced by conservative endpoint unions below.
  const Attribute=this.geometry.getAttribute('position').constructor;
  this.vertices=Float64Array.from(positions);
  this.geometry.setAttribute('position',new Attribute(this.vertices,3));
  this.tree.refit();this.geometry.computeBoundingBox();
  this.Vector3=this.geometry.boundingBox.min.constructor;
  this.Box3=this.geometry.boundingBox.constructor;
 }

 solve(p,previous,inverseMass,passes=2,history=previous){
  return this._solveBatches(p,previous,inverseMass,passes,history,true,true);
 }

 // Kept for existing isolated EE probes. The full solve collects both kinds
 // before applying either; it never calls this method between VF mutations.
 solveEdges(p,previous,inverseMass,history=previous){
  return this._solveBatches(p,previous,inverseMass,1,history,false,true);
 }

 _refit(snapshot,history){
  this.vertices.set(snapshot);this.tree.refit();
  if(this.useSweptBounds)this.buildSweptBounds(history);
 }

 _solveBatches(p,previous,inverseMass,passes,history,points,edges){
  const count=p.length/3;
  if(!Number.isInteger(count)||previous.length!==p.length||history.length!==p.length||inverseMass.length!==count)throw Error('Contact arrays have incompatible sizes');
  if(!Number.isInteger(passes)||passes<0)throw Error('Contact passes must be a nonnegative integer');
  if(Array.from(inverseMass).some(v=>!Number.isFinite(v)||v<0))throw Error('Inverse masses must be finite and nonnegative');
  // Always copy before previous is updated. With the default history=previous,
  // both argument names alias one buffer, but this working history never moves.
  const old=Float64Array.from(history),origin=Float64Array.from(p);
  if(!old.every(Number.isFinite)||!origin.every(Number.isFinite))throw Error('Contact positions must be finite');
  const spent=new Float64Array(count),travelled=new Float64Array(count),sums=new Float64Array(p.length),counts=new Uint32Array(count);
  this.lastPassMaxCorrections=[];
  this.changed=new Set();this.lastProfile={pointMs:0,edgeMs:0,vfConstraints:0,eeConstraints:0,vfCandidates:0,eeCandidates:0,uncertainEdges:0,conservativeEdges:0,uncertainVertices:0,conservativeVertices:0,batches:0,maxPassVertexCorrection:0,maxAccumulatedCorrection:0};
  let contacts=0;
  for(let pass=0;pass<passes;pass++){
   const snapshot=Float64Array.from(p);sums.fill(0);counts.fill(0);spent.fill(0);
   this._refit(snapshot,old);
   let maxMotion=0;
   for(let id=0;id<count;id++)maxMotion=Math.max(maxMotion,Math.hypot(snapshot[id*3]-old[id*3],snapshot[id*3+1]-old[id*3+1],snapshot[id*3+2]-old[id*3+2]));
   const add=(ids,coefficients,normal,residual,limit)=>{
    if(!(residual>0)||!normal.every(Number.isFinite))return false;
    const norm=Math.hypot(...normal);if(norm<1e-12)return false;
    let denominator=0,remaining=false;
    for(let j=0;j<ids.length;j++){
     const id=ids[j],w=coefficients[j];denominator+=inverseMass[id]*w*w;
     if(inverseMass[id]>0&&w!==0&&spent[id]<this.maxVertexCorrection)remaining=true;
    }
    if(denominator<1e-20||!remaining)return false;
    const lambda=Math.min(limit,residual)/denominator;
    for(let j=0;j<ids.length;j++){
     const id=ids[j],w=inverseMass[id]*coefficients[j]*lambda/norm;
     if(w===0||spent[id]>=this.maxVertexCorrection)continue;
     for(let k=0;k<3;k++)sums[id*3+k]+=normal[k]*w;
     counts[id]++;
    }
    return true;
   };
   if(points){const start=performance.now();contacts+=this._gatherVertices(snapshot,old,maxMotion,add);this.lastProfile.pointMs+=performance.now()-start;}
   if(edges){const start=performance.now();contacts+=this._gatherEdges(snapshot,old,add);this.lastProfile.edgeMs+=performance.now()-start;}
   // Average simultaneous VF+EE proposals, then apply once. The correction cap
   // is per complete Jacobi pass, never per constraint. Additional requested
   // passes are allowed to make further bounded progress after refit/requery.
   let moved=0;
   for(let id=0;id<count;id++){
    if(!counts[id]||inverseMass[id]===0)continue;
    const delta=[0,1,2].map(k=>sums[id*3+k]/counts[id]),length=Math.hypot(...delta),budget=this.maxVertexCorrection-spent[id];
    if(!(length>0)||!(budget>0))continue;
    const before=[p[id*3],p[id*3+1],p[id*3+2]],is32=p instanceof Float32Array;
    let scale=Math.min(1,budget/length),next,distance;
    for(let attempt=0;attempt<32;attempt++){
     next=delta.map((value,k)=>is32?Math.fround(before[k]+value*scale):before[k]+value*scale);
     distance=Math.hypot(...next.map((value,k)=>value-before[k]));
     if(distance<=budget)break;
     // A float32 ulp may itself exceed the remaining budget. Reduce the
     // proposal rather than writing an over-cap value and clamping telemetry.
     scale*=Math.min(.9999999,budget/distance*.9999999);
    }
    if(!(distance>0)||distance>budget)continue;
    for(let k=0;k<3;k++){const actual=next[k]-before[k];p[id*3+k]=next[k];previous[id*3+k]+=.8*actual;}
    spent[id]+=distance;travelled[id]+=distance;this.changed.add(id);moved++;
   }
   this.lastProfile.batches++;
   this.lastPassMaxCorrections.push(Math.max(0,...spent));
   if(!moved)break;
  }
  // Expose a hierarchy consistent with the returned positions, including when a
  // caller queries immediately after solve or requests zero passes.
  this._refit(p,old);
  this.lastPassVertexCorrection=spent;this.lastAccumulatedVertexCorrection=travelled;
  this.lastMaxVertexCorrection=Math.max(0,...this.lastPassMaxCorrections);
  this.lastProfile.maxPassVertexCorrection=this.lastMaxVertexCorrection;
  this.lastProfile.maxAccumulatedCorrection=Math.max(0,...travelled);
  this.lastProfile.maxNetCorrection=0;
  for(let id=0;id<count;id++)this.lastProfile.maxNetCorrection=Math.max(this.lastProfile.maxNetCorrection,Math.hypot(p[id*3]-origin[id*3],p[id*3+1]-origin[id*3+1],p[id*3+2]-origin[id*3+2]));
  return contacts;
 }

 _gatherVertices(snapshot,history,maxMotion,add){
  const V=this.Vector3,point=new V(),closest=new V(),startPoint=new V(),queryBox=new this.Box3();
  const query=prepareSweptVertexContacts(history,snapshot,this.thickness,this.vertexOptions);
  let queryId,firstTime,bestResidual,best,contacts=0;
  const callbacks={
   intersectsBounds:(box,isLeaf,score,depth,node)=>{
    if(!this.useSweptBounds)return box.intersectsBox(queryBox);
    const b=this.sweptNodes.get(node);if(!b)throw Error('Missing swept BVH node');
    return queryBox.min.x<=b[3]&&queryBox.max.x>=b[0]&&queryBox.min.y<=b[4]&&queryBox.max.y>=b[1]&&queryBox.min.z<=b[5]&&queryBox.max.z>=b[2];
   },
   intersectsTriangle:(triangle,face)=>{
    const ids=this.faceIndices[face];
    if(ids.includes(queryId)||(this.useCustomExclusions&&this.excludeVertexFace?.(queryId,face)))return false;
    this.lastProfile.vfCandidates++;
    triangle.closestPointToPoint(point,closest);
    if(point.distanceTo(closest)>this.thickness+2*maxMotion+1e-12)return false;
    const contact=query(queryId,...ids);if(!contact)return false;
    if(contact.status==='uncertain')this.lastProfile.uncertainVertices++;
    if(contact.status==='conservative')this.lastProfile.conservativeVertices++;
    const weights=contact.barycentric,normal=contact.normal;
    if(!weights||weights.length!==3||!normal||normal.length!==3||Math.hypot(...normal)<1e-12)return false;
    const delta=[0,1,2].map(k=>snapshot[queryId*3+k]-ids.reduce((sum,id,j)=>sum+snapshot[id*3+k]*weights[j],0));
    const residual=this.thickness-normal.reduce((sum,value,k)=>sum+value*delta[k],0);
    // An earlier candidate whose endpoint constraint is already satisfied must
    // not hide a later active contact with a different actual triangle.
    if(residual>0&&(contact.time<firstTime-1e-12||Math.abs(contact.time-firstTime)<=1e-12&&residual>bestResidual)){
     firstTime=contact.time;bestResidual=residual;best={ids,weights,normal};
    }
    return false;
   }
  };
  for(let id=0;id<snapshot.length/3;id++){
   queryId=id;point.fromArray(snapshot,id*3);startPoint.fromArray(history,id*3);
   queryBox.min.copy(startPoint).min(point);queryBox.max.copy(startPoint).max(point);queryBox.expandByScalar(this.thickness+(this.useSweptBounds?0:maxMotion));
   firstTime=Infinity;bestResidual=0;best=null;
   this.tree.shapecast(callbacks);if(!best)continue;
   if(add([id,...best.ids],[1,...best.weights.map(w=>-w)],best.normal,bestResidual,.02)){
    contacts++;this.lastProfile.vfConstraints++;
   }
  }
  return contacts;
 }

 _gatherEdges(snapshot,history,add){
  let contacts=0;
  // The factory owns this pass's immutable motion and cached velocities. It is
  // recreated after every refit/requery; no current/history identity cache can
  // silently refer to a previous projection batch.
  const query=prepareSweptEdgeContacts(history,snapshot,this.thickness,this.edgeOptions);
  this.forEachCandidate(snapshot,(i,j)=>{
   this.lastProfile.eeCandidates++;
   const [a,b]=this.edges[i],[c,d]=this.edges[j],contact=query(a,b,c,d);
   if(!contact)return;
   if(contact.status==='uncertain')this.lastProfile.uncertainEdges++;
   if(contact.status==='conservative')this.lastProfile.conservativeEdges++;
   const u=contact.u,v=contact.v;
   if(!Number.isFinite(u)||!Number.isFinite(v)||u<0||u>1||v<0||v>1)return;
   const ids=[a,b,c,d],weights=[1-u,u,-(1-v),-v];
   let normal=Array.from(contact.normal??[]);if(normal.length!==3||Math.hypot(...normal)<1e-12)return;
   const before=[0,1,2].map(k=>ids.reduce((sum,id,index)=>sum+history[id*3+k]*weights[index],0));
   if(normal.reduce((sum,value,k)=>sum+value*before[k],0)<0)normal=normal.map(value=>-value);
   const length=Math.hypot(...normal);normal=normal.map(value=>value/length);
   const delta=[0,1,2].map(k=>ids.reduce((sum,id,index)=>sum+snapshot[id*3+k]*weights[index],0));
   const signed=normal.reduce((sum,value,k)=>sum+value*delta[k],0);
   if(add(ids,weights,normal,this.thickness-signed,.006)){contacts++;this.lastProfile.eeConstraints++;}
  },history);
  return contacts;
 }

 // Conservative endpoint-union boxes for each moving edge. Both VF and EE
 // narrow phases use the exact same snapshot that produced these candidates.
 forEachCandidate(p,callback,history=p){
  const n=this.edges.length,h=this.thickness;if(!n)return;
  if(!this.bounds||this.bounds.length!==n*6){this.bounds=new Float64Array(n*6);this.order=Array.from({length:n},(_,i)=>i);}
  if(!this.order||this.order.length!==n)this.order=Array.from({length:n},(_,i)=>i);
  const box=this.bounds,low=[Infinity,Infinity,Infinity],high=[-Infinity,-Infinity,-Infinity],width=[0,0,0];
  for(let i=0;i<n;i++){
   const [a,b]=this.edges[i];
   for(let k=0;k<3;k++){
    const lo=Math.min(p[a*3+k],p[b*3+k],history[a*3+k],history[b*3+k])-h,hi=Math.max(p[a*3+k],p[b*3+k],history[a*3+k],history[b*3+k])+h;
    box[i*6+k*2]=lo;box[i*6+k*2+1]=hi;low[k]=Math.min(low[k],lo);high[k]=Math.max(high[k],hi);width[k]+=hi-lo;
   }
  }
  let axis=0;for(let k=1;k<3;k++)if((high[k]-low[k])/Math.max(width[k],1e-30)>(high[axis]-low[axis])/Math.max(width[axis],1e-30))axis=k;
  const first=axis*2,other=(axis+1)%3*2,last=(axis+2)%3*2;
  this.order.sort((a,b)=>box[a*6+first]-box[b*6+first]||a-b);
  for(let ai=0;ai<n;ai++){
   const i=this.order[ai],ia=i*6,[a,b]=this.edges[i];
   for(let bj=ai+1;bj<n;bj++){
    const j=this.order[bj],ib=j*6;if(box[ib+first]>box[ia+first+1])break;
    const [c,d]=this.edges[j];
    if(a===c||a===d||b===c||b===d||(this.useCustomExclusions&&this.excludeEdgePair?.([a,b],[c,d])))continue;
    if(box[ia+other]>box[ib+other+1]||box[ia+other+1]<box[ib+other]||box[ia+last]>box[ib+last+1]||box[ia+last+1]<box[ib+last])continue;
    callback(i,j);
   }
  }
 }
}

