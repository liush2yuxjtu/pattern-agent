import * as THREE from '../../freesewing_cloth_lab/node_modules/three/build/three.module.js';
import {OrbitControls} from '../../freesewing_cloth_lab/node_modules/three/examples/jsm/controls/OrbitControls.js';
import {decodeBlock,encodeBase64} from './recording-codec.mjs';

const $=id=>document.getElementById(id), decode=(s,Type=Float32Array)=>{
 const bytes=Uint8Array.from(atob(s),c=>c.charCodeAt(0));return new Type(bytes.buffer);
};
const cleanDocument=document.documentElement.cloneNode(true);
const saved=$('saved-state')?JSON.parse($('saved-state').textContent):null;
const bytes=Uint8Array.from(atob($('physics-payload').textContent.trim()),c=>c.charCodeAt(0));
const blob=new Blob([bytes]);
const payload=JSON.parse(await new Response(blob.stream().pipeThrough(new DecompressionStream('gzip'))).text());
const host=$('canvas-host'),renderer=new THREE.WebGLRenderer({antialias:true,preserveDrawingBuffer:true});
renderer.setPixelRatio(Math.min(devicePixelRatio,2));renderer.setClearColor('#e9eee8');renderer.outputColorSpace=THREE.SRGBColorSpace;
host.prepend(renderer.domElement);renderer.domElement.setAttribute('aria-label','实际布料三维模型');
const scene=new THREE.Scene(),camera=new THREE.PerspectiveCamera(34,1,.01,30);
const controls=new OrbitControls(camera,renderer.domElement);controls.enableDamping=true;controls.dampingFactor=.12;
scene.add(new THREE.HemisphereLight(0xffffff,0x667361,2.5));const light=new THREE.DirectionalLight(0xffffff,3);light.position.set(-2,4,3);scene.add(light);
const clothMaterial=new THREE.MeshStandardMaterial({color:0xffffff,vertexColors:true,roughness:.85,metalness:0,side:THREE.DoubleSide});
let cloth,body,wire,seamLine,selection,geometry,current,index=0,mode='cloth',playing=false,anchor=0,lastTime=0,selectedFace=-1;
let seekCount=0;const framesDecoded=new Map(),ray=new THREE.Raycaster(),pointer=new THREE.Vector2();
let viewMode='3d',patternSVG=null,patternBaseBox=null,patternBox=null,patternBaseText='',specOpener=null,sourceReady=false;
const sourceBytes=new Map(),patternPointers=new Map();let patternGesture=null;
const faceValues=(frame)=>decode(frame.fields);
const palette=[[.16,.29,.65],[.20,.65,.68],[.85,.91,.78],[.94,.65,.25],[.76,.20,.18]];
function colorAt(t){t=Math.max(0,Math.min(1,t));const a=t*4,k=Math.min(3,Math.floor(a)),f=a-k;return palette[k].map((v,i)=>v+(palette[k+1][i]-v)*f);}
const ranges={strain:[-.1,.5,0,'最大主应变','−10%','≥50%'],stress:[-20000,100000,3,'最大主应力 · kPa','−20','≥100'],fold:[-180,180,null,'有向折角 · °','−180','180']};

function sourceFileBytes(file){
 if(!file||typeof file.base64!=='string')throw Error('没有随附完整设计文件');
 const key=file.sha256+'\0'+file.name;
 if(!sourceBytes.has(key)){
  const raw=Uint8Array.from(atob(file.base64),c=>c.charCodeAt(0));
  if(raw.byteLength!==file.byte_length)throw Error('设计文件的实际字节数与记录不一致');
  sourceBytes.set(key,raw);
 }
 return sourceBytes.get(key);
}
function downloadSource(kind){
 try{const file=current.source_package?.files?.[kind];if(!file)throw Error('本款没有此文件');download(file.name,sourceFileBytes(file),file.mime||'application/octet-stream');}
 catch(error){$('source-status').textContent=error.message;$('source-status').classList.add('error');}
}
function validBox(box){return Array.isArray(box)&&box.length===4&&box.every(Number.isFinite)&&box[2]>0&&box[3]>0;}
function applyPatternBox(box){
 if(!patternSVG||!validBox(box))return;
 patternBox=box.slice();
 const original=patternBaseBox.every((v,i)=>v===patternBox[i]);
 patternSVG.setAttribute('viewBox',original?patternBaseText:patternBox.join(' '));
 $('pattern-zoom-level').textContent=`${Math.round(patternBaseBox[2]/patternBox[2]*100)}%`;
}
function resetPattern(){if(patternBaseBox)applyPatternBox(patternBaseBox);}
function patternPoint(x,y,matrix){
 if(!patternSVG)return null;
 const inverse=matrix||patternSVG.getScreenCTM()?.inverse();if(!inverse)return null;
 const point=patternSVG.createSVGPoint();point.x=x;point.y=y;return point.matrixTransform(inverse);
}
function zoomPattern(factor,anchor){
 if(!patternBox||!Number.isFinite(factor)||!(factor>0))return;
 const [x,y,w,h]=patternBox,point=anchor||{x:x+w/2,y:y+h/2};
 const scale=Math.max(.5,Math.min(16,patternBaseBox[2]/w*factor)),width=patternBaseBox[2]/scale,height=patternBaseBox[3]/scale;
 applyPatternBox([point.x-(point.x-x)/w*width,point.y-(point.y-y)/h*height,width,height]);
}
function setView(value){
 viewMode=value==='2d'&&sourceReady?'2d':'3d';
 if(viewMode==='2d')setPlaying(false);
 const two=viewMode==='2d';
 $('view-2d').setAttribute('aria-pressed',String(two));$('view-3d').setAttribute('aria-pressed',String(!two));
 $('pattern-2d').hidden=!two;$('pattern-tools').hidden=!two;renderer.domElement.hidden=two;
 for(const id of ['three-tools','three-hint','replay-controls','three-foot'])$(id).hidden=two;
 controls.enabled=!two;patternPointers.clear();patternGesture=null;$('pattern-svg-host').classList.remove('dragging');
 paint();
}
function loadSources(){
 sourceReady=false;patternSVG=null;patternBaseBox=null;patternBox=null;patternPointers.clear();patternGesture=null;
 $('pattern-svg-host').replaceChildren();$('source-status').classList.remove('error');
 for(const id of ['view-2d','open-spec','download-spec','download-dxf'])$(id).disabled=true;
 for(const [key,id] of [['spec_diff','download-spec-diff'],['geometry_patch','download-geometry-patch']])$(id).hidden=!current.source_package?.files?.[key];
 const source=current.source_package;
 $('intent-text').textContent=typeof source?.intent==='string'?source.intent:'原型输入；尚未应用新的设计意图。';
 const changes=Array.isArray(source?.changes)?source.changes:[];
 $('intent-changes').replaceChildren(...changes.map(change=>{
  const row=document.createElement('li'),format=value=>Number.isFinite(value)?new Intl.NumberFormat('zh-CN',{maximumFractionDigits:6}).format(value):String(value??'—');
  row.textContent=`${change.name}：${format(change.before)} → ${format(change.after)} U`;return row;
 }));$('intent-changes').hidden=!changes.length;
 try{
  const files=source?.files,twoD=source?.twoD;
  if(!files?.yaml||!files?.dxf||!twoD?.svg)throw Error('本款未随附完整二维纸样与规格文件');
  if(files.yaml.sha256!==current.input.source_spec_sha256||files.dxf.sha256!==current.input.source_dxf_sha256||twoD.source_yaml_sha256!==files.yaml.sha256||twoD.source_dxf_sha256!==files.dxf.sha256)throw Error('二维文件与当前三维记录的来源版次不一致');
  for(const file of Object.values(files))sourceFileBytes(file);
  const parsed=new DOMParser().parseFromString(twoD.svg,'image/svg+xml'),svg=parsed.documentElement;
  if(svg.localName!=='svg'||parsed.querySelector('parsererror'))throw Error('本款二维SVG无法读取');
  // The builder emits source-bound vector primitives. Do not execute active SVG
  // content or let a saved review make external network requests.
  for(const node of [svg,...svg.querySelectorAll('*')]){
   if(['script','foreignobject','iframe','object','embed','image','audio','video'].includes(node.localName.toLowerCase()))throw Error('二维SVG包含不支持的活动内容');
   for(const attr of node.attributes)if(/^on/i.test(attr.name)||(['href','xlink:href','src'].includes(attr.name)&&!attr.value.startsWith('#'))||(attr.name==='style'&&/url\s*\(/i.test(attr.value)))throw Error('二维SVG包含外部或活动引用');
  }
  patternBaseText=svg.getAttribute('viewBox')||'';
  const box=patternBaseText.trim().split(/[\s,]+/).map(Number);if(!validBox(box))throw Error('本款二维纸样缺少有效的图形范围');
  const primitives=twoD.primitives||[],texts=primitives.filter(p=>p.kind==='TEXT').length,lines=primitives.length-texts;
  if(svg.querySelectorAll('polyline').length!==lines||svg.querySelectorAll('text').length!==texts)throw Error('二维SVG与完整图形清单不一致');
  patternSVG=document.importNode(svg,true);patternBaseBox=box;$('pattern-svg-host').replaceChildren(patternSVG);resetPattern();
  $('source-status').textContent=`完整二维纸样：${lines} 条线 · ${texts} 处文字 · 图形单位 U。完整 YAML 与 DXF 均随此文件保存。`;
  for(const id of ['view-2d','open-spec','download-spec','download-dxf'])$(id).disabled=false;
  sourceReady=true;
 }catch(error){$('source-status').textContent=error.message;$('source-status').classList.add('error');}
 setView(viewMode);
}
function openSpec(){
 if(!sourceReady)return;
 const file=current.source_package.files.yaml;
 try{
  $('spec-content').textContent=new TextDecoder('utf-8',{fatal:true}).decode(sourceFileBytes(file));
  $('spec-file-name').textContent=file.name;$('spec-file-size').textContent=`${file.byte_length.toLocaleString()} 字节 · UTF-8`;
  $('spec-file-hash').textContent=`SHA-256 ${file.sha256}`;$('spec-file-hash').title=file.sha256;
  specOpener=document.activeElement;document.body.classList.add('spec-reading');
  if(!$('spec-dialog').open)$('spec-dialog').showModal();
  $('open-spec').setAttribute('aria-expanded','true');$('spec-content').scrollTop=0;$('spec-content').scrollLeft=0;$('spec-content').focus({preventScroll:true});
 }catch(error){$('source-status').textContent=error.message;$('source-status').classList.add('error');}
}
function beginPatternGesture(){
 const entries=[...patternPointers.values()];if(!entries.length||!patternSVG){patternGesture=null;return;}
 const matrix=patternSVG.getScreenCTM()?.inverse();if(!matrix)return;
 const center=entries.length>1?{x:(entries[0].x+entries[1].x)/2,y:(entries[0].y+entries[1].y)/2}:entries[0];
 patternGesture={box:patternBox.slice(),matrix,anchor:patternPoint(center.x,center.y,matrix),distance:entries.length>1?Math.hypot(entries[1].x-entries[0].x,entries[1].y-entries[0].y):0};
}
function movePatternGesture(){
 if(!patternGesture)return;const entries=[...patternPointers.values()];if(!entries.length)return;
 const center=entries.length>1?{x:(entries[0].x+entries[1].x)/2,y:(entries[0].y+entries[1].y)/2}:entries[0],point=patternPoint(center.x,center.y,patternGesture.matrix),box=patternGesture.box;
 if(!point)return;
 const factor=entries.length>1&&patternGesture.distance>0?Math.hypot(entries[1].x-entries[0].x,entries[1].y-entries[0].y)/patternGesture.distance:1;
 const scale=Math.max(.5,Math.min(16,patternBaseBox[2]/box[2]*factor)),width=patternBaseBox[2]/scale,height=patternBaseBox[3]/scale;
 applyPatternBox([patternGesture.anchor.x-(point.x-box[0])/box[2]*width,patternGesture.anchor.y-(point.y-box[1])/box[3]*height,width,height]);
}
function frameData(i){
 if(!framesDecoded.has(i)){
  const f=current.recording.frames[i],data={};for(const key of ['positions','previous','fields','contacts','folds']){
   const block=current.recording_blocks?.[key];data[key]=block?current.decoded_blocks[key].subarray(i*block.width,(i+1)*block.width):(f[key]?decode(f[key]):null);
  }framesDecoded.set(i,data);
 }
 return framesDecoded.get(i);
}
function paint(){
 if(!geometry)return;const f=frameData(index),faces=current.input.triangles,colors=geometry.attributes.color.array,counts=new Uint32Array(f.positions.length/3);colors.fill(0);
 for(let t=0;t<faces.length;t++){
  let color=[.53,.71,.58];
  if(ranges[mode]){const [lo,hi,col]=ranges[mode],v=mode==='fold'?(f.folds?.[t*2]??NaN):f.fields[t*8+col];color=Number.isFinite(v)?colorAt((v-lo)/(hi-lo)):[.7,.08,.6];}
  for(const v of faces[t]){counts[v]++;for(let k=0;k<3;k++)colors[v*3+k]+=color[k];}
 }
 for(let v=0;v<counts.length;v++)for(let k=0;k<3;k++)colors[v*3+k]/=counts[v]||1;
 if(mode==='contacts')for(let v=0;v<counts.length;v++){const c=f.contacts[v]>0?[.83,.28,.16]:[.56,.69,.59];colors.set(c,v*3);}
 geometry.attributes.color.needsUpdate=true;
 $('legend').hidden=viewMode!=='3d'||!ranges[mode];if(ranges[mode]){const r=ranges[mode];$('legend').querySelector('strong').textContent=r[3];const spans=$('legend').querySelectorAll('span');spans[0].textContent=r[4];spans[1].textContent=r[5];}
 for(const button of document.querySelectorAll('[data-mode]'))button.setAttribute('aria-pressed',String(button.dataset.mode===mode));
 seamLine.visible=mode==='seams';
}
function metric(label,value,unit='',bad=false){return `<div><div class="metric-label">${label}</div><div class="metric-value ${bad?'bad':'good'}">${value}<small>${unit}</small></div></div>`;}
function showMetrics(){
 const row=current.audit.frames.find(r=>r.frame===index),f=current.recording.frames[index],passed=current.audit.verdict==='PASS';
 $('frame-verdict').textContent=row?(row.verdict||(row.max_seam_gap_mm<=2&&row.max_body_penetration_mm<=.2&&!row.cloth_edge_body_hits&&!row.body_edge_cloth_hits&&!row.strict_self_intersections&&row.tensor_pass&&row.fold_pass===true&&(!row.arm_wear||row.arm_wear.both_arms_threaded)?'PASS':'FAIL')):'未逐帧验收';
 $('metrics').innerHTML=metric('最大接缝间隙',row?row.max_seam_gap_mm.toFixed(2):'—','mm',!row||row.max_seam_gap_mm>2)+metric('人体穿入',row?row.max_body_penetration_mm.toFixed(2):'—','mm',!row||row.max_body_penetration_mm>.2)+metric('严格自交',row?row.strict_self_intersections:'—','处',!row||row.strict_self_intersections>0)+metric('人体交叉',row?row.cloth_edge_body_hits+row.body_edge_cloth_hits:'—','处',!row||row.cloth_edge_body_hits+row.body_edge_cloth_hits>0);
 $('outcome').classList.toggle('pass',passed);
 $('outcome').textContent=passed?'整衣离散数值验收通过。面料实测与真人合身仍未验证。':`整衣验收 ${current.audit.verdict}。闭缝不能代替碰撞与穿插验收；${current.audit.frames_checked}/${current.audit.total_frames} 帧已有独立检查，失败项保留。`;
 $('frame-info').textContent=`${current.input.positions.length.toLocaleString()} 顶点 · ${current.input.triangles.length.toLocaleString()} 三角面 · t = ${f.time.toFixed(3)} s`;
}
function updateSeam(){
 const input=current.input,key=$('seam').value,pair=input.source_sewing.seams.find(s=>s.name===key),segment=input.source_sewing.segments[pair.a],other=input.source_sewing.segments[pair.b];
 const rawIds=segment.local_vertices.map(id=>input.panels.find(p=>p.name===segment.patch).start+id),f=frameData(index),points=[];
 for(let j=0;j<rawIds.length-1;j++)for(const id of [rawIds[j],rawIds[j+1]])points.push(...f.positions.slice(id*3,id*3+3));
 seamLine.geometry.dispose();seamLine.geometry=new THREE.BufferGeometry();seamLine.geometry.setAttribute('position',new THREE.Float32BufferAttribute(points,3));
 $('seam-detail').textContent=`${segment.patch} ↔ ${other.patch}；${rawIds.length} 对对应采样点。处理后平面走缝：${(segment.rest_length_mm+segment.process_mm).toFixed(2)} / ${(other.rest_length_mm+other.process_mm).toFixed(2)} U；本次数值实验假定 1 U = 1 mm。`;
}
function inspectTriangle(face){
 if(face<0)return;selectedFace=face;const ids=current.input.triangles[face],f=frameData(index),panel=current.input.panels.find(p=>face>=p.face_start&&face<p.face_start+p.faces),flat=ids.map(id=>current.input.uv[id].map((v,k)=>(v+(panel.uv_origin_m?.[k]||0))*1000));
 const lo=[0,1].map(k=>Math.min(...flat.map(v=>v[k]))),hi=[0,1].map(k=>Math.max(...flat.map(v=>v[k]))),size=Math.max(hi[0]-lo[0],hi[1]-lo[1],1),points=flat.map(v=>`${100+(v[0]-(lo[0]+hi[0])/2)*65/size},${45-(v[1]-(lo[1]+hi[1])/2)*65/size}`).join(' ');
 $('uv-preview').innerHTML=`<polygon points="${points}" fill="#e0ede2" stroke="#306a50" stroke-width="1.5"/>`;
 $('picked').textContent=`#${face} · ${panel.name}`;const fields=f.fields.subarray(face*8,face*8+8),fold=f.folds?.[face*2];
 const rows=[['最大主应变',`${(fields[0]*100).toFixed(2)} %`],['最大主应力',`${(fields[3]/1000).toFixed(3)} kPa`],['有向折角',fold===undefined?'未计算':`${fold.toFixed(2)} °`],['二维顶点 (U)',flat.map(p=>p.map(v=>v.toFixed(2)).join(', ')).join(' / ')]];
 $('triangle-detail').innerHTML=rows.map(([a,b])=>`<dt>${a}</dt><dd>${b}</dd>`).join('');
 const verts=ids.flatMap(id=>Array.from(f.positions.subarray(id*3,id*3+3)));verts.push(...verts.slice(0,3));selection.geometry.dispose();selection.geometry=new THREE.BufferGeometry();selection.geometry.setAttribute('position',new THREE.Float32BufferAttribute(verts,3));
}
function seek(i){
 index=Math.max(0,Math.min(current.recording.frames.length-1,Number(i)));seekCount++;
 const f=frameData(index);geometry.attributes.position.array.set(f.positions);geometry.attributes.position.needsUpdate=true;geometry.computeVertexNormals();geometry.computeBoundingSphere();
 if(wire){wire.geometry.dispose();wire.geometry=new THREE.WireframeGeometry(geometry);}
 $('timeline').value=index;$('clock').textContent=`${index} / ${current.recording.frames.length-1}`;paint();updateSeam();showMetrics();if(selectedFace>=0)inspectTriangle(selectedFace);
}
function setPlaying(value){playing=value;anchor=index;lastTime=performance.now();$('play').textContent=playing?'Ⅱ':'▶';$('play').setAttribute('aria-label',playing?'暂停物理记录':'播放物理记录');}
function resetCamera(){camera.position.set(1.12,1.25,2.15);controls.target.set(0,1.15,.05);controls.update();}
function disposeObject(object){if(object){scene.remove(object);object.geometry?.dispose();if(object!==cloth)object.material?.dispose();}}
function loadCase(id){
 if($('spec-dialog').open)$('spec-dialog').close();
 setPlaying(false);current=payload.cases.find(c=>c.input.case===id);framesDecoded.clear();selectedFace=-1;
 current.decoded_blocks={};for(const [key,block] of Object.entries(current.recording_blocks||{}))current.decoded_blocks[key]=decodeBlock(block);
 for(const object of [wire,cloth,body,seamLine,selection])disposeObject(object);
 const input=current.input,flat=input.triangles.flat();geometry=new THREE.BufferGeometry();geometry.setAttribute('position',new THREE.Float32BufferAttribute(new Float32Array(input.positions.length*3),3));geometry.setAttribute('color',new THREE.Float32BufferAttribute(new Float32Array(input.positions.length*3),3));geometry.setIndex(flat);
 cloth=new THREE.Mesh(geometry,clothMaterial);scene.add(cloth);wire=new THREE.LineSegments(new THREE.WireframeGeometry(geometry),new THREE.LineBasicMaterial({color:'#214e3a',transparent:true,opacity:.18}));wire.visible=$('wire').checked;scene.add(wire);
 const bodyGeometry=new THREE.BufferGeometry();bodyGeometry.setAttribute('position',new THREE.BufferAttribute(decode(input.body.positions),3));bodyGeometry.setIndex(new THREE.BufferAttribute(decode(input.body.indices,Uint32Array),1));bodyGeometry.computeVertexNormals();body=new THREE.Mesh(bodyGeometry,new THREE.MeshStandardMaterial({color:'#ccbdb0',roughness:1,transparent:true,opacity:.58,depthWrite:false}));body.visible=$('body').checked;scene.add(body);
 seamLine=new THREE.LineSegments(new THREE.BufferGeometry(),new THREE.LineBasicMaterial({color:'#e77b2a',depthTest:false}));seamLine.renderOrder=3;scene.add(seamLine);
 selection=new THREE.Line(new THREE.BufferGeometry(),new THREE.LineBasicMaterial({color:'#aa372e',depthTest:false}));selection.renderOrder=4;scene.add(selection);
 $('seam').replaceChildren(...input.source_sewing.seams.map(s=>new Option(s.name,s.name)));$('timeline').max=current.recording.frames.length-1;
 $('conditions').textContent=current.conditions;for(const id of ['play','prev','next','timeline'])$(id).disabled=false;
 seek(0);const f=frameData(0);let max=0;for(let i=1;i<input.triangles.length;i++)if(f.fields[i*8]>f.fields[max*8])max=i;inspectTriangle(max);resetCamera();loadSources();$('loading').hidden=true;
}
function download(name,content,type='application/json'){const url=URL.createObjectURL(new Blob([content],{type})),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
function fullRecording(){const recording=structuredClone(current.recording);for(let i=0;i<recording.frames.length;i++)for(const key of ['positions','previous','fields','contacts','folds'])recording.frames[i][key]=encodeBase64(frameData(i)[key]);return recording;}
for(const c of payload.cases)$('case').add(new Option(c.label,c.input.case));
$('case').onchange=()=>loadCase($('case').value);$('timeline').oninput=e=>{setPlaying(false);seek(e.target.value);};
$('play').onclick=()=>{if(index===current.recording.frames.length-1)seek(0);setPlaying(!playing);};$('prev').onclick=()=>{setPlaying(false);seek(index-1);};$('next').onclick=()=>{setPlaying(false);seek(index+1);};
$('speed').onchange=()=>{anchor=index;lastTime=performance.now();};$('body').onchange=e=>body.visible=e.target.checked;$('wire').onchange=e=>wire.visible=e.target.checked;$('reset-camera').onclick=resetCamera;
$('seam').onchange=()=>{mode='seams';paint();updateSeam();};for(const b of document.querySelectorAll('[data-mode]'))b.onclick=()=>{mode=b.dataset.mode;paint();};
$('view-2d').onclick=()=>setView('2d');$('view-3d').onclick=()=>setView('3d');
$('pattern-zoom-in').onclick=()=>zoomPattern(1.25);$('pattern-zoom-out').onclick=()=>zoomPattern(.8);$('pattern-reset').onclick=resetPattern;
$('open-spec').setAttribute('aria-controls','spec-dialog');$('open-spec').setAttribute('aria-expanded','false');$('open-spec').onclick=openSpec;
$('download-spec').onclick=() =>downloadSource('yaml');$('download-dxf').onclick=()=>downloadSource('dxf');
$('download-spec-diff').onclick=()=>downloadSource('spec_diff');$('download-geometry-patch').onclick=()=>downloadSource('geometry_patch');
$('spec-download').onclick=()=>downloadSource('yaml');$('spec-top').onclick=()=>{$('spec-content').scrollTop=0;$('spec-content').scrollLeft=0;$('spec-content').focus({preventScroll:true});};
$('close-spec').onclick=()=> $('spec-dialog').close();
$('spec-dialog').addEventListener('cancel',event=>{event.preventDefault();$('spec-dialog').close();});
$('spec-dialog').addEventListener('close',()=>{document.body.classList.remove('spec-reading');$('open-spec').setAttribute('aria-expanded','false');const target=specOpener?.isConnected?specOpener:$('open-spec');target.focus({preventScroll:true});specOpener=null;});
$('spec-dialog').addEventListener('click',event=>{if(event.target!==$('spec-dialog'))return;const r=$('spec-dialog').getBoundingClientRect();if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom)$('spec-dialog').close();});
const patternHost=$('pattern-svg-host');
patternHost.addEventListener('wheel',event=>{if(viewMode!=='2d')return;event.preventDefault();const delta=event.deltaY*(event.deltaMode===1?16:event.deltaMode===2?patternHost.clientHeight:1);zoomPattern(Math.exp(-delta*.0015),patternPoint(event.clientX,event.clientY));beginPatternGesture();},{passive:false});
patternHost.addEventListener('pointerdown',event=>{if(viewMode!=='2d'||event.button!==0)return;event.preventDefault();patternHost.focus({preventScroll:true});patternPointers.set(event.pointerId,{x:event.clientX,y:event.clientY});patternHost.setPointerCapture(event.pointerId);patternHost.classList.add('dragging');beginPatternGesture();});
patternHost.addEventListener('pointermove',event=>{if(!patternPointers.has(event.pointerId))return;event.preventDefault();patternPointers.set(event.pointerId,{x:event.clientX,y:event.clientY});movePatternGesture();});
for(const name of ['pointerup','pointercancel','lostpointercapture'])patternHost.addEventListener(name,event=>{if(!patternPointers.delete(event.pointerId))return;if(patternHost.hasPointerCapture(event.pointerId))patternHost.releasePointerCapture(event.pointerId);patternHost.classList.toggle('dragging',patternPointers.size>0);beginPatternGesture();});
patternHost.addEventListener('keydown',event=>{
 if(viewMode!=='2d'||!patternBox)return;const box=patternBox.slice();
 if(['+','=','-','0','Home','ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(event.key)){event.preventDefault();event.stopPropagation();}
 if(event.key==='+'||event.key==='=')zoomPattern(1.25);else if(event.key==='-')zoomPattern(.8);else if(event.key==='0'||event.key==='Home')resetPattern();
 else if(event.key==='ArrowLeft'||event.key==='ArrowRight'){box[0]+=(event.key==='ArrowLeft'?-1:1)*box[2]*.06;applyPatternBox(box);}
 else if(event.key==='ArrowUp'||event.key==='ArrowDown'){box[1]+=(event.key==='ArrowUp'?-1:1)*box[3]*.06;applyPatternBox(box);}
});
$('download-record').onclick=()=>download(`${current.input.case}-physical-recording.json`,JSON.stringify({input:current.input,recording:fullRecording(),audit:current.audit}));
$('download-html').onclick=()=>{const doc=cleanDocument.cloneNode(true);doc.querySelector('#saved-state')?.remove();const state=document.createElement('script');state.id='saved-state';state.type='application/json';state.textContent=JSON.stringify({case:current.input.case,index,mode,body:body.visible,wire:wire.visible,selectedFace,camera:camera.position.toArray(),target:controls.target.toArray(),view:viewMode,patternViewBox:patternBox?.slice()});doc.querySelector('body').append(state);download('pattern-physics-review.html','<!doctype html>\n'+doc.outerHTML,'text/html');};
$('download-obj').onclick=()=>{const f=frameData(index),rows=['# actual physical recording in metres',`# source DXF sha256 ${current.input.source_dxf_sha256}`,`# frame ${index}; actual fit NOT_RUN`];for(let i=0;i<f.positions.length;i+=3)rows.push(`v ${f.positions[i]} ${f.positions[i+1]} ${f.positions[i+2]}`);for(const face of current.input.triangles)rows.push('f '+face.map(i=>i+1).join(' '));download(`${current.input.case}-frame-${index}.obj`,rows.join('\n'),'text/plain');};
let down;renderer.domElement.addEventListener('pointerdown',e=>down=[e.clientX,e.clientY]);renderer.domElement.addEventListener('pointerup',e=>{if(!down||Math.hypot(e.clientX-down[0],e.clientY-down[1])>5)return;const r=renderer.domElement.getBoundingClientRect();pointer.set((e.clientX-r.left)/r.width*2-1,-(e.clientY-r.top)/r.height*2+1);ray.setFromCamera(pointer,camera);const hit=ray.intersectObject(cloth)[0];if(hit)inspectTriangle(hit.faceIndex);});
window.addEventListener('keydown',e=>{if(viewMode!=='3d'||$('spec-dialog').open||['INPUT','SELECT','BUTTON'].includes(document.activeElement.tagName))return;if(e.code==='Space'){e.preventDefault();$('play').click();}if(e.code==='ArrowRight')$('next').click();if(e.code==='ArrowLeft')$('prev').click();});
const observer=new ResizeObserver(()=>{const r=host.getBoundingClientRect();renderer.setSize(r.width,r.height);camera.aspect=r.width/r.height;camera.updateProjectionMatrix();});observer.observe(host);
$('engines').innerHTML=payload.engines.map((e,i)=>`<article class="engine"><span class="engine-number">0${i+1}</span><h3>${e.name}</h3><span class="status ${e.verdict==='PASS'?'':e.verdict==='FAIL'?'failed':'pending'}">${i===5?'界面验收':'机制对照'} ${e.verdict==='NOT_RUN'?'待验证':e.verdict}</span><p>${e.note}</p></article>`).join('');
loadCase(payload.cases[0].input.case);
if(saved){$('case').value=saved.case;loadCase(saved.case);mode=saved.mode;seek(saved.index);body.visible=$('body').checked=saved.body;wire.visible=$('wire').checked=saved.wire;inspectTriangle(saved.selectedFace);camera.position.fromArray(saved.camera);controls.target.fromArray(saved.target);controls.update();if(validBox(saved.patternViewBox)&&patternBaseBox)applyPatternBox(saved.patternViewBox);setView(saved.view||'3d');}
function animate(now){requestAnimationFrame(animate);if(playing){const next=Math.min(current.recording.frames.length-1,anchor+Math.floor((now-lastTime)*Number($('speed').value)*120/1000));if(next!==index)seek(next);if(index===current.recording.frames.length-1)setPlaying(false);}if(viewMode==='3d'){controls.update();renderer.render(scene,camera);}}requestAnimationFrame(animate);
window.physicsReview={
 info:()=>({case:current.input.case,index,frames:current.recording.frames.length,playing,mode,seekCount,integrationCallsDuringReplay:0,selectedFace,sourceDXF:current.input.source_dxf_sha256,sourceSpec:current.input.source_spec_sha256,verdict:current.audit.verdict,view:viewMode,patternViewBox:patternBox?.slice()||null,specOpen:$('spec-dialog').open,viewerSources:{...payload.viewer_sources}}),
 state:()=>({positions:Array.from(geometry.attributes.position.array),previous:Array.from(frameData(index).previous),fields:Array.from(frameData(index).fields),contacts:Array.from(frameData(index).contacts),folds:frameData(index).folds?Array.from(frameData(index).folds):null,clock:current.recording.frames[index].time}),
 surface:()=>({positions:Array.from(geometry.attributes.position.array),colors:Array.from(geometry.attributes.color.array),triangles:current.input.triangles,mode}),
 source:()=>({input:current.input,recording:fullRecording(),audit:current.audit}),
 sources:()=>structuredClone(current.source_package??null),
 renderer:()=>({calls:renderer.info.render.calls,triangles:renderer.info.render.triangles,geometries:renderer.info.memory.geometries}),
 projectPoint:vertex=>{const p=new THREE.Vector3().fromArray(geometry.attributes.position.array,vertex*3).project(camera),r=renderer.domElement.getBoundingClientRect();return{x:r.left+(p.x+1)*r.width/2,y:r.top+(1-p.y)*r.height/2};}
};
