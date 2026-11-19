import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {BufferGeometry, Float32BufferAttribute, Vector3} from 'three';
import {MeshBVH, SAH} from 'three-mesh-bvh';
import {createBodyQuery} from './source/body-query.js';

const body=JSON.parse(readFileSync(new URL('./source/body.json',import.meta.url)));
const geometry=new BufferGeometry();
geometry.setAttribute('position',new Float32BufferAttribute(body.vertices,3));
geometry.setIndex(body.indices);
const bvh=new MeshBVH(geometry,{strategy:SAH,indirect:true,maxLeafSize:8});
const query=createBodyQuery(bvh,geometry);
const point=new Vector3(), hit=new Vector3(), reference={point:new Vector3()};
const samples=[];
let state=20261119;
function random() {
 state=(Math.imul(1664525,state)+1013904223)>>>0;
 return state/2**32;
}
for(let i=0;i<4096;i++)samples.push([random()-.5,random()*1.8,random()-.5]);
const positions=geometry.attributes.position.array;
for(let i=0;i<positions.length;i+=51)samples.push(Array.from(positions.subarray(i,i+3)));
for(const [x,y,z] of samples){
 bvh.closestPointToPoint(point.set(x,y,z),reference);
 assert.equal(query(x,y,z,hit),reference.faceIndex);
 assert.deepEqual(hit.toArray(),reference.point.toArray());
}
console.log(JSON.stringify({verdict:'PASS',exactFaceAndPoint:samples.length,includesExactMeshVertices:true}));
