import * as THREE from 'three';
import {OrbitControls} from '../dist/vendor/OrbitControls.js';
import {SceneViewport} from './scene-viewport.mjs';
import {inspectSleeveCreases} from './crease-diagnostics.mjs';
import {makeCreaseOverlay} from './crease-overlay.mjs';
import {DiagnosticLog} from './diagnostic-log.mjs';
const $=s=>document.querySelector(s),log=new DiagnosticLog('sleeve-debugger'),views={},sourceHashes={};
let manifest,referenceBody,linked=false,side='sleeve-right';
const expectedSchema='garment-body-wear-audit-input/2';
function save(name,data){const href=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=href;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(href),1000);}
async function sha256(bytes){const hash=await crypto.subtle.digest('SHA-256',bytes);return Array.from(new Uint8Array(hash)).map(x=>x.toString(16).padStart(2,'0')).join('');}
async function load(file,expected){const r=await fetch('./diagnostics/'+file);if(!r.ok)throw Error('证据文件不可读：'+file);const bytes=await r.arrayBuffer(),hash=await sha256(bytes);if(expected&&hash!==expected)throw Error('证据摘要不匹配：'+file);sourceHashes[file]=hash;log.record('source-readback',{file,sha256:hash,bytes:bytes.byteLength});return JSON.parse(new TextDecoder().decode(bytes));}
function release(group){const geometries=new Set(),materials=new Set();group.traverse(o=>{if(o.geometry)geometries.add(o.geometry);for(const m of(Array.isArray(o.material)?o.material:[o.material]))if(m)materials.add(m);});geometries.forEach(g=>g.dispose());materials.forEach(m=>m.dispose());}
function addMesh(group,data,color,index=-1){const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(data.vertices.flat(),3));g.setIndex(data.triangles.flatMap(t=>index===1||index===3?t.slice().reverse():t));g.computeVertexNormals();const material=new THREE.MeshStandardMaterial({color,roughness:.92,side:THREE.DoubleSide});const mesh=new THREE.Mesh(g,material);mesh.userData.partId=data.partId;group.add(mesh);return mesh;}
function refreshEventList(){const scans=log.entries.filter(e=>e.stage==='geometry-fold-scan');$('#performance-summary').textContent=scans.map(e=>`${e.detail.case==='before'?'修复前':e.detail.case==='after'?'右侧网格':e.detail.case}：扫描 ${e.durationMs.toFixed(2)} ms`).join('；')+'。耗时是本次实测，不是材料参数。';$('#event-list').replaceChildren(...log.entries.slice(-12).map(e=>{const li=document.createElement('li');li.textContent=`#${e.sequence} ${e.stage} · ${e.durationMs.toFixed(2)} ms`;return li;}));}
function updateAppearance(){for(const v of Object.values(views)){v.overlay.group.visible=$('#diagnostic-colors').checked;v.overlay.group.traverse(o=>{if(o.name==='crease-faces')o.material.wireframe=$('#show-grid').checked;});v.cloth.forEach(m=>m.material.wireframe=$('#show-grid').checked&&!$('#diagnostic-colors').checked);v.overlay.select($('#show-normals').checked?v.selected:null);v.recordFrame=true;v.viewport.render();}}
function selectEdge(id,edge,focus=false){const v=views[id];v.selected=edge;v.overlay.select($('#show-normals').checked?edge:null);$('#'+id+'-selection').textContent=`${edge.id} · ${edge.angleDeg.toFixed(3)}° · 距袖底缝 ${edge.underarmDistanceMm.toFixed(2)} mm · 相邻面 ${edge.faces.join(' / ')}`;if(focus){const target=new THREE.Vector3(...edge.midpoint),direction=new THREE.Vector3(Math.sign(target.x)*.8,.4,1).normalize();for(const view of Object.values(views)){view.viewport.setPose(target.clone().addScaledVector(direction,.78),target);view.recordFrame=true;view.viewport.render();}}log.record('select-edge',{case:id,edgeId:edge.id,angleDeg:edge.angleDeg,faces:edge.faces,midpoint:edge.midpoint});if(id==='before')matchMaterialEdge(edge);$('#edge-list').querySelectorAll('button').forEach(b=>b.classList.toggle('active',b.dataset.edge===edge.id));refreshEventList();}
function sidePeak(v){return v.diagnostic.parts.find(p=>p.partId===side).edges.filter(e=>!e.excluded).reduce((a,b)=>!a||b.angleDeg>a.angleDeg?b:a,null);}
function ridgeEdge(){const p=views.before.diagnostic.parts.find(p=>p.partId===side),cluster=p.clusters.reduce((a,b)=>!a||b.lengthMm>a.lengthMm?b:a,null);if(!cluster)return sidePeak(views.before);const ids=new Set(cluster.edgeIds);return p.edges.filter(e=>ids.has(e.id)).reduce((a,b)=>!a||Math.abs(b.midpoint[0])>Math.abs(a.midpoint[0])?b:a,null);}
function matchMaterialEdge(edge){
 const v=views.after;if(v.data.provenance?.kind!=='fixed-reference-mesh')return;
 const dist=(a,b)=>Math.hypot(a.x-b.x,a.y-b.y),error=e=>Math.min(Math.max(dist(edge.endpointsUv[0],e.endpointsUv[0]),dist(edge.endpointsUv[1],e.endpointsUv[1])),Math.max(dist(edge.endpointsUv[0],e.endpointsUv[1]),dist(edge.endpointsUv[1],e.endpointsUv[0])));
 const candidates=v.diagnostic.parts.find(p=>p.partId===edge.id.split(':')[0]).edges.filter(e=>!e.excluded),match=candidates.reduce((a,b)=>!a||error(b)<error(a)?b:a,null);
 if(!match||error(match)>.01){$('#after-selection').textContent='此边没有在0.01 mm内匹配的原纸样材料边；保留当前测点，不作同点比较。';return;}
 v.selected=match;v.overlay.select($('#show-normals').checked?match:null);$('#after-selection').textContent=`同一材料边 ${match.id} · ${match.angleDeg.toFixed(3)}° · UV端点误差 ${error(match).toFixed(6)} mm`;
 log.record('material-edge-correspondence',{beforeEdge:edge.id,afterEdge:match.id,beforeDeg:edge.angleDeg,afterDeg:match.angleDeg,uvEndpointMaxErrorMm:error(match),toleranceMm:.01});
}
function focusRidge(focus=true){selectEdge('before',ridgeEdge(),focus);}
function renderList(){const ridge=ridgeEdge(),edges=[ridge,...views.before.diagnostic.parts.find(p=>p.partId===side).edges.filter(e=>!e.excluded&&e.id!==ridge.id).sort((a,b)=>b.angleDeg-a.angleDeg).slice(0,15)];$('#edge-list').replaceChildren(...edges.map(e=>{const b=document.createElement('button');b.type='button';b.dataset.edge=e.id;b.textContent=(e.id===ridge.id?'尖棱 ':'')+e.id+' ';const n=document.createElement('span');n.textContent=e.angleDeg.toFixed(1)+'°';b.appendChild(n);b.onclick=()=>selectEdge('before',e,true);return b;}));}
function buildCase(id,data,body){
 const v=views[id];if(data.schema!==expectedSchema)throw Error('需要声明三维米／纸样毫米的工作室网格格式');
 // Validate and measure before replacing any currently displayed geometry.
 const diagnostic=log.measure('geometry-fold-scan',()=>inspectSleeveCreases(data.garment),r=>({case:id,sourceKind:data.provenance?.kind||'user-import',status:r.status,sharpCount:r.sharpCount,maxDeg:r.peak.angleDeg,invalidCount:r.invalidCount,geometrySourceHashes:{...sourceHashes}}));
 v.overlay?.dispose();release(v.group);v.group.clear();v.data=data;v.diagnostic=diagnostic;v.cloth=[];
 if(body?.vertices?.length)addMesh(v.group,body,0xb6b2a6);
 data.garment.forEach((p,i)=>v.cloth.push(addMesh(v.group,p,0xb9c0c7,i)));
 v.overlay=makeCreaseOverlay(data.garment,diagnostic);v.group.add(v.overlay.group);
 const max=diagnostic.peak.angleDeg,excluded=diagnostic.parts.reduce((s,p)=>s+p.excludedCount,0);
 $('#'+id+'-verdict').textContent=diagnostic.status;$('#'+id+'-verdict').dataset.status=diagnostic.status;
 $('#'+id+'-metrics').innerHTML=`最大 <strong>${max.toFixed(2)}°</strong> · 超过45° <b>${diagnostic.sharpCount}</b> 条<br>纳入统计 ${diagnostic.parts.reduce((s,p)=>s+p.stats.count,0)} 条 · 排除 ${excluded} 条 · 无效 ${diagnostic.invalidCount}`;
 v.selected=sidePeak(v);v.overlay.select(v.selected);$('#'+id+'-selection').textContent=`${v.selected.id} · ${v.selected.angleDeg.toFixed(3)}° · 相邻面 ${v.selected.faces.join(' / ')}`;
 v.recordFrame=true;
}
function makeView(id){const element=$('#'+id+'-scene'),renderer=new THREE.WebGLRenderer({antialias:true,alpha:false});renderer.setClearColor(0xe9edf0);renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.16;element.appendChild(renderer.domElement);renderer.domElement.tabIndex=0;renderer.domElement.setAttribute('aria-label',id==='before'?'修复前真实袖子网格，可拖动旋转':'修复后真实袖子网格，可拖动旋转');
 const scene=new THREE.Scene(),group=new THREE.Group();scene.add(group);scene.add(new THREE.HemisphereLight(0xffffff,0x8e9e8a,2.4));for(const[pos,color,intensity]of[[[-2,3,3],0xfff8ed,3.5],[[2,1,-2],0xe3ecf4,2]]){const light=new THREE.DirectionalLight(color,intensity);light.position.set(...pos);scene.add(light);}
 const camera=new THREE.PerspectiveCamera(33,1,.01,30),controls=new OrbitControls(camera,renderer.domElement);controls.enableDamping=true;controls.minDistance=.2;
 const v=views[id]={id,element,renderer,scene,group,camera,controls,recordFrame:true};
 v.viewport=new SceneViewport({renderer,camera,controls,element,bounds:()=>new THREE.Box3(new THREE.Vector3(.0,-.08,-.23),new THREE.Vector3(.49,.50,.18)),changed:()=>{},releaseResources:()=>release(scene),resetView:()=>setCamera('close'),prepare:(r,c)=>{const start=performance.now();r.render(scene,c);if(v.recordFrame){log.record('render-frame',{case:id,drawCalls:r.info.render.calls,triangles:r.info.render.triangles,buffer:[r.domElement.width,r.domElement.height]},performance.now()-start,start);v.recordFrame=false;}}});
 new ResizeObserver(()=>v.viewport.resize()).observe(element);
 controls.addEventListener('change',()=>{if(linked)return;linked=true;for(const other of Object.values(views))if(other!==v){other.viewport.setPose(camera.position.clone(),controls.target.clone());other.recordFrame=true;}linked=false;});
 controls.addEventListener('end',()=>{log.record('camera-interaction',{case:id,camera:camera.position.toArray(),target:controls.target.toArray()});v.recordFrame=true;refreshEventList();});return v;
}
function setCamera(name){const target=new THREE.Vector3(side==='sleeve-right'?.22:-.22,.20,-.045);const direction=name==='front'?new THREE.Vector3(0,0,1):name==='side'?new THREE.Vector3(Math.sign(target.x),.15,0):name==='back'?new THREE.Vector3(0,0,-1):new THREE.Vector3(Math.sign(target.x)*.8,.35,1);linked=true;for(const v of Object.values(views)){v.viewport.resize();v.viewport.setPose(target.clone().addScaledVector(direction.normalize(),name==='close'?.98:1.15),target);v.recordFrame=true;v.viewport.render();}linked=false;log.record('camera-preset',{name,side});refreshEventList();}
function report(){return{schema:'sleeve-debugger-evidence/1',manifest,sourceHashes,metric:'adjacent-face-dihedral-degrees',limits:views.before.diagnostic.limits,before:{diagnostic:views.before.diagnostic,geometry:views.before.data,selected:views.before.selected},after:{diagnostic:views.after.diagnostic,geometry:views.after.data,selected:views.after.selected},performance:log.export()};}
async function init(){try{
 manifest=await load('sleeve-manifest.json');referenceBody=await load(manifest.body.file,manifest.body.sha256);const data=await Promise.all([load(manifest.cases.before.file,manifest.cases.before.sha256),load(manifest.cases.after.file,manifest.cases.after.sha256)]);
 makeView('before');makeView('after');buildCase('before',data[0],referenceBody);buildCase('after',data[1],referenceBody);renderList();updateAppearance();setCamera('close');focusRidge(false);
 for(const id of['diagnostic-colors','show-grid','show-normals'])$('#'+id).onchange=()=>{updateAppearance();log.record('display-toggle',{control:id,value:$('#'+id).checked});refreshEventList();};
 $('#sleeve-side').onchange=e=>{side=e.target.value;renderList();focusRidge(false);setCamera('close');};$('#focus-old').onclick=()=>focusRidge(true);
 for(const name of['front','side','back'])$('#view-'+name).onclick=()=>setCamera(name);
 $('#download-report').onclick=()=>save('teagan-sleeve-crease-evidence.json',report());$('#download-trace').onclick=()=>save('teagan-sleeve-performance-trace.json',log.export());
 $('#import-diagnostic').onchange=async e=>{try{const file=e.target.files[0];if(!file)return;if(file.size>32*1024*1024)throw Error('文件超过32 MiB');const bytes=await file.arrayBuffer(),parsed=JSON.parse(new TextDecoder().decode(bytes)),geometry=parsed.geometry||parsed;const hash=await sha256(bytes);geometry.provenance={kind:'user-import',sha256:hash};buildCase('after',geometry,geometry.human||null);sourceHashes['user-import.json']=hash;log.record('user-import',{sha256:hash,accepted:true});$('#after-source').textContent='导入网格 · 不预设为左侧模型的修复版';$('#after-title').textContent='当前导入';$('#import-status').textContent='已独立重测导入网格。'+(geometry.human?'同时读取文件中的人体。':'文件没有人体，右侧隐藏人模。');updateAppearance();setCamera('close');refreshEventList();}catch(e){$('#import-status').textContent='未替换右侧模型：'+e.message;}};
 function frame(){requestAnimationFrame(frame);for(const v of Object.values(views))v.viewport.render();}frame();
 window.sleeveDebugger={ready:true,getReport:report,getPerformance:()=>log.export(),getViews:()=>Object.fromEntries(Object.entries(views).map(([id,v])=>[id,v.viewport.diagnostics()]))};refreshEventList();
 }catch(e){console.error(e);$('#error').hidden=false;$('#error').textContent='诊断未完成：'+e.message;}}
init();
