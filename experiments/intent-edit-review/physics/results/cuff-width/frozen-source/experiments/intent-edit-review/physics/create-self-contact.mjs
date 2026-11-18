import {MeshContact} from './mesh-contact.mjs';

// BufferGeometry.setIndex accepts a JS Array or BufferAttribute, not a raw typed
// array. A Uint32Array can otherwise produce a BVH with zero triangle callbacks.
export function createSelfContact(positions,triangles,thickness,options={}){
 const contact=new MeshContact(positions,Array.from(triangles),thickness,{...options,sweptBounds:true});
 if(!contact.geometry.index?.isBufferAttribute||contact.geometry.index.count!==triangles.length)throw Error('Actual self-contact index buffer is incomplete');
 let visits=0;contact.tree.shapecast({intersectsBounds:()=>true,intersectsTriangle:()=>{visits++;return false;}});
 if(visits!==triangles.length/3)throw Error('Actual self-contact BVH omitted triangles');
 contact.verifiedTriangleCount=visits;
 return contact;
}
