import {Triangle, Vector3} from 'three/src/Three.Core.js';

// The static body needs only closest-point queries. Flatten the public BVH
// traversal once, preserving its child order and leaf triangle order.
export function createBodyQuery(bvh, geometry) {
 const nodes=[], parents=[], triangles=[];
 const point=new Vector3(), closest=new Vector3();
 const position=geometry.attributes.position.array, index=geometry.index.array;
 bvh.traverse((depth,isLeaf,bounds,offset,count)=>{
  const node={bounds, left:-1, right:-1, start:triangles.length, end:triangles.length};
  const id=nodes.push(node)-1;
  if(depth){
   const parent=nodes[parents[depth-1]];
   if(parent.left<0)parent.left=id;
   else parent.right=id;
  }
  parents[depth]=id;
  if(isLeaf){
   for(let i=offset;i<offset+count;i++){
    const face=bvh.resolveTriangleIndex(i), k=face*3;
    const triangle=new Triangle(
     new Vector3().fromArray(position,index[k]*3),
     new Vector3().fromArray(position,index[k+1]*3),
     new Vector3().fromArray(position,index[k+2]*3)
    );
    triangles.push({face,triangle});
   }
   node.end=triangles.length;
  }
 });
 const pending=new Int32Array(parents.length+1), scores=new Float64Array(pending.length);
 function distanceToBounds(id,x,y,z){
  const b=nodes[id].bounds;
  const dx=Math.max(b[0],Math.min(b[3],x))-x;
  const dy=Math.max(b[1],Math.min(b[4],y))-y;
  const dz=Math.max(b[2],Math.min(b[5],z))-z;
  return dx*dx+dy*dy+dz*dz;
 }
 return function closestBodyPoint(x,y,z,target){
  point.set(x,y,z);
  let count=1,best=Infinity,face=-1;
  pending[0]=0;scores[0]=0;
  while(count){
   const entry=--count;
   if(scores[entry]>=best)continue;
   const node=nodes[pending[entry]];
   if(node.left<0){
    for(let i=node.start;i<node.end;i++){
     const item=triangles[i];
     item.triangle.closestPointToPoint(point,closest);
     const distance=point.distanceToSquared(closest);
     if(distance<best){best=distance;face=item.face;target.copy(closest);}
    }
   }else{
    let first=node.left,second=node.right;
    let firstScore=distanceToBounds(first,x,y,z),secondScore=distanceToBounds(second,x,y,z);
    if(secondScore<firstScore){
     const id=first;first=second;second=id;
     const score=firstScore;firstScore=secondScore;secondScore=score;
    }
    if(secondScore<best){pending[count]=second;scores[count++]=secondScore;}
    if(firstScore<best){pending[count]=first;scores[count++]=firstScore;}
   }
  }
  return face;
 };
}
