import * as THREE from 'three';
import {OrbitControls} from './vendor/OrbitControls.js';
import {GLTFExporter} from './vendor/GLTFExporter.js';
import {clone as cloneRig} from './vendor/SkeletonUtils.js';
import {DEFAULT_DIMENSIONS,MODEL_VERSION,normalizeDimensions,fitDimensions,jointPosition} from './body-engine.js';

const $=id=>document.getElementById(id),RAD=Math.PI/180,CACHE='pattern-agent:human-studio:v1';
const MAIN_JOINTS=[['root','Whole body'],['spine04','Lower spine'],['spine02','Chest'],['neck01','Neck'],['head','Head'],['shoulder01.L','Left collar / shoulder'],['shoulder01.R','Right collar / shoulder'],['upperarm01.L','Left shoulder'],['upperarm01.R','Right shoulder'],['lowerarm01.L','Left elbow'],['lowerarm01.R','Right elbow'],['wrist.L','Left wrist'],['wrist.R','Right wrist'],['upperleg01.L','Left hip'],['upperleg01.R','Right hip'],['lowerleg01.L','Left knee'],['lowerleg01.R','Right knee'],['foot.L','Left ankle'],['foot.R','Right ankle']];
let data,provenance,fit,mesh,skeleton,helper,restQuaternions=[],bones=[],eyeGeometry,rendered=false;
let cachedMorphWeights=null;
let dimensions={...DEFAULT_DIMENSIONS},pose={},selectedJoint='upperarm01.L',activeMeasure='height',tab='body',timer;
const scene=new THREE.Scene();scene.background=new THREE.Color('#e4e9eb');
const host=$('scene'),camera=new THREE.OrthographicCamera(-150,150,115,-115,.1,2000);
camera.position.set(240,120,380);
const renderer=new THREE.WebGLRenderer({antialias:true,preserveDrawingBuffer:true});
renderer.setPixelRatio(Math.min(devicePixelRatio,2));renderer.setSize(host.clientWidth,host.clientHeight);
renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.15;
host.appendChild(renderer.domElement);
const orbit=new OrbitControls(camera,renderer.domElement);orbit.target.set(0,85,0);orbit.enableDamping=true;orbit.minZoom=.35;orbit.maxZoom=4;orbit.maxPolarAngle=Math.PI*.96;orbit.update();
scene.add(new THREE.HemisphereLight(0xffffff,0x8e999e,2.3));
for(const [x,y,z,intensity] of [[-160,250,210,3.8],[180,160,-130,2.8],[0,90,260,.7]]){const light=new THREE.DirectionalLight(0xffffff,intensity);light.position.set(x,y,z);scene.add(light);}
const floor=new THREE.Mesh(new THREE.PlaneGeometry(2000,2000),new THREE.MeshStandardMaterial({color:0xdce3e5,roughness:1}));floor.rotation.x=-Math.PI/2;floor.position.y=-.15;scene.add(floor);
const grid=new THREE.GridHelper(500,20,0xbcc9cd,0xd0dadd);grid.position.y=-.1;scene.add(grid);
const modelRoot=new THREE.Group();scene.add(modelRoot);
const markerGroup=new THREE.Group();scene.add(markerGroup);
const markerGeometry=new THREE.SphereGeometry(.9,10,8),markerMaterial=new THREE.MeshBasicMaterial({color:0x4d99b4,depthTest:false,transparent:true,opacity:.85}),selectedMaterial=new THREE.MeshBasicMaterial({color:0xd48a4d,depthTest:false});
const ruler=new THREE.Line(new THREE.BufferGeometry(),new THREE.LineBasicMaterial({color:0xaa7649,depthTest:false,transparent:true,opacity:.85}));ruler.renderOrder=3;scene.add(ruler);
let markers=[];

function toast(message){$('toast').textContent=message;$('toast').hidden=false;clearTimeout(toast.timeout);toast.timeout=setTimeout(()=>$('toast').hidden=true,4500);}
function normalizePose(value){const result={};if(!value||typeof value!=='object')return result;for(const bone of data.bones){const entry=value[bone.name];if(Array.isArray(entry)&&entry.length===3&&entry.every(v=>typeof v==='number'&&Number.isFinite(v))){result[bone.name]=entry.map(v=>Math.round(Math.max(-180,Math.min(180,v))*10)/10);}}return result;}
function validWeights(values){return Array.isArray(values)&&values.length===data.controls.length&&values.every(v=>typeof v==='number'&&Number.isFinite(v)&&Math.abs(v)<=2)?values:null;}
function saveCache(){try{localStorage.setItem(CACHE,JSON.stringify({version:MODEL_VERSION,asset:provenance?.human_sha256,dimensions,pose,morphWeights:fit?.weights}));}catch{}}
function loadCache(){try{const state=JSON.parse(localStorage.getItem(CACHE));if(state?.version===MODEL_VERSION&&state.asset===provenance.human_sha256){dimensions=normalizeDimensions(data,state.dimensions);pose=normalizePose(state.pose);cachedMorphWeights=validWeights(state.morphWeights);}}catch{dimensions={...DEFAULT_DIMENSIONS};pose={};}}
function setBusy(value){for(const id of ['export-state','export-png','export-obj','export-glb'])$(id).disabled=value;}

function coordinateFrame(head,tail){
  const y=tail.clone().sub(head).normalize();if(y.lengthSq()<.5)y.set(0,1,0);
  let x=new THREE.Vector3().crossVectors(y,new THREE.Vector3(0,0,1));if(x.lengthSq()<1e-8)x.crossVectors(y,new THREE.Vector3(0,1,0));x.normalize();
  const z=new THREE.Vector3().crossVectors(x,y).normalize();return new THREE.Quaternion().setFromRotationMatrix(new THREE.Matrix4().makeBasis(x,y,z));
}

function rebuildRig(){
  modelRoot.position.y=0;modelRoot.updateMatrixWorld(true);
  if(skeleton)skeleton.dispose();
  mesh.traverse(child=>{if(child!==mesh&&child.isMesh){if(child.geometry!==eyeGeometry)child.geometry.dispose();child.material.dispose();}});mesh.clear();
  const heads=data.bones.map(b=>new THREE.Vector3(...jointPosition(data,fit.positions,b.head)));
  const worldQ=data.bones.map((b,i)=>coordinateFrame(heads[i],new THREE.Vector3(...jointPosition(data,fit.positions,b.tail))));
  const indexByName=new Map(data.bones.map((b,i)=>[b.name,i]));
  bones=data.bones.map(b=>{const bone=new THREE.Bone();bone.name=b.name;return bone;});
  data.bones.forEach((spec,i)=>{
    const parent=indexByName.get(spec.parent);
    if(parent!==undefined){bones[parent].add(bones[i]);bones[i].position.copy(heads[i]).sub(heads[parent]).applyQuaternion(worldQ[parent].clone().invert());bones[i].quaternion.copy(worldQ[parent].clone().invert().multiply(worldQ[i]));}
    else{mesh.add(bones[i]);bones[i].position.copy(heads[i]);bones[i].quaternion.copy(worldQ[i]);}
  });
  restQuaternions=bones.map(b=>b.quaternion.clone());
  modelRoot.updateMatrixWorld(true);skeleton=new THREE.Skeleton(bones);mesh.bind(skeleton);mesh.normalizeSkinWeights();
  if(helper){scene.remove(helper);helper.dispose();}
  helper=new THREE.SkeletonHelper(mesh);helper.material.depthTest=false;helper.material.transparent=true;helper.material.opacity=.55;helper.renderOrder=2;scene.add(helper);
  if(!eyeGeometry)eyeGeometry=new THREE.SphereGeometry(.87,20,12);
  for(const side of ['L','R']){
    const bone=bones[indexByName.get('eye.'+side)];
    const eye=new THREE.Mesh(eyeGeometry,new THREE.MeshStandardMaterial({color:0xd4d3c8,roughness:.65}));bone.add(eye);
    const iris=new THREE.Mesh(new THREE.SphereGeometry(.33,16,10),new THREE.MeshStandardMaterial({color:0x59635f,roughness:.6}));iris.position.y=.82;iris.scale.y=.19;bone.add(iris);
  }
  markerGroup.clear();markers=[];
  for(const [name]of MAIN_JOINTS){const marker=new THREE.Mesh(markerGeometry,markerMaterial);marker.userData.boneName=name;marker.renderOrder=4;markerGroup.add(marker);markers.push(marker);}
  applyPose();
}

function posedVertex(index,target=new THREE.Vector3()){
  target.fromBufferAttribute(mesh.geometry.attributes.position,index);mesh.applyBoneTransform(index,target);return target.applyMatrix4(mesh.matrixWorld);
}
function posedBounds(){const box=new THREE.Box3(),point=new THREE.Vector3();for(const index of data.bodyVertexIds)box.expandByPoint(posedVertex(index,point));return box;}
function viewBounds(){camera.updateMatrixWorld(true);let left=Infinity,top=Infinity,right=-Infinity,bottom=-Infinity;const point=new THREE.Vector3();for(const index of data.bodyVertexIds){posedVertex(index,point).project(camera);const x=(point.x+1)*host.clientWidth/2,y=(1-point.y)*host.clientHeight/2;left=Math.min(left,x);right=Math.max(right,x);top=Math.min(top,y);bottom=Math.max(bottom,y);}return{left,top,right,bottom,width:host.clientWidth,height:host.clientHeight};}
function applyPose(){
  if(!mesh)return;
  modelRoot.position.y=0;
  bones.forEach((bone,i)=>{const angles=pose[bone.name]||[0,0,0];bone.quaternion.copy(restQuaternions[i]).multiply(new THREE.Quaternion().setFromEuler(new THREE.Euler(...angles.map(v=>v*RAD),'XYZ')));});
  modelRoot.updateMatrixWorld(true);skeleton.update();
  const box=posedBounds();modelRoot.position.y=-box.min.y;modelRoot.updateMatrixWorld(true);skeleton.update();
  const map=new Map(bones.map(b=>[b.name,b]));
  for(const marker of markers){map.get(marker.userData.boneName).getWorldPosition(marker.position);marker.material=marker.userData.boneName===selectedJoint?selectedMaterial:markerMaterial;}
  helper.visible=$('show-rig').checked;markerGroup.visible=$('show-rig').checked;
  updateRuler();saveCache();
}

function updateRuler(){
  if(!mesh)return;
  let points=[];
  if(activeMeasure==='height'){const x=-43;points=[new THREE.Vector3(x,0,0),new THREE.Vector3(x,fit.measurements.height,0)];}
  else{const control=data.controls.find(c=>c.key===activeMeasure);points=control.path.map(index=>posedVertex(index));}
  ruler.geometry.dispose();ruler.geometry=new THREE.BufferGeometry().setFromPoints(points);ruler.visible=$('show-ruler').checked;
  const control=data.controls.find(c=>c.key===activeMeasure);$('ruler-label').textContent=control.label+' · '+fit.measurements[activeMeasure].toFixed(1)+' cm · neutral-pose measurement';
}

function updateBody(){
  setBusy(true);$('status').textContent='Updating shape…';
  dimensions=normalizeDimensions(data,dimensions);fit=fitDimensions(data,dimensions,fit?.weights||cachedMorphWeights);
  if(!mesh){
    const geometry=new THREE.BufferGeometry();geometry.setAttribute('position',new THREE.Float32BufferAttribute(fit.positions,3));geometry.setIndex(data.indices);
    geometry.setAttribute('skinIndex',new THREE.Uint16BufferAttribute(data.skinIndices,4));geometry.setAttribute('skinWeight',new THREE.Float32BufferAttribute(data.skinWeights,4));
    geometry.computeVertexNormals();mesh=new THREE.SkinnedMesh(geometry,new THREE.MeshStandardMaterial({color:0xb6a99c,roughness:.72,metalness:.02}));mesh.name='MakeHuman body · centimetres';mesh.frustumCulled=false;modelRoot.add(mesh);
  }else{mesh.geometry.attributes.position.array.set(fit.positions);mesh.geometry.attributes.position.needsUpdate=true;mesh.geometry.computeVertexNormals();mesh.geometry.computeBoundingSphere();}
  rebuildRig();syncDimensionControls();
  $('status').textContent=fit.maxError<=.15?'Dimensions matched':'Closest supported shape';
  $('fit-result').textContent=fit.maxError<=.15?'Mesh measurements match the entered dimensions (within 0.2 cm).':'Largest target difference: '+fit.maxError.toFixed(1)+' cm. Measured values are shown beside affected controls.';
  if(rendered)frameModel();
  setBusy(false);
}
function requestBody(){setBusy(true);clearTimeout(timer);timer=setTimeout(updateBody,65);}

function dimensionControl(control){
  const wrapper=document.createElement('div');wrapper.className='dimension';wrapper.dataset.dimension=control.key;
  const head=document.createElement('div');head.className='dimension-head';
  const label=document.createElement('label');label.htmlFor='size-'+control.key;label.textContent=control.label;
  const numbers=document.createElement('div');numbers.className='number-wrap';
  const input=document.createElement('input');input.id='size-'+control.key;input.type='number';input.min=control.min;input.max=control.max;input.step=.1;input.setAttribute('aria-label',control.label+' in centimetres');
  const unit=document.createElement('span');unit.textContent='cm';numbers.append(input,unit);head.append(label,numbers);
  const range=document.createElement('input');range.type='range';range.id='range-'+control.key;range.min=control.min;range.max=control.max;range.step=.1;range.setAttribute('aria-label',control.label+' slider');
  const measured=document.createElement('p');measured.className='measured';measured.id='measured-'+control.key;
  input.addEventListener('change',()=>{const value=input.valueAsNumber;if(!Number.isFinite(value)){input.value=dimensions[control.key];return;}dimensions[control.key]=value;activeMeasure=control.key;requestBody();});
  range.addEventListener('input',()=>{dimensions[control.key]=Number(range.value);input.value=range.value;activeMeasure=control.key;requestBody();});
  for(const element of[input,range])element.addEventListener('focus',()=>{activeMeasure=control.key;updateRuler();});
  wrapper.append(head,range,measured);return wrapper;
}
function syncDimensionControls(){for(const control of data.controls){const value=dimensions[control.key];$('size-'+control.key).value=value;$('range-'+control.key).value=value;$('measured-'+control.key).textContent=Math.abs(fit.measurements[control.key]-value)>.15?'Measured '+fit.measurements[control.key].toFixed(1)+' cm':'';}}

function makeJointMenu(){
  const known=new Set(MAIN_JOINTS.map(row=>row[0]));$('joint-select').replaceChildren();
  for(const[name,label]of MAIN_JOINTS){const option=document.createElement('option');option.value=name;option.textContent=label;$('joint-select').append(option);}
  if($('full-rig').checked){const group=document.createElement('optgroup');group.label='Full anatomical rig';for(const b of data.bones)if(!known.has(b.name)){const option=document.createElement('option');option.value=b.name;option.textContent=b.name;group.append(option);}$('joint-select').append(group);}
  if(!Array.from($('joint-select').options).some(o=>o.value===selectedJoint))selectedJoint='upperarm01.L';$('joint-select').value=selectedJoint;syncPoseControls();
}
function syncPoseControls(){const value=pose[selectedJoint]||[0,0,0];for(let i=0;i<3;i++){$('angle-'+i).value=value[i];$('angle-range-'+i).value=value[i];}for(const marker of markers)marker.material=marker.userData.boneName===selectedJoint?selectedMaterial:markerMaterial;}
function setJointAngle(axis,value){
  value=Math.round(Math.max(-180,Math.min(180,value))*10)/10;if(!Number.isFinite(value))return;
  const entry=[...(pose[selectedJoint]||[0,0,0])];entry[axis]=value;pose[selectedJoint]=entry;
  if($('mirror-pose').checked&&/\.[LR]$/.test(selectedJoint)){const other=selectedJoint.slice(0,-1)+(selectedJoint.endsWith('L')?'R':'L');pose[other]=[entry[0],-entry[1],-entry[2]];}
  document.querySelectorAll('[data-preset]').forEach(b=>b.classList.remove('selected'));applyPose();syncPoseControls();
}
function setTab(name){tab=name;$('body-panel').hidden=name!=='body';$('pose-panel').hidden=name!=='pose';for(const key of['body','pose']){$('tab-'+key).classList.toggle('active',name===key);$('tab-'+key).setAttribute('aria-selected',String(name===key));}if(name==='pose'){$('show-rig').checked=true;applyPose();}}

function preset(name){
  pose={};
  applyPose();
  if(name==='tpose'){for(const side of['L','R']){const i=data.bones.findIndex(b=>b.name==='upperarm01.'+side);const world=bones[i].getWorldQuaternion(new THREE.Quaternion());const target=new THREE.Vector3(side==='L'?1:-1,0,0).applyQuaternion(world.invert());pose['upperarm01.'+side]=[0,0,Math.atan2(-target.x,target.y)/RAD];}}
  if(name==='walk'){pose={'upperleg01.L':[27,0,0],'upperleg01.R':[-24,0,0],'lowerleg01.L':[-14,0,0],'lowerleg01.R':[-35,0,0],'upperarm01.L':[-22,0,5],'upperarm01.R':[25,0,-5],'lowerarm01.L':[18,0,0],'lowerarm01.R':[22,0,0]};}
  if(name==='sit'){pose={'upperleg01.L':[90,0,3],'upperleg01.R':[90,0,-3],'lowerleg01.L':[-90,0,0],'lowerleg01.R':[-90,0,0],'lowerarm01.L':[65,0,0],'lowerarm01.R':[65,0,0]};}
  if(name==='reach'){pose={'upperarm01.L':[0,0,150],'upperarm01.R':[0,0,-150],'lowerarm01.L':[12,0,0],'lowerarm01.R':[12,0,0]};}
  pose=normalizePose(pose);document.querySelectorAll('[data-preset]').forEach(b=>b.classList.toggle('selected',b.dataset.preset===name));applyPose();syncPoseControls();frameModel();
}
function frameModel(){
  if(!mesh)return;const box=posedBounds(),size=box.getSize(new THREE.Vector3()),center=box.getCenter(new THREE.Vector3());
  const offset=camera.position.clone().sub(orbit.target).normalize().multiplyScalar(420);orbit.target.copy(center);camera.position.copy(center).add(offset);
  const aspect=host.clientWidth/host.clientHeight,vertical=Math.max(size.y+45,(Math.max(size.x,size.z)+40)/aspect,170);camera.top=vertical/2;camera.bottom=-vertical/2;camera.left=-vertical*aspect/2;camera.right=vertical*aspect/2;camera.zoom=1;camera.updateProjectionMatrix();orbit.update();
}
function view(name){const center=orbit.target.clone(),offset={front:[0,0,420],side:[420,0,0],back:[0,0,-420],three:[250,55,360]}[name];camera.position.copy(center).add(new THREE.Vector3(...offset));camera.up.set(0,1,0);orbit.update();}

function exportSnapshot(){
  return {version:MODEL_VERSION,asset:provenance.human_sha256,units:'cm',dimensions:{...dimensions},measuredNeutral:{...fit.measurements},maximumTargetErrorCm:fit.maxError,morphWeights:[...fit.weights],poseDegrees:structuredClone(pose),measurementDefinition:data.measurementDefinition,source:'MakeHuman CC0 adult female mesh and anatomical rig',limitations:['Dimensions describe this model, not a recovered person.','Neutral-pose tape measurements; skeletal skinning is not physical tissue simulation.']};
}
function download(name,content,type){const url=URL.createObjectURL(new Blob([content],{type}));const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),2000);}
function exportObj(){const ids=data.bodyVertexIds,map=new Map(ids.map((id,i)=>[id,i+1]));const lines=['# Human Studio: posed surface, centimetres','# CC0 MakeHuman source; actual skinned vertices','o Human'];for(const id of ids){const p=posedVertex(id);lines.push('v '+p.toArray().map(v=>v.toFixed(6)).join(' '));}for(let i=0;i<data.indices.length;i+=3)lines.push('f '+[0,1,2].map(j=>map.get(data.indices[i+j])).join(' '));download('human-posed-cm.obj',lines.join('\n'),'text/plain');}
async function exportGlb(){
  setBusy(true);
  try{const object=cloneRig(modelRoot);object.scale.setScalar(.01);object.position.multiplyScalar(.01);object.name='Human Studio · metres';object.userData={bodyDimensionsCm:dimensions,measuredNeutralCm:fit.measurements,poseDegrees:pose,sourceLicense:'CC0-1.0',exportUnits:'metres'};object.updateMatrixWorld(true);
    const result=await new GLTFExporter().parseAsync(object,{binary:true,onlyVisible:true});download('human-rigged.glb',result,'model/gltf-binary');toast('Exported rigged GLB in metres. Body dimensions are stored in cm.');
  }catch(error){toast('GLB export failed: '+error.message);}finally{setBusy(false);}
}

async function init(){
  try{
    [data,provenance]=await Promise.all([fetch('./assets/human.json').then(r=>{if(!r.ok)throw Error('Mesh download failed');return r.json();}),fetch('./assets/provenance.json').then(r=>r.json())]);
    for(const control of data.controls)$(['height','bust','waist','hips','shoulders'].includes(control.key)?'primary-dimensions':'secondary-dimensions').append(dimensionControl(control));
    for(let axis=0;axis<3;axis++){
      const row=document.createElement('div');row.className='dimension';row.innerHTML='<div class="dimension-head"><label for="angle-'+axis+'">'+['X · bend','Y · twist','Z · side bend'][axis]+'</label><div class="number-wrap"><input id="angle-'+axis+'" type="number" min="-180" max="180" step="0.1"><span>°</span></div></div><input id="angle-range-'+axis+'" type="range" min="-180" max="180" step="0.1" aria-label="Joint '+['X','Y','Z'][axis]+' angle">';$('joint-rotations').append(row);
      $('angle-'+axis).addEventListener('change',e=>setJointAngle(axis,Number(e.target.value)));$('angle-range-'+axis).addEventListener('input',e=>setJointAngle(axis,Number(e.target.value)));
    }
    loadCache();makeJointMenu();updateBody();frameModel();view('three');
    $('tab-body').onclick=()=>setTab('body');$('tab-pose').onclick=()=>setTab('pose');$('joint-select').onchange=e=>{selectedJoint=e.target.value;syncPoseControls();};$('full-rig').onchange=makeJointMenu;
    $('show-rig').onchange=applyPose;$('show-ruler').onchange=updateRuler;
    $('reset-body').onclick=()=>{dimensions={...DEFAULT_DIMENSIONS};fit=null;updateBody();toast('Body dimensions reset. Current pose preserved.');};
    $('reset-pose').onclick=()=>preset('neutral');$('reset-joint').onclick=()=>{pose[selectedJoint]=[0,0,0];if($('mirror-pose').checked&&/\.[LR]$/.test(selectedJoint))pose[selectedJoint.slice(0,-1)+(selectedJoint.endsWith('L')?'R':'L')]=[0,0,0];applyPose();syncPoseControls();};
    for(const b of document.querySelectorAll('[data-view]'))b.onclick=()=>view(b.dataset.view);
    for(const b of document.querySelectorAll('[data-preset]'))b.onclick=()=>preset(b.dataset.preset);$('frame-model').onclick=frameModel;
    $('export-state').onclick=()=>download('human-model.json',JSON.stringify(exportSnapshot(),null,2),'application/json');$('export-obj').onclick=exportObj;$('export-glb').onclick=exportGlb;
    $('export-png').onclick=()=>{const ratio=renderer.getPixelRatio();try{renderer.setPixelRatio(ratio*2);renderer.render(scene,camera);const url=renderer.domElement.toDataURL('image/png'),a=document.createElement('a');a.href=url;a.download='human-view-2x.png';a.click();}finally{renderer.setPixelRatio(ratio);renderer.render(scene,camera);}};
    $('import-state').onclick=()=>$('state-file').click();$('state-file').onchange=async e=>{try{const saved=JSON.parse(await e.target.files[0].text());if(saved.version!==MODEL_VERSION||saved.asset!==provenance.human_sha256)throw Error('This file belongs to a different model version.');dimensions=normalizeDimensions(data,saved.dimensions);pose=normalizePose(saved.poseDegrees);cachedMorphWeights=validWeights(saved.morphWeights);fit=null;updateBody();syncPoseControls();frameModel();toast('Dimensions and joint pose restored.');}catch(error){toast('Could not import: '+error.message);}e.target.value='';};
    const raycaster=new THREE.Raycaster();let down;
    renderer.domElement.addEventListener('pointerdown',e=>down=[e.clientX,e.clientY]);renderer.domElement.addEventListener('pointerup',e=>{if(tab!=='pose'||!down||Math.hypot(e.clientX-down[0],e.clientY-down[1])>5)return;const rect=renderer.domElement.getBoundingClientRect();raycaster.setFromCamera(new THREE.Vector2((e.clientX-rect.left)/rect.width*2-1,-(e.clientY-rect.top)/rect.height*2+1),camera);const hit=raycaster.intersectObjects(markers)[0];if(hit){selectedJoint=hit.object.userData.boneName;$('joint-select').value=selectedJoint;syncPoseControls();}});
    window.humanStudio={getSnapshot:exportSnapshot,getViewBounds:viewBounds,getGeometry:()=>({unit:'cm',rest:Array.from(mesh.geometry.attributes.position.array),posed:data.bodyVertexIds.map(i=>posedVertex(i).toArray()),bodyVertexIds:data.bodyVertexIds,indices:data.indices,bones:bones.map(b=>({name:b.name,position:b.getWorldPosition(new THREE.Vector3()).toArray()}))}),getAsset:()=>data,setDimensions:values=>{dimensions=normalizeDimensions(data,{...dimensions,...values});updateBody();},setPose:values=>{pose=normalizePose(values);applyPose();syncPoseControls();},preset,ready:true};
    rendered=true;
  }catch(error){$('status').textContent='Could not load model';toast(error.message);console.error(error);}
}
new ResizeObserver(()=>{const width=host.clientWidth,height=host.clientHeight;if(!width||!height)return;const vertical=camera.top-camera.bottom;camera.left=-vertical*width/height/2;camera.right=vertical*width/height/2;camera.updateProjectionMatrix();renderer.setSize(width,height);if(rendered)frameModel();}).observe(host);
function animate(){requestAnimationFrame(animate);orbit.update();renderer.render(scene,camera);}animate();init();
