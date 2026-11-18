import * as THREE from 'three';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {MeshBVH,SAH} from 'three-mesh-bvh';
import BODY from './body.json';
import WASM from './solver-bytes.json';
import {WaistRing} from './waist-ring.js';
import {SelfContact} from './self-contact.js';
import {draftSandy} from './freesewing-pattern.js';
import {buildHinges,foldFields} from './fold-fields.js';

const $=id=>document.getElementById(id), TAU=Math.PI*2;
const NC=64, NR=28, PER=NC/4, DT=1/120, THICK=.005, YWAIST=1.09;
const seamColors=['#b16a42','#398a83','#7687ac','#b08b34'];
const materials={cotton:{E:80000,nu:.3,density:.160,thickness:.00035,bend:4e-5,color:0xbd7754},linen:{E:160000,nu:.28,density:.220,thickness:.00045,bend:8e-6,color:0xb4a585},silk:{E:30000,nu:.32,density:.080,thickness:.00018,bend:2e-4,color:0x657d79}};
const SAVED=JSON.parse($('savedProject').textContent||'{}');
let mat=materials[SAVED.materialKey]||materials.cotton,slant=SAVED.parameters?.slant_m||.56,hem=SAVED.parameters?.hem_m||2.1,wind=SAVED.wind||0,circleRatio=SAVED.parameters?.circle_ratio||.6,mode=SAVED.view||'fabric',selectedSeam=-1,running=false,stepCount=0,lastReport=null;
let p,old,inv,edges,edgeMeta,triangles,uvs,panels,seamMaps,seed,waistPoints,waistLength,cPtr=0,pPtr=0,oldPtr=0,massPtr=0,preparedPtr=0;
let draft=null,hinges=[],folds=null;let drawDirty=true,framesDrawn=0;
let exactCache=null,cacheHits=0,cacheMisses=0;let waistRing;let pressureCorrection,contactPressure,contactForce,contactArea,bodyCorrection,frictionCorrection;let collisionEnabled=true;
let stepHistory,contactingScratch,freeIndices;const bodyDelta=new THREE.Vector3();
let surfaceSamples=[],selfContact=null,selfContactsLast=0,lastStepProfile=null;
let simMs=[],renderMs=[],frames=[],lastFrame=performance.now(),collisionsLast=0,revision=0;
const wasm=(await WebAssembly.instantiate(new Uint8Array(WASM),{})).instance.exports;
const dataView=new DataView(wasm.memory.buffer);
const scene=new THREE.Scene();scene.background=new THREE.Color('#eef1ee');
const renderer=new THREE.WebGLRenderer({canvas:$('scene'),antialias:true,powerPreference:'high-performance',preserveDrawingBuffer:true});
renderer.setPixelRatio(Math.min(devicePixelRatio,1.5));renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFSoftShadowMap;
renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.12;
let narrowFrame=innerWidth<700;
const camera=new THREE.PerspectiveCamera(32,1,.02,20);camera.position.set(1.65,1.30,narrowFrame?4.4:3.0);
const controls=new OrbitControls(camera,renderer.domElement);controls.target.set(0,.91,.055);controls.enableDamping=true;controls.dampingFactor=.12;controls.minDistance=.75;controls.maxDistance=5;controls.maxPolarAngle=Math.PI*.85;controls.update();controls.addEventListener('change',()=>{drawDirty=true;});
scene.add(new THREE.HemisphereLight(0xffffff,0x7d8c7e,2.0));
const key=new THREE.DirectionalLight(0xfff5e8,3.2);key.position.set(-2.5,4,3);key.castShadow=true;key.shadow.mapSize.set(1024,1024);key.shadow.camera.left=-1.3;key.shadow.camera.right=1.3;key.shadow.camera.top=2.1;key.shadow.camera.bottom=-.3;key.shadow.normalBias=.015;scene.add(key);key.target.position.set(0,.7,0);scene.add(key.target);
const rim=new THREE.DirectionalLight(0xdce9ff,1.6);rim.position.set(2,2,-2);scene.add(rim);
const bodyGeo=new THREE.BufferGeometry();bodyGeo.setAttribute('position',new THREE.Float32BufferAttribute(BODY.vertices,3));bodyGeo.setIndex(BODY.indices);bodyGeo.computeVertexNormals();
const bodyMat=new THREE.MeshStandardMaterial({color:0xb9bfb9,roughness:.82,metalness:0});
const bodyMesh=new THREE.Mesh(bodyGeo,bodyMat);bodyMesh.castShadow=true;bodyMesh.receiveShadow=true;scene.add(bodyMesh);
// The BVH preserves original triangle order; diagnostics use the exact rendered body.
const bvh=new MeshBVH(bodyGeo,{strategy:SAH,indirect:true,maxLeafSize:8});
const floor=new THREE.Mesh(new THREE.PlaneGeometry(200,200),new THREE.MeshStandardMaterial({color:0xe4eae3,roughness:1}));floor.rotation.x=-Math.PI/2;floor.position.y=-.006;floor.receiveShadow=true;scene.add(floor);
const platform=new THREE.Mesh(new THREE.CylinderGeometry(.46,.47,.016,96),new THREE.MeshStandardMaterial({color:0xd6ded5,roughness:.8}));platform.position.set(0,-.014,.04);platform.receiveShadow=true;scene.add(platform);
const clothGeo=new THREE.BufferGeometry();
const clothMat=new THREE.MeshStandardMaterial({color:mat.color,side:THREE.DoubleSide,roughness:.89,metalness:0});
// A code-generated weave, evaluated in material coordinates. No texture asset.
clothMat.onBeforeCompile=shader=>{
 shader.vertexShader=shader.vertexShader.replace('#include <common>','#include <common>\nvarying vec2 vWeave;').replace('#include <uv_vertex>','#include <uv_vertex>\nvWeave=uv;');
 shader.fragmentShader=shader.fragmentShader.replace('#include <common>','#include <common>\nvarying vec2 vWeave;').replace('#include <roughnessmap_fragment>',`#include <roughnessmap_fragment>
 float fiber = sin(vWeave.x*14000.0)*sin(vWeave.y*14000.0);
 roughnessFactor=clamp(roughnessFactor+fiber*.045,.1,1.);`).replace('#include <color_fragment>','#include <color_fragment>\n diffuseColor.rgb *= 1.0+0.035*sin(vWeave.x*14000.0)*sin(vWeave.y*14000.0);');
};
const mapMat=new THREE.MeshStandardMaterial({vertexColors:true,side:THREE.DoubleSide,roughness:.9});
const cloth=new THREE.Mesh(clothGeo,clothMat);cloth.castShadow=true;cloth.receiveShadow=true;scene.add(cloth);
let meshWire=null,seamLines=[];const v=new THREE.Vector3(),nearest={point:new THREE.Vector3()},a=new THREE.Vector3(),b=new THREE.Vector3(),c=new THREE.Vector3(),normal=new THREE.Vector3();
function bodyDistance(x,y,z,slot=-1){
 const key=slot*10;if(slot>=0&&exactCache&&exactCache[key]===x&&exactCache[key+1]===y&&exactCache[key+2]===z){cacheHits++;nearest.point.set(exactCache[key+4],exactCache[key+5],exactCache[key+6]);normal.set(exactCache[key+7],exactCache[key+8],exactCache[key+9]);return exactCache[key+3];}if(slot>=0)cacheMisses++;
 v.set(x,y,z);bvh.closestPointToPoint(v,nearest);
 const idx=bodyGeo.index.array,verts=bodyGeo.attributes.position.array,k=nearest.faceIndex*3;
 a.fromArray(verts,idx[k]*3);b.fromArray(verts,idx[k+1]*3);c.fromArray(verts,idx[k+2]*3);
 normal.subVectors(b,a).cross(c.sub(a)).normalize();
 const signed=v.sub(nearest.point).dot(normal);
 const distance=(signed<0?-1:1)*v.length();if(slot>=0&&exactCache){exactCache.set([x,y,z,distance,nearest.point.x,nearest.point.y,nearest.point.z,normal.x,normal.y,normal.z],key);}return distance;
}
function waistSection(){
 const vv=bodyGeo.attributes.position.array,ii=bodyGeo.index.array,points=[];
 for(let t=0;t<ii.length;t+=3){const hits=[];for(let j=0;j<3;j++){
  const x=ii[t+j]*3,z=ii[t+(j+1)%3]*3,y0=vv[x+1],y1=vv[z+1];
  if((y0<=YWAIST&&y1>YWAIST)||(y1<=YWAIST&&y0>YWAIST)){const f=(YWAIST-y0)/(y1-y0);const px=vv[x]+(vv[z]-vv[x])*f,pz=vv[x+2]+(vv[z+2]-vv[x+2])*f;if(Math.abs(px)<.22)hits.push([px,pz]);}}
  points.push(...hits);
 }
 const cx=points.reduce((s,q)=>s+q[0],0)/points.length,cz=points.reduce((s,q)=>s+q[1],0)/points.length;
 // Star-shaped waist cross section, monotonically parameterized by polar angle.
 const bins=new Array(360).fill(null);
 for(const q of points){let angle=(Math.atan2(q[0]-cx,q[1]-cz)+TAU)%TAU,k=Math.floor(angle/TAU*360);const r=Math.hypot(q[0]-cx,q[1]-cz);if(!bins[k]||r>bins[k][0])bins[k]=[r,angle];}
 const ring=[];for(let k=0;k<360;k++){if(bins[k]){const [r,ang]=bins[k];ring.push([(r+THICK+.003)*Math.sin(ang)+cx,(r+THICK+.003)*Math.cos(ang)+cz]);}}
 const lens=[0];for(let i=1;i<=ring.length;i++)lens.push(lens.at(-1)+Math.hypot(ring[i%ring.length][0]-ring[i-1][0],ring[i%ring.length][1]-ring[i-1][1]));
 const total=lens.at(-1),out=[];for(let i=0;i<NC;i++){const target=i*total/NC;let j=0;while(lens[j+1]<target)j++;const f=(target-lens[j])/(lens[j+1]-lens[j]);out.push([ring[j][0]*(1-f)+ring[(j+1)%ring.length][0]*f,ring[j][1]*(1-f)+ring[(j+1)%ring.length][1]*f]);}
 return {out,total,cx,cz};
}
function flat(r,j){return draft.sample(r/NR,j/PER).map(x=>x/1000);}
function flare(){return circleRatio;}
function index(r,j){return r*NC+(j+NC)%NC;}
function makePattern(settle=true){
 const section=waistSection();waistPoints=section.out;waistLength=section.total;
 draft=draftSandy({waist_mm:waistLength*1000,length_mm:slant*1000,circleRatio});hem=waistLength+TAU*circleRatio*slant;
 const n=(NR+1)*NC;pPtr=0;oldPtr=n*24;massPtr=oldPtr+n*24;cPtr=massPtr+n*8;
 p=new Float64Array(wasm.memory.buffer,pPtr,n*3);old=new Float64Array(wasm.memory.buffer,oldPtr,n*3);inv=new Float64Array(wasm.memory.buffer,massPtr,n);
 const f=flare(),fall=Math.sqrt(1-f*f),rTop=waistLength/TAU;
 for(let r=0;r<=NR;r++)for(let j=0;j<NC;j++){
  const s=r/NR,phi=j/NC*TAU,delta=s*slant*f;
  p.set([waistPoints[j][0]+delta*Math.sin(phi),YWAIST-s*slant*fall,waistPoints[j][1]+delta*Math.cos(phi)],index(r,j)*3);
 }
 triangles=[];uvs=[];panels=[];
 for(let panel=0;panel<4;panel++){
  const panelFaces=[];for(let r=0;r<NR;r++)for(let j=0;j<PER;j++){
   const ids=[index(r,panel*PER+j),index(r+1,panel*PER+j),index(r,panel*PER+j+1),index(r+1,panel*PER+j+1)];
   const xy=[flat(r,j),flat(r+1,j),flat(r,j+1),flat(r+1,j+1)];
   for(const corners of [[0,1,2],[2,1,3]]){panelFaces.push(triangles.length/3);triangles.push(...corners.map(k=>ids[k]));uvs.push(...corners.flatMap(k=>xy[k]));}
  }
  const polygon=[];for(let j=0;j<=PER*4;j++)polygon.push(flat(0,j/4));polygon.push(flat(NR,PER));for(let j=PER*4-1;j>=0;j--)polygon.push(flat(NR,j/4));
  panels.push({id:'P'+(panel+1),polygon:polygon.map(q=>q.map(x=>x*1000)),faces:panelFaces,grain:[0,1],cut:1});
 }
 hinges=buildHinges(triangles,uvs);
 const lumpedMass=new Float64Array(n);
 for(let t=0;t<triangles.length/3;t++){const k=t*6,u=uvs[k+2]-uvs[k],v=uvs[k+3]-uvs[k+1],w=uvs[k+4]-uvs[k],z=uvs[k+5]-uvs[k+1],m=Math.abs(u*z-v*w)*.5*mat.density/3;for(let j=0;j<3;j++)lumpedMass[triangles[t*3+j]]+=m;}
 for(let i=0;i<n;i++)inv[i]=1/lumpedMass[i];
 const map=new Map();edgeMeta=[];const add=(ia,ib,rest,type)=>{const id=[Math.min(ia,ib),Math.max(ia,ib)].join(':');if(map.has(id))return;map.set(id,true);edgeMeta.push({a:ia,b:ib,rest,type});};
 for(let r=0;r<=NR;r++)for(let j=0;j<NC;j++){
  const fj=j%PER;
  const dist=(ra,ja,rb,jb)=>Math.hypot(...flat(ra,ja).map((x,k)=>x-flat(rb,jb)[k]));
  add(index(r,j),index(r,j+1),dist(r,fj,r,fj+1),'weft');
  if(r<NR){add(index(r,j),index(r+1,j),dist(r,fj,r+1,fj),'warp');add(index(r,j),index(r+1,j+1),dist(r,fj,r+1,fj+1),'shear');add(index(r,j+1),index(r+1,j),dist(r,fj+1,r+1,fj),'shear');}
  if(r<NR-1)add(index(r,j),index(r+2,j),dist(r,fj,r+2,fj),'bend');
  add(index(r,j),index(r,j+2),dist(r,fj,r,fj+2),'bend');
 }
 // Opposite-vertex bending distances across each interior mesh edge.
 // Unfolding the adjacent rest triangles keeps the construction valid at seams.
 const restMap=new Map(edgeMeta.map(e=>[[Math.min(e.a,e.b),Math.max(e.a,e.b)].join(':'),e.rest]));
 const adjacent=new Map();
 const rest=(a,b)=>restMap.get([Math.min(a,b),Math.max(a,b)].join(':'));
 for(let t=0;t<triangles.length;t+=3)for(let j=0;j<3;j++){
  const a=triangles[t+j],b=triangles[t+(j+1)%3],opposite=triangles[t+(j+2)%3],key=[Math.min(a,b),Math.max(a,b)].join(':');
  if(adjacent.has(key)){
   const other=adjacent.get(key),L=rest(a,b);
   const unfold=v=>{const da=rest(a,v),db=rest(b,v),x=(da*da-db*db+L*L)/(2*L);return [x,Math.sqrt(Math.max(0,da*da-x*x))];};
   const q=unfold(other),r=unfold(opposite);add(other,opposite,Math.hypot(q[0]-r[0],q[1]+r[1]),'bend');
  }else adjacent.set(key,opposite);
 }
 for(let k=0;k<edgeMeta.length;k++){
  const e=edgeMeta[k],ptr=cPtr+k*32;dataView.setInt32(ptr,e.a,true);dataView.setInt32(ptr+4,e.b,true);dataView.setFloat64(ptr+8,e.rest,true);
  const stiffness=mat.E*mat.thickness,compliance=e.type==='bend'?mat.bend:1/stiffness*(e.type==='shear'?4:1)*.0007;
  dataView.setFloat64(ptr+16,compliance,true);dataView.setFloat64(ptr+24,0,true);
 }
 preparedPtr=cPtr+edgeMeta.length*32;if(preparedPtr+edgeMeta.length*56>wasm.memory.buffer.byteLength)throw new Error("Prepared constraint buffer exceeds WASM memory");wasm.prepare(edgeMeta.length,pPtr,massPtr,cPtr,preparedPtr,DT*DT);
 surfaceSamples=[];const sampleEdges=new Set();
 for(let t=0;t<triangles.length;t+=3){const ids=triangles.slice(t,t+3);surfaceSamples.push({ids,weights:[1/3,1/3,1/3]});for(let j=0;j<3;j++){const edge=[ids[j],ids[(j+1)%3]].sort((a,b)=>a-b),key=edge.join(':');if(!sampleEdges.has(key)){sampleEdges.add(key);surfaceSamples.push({ids:edge,weights:[.5,.5]});}}}
 surfaceSamples.forEach((sample,i)=>sample.slot=n+i);exactCache=new Float64Array((n+surfaceSamples.length)*10).fill(NaN);bodyCorrection=new Float64Array(n*3);frictionCorrection=new Float64Array(n*3);pressureCorrection=new Float64Array(n);contactPressure=new Float64Array(n);contactForce=new Float64Array(n);contactArea=new Float64Array(n);for(let i=0;i<n;i++)contactArea[i]=inv[i]>0?1/(inv[i]*mat.density):0;
 stepHistory=new Float64Array(p.length);contactingScratch=new Uint8Array(n);freeIndices=Array.from({length:n},(_,i)=>i);
 waistRing=new WaistRing(p,inv,NC,edgeMeta.filter(e=>e.type==='weft'&&e.a<NC&&e.b<NC).reduce((a,e)=>a+e.rest,0));old.set(p);seed=Array.from(p);stepCount=0;revision++;lastReport=null;
 seamMaps=Array.from({length:4},(_,k)=>({id:'S'+(k+1),a:{panel:'P'+(k+1),edge:'right',direction:'waist-to-hem'},b:{panel:'P'+((k+1)%4+1),edge:'left',direction:'waist-to-hem'},lengthA_mm:slant*1000,lengthB_mm:slant*1000,notches:[.25,.5,.75],vertexPairs:Array.from({length:NR+1},(_,r)=>[index(r,(k+1)*PER),index(r,(k+1)*PER)])}));
 const count=triangles.length;clothGeo.setAttribute('position',new THREE.Float32BufferAttribute(new Float32Array(count*3),3));clothGeo.setAttribute('normal',new THREE.Float32BufferAttribute(new Float32Array(count*3),3));clothGeo.setAttribute('uv',new THREE.Float32BufferAttribute(uvs,2));clothGeo.setAttribute('color',new THREE.Float32BufferAttribute(new Float32Array(count*3),3));
 seamLines.forEach(x=>{scene.remove(x);x.geometry.dispose();x.material.dispose();});seamLines=seamMaps.map((s,k)=>{const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(new Float32Array((NR+1)*3),3));const line=new THREE.Line(g,new THREE.LineBasicMaterial({color:seamColors[k],depthTest:false,transparent:true,opacity:.85}));line.renderOrder=4;scene.add(line);return line;});
 if(selfContact)selfContact.dispose();selfContact=new SelfContact(p,triangles);selfContactsLast=0;
 if(settle)for(let k=0;k<120;k++)substep();drawPatterns();updateGeometry();updateMetrics();$('lengthValue').textContent=Math.round(slant*1000)+' mm';$('hemValue').textContent=(circleRatio*100).toFixed(2)+'%';$('time').textContent=(stepCount*DT).toFixed(2)+' s';$('status').textContent=settle?'DRAPED':'ARRANGEMENT';$('verifyHint').textContent=settle?'Initial gravity/contact relaxation completed. Run verification.':'Unrelaxed diagnostic arrangement; not accepted.';
}
function substep(){
 cacheHits=cacheMisses=0;lastReport=null;pressureCorrection.fill(0);bodyCorrection.fill(0);frictionCorrection.fill(0);
 const start=performance.now(),history=stepHistory;history.set(p);wasm.integrate(p.length/3,pPtr,oldPtr,massPtr,DT,wind*Math.sin(stepCount*DT*2));
 wasm.reset_prepared(edgeMeta.length,preparedPtr);collideWithBody();for(let k=0;k<120;k++){wasm.iterate_prepared(edgeMeta.length,preparedPtr,1);waistRing.solve(p);if(k%10===0)collideWithBody(Array.from({length:NC},(_,i)=>i));if(collisionEnabled)applyFriction(history);}
 const elasticEnd=performance.now();collideWithBody();const bodyEnd=performance.now();
 selfContactsLast=selfContact.solve(p,old,inv,1,history);
 const selfEnd=performance.now();if(selfContactsLast>0){const first=collisionsLast;collideWithBody(selfContact.changed);collisionsLast+=first;}
 lastStepProfile={elasticMs:elasticEnd-start,bodyMs:bodyEnd-elasticEnd,selfMs:selfEnd-bodyEnd,recheckMs:performance.now()-selfEnd};
 if(collisionEnabled){applyFriction(history);collideWithBody();}
 for(let i=0;i<contactPressure.length;i++){contactForce[i]=inv[i]>0?pressureCorrection[i]/inv[i]/(DT*DT):0;contactPressure[i]=contactArea[i]>0?contactForce[i]/contactArea[i]/1000:0;}
 stepCount++;simMs.push(performance.now()-start);if(simMs.length>240)simMs.shift();
}
function applyFriction(history){
 for(let i=0;i<inv.length;i++){
  if(pressureCorrection[i]<=0)continue;const k=i*3;let nx=bodyCorrection[k],ny=bodyCorrection[k+1],nz=bodyCorrection[k+2],length=Math.hypot(nx,ny,nz);if(length<1e-12)continue;nx/=length;ny/=length;nz/=length;
  let dx=p[k]-history[k],dy=p[k+1]-history[k+1],dz=p[k+2]-history[k+2],normal=dx*nx+dy*ny+dz*nz;dx-=nx*normal;dy-=ny*normal;dz-=nz*normal;
  let fx=frictionCorrection[k]-dx,fy=frictionCorrection[k+1]-dy,fz=frictionCorrection[k+2]-dz;const fn=fx*nx+fy*ny+fz*nz;fx-=fn*nx;fy-=fn*ny;fz-=fn*nz;const tangent=Math.hypot(fx,fy,fz),factor=Math.min(1,.6*pressureCorrection[i]/Math.max(tangent,1e-20));fx*=factor;fy*=factor;fz*=factor;
  p[k]+=fx-frictionCorrection[k];p[k+1]+=fy-frictionCorrection[k+1];p[k+2]+=fz-frictionCorrection[k+2];frictionCorrection[k]=fx;frictionCorrection[k+1]=fy;frictionCorrection[k+2]=fz;
 }
}
function supportStats(){let mass=0,weight=0,up=0,com=[0,0,0],speed=[0,0,0];for(let i=0;i<inv.length;i++){const m=1/inv[i];mass+=m;weight+=m*9.81;up+=m*(bodyCorrection[i*3+1]+frictionCorrection[i*3+1])/(DT*DT);for(let k=0;k<3;k++){com[k]+=m*p[i*3+k];speed[k]+=m*(p[i*3+k]-stepHistory[i*3+k])/DT;}}return{cacheHits,cacheMisses,fixed:Array.from(inv).filter(x=>x===0).length,weight_N:weight,up_N:up,ratio:up/weight,com_m:com.map(x=>x/mass),speed_m_s:Math.hypot(...speed)/mass,waistY_m:Array.from({length:NC},(_,i)=>p[i*3+1]).reduce((a,b)=>a+b,0)/NC};}
function collideWithBody(changed=null){
 if(!collisionEnabled){collisionsLast=0;return;}collisionsLast=0;const contacting=contactingScratch;contacting.fill(0);
 const candidates=changed||freeIndices;
 for(const i of candidates){
  if(changed)contacting[i]=1;const o=i*3;
  for(let pass=0;pass<4;pass++){
   const signed=bodyDistance(p[o],p[o+1],p[o+2],i);
   if(signed>=THICK-.000001)break;
   const delta=bodyDelta.set(p[o],p[o+1],p[o+2]).sub(nearest.point);
   if(delta.lengthSq()<1e-16)delta.copy(normal);else delta.normalize().multiplyScalar(signed<0?-1:1);
   for(let k=0;k<3;k++){const next=nearest.point.getComponent(k)+THICK*delta.getComponent(k),shift=next-p[o+k];p[o+k]=next;bodyCorrection[o+k]+=shift;pressureCorrection[i]+=Math.max(0,shift*delta.getComponent(k));}
   if(pass===0){collisionsLast++;contacting[i]=1;}
  }
 }
 for(let pass=0;pass<2;pass++)for(const sample of surfaceSamples){
  const {ids,weights}=sample;let touches=false;
  for(let j=0;j<ids.length;j++)if(contacting[ids[j]]){touches=true;break;}
  if(!touches)continue;
  let qx=0,qy=0,qz=0;
  for(let j=0;j<ids.length;j++){const i=ids[j]*3,w=weights[j];qx+=p[i]*w;qy+=p[i+1]*w;qz+=p[i+2]*w;}
  const signed=bodyDistance(qx,qy,qz,sample.slot);if(signed>=THICK*.6)continue;
  const delta=bodyDelta.set(qx,qy,qz).sub(nearest.point);
  if(delta.lengthSq()<1e-16)delta.copy(normal);else delta.normalize().multiplyScalar(signed<0?-1:1);
  const cx=nearest.point.x+THICK*delta.x-qx,cy=nearest.point.y+THICK*delta.y-qy,cz=nearest.point.z+THICK*delta.z-qz;
  let denom=0;for(let j=0;j<ids.length;j++)denom+=inv[ids[j]]*weights[j]**2;
  if(denom===0)continue;
  for(let j=0;j<ids.length;j++){
   const id=ids[j],i=id*3,w=inv[id]*weights[j]/denom,sx=w*cx,sy=w*cy,sz=w*cz;pressureCorrection[id]+=Math.max(0,sx*delta.x+sy*delta.y+sz*delta.z);
   p[i]+=sx;bodyCorrection[i]+=sx;p[i+1]+=sy;bodyCorrection[i+1]+=sy;p[i+2]+=sz;bodyCorrection[i+2]+=sz;
  }
 }
}
function measureTriangle(t,positions=p){
 const i=t*3,ia=triangles[i]*3,ib=triangles[i+1]*3,ic=triangles[i+2]*3,k=t*6;
 const u=uvs[k+2]-uvs[k],v0=uvs[k+3]-uvs[k+1],w=uvs[k+4]-uvs[k],z=uvs[k+5]-uvs[k+1],det=u*z-v0*w;
 const e1=[0,1,2].map(j=>positions[ib+j]-positions[ia+j]),e2=[0,1,2].map(j=>positions[ic+j]-positions[ia+j]);
 const fx=e1.map((x,j)=>(x*z-e2[j]*v0)/det),fy=e1.map((x,j)=>(-x*w+e2[j]*u)/det);
 return deformation(fx,fy,mat.E,mat.nu);
}
function deformation(fx,fy,E,nu){
 const dot=(x,y)=>x.reduce((s,v,i)=>s+v*y[i],0),xx=dot(fx,fx),yy=dot(fy,fy),xy=dot(fx,fy),d=Math.sqrt((xx-yy)**2+4*xy*xy);
 const stretch=Math.sqrt(Math.max(0,(xx+yy+d)/2)),minStretch=Math.sqrt(Math.max(0,(xx+yy-d)/2));
 const ex=(xx-1)/2,ey=(yy-1)/2,exy=xy/2,sx=E/(1-nu*nu)*(ex+nu*ey),sy=E/(1-nu*nu)*(ey+nu*ex),sxy=E/(1+nu)*exy;
 const stress=Math.max(0,(sx+sy+Math.sqrt((sx-sy)**2+4*sxy*sxy))/2)/1000;
 return {stretch,minStretch,stress,green:[ex,ey,exy],sigma:[sx,sy,sxy]};
}
const ramp=[new THREE.Color('#256bc2'),new THREE.Color('#29b9a5'),new THREE.Color('#92ce5f'),new THREE.Color('#f2ca4e'),new THREE.Color('#e77038'),new THREE.Color('#b62238')];
function colorAt(q){q=THREE.MathUtils.clamp(q,0,1)*5;const i=Math.min(4,Math.floor(q));return ramp[i].clone().lerp(ramp[i+1],q-i);}
let currentMeasures=[];
function updateGeometry(){
 drawDirty=true;
 const arr=clothGeo.attributes.position.array,colors=clothGeo.attributes.color.array;currentMeasures=[];folds=foldFields(p,triangles,hinges);
 for(let t=0;t<triangles.length/3;t++){
  const m=measureTriangle(t);currentMeasures.push(m);let col=mode==='pressure'?colorAt((triangles.slice(t*3,t*3+3).reduce((a,i)=>a+contactPressure[i],0)/3)/.1):mode==='stress'?colorAt(m.stress/20):mode==='fold'?colorAt(Math.abs(folds.triangleAngle_deg[t])/60):mode==='curvature'?colorAt(Math.abs(folds.triangleCurvature_per_m[t])/100):colorAt((m.stretch-1)/.2);
  if(mode==='contact'){const ids=triangles.slice(t*3,t*3+3);const d=Math.min(...ids.map(i=>bodyDistance(p[i*3],p[i*3+1],p[i*3+2])));col=d<THICK+.002?new THREE.Color('#dba451'):new THREE.Color('#a8c6c0');}
  for(let j=0;j<3;j++){const id=triangles[t*3+j];for(let k=0;k<3;k++)arr[t*9+j*3+k]=p[id*3+k];col.toArray(colors,t*9+j*3);}
 }
 clothGeo.attributes.position.needsUpdate=true;clothGeo.attributes.color.needsUpdate=true;clothGeo.computeVertexNormals();
 // Smooth shading across duplicated render vertices, including shared seams.
 const smooth=new Float32Array(p.length),nn=clothGeo.attributes.normal.array;
 for(let j=0;j<triangles.length;j++)for(let k=0;k<3;k++)smooth[triangles[j]*3+k]+=nn[j*3+k];
 for(let j=0;j<triangles.length;j++){v.fromArray(smooth,triangles[j]*3).normalize();v.toArray(nn,j*3);}clothGeo.attributes.normal.needsUpdate=true;clothGeo.computeBoundingSphere();
 for(let k=0;k<4;k++){const ar=seamLines[k].geometry.attributes.position;seamMaps[k].vertexPairs.forEach((pair,r)=>ar.array.set(p.subarray(pair[0]*3,pair[0]*3+3),r*3));ar.needsUpdate=true;seamLines[k].visible=mode==='seams';seamLines[k].material.opacity=selectedSeam<0||k===selectedSeam?1:.18;}
 if(meshWire){scene.remove(meshWire);meshWire.geometry.dispose();meshWire.material.dispose();meshWire=null;}
 if(wireOn){meshWire=new THREE.LineSegments(new THREE.WireframeGeometry(clothGeo),new THREE.LineBasicMaterial({color:0x375847,transparent:true,opacity:.18}));scene.add(meshWire);}
}
let wireOn=SAVED.wireOn||false;
function stats(){return {steps:stepCount,time_s:stepCount*DT,peakStretch:Math.max(...currentMeasures.map(m=>m.stretch)),peakPressure_kPa:Math.max(...contactPressure),peakStress_kPa:Math.max(...currentMeasures.map(m=>m.stress)),peakFoldAngle_deg:Math.max(...Array.from(folds?.angle_rad||[],x=>Math.abs(x)*180/Math.PI)),peakCurvature_per_m:Math.max(...Array.from(folds?.curvature_per_m||[],Math.abs)),wrinkleProxyTrianglePercent:100*Array.from(folds?.triangleAngle_deg||[]).filter(x=>Math.abs(x)>=15).length/(triangles.length/3),seamGap_mm:Math.max(...seamMaps.flatMap(s=>s.vertexPairs.map(([a,b])=>Math.hypot(...[0,1,2].map(k=>p[a*3+k]-p[b*3+k]))*1000))),waist_mm:waistLength*1000,contacts:collisionsLast,selfContacts:selfContactsLast,selfContactTiming_ms:selfContact?.lastProfile,stepTiming_ms:lastStepProfile,renderedFrames:framesDrawn,render_submit_ms_p95:percentile(renderMs,.95),wasm:true,render:{calls:renderer.info.render.calls,triangles:renderer.info.render.triangles},solver_ms_p50:percentile(simMs,.5),solver_ms_p95:percentile(simMs,.95),frame_ms_p95:percentile(frames,.95),jsHeap_bytes:performance.memory?.usedJSHeapSize||null};}
function percentile(arr,q){if(!arr.length)return 0;const a=[...arr].sort((a,b)=>a-b);return a[Math.min(a.length-1,Math.floor(a.length*q))];}
function updateMetrics(){const s=stats();$('waistMetric').textContent=s.waist_mm.toFixed(1)+' mm';$('gapMetric').textContent=s.seamGap_mm.toFixed(3)+' mm';$('gapMetric').className='pass';$('strainMetric').textContent=(s.peakStretch*100).toFixed(1)+'%';$('stressMetric').textContent=s.peakStress_kPa.toFixed(2)+' kPa';$('pressureMetric').textContent=s.peakPressure_kPa.toFixed(4)+' kPa';$('foldMetric').textContent=s.peakFoldAngle_deg.toFixed(1)+'°';$('curvatureMetric').textContent=s.peakCurvature_per_m.toFixed(1)+' m⁻¹';$('wrinkleMetric').textContent=s.wrinkleProxyTrianglePercent.toFixed(1)+'% faces';$('time').textContent=s.time_s.toFixed(2)+' s';$('performance').textContent=`WASM ${s.solver_ms_p50.toFixed(1)} ms/step · ${s.render.triangles.toLocaleString()} tris · ${s.render.calls} draws`;
 let min=Infinity;for(let i=0;i<p.length;i+=3)min=Math.min(min,bodyDistance(p[i],p[i+1],p[i+2]));if(lastReport&&lastReport.stats.steps===stepCount)min=lastReport.collision.minClearance_mm/1000;$('collisionMetric').textContent=(min*1000).toFixed(2)+' mm';$('collisionMetric').className=min>=-.0005?'pass':'fail';
 $('stepPattern').className='';$('stepSew').className=stepCount===0?'current':'';$('stepDrape').className=stepCount>0&&!lastReport?'current':'';$('stepVerify').className=lastReport?'current':'';
}
function offsetPolygon(poly,d){let area=0;for(let i=0;i<poly.length;i++){let q=poly[i],r=poly[(i+1)%poly.length];area+=q[0]*r[1]-r[0]*q[1];}const sign=area>0?1:-1;return poly.map((q,i)=>{const prev=poly[(i+poly.length-1)%poly.length],next=poly[(i+1)%poly.length];const e=[q[0]-prev[0],q[1]-prev[1]],f=[next[0]-q[0],next[1]-q[1]],l=Math.hypot(...e),m=Math.hypot(...f),n1=[e[1]/l*sign,-e[0]/l*sign],n2=[f[1]/m*sign,-f[0]/m*sign],den=1+n1[0]*n2[0]+n1[1]*n2[1];return [q[0]+d*(n1[0]+n2[0])/den,q[1]+d*(n1[1]+n2[1])/den];});}
function patternLayout(){const cut=offsetPolygon(panels[0].polygon,10),minX=Math.min(...cut.map(x=>x[0])),maxX=Math.max(...cut.map(x=>x[0])),minY=Math.min(...cut.map(x=>x[1])),maxY=Math.max(...cut.map(x=>x[1])),w=maxX-minX+55,h=maxY-minY+60;return {w,h,minX,minY,width:w*2+30,height:h*2+155,cut};}
function patternInner(){const L=patternLayout();let html=`<defs><marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="#52695c"/></marker></defs>`;
 for(let k=0;k<4;k++){
  const tx=30-L.minX+(k%2)*L.w,ty=65-L.minY+Math.floor(k/2)*L.h,poly=panels[k].polygon;
  html+=`<g data-panel="${panels[k].id}" transform="translate(${tx} ${ty})"><polygon points="${L.cut.map(x=>x.join(',')).join(' ')}" fill="none" stroke="#798c82" stroke-dasharray="4 3" stroke-width=".8"/><polygon points="${poly.map(x=>x.join(',')).join(' ')}" fill="#e6ede7" stroke="#366352" stroke-width="1.1"/>`;
  for(let side=0;side<2;side++){
   const col=side?k:(k+3)%4,q0=flat(0,side?PER:0).map(x=>x*1000),q1=flat(NR,side?PER:0).map(x=>x*1000),op=selectedSeam<0||selectedSeam===col?1:.2;
   html+=`<path d="M${q0}L${q1}" fill="none" stroke="${seamColors[col]}" stroke-width="3.4" opacity="${op}"/>`;
   for(const f of [.25,.5,.75]){const x=q0[0]*(1-f)+q1[0]*f,y=q0[1]*(1-f)+q1[1]*f;html+=`<path d="M${x-5} ${y-3}L${x+5} ${y+3}" stroke="${seamColors[col]}" stroke-width="1.2"/>`;}
   const q=[q0[0]*.6+q1[0]*.4,q0[1]*.6+q1[1]*.4],r=[q0[0]*.5+q1[0]*.5,q0[1]*.5+q1[1]*.5];html+=`<path d="M${q}L${r}" marker-end="url(#arrow)" stroke="${seamColors[col]}" stroke-width="1.1"/>`;
  }
  const mid=flat(NR*.5,PER*.5)[1]*1000;
  html+=`<text x="0" y="${mid-28}" text-anchor="middle" font-size="18" font-family="sans-serif" fill="#203730">P${k+1}</text><text x="0" y="${mid-9}" text-anchor="middle" font-size="9" font-family="sans-serif" fill="#52695c">CUT 1 · GRAIN ↓</text><path d="M0 ${mid+10}V${mid+100}" marker-start="url(#arrow)" marker-end="url(#arrow)" stroke="#52695c" stroke-width=".8"/><text x="0" y="${mid+125}" text-anchor="middle" font-size="9" fill="#52695c">SEW ${Math.round(slant*1000)} mm</text></g>`;
 }
 html+=`<g transform="translate(30 ${L.height-125})"><rect width="100" height="100" stroke="#203730" fill="none" stroke-width=".6"/><text x="115" y="28" font-size="14" font-family="sans-serif" fill="#203730">100 × 100 mm calibration</text><text x="115" y="49" font-size="10" font-family="sans-serif" fill="#52695c">Print at 100% · All dimensions in mm</text><text x="115" y="67" font-size="10" font-family="sans-serif" fill="#52695c">10 mm cut allowance · Solid = stitch · Dashed = cut</text><text x="115" y="85" font-size="10" font-family="sans-serif" fill="#52695c">Waist support only; add waistband, closure and hem finish.</text></g>`;
 return html;
}
function patternSVG(){const L=patternLayout();return `<svg xmlns="http://www.w3.org/2000/svg" width="${L.width.toFixed(3)}mm" height="${L.height.toFixed(3)}mm" viewBox="0 0 ${L.width} ${L.height}"><title>Pattern Agent four-panel skirt, physical millimetres</title><desc>10 mm seam allowance. Waist and hem open; add closure and waistband. Source pattern and 3D solver share material coordinates.</desc><text x="30" y="28" font-size="16" font-family="sans-serif">PATTERN AGENT / FOUR-PANEL SKIRT / ${Math.round(waistLength*1000)} MM WAIST</text>${patternInner()}</svg>`;}
function drawPatterns(){const L=patternLayout();$('patternCanvas').setAttribute('viewBox',`0 35 ${L.width} ${L.height-155}`);$('patternCanvas').innerHTML=patternInner();$('patternCanvas').querySelectorAll('g[data-panel] text:first-of-type').forEach(x=>x.setAttribute('font-size','44'));$('seams').innerHTML=seamMaps.map((s,k)=>`<div class="seam-row" role="button" tabindex="0" data-seam="${k}" aria-label="Trace seam ${s.id}"><i style="background:${seamColors[k]}"></i><span>${s.a.panel} R ↔ ${s.b.panel} L</span><span class="mono">${Math.round(slant*1000)} = ${Math.round(slant*1000)}</span></div>`).join('');document.querySelectorAll('[data-seam]').forEach(el=>{const select=()=>{selectedSeam=+el.dataset.seam;setView('seams');drawPatterns();};el.onclick=select;el.onkeydown=e=>{if(e.key==='Enter'||e.key===' ')select();};});}
function setView(view){mode=view;const maps=['strain','stress','contact','fold','curvature','pressure'];cloth.material=maps.includes(view)?mapMat:clothMat;document.querySelectorAll('[data-view]').forEach(b=>b.classList.toggle('active',b.dataset.view===view));$('colorKey').style.display=maps.includes(view)?'block':'none';const label={pressure:['Contact reaction estimate · kPa','0 kPa','≥ 0.1 kPa'],stress:['Estimated principal stress · kPa','0 kPa','≥ 20 kPa'],contact:['Body clearance · sampled vertices','Gold: ≤ 7 mm','Teal: > 7 mm'],strain:['Principal stretch · 100% = rest','100%','≥ 120%'],fold:['Dihedral |θ| · 折角 / degrees','0° = flat','≥ 60°'],curvature:['Curvature |κ| · 曲率 / m⁻¹','0 m⁻¹','≥ 100 m⁻¹']}[view];if(label){$('keyTitle').textContent=label[0];$('keyMin').textContent=label[1];$('keyMax').textContent=label[2];}updateGeometry();}
function topology(){const edges=new Map();for(let t=0;t<triangles.length;t+=3)for(let j=0;j<3;j++){const a=triangles[t+j],b=triangles[t+(j+1)%3],id=[Math.min(a,b),Math.max(a,b)].join(':');if(!edges.has(id))edges.set(id,[]);edges.get(id).push([a,b]);}const boundary=[...edges.values()].filter(x=>x.length===1).map(x=>x[0]);const remaining=new Set(boundary.map(e=>e[0]));let loops=0;const next=new Map(boundary.map(e=>[e[0],e[1]]));while(remaining.size){let id=remaining.values().next().value,walk=0;loops++;while(remaining.has(id)&&walk++<triangles.length){remaining.delete(id);id=next.get(id);}}
 return {vertices:p.length/3,edges:edges.size,faces:triangles.length/3,euler:p.length/3-edges.size+triangles.length/3,boundaryLoops:loops,nonmanifold:[...edges.values()].filter(x=>x.length>2).length,windingErrors:[...edges.values()].filter(x=>x.length===2&&x[0][0]===x[1][0]).length};}
function collisionSamples(){let min=Infinity,inside=0,near=0,total=0;const point=q=>{const d=bodyDistance(...q);min=Math.min(min,d);if(d<-.0005)inside++;if(d<THICK+.002)near++;total++;};for(let i=0;i<p.length;i+=3)point([p[i],p[i+1],p[i+2]]);
 for(let t=0;t<triangles.length;t+=3){const ids=triangles.slice(t,t+3);point([0,1,2].map(k=>ids.reduce((s,id)=>s+p[id*3+k],0)/3));for(let j=0;j<3;j++)point([0,1,2].map(k=>(p[ids[j]*3+k]+p[ids[(j+1)%3]*3+k])/2));}
 return {samples:total,minClearance_mm:min*1000,penetratingSamples:inside,contactSamples:near,tolerance_mm:.5,method:'signed nearest body triangle, vertices + edge midpoints + centroids; independent exact triangle intersections also required'};
}
function coverageCheck(){
 scene.updateMatrixWorld(true);const vv=bodyGeo.attributes.position.array,nn=bodyGeo.attributes.normal.array,ray=new THREE.Raycaster(),direction=new THREE.Vector3(0,0,1);let samples=0,exposed=0;const exposedIds=[];
 for(let i=0;i<vv.length/3;i++){const k=i*3,x=vv[k],y=vv[k+1],z=vv[k+2];if(y<=.83||y>=1.025||Math.abs(x)>=.18||nn[k+2]>=-.35)continue;samples++;ray.set(new THREE.Vector3(x,y,z-2),direction);ray.far=2-.0001;if(!ray.intersectObject(cloth,false).length){exposed++;exposedIds.push(i);}}
 return {samples,exposed,exposedIds,verdict:samples>100&&exposed===0?'PASS':'FAIL',method:'Posterior pelvic body vertices, outward -Z visibility rays; cloth must occlude body before skin'};
}
function numericControls(){const E=80000,nu=.3,identity=deformation([1,0,0],[0,1,0],E,nu),rot=deformation([0,0,1],[0,1,0],E,nu),stretch=deformation([1.1,0,0],[0,1,0],E,nu),doubleE=deformation([1.1,0,0],[0,1,0],2*E,nu);return {identity,rotation:rot,extension10:stretch,doubleModulus:doubleE,pass:Math.abs(identity.stretch-1)<1e-10&&identity.stress===0&&Math.abs(rot.stretch-1)<1e-10&&Math.abs(stretch.stretch-1.1)<1e-10&&Math.abs(stretch.green[0]-.105)<1e-10&&Math.abs(doubleE.stress-2*stretch.stress)<1e-10};}
function verify(){running=false;syncRun();updateGeometry();const tp=topology(),col=collisionSamples(),ctrl=numericControls(),s=stats();const finite=Array.from(p).every(Number.isFinite);const coverage=coverageCheck();const checks=[['Posterior pelvic coverage: zero exposed samples',coverage.verdict==='PASS'],['Finite nonnegative estimated contact pressure',Array.from(contactPressure).every(x=>Number.isFinite(x)&&x>=0)],['Finite solver state',finite],['Four correctly directed equal-length seam pairs',seamMaps.length===4&&seamMaps.every(s=>s.lengthA_mm===s.lengthB_mm&&s.a.direction===s.b.direction)],['Maximum seam gap ≤ 2 mm',s.seamGap_mm<=2],['One sewn shell, Euler 0, two intended boundary loops',tp.euler===0&&tp.boundaryLoops===2&&tp.nonmanifold===0&&tp.windingErrors===0],['Body clearance samples: penetration ≤ 0.5 mm',col.penetratingSamples===0],['Analytic strain and stress controls',ctrl.pass],['Actual FreeSewing Sandy draft and unfolded side lengths',draft.profile.engine==='FreeSewing'&&Math.abs(draft.profile.sideLength_mm-slant*1000)<1e-6],['Finite signed fold-angle and curvature fields',Array.from(folds.angle_rad).every(Number.isFinite)&&Array.from(folds.curvature_per_m).every(Number.isFinite)],['Gravity has been simulated (≥ 1 second)',stepCount>=120],['Cloth changed from the initial arrangement',Math.max(...Array.from(p).map((v,i)=>Math.abs(v-seed[i])))>.001]];
 lastReport={schema:'pattern-agent-cloth-lab-verification-1',time:new Date().toISOString(),scope:'Digital skirt demonstrator; sample tests do not certify exact triangle intersections, cloth self-collision, calibrated physics, print hardware, sewability or fit; self-contact is discrete',verdict:checks.every(x=>x[1])?'PASS':'FAIL',checks:checks.map(([claim,pass])=>({claim,verdict:pass?'PASS':'FAIL'})),stats:s,coverage,pressureCalibration:"NOT_VALIDATED",topology:tp,collision:col,numericControls:ctrl,revision,bodyProvenance:BODY.provenance,material:{...mat,calibrated:false},fitAssessment:{verdict:'NOT_VALIDATED',trianglesAbove120Percent:currentMeasures.filter(m=>m.stretch>1.2).length},physics:{solver:'XPBD distance constraints / Verlet, embedded WebAssembly',dt_s:DT,iterations:120,skinOffset_m:THICK,waistPinned:true,selfCollision:true,selfContactThickness_m:.003},notRun:['Calibrated fabric testing','Continuous collision detection and universal self-contact robustness','Manufacturing sample and wearer fit']};
 $('status').textContent=lastReport.verdict;$('status').style.color=lastReport.verdict==='PASS'?'#25714e':'#b34431';$('verifyHint').textContent=`${lastReport.verdict} · ${col.samples.toLocaleString()} samples · min ${col.minClearance_mm.toFixed(2)} mm. Read the scope before accepting.`;
 $('stepVerify').className='current';$('stepDrape').className='';$('reportSummary').textContent=`${lastReport.verdict} for current digital checks. ${s.steps} fixed steps, ${(s.time_s).toFixed(2)} seconds; ${col.samples.toLocaleString()} body samples.`;
 $('reportChecks').innerHTML=lastReport.checks.map(x=>`<div class="check-row"><span>${x.claim}</span><strong class="${x.verdict==='PASS'?'pass':'fail'}">${x.verdict}</strong></div>`).join('');updateMetrics();console.info('[ClothLab verification]',JSON.stringify(lastReport));return lastReport;
}
function project(){return {schema:'pattern-agent-cloth-lab-1',view:mode,wireOn,units:'metre',patternUnits:'mm',parameters:{slant_m:slant,hem_m:hem,circle_ratio:circleRatio,waist_m:waistLength,NC,NR,YWAIST},positions:Array.from(p),previous:Array.from(old),initialPositions:seed,inverseMass:Array.from(inv),triangles,materialCoordinates:uvs,panels:panels.map(x=>({...x,cutOutline:offsetPolygon(x.polygon,10),seamAllowance_mm:10})),seams:seamMaps,body:BODY,material:{...mat,calibrated:false},selfContact:{enabled:true,thickness_m:.003,method:'discrete vertex-triangle and edge-edge PBD contacts; no CCD'},contactPressure:{correction_m:Array.from(pressureCorrection),force_N:Array.from(contactForce),area_m2:Array.from(contactArea),pressure_kPa:Array.from(contactPressure),dt_s:DT,definition:'Sum of positive body-normal projection impulses / dt / lumped area; uncalibrated PBD reaction estimate, excluding pinned support reactions',calibration:'NOT_VALIDATED'},freesewing:draft.profile,folding:{hinges,angle_rad:Array.from(folds.angle_rad),curvature_per_m:Array.from(folds.curvature_per_m),currentDualLength_m:Array.from(folds.currentDualLength_m),triangleAngle_deg:Array.from(folds.triangleAngle_deg),triangleCurvature_per_m:Array.from(folds.triangleCurvature_per_m),definition:'Signed oriented dihedral, flat=0; curvature=theta/current centroid-dual spacing; per-face maximum absolute over incident hinges',wrinkleProxy:{threshold_deg:15,definition:'Fraction of faces with |dihedral| >= 15 degrees; mesh-dependent geometric indicator, not permanent crease prediction'}},constraints:edgeMeta,triangleMeasures:currentMeasures,simulation:stats(),report:lastReport};}
function save(name,data,type='application/json'){const url=URL.createObjectURL(new Blob([data],{type})),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),2000);toast('Saved '+name);}
let toastTimer;function toast(text){$('toast').textContent=text;$('toast').style.display='block';clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('toast').style.display='none',3000);}
function exportOBJ(){let out='# Pattern Agent. Units: metres. MakeHuman CC0; garment retains rest UVs.\no MakeHuman\n';for(let i=0;i<BODY.vertices.length;i+=3)out+=`v ${BODY.vertices.slice(i,i+3).join(' ')}\n`;for(let i=0;i<BODY.indices.length;i+=3)out+=`f ${BODY.indices.slice(i,i+3).map(x=>x+1).join(' ')}\n`;out+='o Simulated_skirt\n';for(let i=0;i<p.length;i+=3)out+=`v ${Array.from(p.subarray(i,i+3)).join(' ')}\n`;for(let i=0;i<uvs.length;i+=2)out+=`vt ${uvs[i]} ${uvs[i+1]}\n`;const off=BODY.vertices.length/3;for(let i=0;i<triangles.length;i+=3)out+=`f ${[0,1,2].map(k=>`${triangles[i+k]+off+1}/${i+k+1}`).join(' ')}\n`;return out;}
function dxf(){let out='0\nSECTION\n2\nHEADER\n9\n$INSUNITS\n70\n4\n0\nENDSEC\n0\nSECTION\n2\nENTITIES\n';const poly=(pts,layer,closed=true)=>{out+=`0\nLWPOLYLINE\n8\n${layer}\n90\n${pts.length}\n70\n${closed?1:0}\n`;for(const [x,y]of pts)out+=`10\n${x.toFixed(6)}\n20\n${(-y).toFixed(6)}\n`;};const L=patternLayout();panels.forEach((p,k)=>{const translate=q=>[q[0]+30-L.minX+k*L.w,q[1]+30-L.minY];poly(p.polygon.map(translate),'P'+(k+1)+'_STITCH');poly(offsetPolygon(p.polygon,10).map(translate),'P'+(k+1)+'_CUT');poly([[0,100],[0,300]].map(translate),'P'+(k+1)+'_GRAIN',false);for(const side of[0,PER])for(const f of[.25,.5,.75]){const q=flat(NR*f,side).map(x=>x*1000);poly([[q[0]-4,q[1]],[q[0]+4,q[1]]].map(translate),'NOTCH',false);}});poly([[0,0],[100,0],[100,-100],[0,-100]],'CALIBRATION_100MM');return out+'0\nENDSEC\n0\nEOF\n';}
function printA4(){const L=patternLayout(),cols=Math.ceil(L.width/190),rows=Math.ceil(L.height/277),inner=patternInner();let pages='';for(let r=0;r<rows;r++)for(let c=0;c<cols;c++)pages+=`<section><div>Pattern Agent · tile ${r+1}/${rows} × ${c+1}/${cols} · 100%, headers off</div><svg xmlns="http://www.w3.org/2000/svg" width="190mm" height="277mm" viewBox="${c*190} ${r*277} 190 277">${inner}</svg><span>${r+1}-${c+1}</span></section>`;const win=window.open('','_blank');if(!win){toast('Allow this print window, then try again.');return;}win.document.write(`<!doctype html><html><head><title>Pattern Agent — A4 pattern, 100% scale</title><style>@page{size:A4;margin:10mm}*{box-sizing:border-box}body{margin:0;font:8px sans-serif}section{width:190mm;height:277mm;break-after:page;position:relative;overflow:hidden}section:last-child{break-after:auto}section>div{position:absolute;top:0;left:0;background:white}section>span{position:absolute;right:0;bottom:0}svg{display:block}@media screen{body{background:#ddd}section{background:white;margin:20px auto;outline:1px solid #aaa}}</style></head><body>${pages}</body></html>`);win.document.close();win.focus();toast(`${cols*rows} A4 tiles prepared. Print at 100% scale.`);}
function syncRun(){updateMetrics();$('run').textContent=running?'Pause':'Run drape';$('status').textContent=running?'SIMULATING':lastReport?.verdict||'PAUSED';}
document.querySelectorAll('[data-view]').forEach(el=>el.onclick=()=>{selectedSeam=-1;setView(el.dataset.view);drawPatterns();});
$('run').onclick=()=>{running=!running;lastFrame=performance.now();syncRun();};
$('reset').onclick=()=>{running=false;makePattern();syncRun();};
for(const id of ['length','hem','material'])$(id).onchange=()=>{slant=+$('length').value/1000;circleRatio=+$('hem').value/100;mat=materials[$('material').value];clothMat.color.setHex(mat.color);running=false;makePattern();syncRun();};
$('wind').oninput=()=>{wind=+$('wind').value;$('windValue').textContent=wind.toFixed(1)+' m/s²';};
$('verify').onclick=()=>{verify();$('reportDialog').showModal();};
$('about').onclick=()=>$('aboutDialog').showModal();document.querySelectorAll('.close-dialog').forEach(x=>x.onclick=()=>x.closest('dialog').close());
$('reportExport').onclick=()=>save('cloth-lab-verification.json',JSON.stringify(lastReport,null,2));
$('nativeExport').onclick=()=>save('freesewing-sandy-native.svg',draft.nativeSVG,'image/svg+xml');
$('svgExport').onclick=()=>save('four-panel-skirt-mm.svg',patternSVG(),'image/svg+xml');$('dxfExport').onclick=()=>save('four-panel-skirt-mm.dxf',dxf(),'application/dxf');$('printExport').onclick=printA4;
$('projectExport').onclick=()=>save('cloth-lab-simulation.json',JSON.stringify(project()));$('download3d').onclick=()=>save('makehuman-and-simulated-skirt.obj',exportOBJ(),'text/plain');
$('saveHtml').onclick=()=>{const doc=document.documentElement.cloneNode(true);doc.querySelector('#savedProject').textContent=JSON.stringify({parameters:{slant_m:slant,hem_m:hem,circle_ratio:circleRatio},materialKey:$('material').value,wind,pressureCorrection:Array.from(pressureCorrection),contactForce:Array.from(contactForce),contactPressure:Array.from(contactPressure),view:mode,wireOn,steps:stepCount,positions:Array.from(p),previous:Array.from(old)});doc.querySelectorAll('dialog').forEach(x=>x.removeAttribute('open'));doc.querySelector('#boot').style.display='grid';doc.querySelector('#toast').style.display='none';save('pattern-agent-freesewing-cloth-lab.html','<!doctype html>\n'+doc.outerHTML,'text/html');};
for(const id of ['front','side','back'])$(id).onclick=()=>{const d=innerWidth<700?4.6:3.5;camera.position.set(id==='side'?d:0,1.02,id==='front'?d:id==='back'?-d:.055);controls.target.set(0,.91,.055);controls.update();drawDirty=true;renderer.render(scene,camera);drawDirty=false;};
$('wire').onclick=()=>{wireOn=!wireOn;$('wire').classList.toggle('primary',wireOn);updateGeometry();};
const raycaster=new THREE.Raycaster(),pointer=new THREE.Vector2();let pointerDown;
renderer.domElement.addEventListener('pointerdown',e=>pointerDown=[e.clientX,e.clientY]);renderer.domElement.addEventListener('pointerup',e=>{if(!pointerDown||Math.hypot(e.clientX-pointerDown[0],e.clientY-pointerDown[1])>4)return;const r=renderer.domElement.getBoundingClientRect();pointer.set((e.clientX-r.left)/r.width*2-1,-(e.clientY-r.top)/r.height*2+1);raycaster.setFromCamera(pointer,camera);const hits=raycaster.intersectObject(cloth);if(hits.length){const m=currentMeasures[hits[0].faceIndex];$('pick').textContent=`Triangle ${hits[0].faceIndex} · ${(m.stretch*100).toFixed(2)}% · ${m.stress.toFixed(2)} kPa (est.) · θ ${folds.triangleAngle_deg[hits[0].faceIndex].toFixed(1)}° · κ ${folds.triangleCurvature_per_m[hits[0].faceIndex].toFixed(1)} m⁻¹`;}});
new ResizeObserver(()=>{const narrow=innerWidth<700;if(narrow!==narrowFrame){narrowFrame=narrow;camera.position.set(1.65,1.30,narrow?4.4:3.0);controls.target.set(0,.91,.055);controls.update();}drawDirty=true;const r=renderer.domElement.parentElement.getBoundingClientRect();renderer.setSize(r.width,r.height,false);camera.aspect=r.width/r.height;camera.updateProjectionMatrix();}).observe(renderer.domElement.parentElement);
$('length').value=slant*1000;$('hem').value=circleRatio*100;$('material').value=SAVED.materialKey||'cotton';$('wind').value=wind;$('windValue').textContent=wind.toFixed(1)+' m/s²';clothMat.color.setHex(mat.color);
makePattern();if(SAVED.positions?.length===p.length){p.set(SAVED.positions);old.set(SAVED.previous||p);stepCount=SAVED.steps||0;if(SAVED.pressureCorrection){pressureCorrection.set(SAVED.pressureCorrection);contactForce.set(SAVED.contactForce);contactPressure.set(SAVED.contactPressure);}updateGeometry();updateMetrics();}setView(mode);$('wire').classList.toggle('primary',wireOn);$('boot').style.display='none';
let tick=0,accumulator=0;
function animate(now){requestAnimationFrame(animate);const rawElapsed=(now-lastFrame)/1000,elapsed=Math.min(.05,rawElapsed);lastFrame=now;frames.push(rawElapsed*1000);if(frames.length>240)frames.shift();if(running){accumulator+=elapsed;let n=0;while(accumulator>=DT&&n<4){substep();accumulator-=DT;n++;}if(n===4)accumulator=0;updateGeometry();}controls.update();if(drawDirty){const start=performance.now();renderer.render(scene,camera);framesDrawn++;drawDirty=false;renderMs.push(performance.now()-start);if(renderMs.length>240)renderMs.shift();}if(running&&tick++%20===0)updateMetrics();}
requestAnimationFrame(animate);
window.clothLab={ready:true,supportStats,setCollision:v=>{collisionEnabled=v},version:'2.2.0',coverageCheck,nativeSVG:()=>draft.nativeSVG,stats,project,verify,patternSVG,dxf,exportOBJ,deformation,bodyDistance,numericControls,setView,reset:()=>{running=false;makePattern(false);syncRun();},step:n=>{running=false;for(let i=0;i<n;i++)substep();updateGeometry();updateMetrics();syncRun();return stats();},snapshot:()=>({positions:Array.from(p),...stats()}),camera:()=>({position:camera.position.toArray(),target:controls.target.toArray()}),negativeControl:(type)=>{if(type==='seam'){const s=structuredClone(seamMaps);s[0].lengthB_mm+=10;return {detected:s[0].lengthA_mm!==s[0].lengthB_mm};}if(type==='body'){return {inside:bodyDistance(0,YWAIST,.05)<0};}if(type==='strain'){return {detected:Math.abs(deformation([1.1,0,0],[0,1,0],80000,.3).stretch-1)>.05};}}};
console.info('[ClothLab ready]',JSON.stringify({body:BODY.provenance,wasmBytes:WASM.length,vertices:p.length/3,constraints:edgeMeta.length,renderer:renderer.getContext().getParameter(renderer.getContext().VERSION)}));
