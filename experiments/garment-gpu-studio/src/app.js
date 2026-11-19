import {BASE_SIZE,makeBody}from './body.js';
import {draft}from './pattern.js';
import {buildConstraints}from './constraints.js';
import {checkSeams}from './seams.js';
import {initStrain,strainField}from './strain.js';
import {foldField}from './folds.js';
import {createContactSystem}from './collision.js';
import {GPUSolver}from './solver-gpu.js';
import {Replay}from './replay.js';
import {gradeSizes}from './grading.js';
import {Viewer}from './viewer.js';
import {verdict}from './debugger.js';
import {download,patternSVG,objExport,printable}from './exports.js';
const $=id=>document.getElementById(id),initial={...BASE_SIZE,heightCm:166.6,chestMm:855,waistMm:670,hipMm:969,lengthMm:650,sleeveMm:200,easePct:24,allowanceMm:10,iterations:128};
const state={revision:0,stale:true,running:false,busy:false,mode:'fabric',material:{E:100000,nu:.3,thicknessMm:1,arealDensity:180,status:'ASSUMED'},frames:new Replay(),errors:[],selected:null};
let viewer=null,solver=null,working=null;const runtimeErrors=[];
window.addEventListener('error',e=>{runtimeErrors.push(e.message);$('error').textContent=e.message;$('error').hidden=false;});
function inputs(){return Object.fromEntries(Object.keys(initial).map(k=>[k,Number($(k).value)]));}
function stop(){state.running=false;$('run').textContent='▶ 运行仿真';}
function message(text){$('message').textContent=text;}
function syncControls(){const disabled=state.stale||state.busy;for(const id of ['run','step','batch','verify','save','obj','svg','print','grade','poke'])$(id).disabled=disabled||( ['run','step','batch','poke'].includes(id)&&!solver);$('run').disabled=state.stale||!solver||(state.busy&&!state.running);for(const id of ['support','gravity'])$(id).disabled=disabled||!solver;for(const id of ['prev','next','playback','seek','report','grade-export'])$(id).disabled=disabled||(!state.grade&&id==='grade-export');$('apply').disabled=state.busy;$('status').textContent=state.busy?'正在构建':state.stale?'STALE · 请重建':solver?'GPU READY':'GPU BLOCKED';$('status').className='pill '+(state.stale?'warn':solver?'good':'warn');}
function markStale(){stop();state.stale=true;state.grade=null;state.verdict=null;state.revision++;for(const id of ['strain-value','gap-value','contact-value','fold-value'])$(id).textContent='—';$('diagnostics').innerHTML='<p class="tiny-note">STALE · 尺寸已修改，旧验证结果无效。</p>';message('尺寸已修改。旧纸样、碰撞与回放已失效。点击「应用尺寸」重新生成。');syncControls();publish();}
async function fingerprint(value){const data=new TextEncoder().encode(JSON.stringify(value));const hash=await crypto.subtle.digest('SHA-256',data);return Array.from(new Uint8Array(hash)).map(x=>x.toString(16).padStart(2,'0')).join('');}
function timeline(){const f=state.frames; $('seek').max=Math.max(0,f.frames.length-1);$('seek').value=f.cursor;$('frame').textContent=`${f.frames[f.cursor]?.id||0} · ${(f.frames[f.cursor]?.time||0).toFixed(3)} s`;$('records').textContent=`${f.frames.length}/240 帧`;}
function paper(){if(!state.doc)return;const svg=patternSVG(state.doc,{grade:state.grade,selected:state.selected?.piece});$('paper').innerHTML=svg;$('paper-mini').innerHTML=svg;}
function select(selection){state.selected={...selection,piece:state.doc.pieces.find(p=>selection.vertex>=p.offset&&selection.vertex<p.offset+p.vertices.length)?.id};viewer?.select(selection.vertex);$('selection').textContent=`裁片 ${state.selected.piece} · 顶点 ${selection.vertex} · GPU 节点 ${selection.node??state.model.map[selection.vertex]}${selection.triangle!=null?' · 面 '+selection.triangle:''}`;paper();}
function publish(){
 const out={version:state.version,revision:state.revision,stale:state.stale,busy:state.busy,running:state.running,mode:state.mode,backend:solver?.info||null,render:viewer?.renderInfo||null,step:solver?.steps||0,dispatches:solver?.dispatches||0,gpuCandidateDeltaMm:solver?.lastGpuDeltaMm??0,wasm:state.wasm||null,frameCount:state.frames.frames.length,cursor:state.frames.cursor,displayedFrame:state.frames.frames[state.frames.cursor]?.id,metrics:state.metrics,verdict:state.verdict,measurements:state.body?.measurementErrorMm,bodyVertices:state.body?.positions.length/3,bodyFaces:state.body?.triangles.length/3,pieces:state.doc?.pieces.length,vertices:state.doc?.mesh.restUV.length,seams:state.seams,grade:state.grade?.map(x=>({label:x.label,chest:x.doc.input.chestMm,area:x.doc.pieces[0].vertices.length})),errors:[...state.errors,...runtimeErrors,...(solver?.errors||[])]};
 $('runtime-state').textContent=JSON.stringify(out,null,2);$('runtime-state').dataset.step=String(out.step);window.garmentState=out;
}
function metrics(full=false,record=true){
 const p=state.p,doc=state.doc;state.strain=strainField(doc,p,state.material);state.folds=foldField(doc,state.model,p);state.collision=state.contact.inspect(p,full);state.seams=checkSeams(doc,p);
 const c=state.collision,s=state.strain,frameStep=record?(solver?.steps||0):(state.frames.frames[state.frames.cursor]?.id??solver?.steps??0);
 state.metrics={finite:p.every(Number.isFinite),strainP95:s.p95,strainMax:s.max,referenceStressMaxKPa:s.maxStressPa/1000,seamGapMm:state.seams.maxGapMm,penetrationMm:c.penetrationMm,penetratingVertices:c.penetratingVertices,penetratingSamples:c.penetratingSamples,bodyFaceCrossings:c.bodyFacePairs?.pairs.length??null,selfFaceCrossings:c.selfFacePairs?.pairs.length??null,fullCollision:full,foldMaxDeg:state.folds.maxDeg,step:frameStep,time:frameStep/120,lastStepMs:solver?.lastStepMs||0,contactQueries:c.queries};
 state.verdict=verdict(state.metrics,state.seams);
 $('strain-value').textContent=(s.p95*100).toFixed(1)+'%';$('gap-value').textContent=state.seams.maxGapMm.toFixed(2)+' mm';$('contact-value').textContent=String(c.penetratingVertices);$('fold-value').textContent=state.folds.maxDeg.toFixed(0)+'°';
 $('diagnostics').innerHTML=state.verdict.checks.map(x=>`<button class="check" data-check="${x.id}"><span class="dot ${x.status.toLowerCase()}"></span><span>${x.name}${['bodyFaces','self'].includes(x.id)&&x.value!=null?' · '+x.value+' 对':''}</span><b>${x.status}</b></button>`).join('');
 $('seam-table').innerHTML=state.seams.rows.map(x=>`<tr><td>${x.id.replace('right','R').replace('left','L')}</td><td>${(x.mismatch*100).toFixed(2)}%</td><td>${x.gapMm.toFixed(2)}</td></tr>`).join('');
 $('timing').textContent=`${state.model.nodeCount.toLocaleString()} 节点 · ${state.doc.mesh.triangles.length/3} 面 · ${(solver?.lastStepMs||0).toFixed(0)} ms/步`;
 if(record)state.frames.record(p,solver?.steps||0,1/120,state.metrics);timeline();viewer?.update(p,state.strain,state.folds,state.collision);publish();
}
async function build(overrides=null){
 stop();if(working)await working;state.busy=true;syncControls();$('error').hidden=true;message('正在重新制版与测量人体网格…');await new Promise(r=>requestAnimationFrame(r));
 const values=overrides||inputs();
 try{
  if(solver){solver.dispose();solver=null;}state.body=makeBody(values);state.doc=draft({...values,chestMm:state.body.measurements.chest.circumference*1000},state.body);state.model=buildConstraints(state.doc);state.contact=createContactSystem(state.body,state.model,state.doc);
  state.version=await fingerprint({input:values,pattern:state.doc.mesh.restUV,body:state.body.positions,solver:'hybrid-gpu-pbd-cpu-xpbd-v2-trust1mm',material:state.material,gravity:9.81,dt:1/120});state.frames.reset(state.version);state.grade=null;state.selected=null;state.stale=false;state.revision++;
  state.p=new Float32Array(state.doc.mesh.initial);paper();
  // Show the new project even when the machine cannot expose WebGPU.
  try{solver=await GPUSolver.create(state.model,state.contact,{iterations:values.iterations,document:state.doc,body:state.body});state.p=solver.positions();$('gpu-detail').textContent=(solver.info.isFallbackAdapter?'SwiftShader · 软件 WebGPU':solver.info.description||solver.info.vendor||'WebGPU adapter')+' + CPU XPBD';}
  catch(e){state.errors.push(String(e.message));$('gpu-detail').textContent='WebGPU BLOCKED';$('error').hidden=false;$('error').textContent=e.message;}
  viewer?.setProject(state.body,state.doc,state.model,state.p);$('version').textContent='v'+state.revision+' · '+state.version.slice(0,8);$('piece-count').textContent=`${state.doc.pieces.length} 裁片 · 10 条接缝`;
  $('body-note').textContent=`人体 ${state.body.measurements.height.toFixed(3)} m · 胸 ${(state.body.measurements.chest.circumference*100).toFixed(1)} cm · 腰 ${(state.body.measurements.waist.circumference*100).toFixed(1)} cm · 臀 ${(state.body.measurements.hip.circumference*100).toFixed(1)} cm`;
  metrics(true);message(solver?'已生成新纸样与人体。点击运行，用 WebGPU 计算后续布料状态。':'纸样和初始 3D 摆放已生成。此设备未提供 WebGPU，GPU 仿真未运行。');
 }catch(e){state.stale=true;state.errors.push(e.message);$('error').hidden=false;$('error').textContent=e.stack||e.message;message('构建失败。请检查输入。');}
 finally{state.busy=false;syncControls();publish();}
}
async function advance(count=1){
 if(state.stale||!solver||state.busy||working)return;const revision=state.revision,active=solver;state.busy=true;syncControls();
 working=(async()=>{try{for(let i=0;i<count;i++){const p=await active.step();if(state.revision!==revision)return;state.p=p;if(i%4===3||i===count-1){metrics(false);if(i<count-1)await new Promise(r=>requestAnimationFrame(r));}}}catch(e){stop();state.stale=true;state.verdict=null;state.errors.push(e.message);$('diagnostics').innerHTML='<p class="tiny-note">ERROR / STALE · 仿真已停止，旧验证结果无效。</p>';$('error').textContent=e.stack||e.message;$('error').hidden=false;}finally{state.busy=false;working=null;syncControls();publish();}})();await working;
}
async function runLoop(){if(!state.running)return;await advance(1);if(state.running)requestAnimationFrame(runLoop);}
function mode(name){state.mode=name;for(const b of document.querySelectorAll('[data-mode]'))b.classList.toggle('active',b.dataset.mode===name);$('paper-stage').hidden=name!=='pattern';$('viewport').classList.toggle('dim',name==='pattern');$('legend').hidden=!['strain','stress','folds','collision'].includes(name);const legends={strain:'主应变 · 0% → 25%+',stress:'参考应力 · 0 → 30 kPa+ · 未标定',folds:'二面角 · 0° → 120°+',collision:'蓝：分离 · 黄：接触 · 红：体内'};$('legend-title').textContent=legends[name]||'';if(viewer){viewer.mode=name;viewer.update(state.p,state.strain,state.folds,state.collision);}publish();}
function seek(value){stop();const frame=state.frames.seek(value,state.version);state.p=frame.positions.slice();metrics(false,false);timeline();message(`回放帧 ${frame.id}。回放读取已记录坐标，不推进求解器。`);}
function project(){return {format:'garment-gpu-project',version:1,input:inputs(),binding:state.version,material:state.material,document:state.doc,body:state.body,replay:state.frames.json(),verdict:state.verdict,backend:solver?.info||null};}
for(const key of Object.keys(initial)){$(key).value=initial[key];$(key).addEventListener('input',markStale);}
$('apply').onclick=()=>build();$('run').onclick=()=>{if(state.running){stop();return;}state.running=true;$('run').textContent='Ⅱ 暂停仿真';message('GPU 正在计算。时间步为 1/120 s。');runLoop();};$('step').onclick=()=>{stop();advance(1);};$('batch').onclick=async()=>{stop();message('正在计算 60 个 GPU 物理步…');await advance(60);if(!state.stale)message('已完成 60 步。可拖动时间轴查看真实记录。');};
$('verify').onclick=()=>{stop();metrics(true,false);message(`当前离散几何检查：${state.verdict.geometry}。人体面横穿 ${state.metrics.bodyFaceCrossings} 对；布料面横穿 ${state.metrics.selfFaceCrossings} 对。CCD、材料标定及真人合身：NOT_RUN。`);};
$('seek').oninput=e=>seek(Number(e.target.value));$('prev').onclick=()=>seek(state.frames.cursor-1);$('next').onclick=()=>seek(state.frames.cursor+1);
let replayTimer=null;$('playback').onclick=()=>{stop();if(replayTimer){clearInterval(replayTimer);replayTimer=null;$('playback').textContent='▷ 回放';return;}$('playback').textContent='Ⅱ 停止回放';replayTimer=setInterval(()=>{if(state.stale||state.frames.cursor>=state.frames.frames.length-1){clearInterval(replayTimer);replayTimer=null;$('playback').textContent='▷ 回放';return;}seek(state.frames.cursor+1);},100);};
$('poke').onclick=async()=>{stop();const node=state.selected?.node??state.model.map[state.doc.pieces[0].offset+Math.floor(state.doc.pieces[0].vertices.length*.7)];await solver.poke(node);await advance(1);message('已对选中节点施加局部位移；后续由 GPU 重新求解。');};
$('gravity').onchange=()=>{if(!solver)return;stop();solver.options.gravity=Number($('gravity').value);state.frames.reset(state.version+':g'+solver.options.gravity);state.version=state.frames.version;metrics(false);message('重力已改变。已建立新的回放版本。');};
$('support').onchange=()=>{if(solver){stop();solver.setPinned($('support').checked);state.version+=':p'+Number($('support').checked);state.frames.reset(state.version);metrics(false);}};
$('save').onclick=()=>download('garment-project.json',JSON.stringify(project()));$('obj').onclick=()=>download('garment-frame.obj',objExport(state.doc,state.p),'text/plain');$('svg').onclick=()=>download('teagan-pattern-1to1.svg',patternSVG(state.doc),'image/svg+xml');$('print').onclick=()=>download('teagan-print-1to1.html',printable(state.doc),'text/html');
$('grade').onclick=async()=>{stop();state.busy=true;syncControls();message('正在分别生成 S / M / L 三档纸样…');await new Promise(r=>requestAnimationFrame(r));try{state.grade=gradeSizes(inputs(),inputs());paper();mode('pattern');message('S / M / L 已按胸腰臀每档 40 mm 分别重新制版。放码未运行各档 3D 仿真。');}catch(e){message(e.message);}finally{state.busy=false;syncControls();publish();}};
$('grade-export').onclick=()=>{if(state.grade)download('teagan-grades.svg',patternSVG(state.doc,{grade:state.grade}),'image/svg+xml');};
document.querySelectorAll('[data-mode]').forEach(b=>b.onclick=()=>mode(b.dataset.mode));document.querySelectorAll('[data-view]').forEach(b=>b.onclick=()=>viewer?.view(b.dataset.view));$('transparent').onchange=()=>viewer?.transparency($('transparent').checked);
$('diagnostics').onclick=e=>{const id=e.target.closest('[data-check]')?.dataset.check;if(id==='body'||id==='samples'){mode('collision');select({vertex:state.collision.deepestVertex,node:state.model.map[state.collision.deepestVertex]});}else if(id==='bodyFaces'||id==='self'){mode('collision');const pair=(id==='bodyFaces'?state.collision.bodyFacePairs:state.collision.selfFacePairs)?.pairs[0];if(pair){const vertex=state.doc.mesh.triangles[pair[0]*3];select({vertex,node:state.model.map[vertex],triangle:pair[0]});}}else if(id==='strain'||id==='maxStrain'){mode('strain');const f=state.strain.values.indexOf(Math.max(...state.strain.values)),v=state.doc.mesh.triangles[f*3];select({vertex:v,node:state.model.map[v],triangle:f});}else if(id==='seams')mode('debug');};
$('report').onclick=()=>download('verification-current.json',JSON.stringify({...window.garmentState,positions:Array.from(state.p),restUV:state.doc.mesh.restUV,triangles:state.doc.mesh.triangles},null,2));
async function start(){await initStrain().then(x=>state.wasm={active:true,exports:x,precision:'f64'});try{viewer=new Viewer($('viewport'),select);}catch(e){$('error').hidden=false;$('error').textContent='3D 渲染不可用: '+e.message;state.errors.push(e.message);}
window.garmentAPI={build,advance,getProject:project,getState:()=>state,getSolver:()=>solver,getPositions:()=>Array.from(state.p),seek,mode};await build();}
start().catch(e=>{$('error').hidden=false;$('error').textContent=e.stack||e.message;state.errors.push(e.message);publish();});
