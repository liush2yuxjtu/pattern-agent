import * as THREE from 'three';
export function validateHumanData(data){
 const vector=v=>Array.isArray(v)&&v.length===3&&v.every(Number.isFinite);
 if(!data||!Array.isArray(data.vertices)||!data.vertices.length||!data.vertices.every(vector)||!Array.isArray(data.triangles)||!data.triangles.length||!data.triangles.every(t=>Array.isArray(t)&&t.length===3&&t.every(i=>Number.isInteger(i)&&i>=0&&i<data.vertices.length))||!vector(data.bodyBounds?.min)||!vector(data.bodyBounds?.max)||data.bodyBounds.max[1]<=data.bodyBounds.min[1]||!(data.chestSection?.circumferenceSourceUnits>0)||!['l-shoulder','r-shoulder','l-elbow','r-elbow','neck'].every(k=>vector(data.joints?.[k]))||typeof data.revision!=='string')throw Error('人体文件缺少有效网格、关节或标定范围');
 return data;
}
// A visualization transform of the attributed CC0 asset, not a personalized avatar.
export function humanPositions(data,{chestMm=960,anchorY=.325,armAngleDegrees=43}={}){
 const horizontal=chestMm/1000/data.chestSection.circumferenceSourceUnits;
 const vertical=1.75/(data.bodyBounds.max[1]-data.bodyBounds.min[1]);
 const centerZ=.60,anchorSourceY=5.70,shoulder=data.joints['l-shoulder'],elbow=data.joints['l-elbow'],baseAngle=Math.atan2(shoulder[1]-elbow[1],elbow[0]-shoulder[0]),angle=baseAngle-armAngleDegrees*Math.PI/180;
 return data.vertices.map(([x,y,z])=>{
  const sign=x<0?-1:1,shoulder=data.joints['l-shoulder'];
  const clamp=v=>Math.max(0,Math.min(1,v));
  const w=clamp(y)*clamp((Math.abs(x)-1.45)/.65)*Math.max(clamp((y-1.25)/.8),clamp((Math.abs(x)-2)/.6));
  const px=Math.abs(x)-shoulder[0],py=y-shoulder[1],rx=shoulder[0]+px*Math.cos(angle)-py*Math.sin(angle),ry=shoulder[1]+px*Math.sin(angle)+py*Math.cos(angle);
  const posedX=Math.abs(x)+(rx-Math.abs(x))*w,posedY=y+(ry-y)*w;
  return[sign*posedX*horizontal,anchorY+(posedY-anchorSourceY)*vertical,(z-centerZ)*horizontal];
 });
}
export function makeHuman(data,pattern,armAngleDegrees=43){
 const group=new THREE.Group(),geometry=new THREE.BufferGeometry(),material=new THREE.MeshStandardMaterial({color:0xb6b2a6,roughness:.96,metalness:0,transparent:false,opacity:1,side:THREE.DoubleSide});
 const options={chestMm:pattern.measurements.chest,anchorY:pattern.parts.front.points.hem.y/2000,armAngleDegrees},positions=humanPositions(data,options),joints=Object.fromEntries(['l-shoulder','l-elbow','r-shoulder','r-elbow','neck'].map(k=>[k,humanPositions({...data,vertices:[data.joints[k]]},options)[0]]));
 geometry.setAttribute('position',new THREE.Float32BufferAttribute(positions.flat(),3));geometry.setIndex(data.triangles.flat());geometry.computeVertexNormals();
 const mesh=new THREE.Mesh(geometry,material);group.add(mesh);group.name='MakeHuman CC0 reference human';
 return{group,data,mesh,body:{vertices:positions,triangles:data.triangles,joints,waistY:options.anchorY+(2.5-5.7)*1.75/(data.bodyBounds.max[1]-data.bodyBounds.min[1])},dispose:()=>{geometry.dispose();material.dispose();}};
}
