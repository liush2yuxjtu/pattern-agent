// Independent grading adapter: actual Human Studio/Three.js skeletal export.
import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
const root=path.resolve(import.meta.dirname,'../..');
const THREE=await import(pathToFileURL(root+'/web/human-studio/vendor/three.module.js'));
const {buildRestVertices,jointPosition}=await import(pathToFileURL(root+'/web/human-studio/body-engine.js'));
const data=JSON.parse(fs.readFileSync(root+'/web/human-studio/assets/human.json'));
const state=JSON.parse(fs.readFileSync(process.argv[2]||import.meta.dirname+'/initial-state.json'));
const prefix=process.argv[3]||import.meta.dirname+'/posed';
const positions=buildRestVertices(data,state.morphWeights),index=new Map(data.bones.map((b,i)=>[b.name,i]));
const heads=data.bones.map(b=>new THREE.Vector3(...jointPosition(data,positions,b.head)));
const q=data.bones.map((b,i)=>{const y=new THREE.Vector3(...jointPosition(data,positions,b.tail)).sub(heads[i]).normalize();if(y.lengthSq()<.5)y.set(0,1,0);const x=new THREE.Vector3().crossVectors(y,new THREE.Vector3(0,0,1));if(x.lengthSq()<1e-8)x.crossVectors(y,new THREE.Vector3(0,1,0));x.normalize();const z=new THREE.Vector3().crossVectors(x,y).normalize();return new THREE.Quaternion().setFromRotationMatrix(new THREE.Matrix4().makeBasis(x,y,z));});
const geometry=new THREE.BufferGeometry();geometry.setAttribute('position',new THREE.Float32BufferAttribute(positions,3));geometry.setIndex(data.indices);geometry.setAttribute('skinIndex',new THREE.Uint16BufferAttribute(data.skinIndices,4));geometry.setAttribute('skinWeight',new THREE.Float32BufferAttribute(data.skinWeights,4));geometry.computeVertexNormals();
const mesh=new THREE.SkinnedMesh(geometry,new THREE.MeshStandardMaterial({color:0xb6a99c}));mesh.name='MakeHuman actual anatomical mesh';
const bones=data.bones.map(b=>{const bone=new THREE.Bone();bone.name=b.name;return bone;});
data.bones.forEach((b,i)=>{const p=index.get(b.parent);if(p!==undefined){bones[p].add(bones[i]);bones[i].position.copy(heads[i]).sub(heads[p]).applyQuaternion(q[p].clone().invert());bones[i].quaternion.copy(q[p].clone().invert().multiply(q[i]));}else{mesh.add(bones[i]);bones[i].position.copy(heads[i]);bones[i].quaternion.copy(q[i]);}});
mesh.updateMatrixWorld(true);const skeleton=new THREE.Skeleton(bones);mesh.bind(skeleton);mesh.normalizeSkinWeights();
bones.forEach(b=>{const a=state.poseDegrees[b.name]||[0,0,0];b.quaternion.multiply(new THREE.Quaternion().setFromEuler(new THREE.Euler(...a.map(v=>v*Math.PI/180),'XYZ')));});
mesh.updateMatrixWorld(true);skeleton.update();
let floor=Infinity;const verts=data.bodyVertexIds.map(i=>{const v=new THREE.Vector3().fromBufferAttribute(geometry.attributes.position,i);mesh.applyBoneTransform(i,v);floor=Math.min(floor,v.y);return v;});
const map=new Map(data.bodyVertexIds.map((id,i)=>[id,i+1]));
fs.writeFileSync(prefix+'.obj',['# Actual linear-blend skinned MakeHuman, cm Y up',...verts.map(v=>'v '+[v.x,v.y-floor,v.z].map(v=>v.toFixed(8)).join(' ')),...Array.from({length:data.indices.length/3},(_,i)=>'f '+data.indices.slice(i*3,i*3+3).map(id=>map.get(id)).join(' '))].join('\n')+'\n');
fs.writeFileSync(prefix+'-joints.json',JSON.stringify({units:'cm',source:'Actual163bone rig after source-compatible skinning',joints:bones.map((b,i)=>{const v=b.getWorldPosition(new THREE.Vector3());return{name:b.name,parent:data.bones[i].parent,position:[v.x,v.y-floor,v.z]};})},null,2));
if(process.argv.includes('--glb')){
  globalThis.FileReader=class{readAsArrayBuffer(blob){blob.arrayBuffer().then(v=>{this.result=v;this.onloadend?.();});}readAsDataURL(blob){blob.arrayBuffer().then(v=>{this.result='data:'+blob.type+';base64,'+Buffer.from(v).toString('base64');this.onloadend?.();});}};
  const exporterSource=fs.readFileSync(root+'/web/human-studio/vendor/GLTFExporter.js','utf8').replaceAll("from 'three'","from '"+pathToFileURL(root+'/web/human-studio/vendor/three.module.js').href+"'");
  const {GLTFExporter}=await import('data:text/javascript;base64,'+Buffer.from(exporterSource).toString('base64'));
  const group=new THREE.Group();group.add(mesh);group.scale.setScalar(.01);group.position.y=-floor*.01;group.userData={...state,exportUnits:'metres',bodyDimensionsCm:state.dimensions};group.updateMatrixWorld(true);
  const bin=await new GLTFExporter().parseAsync(group,{binary:true,onlyVisible:true});fs.writeFileSync(prefix+'.glb',Buffer.from(bin));
}
console.log(JSON.stringify({mesh:prefix+'.obj',groundOffsetCm:-floor,bones:bones.length,pose:state.poseDegrees}));
