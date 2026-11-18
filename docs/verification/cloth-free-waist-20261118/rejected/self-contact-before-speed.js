import * as THREE from 'three';
import {MeshBVH} from 'three-mesh-bvh';

// Discrete two-sided cloth contact. The original rest mesh and shared seam IDs
// stay unchanged. Contacts use inverse-mass weighted barycentric corrections.
// This is a finite-thickness contact approximation, not a CCD guarantee.
export class SelfContact {
 constructor(positions,triangles,thickness=.003){
  this.faces=triangles;this.thickness=thickness;this.faceIndices=Array.from({length:triangles.length/3},(_,i)=>triangles.slice(i*3,i*3+3));
  this.geometry=new THREE.BufferGeometry();
  this.vertices=new Float32Array(positions);
  this.geometry.setAttribute('position',new THREE.BufferAttribute(this.vertices,3));
  this.geometry.setIndex(triangles);
  this.tree=new MeshBVH(this.geometry,{indirect:true,maxLeafSize:8});
  const seen=new Set();this.edges=[];
  for(let t=0;t<triangles.length;t+=3)for(let j=0;j<3;j++){
   const a=triangles[t+j],b=triangles[t+(j+1)%3],key=Math.min(a,b)*positions.length+Math.max(a,b);
   if(!seen.has(key)){seen.add(key);this.edges.push([a,b]);}
  }
 }
 dispose(){this.geometry.dispose();}
 solve(p,previous,inverseMass,passes=2,history=previous){
  this.changed=new Set();let contacts=0,maxMotion=0;for(let i=0;i<p.length;i+=3)maxMotion=Math.max(maxMotion,Math.hypot(p[i]-history[i],p[i+1]-history[i+1],p[i+2]-history[i+2]));
  this.lastProfile={pointMs:0,edgeMs:0};
  for(let pass=0;pass<passes;pass++){
   const pointStart=performance.now();
   this.vertices.set(p);this.tree.refit();
   const point=new THREE.Vector3(),closest=new THREE.Vector3(),bary=new THREE.Vector3();
   const hit=new THREE.Vector3(),normal=new THREE.Vector3(),swept=new THREE.Box3(),startPoint=new THREE.Vector3(),n0=new THREE.Vector3(),n1=new THREE.Vector3(),a0=new THREE.Vector3(),b0=new THREE.Vector3(),c0=new THREE.Vector3(),rootPoint=new THREE.Vector3(),rootTri=new THREE.Triangle(),hitNormal=new THREE.Vector3(),scratch0=new THREE.Vector3(),scratch1=new THREE.Vector3(),scratch2=new THREE.Vector3();
   let queryId,best,bestFace,bestWeights,crossing,firstTime;
   const callbacks={
     intersectsBounds:box=>box.intersectsBox(swept),
     intersectsTriangle:(triangle,face)=>{
      const ids=this.faceIndices[face];if(ids.includes(queryId))return false;
      triangle.closestPointToPoint(point,closest);const d=point.distanceTo(closest);
      // Both a vertex and a triangle move by at most maxMotion. A feature
      // farther than h + 2*maxMotion cannot enter the contact band this step.
      if(d>this.thickness+2*maxMotion)return false;
      a0.fromArray(history,ids[0]*3);b0.fromArray(history,ids[1]*3);c0.fromArray(history,ids[2]*3);
      n0.subVectors(b0,a0).cross(scratch0.subVectors(c0,a0)).normalize();triangle.getNormal(n1);
      const d0=n0.dot(scratch1.subVectors(startPoint,a0)),d1=n1.dot(scratch2.subVectors(point,triangle.a));
      if(d0*d1<0&&Math.abs(d0)>1e-6&&Math.abs(d1)>1e-6){
       const f=d0/(d0-d1);rootPoint.lerpVectors(startPoint,point,f);rootTri.a.lerpVectors(a0,triangle.a,f);rootTri.b.lerpVectors(b0,triangle.b,f);rootTri.c.lerpVectors(c0,triangle.c,f);
       rootTri.getBarycoord(rootPoint,bary);
       if(f<firstTime&&bary.x>=-1e-4&&bary.y>=-1e-4&&bary.z>=-1e-4){
        crossing=true;firstTime=f;bestFace=face;bestWeights=bary.toArray();hit.set(0,0,0).addScaledVector(triangle.a,bary.x).addScaledVector(triangle.b,bary.y).addScaledVector(triangle.c,bary.z);hitNormal.copy(n1).multiplyScalar(Math.sign(d0));
       }
      }
      if(!crossing&&d<best&&d>1e-10){
       THREE.Triangle.getBarycoord(closest,triangle.a,triangle.b,triangle.c,bary);
       best=d;bestFace=face;bestWeights=bary.toArray();hit.copy(closest);
      }
      return false;
     }
   };
   for(let id=0;id<p.length/3;id++){
    queryId=id;point.fromArray(p,id*3);startPoint.fromArray(history,id*3);swept.min.copy(startPoint).min(point);swept.max.copy(startPoint).max(point);swept.expandByScalar(this.thickness+maxMotion);best=this.thickness;bestFace=-1;bestWeights=undefined;crossing=false;firstTime=2;
    this.tree.shapecast(callbacks);
    if(bestFace<0)continue;
    const ids=this.faceIndices[bestFace],weights=bestWeights;
    if(crossing)normal.copy(hitNormal);else normal.copy(point).sub(hit).normalize();
    const before=[0,1,2].map(k=>history[id*3+k]-ids.reduce((s,v,j)=>s+history[v*3+k]*weights[j],0));
    if(!crossing&&(normal.x*before[0]+normal.y*before[1]+normal.z*before[2]<0))normal.negate();
    const signed=normal.dot(scratch0.subVectors(point,hit));
    const denom=inverseMass[id]+ids.reduce((s,v,j)=>s+inverseMass[v]*weights[j]**2,0);
    if(denom<1e-12)continue;
    const correction=Math.min(.02,this.thickness-signed)/denom;
    const move=(v,w)=>{if(w!==0)this.changed.add(v);for(let k=0;k<3;k++){const d=normal.getComponent(k)*correction*w;p[v*3+k]+=d;previous[v*3+k]+=.8*d;}maxMotion=Math.max(maxMotion,Math.hypot(p[v*3]-history[v*3],p[v*3+1]-history[v*3+1],p[v*3+2]-history[v*3+2]));};
    move(id,inverseMass[id]);ids.forEach((v,j)=>move(v,-inverseMass[v]*weights[j]));contacts++;
   }
   this.lastProfile.pointMs+=performance.now()-pointStart;const edgeStart=performance.now();
   contacts+=this.solveEdges(p,previous,inverseMass,history);this.lastProfile.edgeMs+=performance.now()-edgeStart;
  }
  return contacts;
 }
 solveEdges(p,previous,inverseMass,history){
  const h=this.thickness,segment=new Float64Array(6);let contacts=0;
  this.forEachCandidate(p,(i,j)=>{
   const [a,b]=this.edges[i],[c,d]=this.edges[j];
   segmentDistance(p,a,b,c,d,segment);const distance=segment[5];if(distance>=h||distance<1e-10)return;
   const u=segment[0],v=segment[1],weights=[1-u,u,-(1-v),-v],ids=[a,b,c,d];
   let nx=segment[2]/distance,ny=segment[3]/distance,nz=segment[4]/distance;
   const oldDelta=[0,1,2].map(k=>ids.reduce((sum,id,j)=>sum+history[id*3+k]*weights[j],0));
   if(nx*oldDelta[0]+ny*oldDelta[1]+nz*oldDelta[2]<0){nx=-nx;ny=-ny;nz=-nz;}
   const signed=nx*segment[2]+ny*segment[3]+nz*segment[4];
   const denom=ids.reduce((sum,id,j)=>sum+inverseMass[id]*weights[j]**2,0);if(denom<1e-12)return;
   const lambda=Math.min(.006,h-signed)/denom;
   ids.forEach((id,j)=>{const w=inverseMass[id]*weights[j]*lambda;if(w!==0)this.changed?.add(id);for(let k=0;k<3;k++){const delta=[nx,ny,nz][k]*w;p[id*3+k]+=delta;previous[id*3+k]+=.8*delta;}});
   contacts++;
  });
  return contacts;
 }
 forEachCandidate(p,callback){
  const n=this.edges.length,h=this.thickness;
  if(!this.bounds||this.bounds.length!==n*6){this.bounds=new Float64Array(n*6);this.order=Array.from({length:n},(_,i)=>i);}
  const box=this.bounds,low=[Infinity,Infinity,Infinity],high=[-Infinity,-Infinity,-Infinity],width=[0,0,0];
  for(let i=0;i<n;i++){const [a,b]=this.edges[i];for(let k=0;k<3;k++){
   const lo=Math.min(p[a*3+k],p[b*3+k])-h,hi=Math.max(p[a*3+k],p[b*3+k])+h;
   box[i*6+k*2]=lo;box[i*6+k*2+1]=hi;low[k]=Math.min(low[k],lo);high[k]=Math.max(high[k],hi);width[k]+=hi-lo;
  }}
  let axis=0;for(let k=1;k<3;k++)if((high[k]-low[k])/width[k]>(high[axis]-low[axis])/width[axis])axis=k;
  const first=axis*2,other=(axis+1)%3*2,last=(axis+2)%3*2;
  this.order.sort((a,b)=>box[a*6+first]-box[b*6+first]||a-b);
  for(let ai=0;ai<n;ai++){
   const i=this.order[ai],ia=i*6,[a,b]=this.edges[i];
   for(let bj=ai+1;bj<n;bj++){
    const j=this.order[bj],ib=j*6;if(box[ib+first]>box[ia+first+1])break;
    const [c,d]=this.edges[j];if(a===c||a===d||b===c||b===d)continue;
    if(box[ia+other]>box[ib+other+1]||box[ia+other+1]<box[ib+other]||box[ia+last]>box[ib+last+1]||box[ia+last+1]<box[ib+last])continue;
    callback(i,j);
   }
  }
 }

}

function segmentDistance(p,a,b,c,d,out){
 const ai=a*3,bi=b*3,ci=c*3,di=d*3;
 const ux=p[bi]-p[ai],uy=p[bi+1]-p[ai+1],uz=p[bi+2]-p[ai+2];
 const vx=p[di]-p[ci],vy=p[di+1]-p[ci+1],vz=p[di+2]-p[ci+2];
 const wx=p[ai]-p[ci],wy=p[ai+1]-p[ci+1],wz=p[ai+2]-p[ci+2];
 const A=ux*ux+uy*uy+uz*uz,B=ux*vx+uy*vy+uz*vz,C=vx*vx+vy*vy+vz*vz,D=ux*wx+uy*wy+uz*wz,E=vx*wx+vy*wy+vz*wz,den=A*C-B*B;
 let s=den>1e-18?THREE.MathUtils.clamp((B*E-C*D)/den,0,1):0,t=C>1e-18?(B*s+E)/C:0;
 if(t<0){t=0;s=A>1e-18?THREE.MathUtils.clamp(-D/A,0,1):0;}
 else if(t>1){t=1;s=A>1e-18?THREE.MathUtils.clamp((B-D)/A,0,1):0;}
 const dx=wx+s*ux-t*vx,dy=wy+s*uy-t*vy,dz=wz+s*uz-t*vz;
 out[0]=s;out[1]=t;out[2]=dx;out[3]=dy;out[4]=dz;out[5]=Math.hypot(dx,dy,dz);
}
