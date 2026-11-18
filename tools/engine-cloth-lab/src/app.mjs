import * as THREE from 'three';
import {jsPDF} from 'jspdf';
import YAML from 'yaml';
import {buildDemo,human} from './pipeline.mjs';
import {makeDraft} from '../probes/pattern/adapter.mjs';
import {newArtifact,invalidate,addFrame,liveExport,GOLDEN_SHA,validSettings} from './domain.mjs';
import {measure,foldAngles} from './metrics.mjs';
import {goldenDrawing} from './golden.mjs';
import {SoftwareRenderer} from '../reference/src/software-renderer.js';
import {auditSurfaceCollisions} from '../reference/benchmarks/collision/surface-audit.mjs';
import {MeshBodyCollider} from '../reference/src/mesh-collider.js';
const golden=YAML.parse(__GOLDEN_YAML__), $=id=>document.getElementById(id);
document.documentElement.dataset.buildSourceSha=__BUILD_ID__;
let artifact=newArtifact(),view='pattern',cameraName='iso',display='fabric',worker=null,job=0,busy=false,workerReady=false,timeout=null;
let sequence=0,auditJob=0,auditBusy=false,selectedTriangle=null,renderer,scene,camera,clothObject,bodyObject,pinGroup,collisionObject;
const bodyCollider=new MeshBodyCollider(human),logEntries=[],performanceEntries=[];
const escape=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt=(x,d=2)=>Number.isFinite(x)?x.toFixed(d):'—';
const current=()=>artifact.frames[artifact.frameIndex]??null;
const identity=()=>({source:artifact.source,artifactId:artifact.id,instanceId:artifact.instanceId,revision:artifact.revision,runId:job});
function log(message){logEntries.push({...identity(),message});if(logEntries.length>100)logEntries.shift();$('log').textContent=logEntries.filter(e=>e.instanceId===artifact.instanceId).map(e=>`R${e.revision} · ${e.message}`).join('\n');$('log').scrollTop=1e5;}
function perf(item){performanceEntries.push({...identity(),...item});if(performanceEntries.length>500)performanceEntries.shift();$('performance-log').textContent=JSON.stringify(performanceEntries.filter(e=>e.instanceId===artifact.instanceId),null,2);}
function terminate(reason){job++;auditJob++;auditBusy=false;worker?.terminate();worker=null;workerReady=false;busy=false;clearTimeout(timeout);if(reason)log(reason);}
const settings=()=>({waistDeltaMM:Number($('waist').value),sleeveLength:Number($('sleeve').value)/100,necklineDepth:Number($('neck').value)/100,spacingMM:Number($('spacing').value),profile:$('profile').value});
function refreshControls(){
  $('waist-output').textContent=`${$('waist').value} mm`;$('sleeve-output').textContent=`${$('sleeve').value}%`;$('neck-output').textContent=`${$('neck').value}%`;
  const demo=artifact.source==='ENGINE_CONFORMANCE';
  $('demo-fields').hidden=!demo;$('golden-fields').hidden=demo;
  $('source-note').innerHTML=demo?'<strong>ENGINE_CONFORMANCE</strong><br>FreeSewing Teagan 4.10.2 · 短袖引擎样衣。独立于 Golden；尺寸、材料和初始装配含演示假设。':'<strong>CANONICAL SOURCE</strong><br>Golden YAML 1.1 · 4 原始裁片。原始设计完整保留。';
  $('golden-fields').innerHTML='坐标单位 <strong>U</strong><br>U→mm：未标定<br>净样／裁剪线：待确认<br>材料、裁数、人体尺寸：待确认';
  $('garment-title').textContent=demo?'Teagan · 原生引擎样衣':'女式长袖圆领 T 恤';
  $('garment-subtitle').textContent=demo?'FreeSewing → Rapier WASM · MakeHuman 真实人体网格':'Golden Garment YAML 1.1 · 保留原始 U 坐标';
  $('build').disabled=!demo||busy;$('build').textContent=artifact.status==='STALE'?'重新生成 · 清除旧结果':'生成引擎样衣';
  $('run').disabled=!demo||!workerReady||busy||auditBusy||artifact.meshRevision!==artifact.revision||artifact.frameIndex!==artifact.frames.length-1||(current()?.step??0)>=600;
  $('stop').disabled=!busy;
  $('audit').disabled=!demo||!current()||busy||auditBusy||artifact.meshRevision!==artifact.revision;
  $('timeline').disabled=busy||auditBusy;
  $('export-pdf').disabled=!demo||!artifact.draft||artifact.status==='STALE';
  $('export-note').textContent=demo?'SVG / PDF 使用 mm；净样线无缝份。仅用于尺寸与引擎检查。':'U 未标定，实际尺寸裁剪暂不可用。';
  $('revision').textContent=`REV ${String(artifact.revision).padStart(2,'0')}`;
  $('artifact-status').textContent=artifact.source==='GOLDEN_YAML'?'BLOCKED · 单位未标定':artifact.status==='COMPLETED'?`计算结束 · ${current()?.metrics.maxSeamGapMM>2?'缝合 FAIL':'合身未验证'}`:`${artifact.status} · ${busy?'原生求解中':artifact.frames.length?'演示来源':'需生成网格'}`;
  $('artifact-status').className='status '+(artifact.status==='ERROR'||artifact.status==='TIMEOUT'?'fail':artifact.status==='STALE'?'warn':'');
}
function updateEvidence(){
  const demo=artifact.source==='ENGINE_CONFORMANCE',m=current()?.metrics,a=artifact.audit;
  const rows=[['原始输入',demo?'DEMO_ASSUMED':'YAML · U'],['物理运行',demo?artifact.status:'BLOCKED'],['缝合拓扑',artifact.mesh?`${artifact.mesh.seams.length} native`:'待确认'],['缝隙 ≤2mm',m?(m.maxSeamGapMM<=2?'PASS':'FAIL'):'NOT_RUN'],['应变',m?'几何量 · 无单位':'NOT_RUN'],['材料应力 / 压力','UNKNOWN'],['人体面穿',a?a.bodySurface.status:'NOT_RUN'],['内部顶点',a?a.vertexInside.status:'NOT_RUN'],['布料自交',a?a.selfSurface.status:'NOT_RUN'],['真实合身','NOT_VALIDATED']];
  $('verdicts').innerHTML=rows.map(([k,v])=>`<div class="verdict"><span>${escape(k)}</span><b class="${v==='FAIL'?'fail':v==='PASS'?'pass':v.includes('BLOCKED')?'warn':''}">${escape(v)}</b></div>`).join('');
  $('metric-panels').textContent=artifact.draft?.panels.length??4;
  $('metric-steps').textContent=current()?.step??'—';
  $('metric-gap').textContent=m?`${fmt(m.maxSeamGapMM,1)} mm`:'—';
  $('metric-collisions').textContent=a?String(a.bodySurface.strictCrossingPairs):'未检查';
  $('timeline').max=Math.max(0,artifact.frames.length-1);$('timeline').value=artifact.frameIndex;
  $('timeline-output').textContent=current()?`F${current().step} · ${fmt(current().step/120,3)} s`:'无求解帧';
  $('detail').innerHTML=demo&&artifact.mesh?`<strong>${artifact.mesh.restXY.length}</strong> 粒子 · <strong>${artifact.mesh.triangles.length}</strong> 三角形<br>接触半径：5mm（演示）<br>dt：1/120s · 原生自接触<br>累计求解：${artifact.native?.stepCount??0} 步<br>肩部支撑：${artifact.pose.pins.length} 个<br>${m?`λmax ${fmt(m.maxStretch,3)} / λmin ${fmt(m.minStretch,3)}<br>拉伸 >20% 面积 ${fmt(m.areaOver20Percent*100,2)}%<br>`:''}${a?`内部顶点 ${a.vertexInside.count} · 最深 ${fmt(a.vertexInside.maxDepthM*1000,3)}mm<br>自交 ${a.selfSurface.strictCrossingPairs} · 退化 ${a.invalidTriangles.clothTriangles.length}<br>检查帧 F${artifact.auditStep} / REV ${artifact.auditRevision}<br>`:''}<span>真实应力、压力和合身：未验证。</span>`:'126 折线 · 78 直线 · 27 文字<br>1487 折线顶点 · 25 命名接口<br>物理计算需先确认单位、结构语义和材料。';
}
function drawPattern(){
  if(artifact.source==='GOLDEN_YAML'){
    const drawing=goldenDrawing(golden);$('pattern-stage').innerHTML=drawing.svg;
    $('stage-caption').textContent=`原始 YAML · ${drawing.stats.parts} 片 / ${drawing.stats.polylines} 折线 / ${drawing.stats.lines} 直线 / ${drawing.stats.texts} 文字 · U`;
  }else if(artifact.draft){
    $('pattern-stage').innerHTML=artifact.draft.svg;
    $('pattern-stage').querySelector('svg')?.removeAttribute('width');$('pattern-stage').querySelector('svg')?.removeAttribute('height');
    if(selectedTriangle!==null&&artifact.mesh){const ids=artifact.mesh.triangles[selectedTriangle],panelID=artifact.mesh.panelOfVertex[ids[0]],index=artifact.draft.panels.findIndex(p=>p.id===panelID),g=$('pattern-stage').querySelectorAll('svg>g')[index];if(g){const polygon=document.createElementNS('http://www.w3.org/2000/svg','polygon');polygon.setAttribute('points',ids.map(i=>artifact.mesh.restXY[i].join(',')).join(' '));polygon.setAttribute('fill','#d8793a');polygon.setAttribute('fill-opacity','.5');polygon.setAttribute('stroke','#ab4d28');polygon.setAttribute('stroke-width','2');g.append(polygon);}}
    $('stage-caption').textContent=`FreeSewing 原生净样 · mm · 2 身片 + 2 短袖 · ${artifact.status==='STALE'?'STALE':'REV '+artifact.revision}`;
  }else{$('pattern-stage').innerHTML='<p>生成引擎样衣后显示参数化纸样。</p>';$('stage-caption').textContent='ENGINE_CONFORMANCE · 尚无网格';}
}
function initScene(){
  scene=new THREE.Scene();scene.background=new THREE.Color('#e9e9e4');camera=new THREE.PerspectiveCamera(34,1,.01,20);
  try{renderer=new THREE.WebGLRenderer({antialias:true,alpha:false});renderer.setPixelRatio(Math.min(devicePixelRatio,1.5));$('renderer-badge').textContent='WebGL · Three.js';}
  catch(error){renderer=new SoftwareRenderer();renderer.setPixelRatio(1);$('renderer-badge').textContent='Canvas · 软件深度缓冲';log('WebGL 不可用；使用同帧软件渲染。');}
  $('three-stage').append(renderer.domElement);
  const geometry=new THREE.BufferGeometry();geometry.setAttribute('position',new THREE.Float32BufferAttribute(human.positions,3));geometry.setIndex(human.triangles);geometry.computeVertexNormals();
  bodyObject=new THREE.Mesh(geometry,new THREE.MeshStandardMaterial({color:'#b6b4a7',roughness:.88,side:THREE.DoubleSide}));scene.add(bodyObject);
  scene.add(new THREE.HemisphereLight(0xffffff,0x737c66,2));const key=new THREE.DirectionalLight(0xffffff,2.2);key.position.set(-2,4,3);scene.add(key);
  pinGroup=new THREE.Group();scene.add(pinGroup);collisionObject=new THREE.Group();scene.add(collisionObject);
  renderer.domElement.addEventListener('click',event=>{
    if(!clothObject||!artifact.mesh)return;
    const b=renderer.domElement.getBoundingClientRect(),ray=new THREE.Raycaster();ray.setFromCamera(new THREE.Vector2((event.clientX-b.x)/b.width*2-1,-(event.clientY-b.y)/b.height*2+1),camera);
    const hit=ray.intersectObject(clothObject)[0];if(hit){selectedTriangle=hit.faceIndex;const m=current()?.metrics?.triangles[hit.faceIndex];log(`选中三角形 ${hit.faceIndex} / ${m?.panel??'—'} / λmax ${fmt(m?.max,3)}；切换二维纸样可追溯。`);$('detail').innerHTML+=`<br><strong>选中 ${hit.faceIndex} · ${escape(m?.panel??'')}</strong>`;}
  });
}
function disposeObject(object){if(!object)return;object.geometry?.dispose();object.material?.dispose();scene.remove(object);}
function clearGroup(group){for(const child of [...group.children]){child.geometry?.dispose();child.material?.dispose();group.remove(child);}}
function draw3D(){
  const container=$('three-stage'),width=Math.max(200,container.clientWidth),height=Math.max(200,container.clientHeight);
  renderer.setSize(width,height);camera.aspect=width/height;camera.updateProjectionMatrix();
  const targets={front:[0,1.12,2.3],back:[0,1.12,-2.3],left:[-2.3,1.12,0],iso:[1.42,1.4,2.15]};camera.position.set(...targets[cameraName]);camera.lookAt(0,1.08,.02);camera.updateMatrixWorld();
  disposeObject(clothObject);clothObject=null;clearGroup(pinGroup);clearGroup(collisionObject);
  const frame=current();
  if(artifact.mesh&&frame){
    const positions=[],colors=[],fold=display==='fold'?foldAngles(artifact.mesh,frame.positions):null;
    artifact.mesh.triangles.forEach((ids,t)=>{
      const metric=frame.metrics.triangles[t];let color=new THREE.Color('#73916b');
      if(display==='strain'){const s=Math.max(0,Math.min(1,(metric.max-1)/.25));color.setHSL(.30*(1-s),.42,.48+.05*(1-s));}
      if(display==='fold'){const s=Math.min(1,fold.values[t]/60);color.setHSL(.30*(1-s),.4,.48);}
      if(display==='collision'){const bad=artifact.audit?.bodySurface.allCrossingPairs?.some(p=>p[0]===t);color.set(bad?'#bb5039':'#78966f');}
      for(const i of ids){positions.push(...frame.positions.slice(i*3,i*3+3));colors.push(color.r,color.g,color.b);}
    });
    const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(positions,3));g.setAttribute('color',new THREE.Float32BufferAttribute(colors,3));g.computeVertexNormals();
    clothObject=new THREE.Mesh(g,new THREE.MeshStandardMaterial({color:'#ffffff',vertexColors:true,side:THREE.DoubleSide,roughness:.9,wireframe:$('wireframe').checked||view==='debugger'}));scene.add(clothObject);
    for(const id of artifact.pose.pins){const sphere=new THREE.Mesh(new THREE.SphereGeometry(.005,8,5),new THREE.MeshBasicMaterial({color:'#db743b'}));sphere.position.fromArray(frame.positions,id*3);pinGroup.add(sphere);}
  }
  const start=performance.now();renderer.render(scene,camera);const renderMS=performance.now()-start;
  perf({kind:'renderCPU',view,camera:cameraName,frame:frame?.step??null,renderMS,triangles:renderer.info.render.triangles,renderer:$('renderer-badge').textContent});
  $('stage-caption').textContent=artifact.source==='GOLDEN_YAML'?'MakeHuman 来源人体参考 · Golden 物理装配 BLOCKED':!frame?`${artifact.status} · 无当前求解帧`:`F${frame.step} · ${frame.mode==='INITIAL_ASSEMBLY'?'ASSUMED 初始装配':'原生 Rapier WASM'} · ${artifact.frameIndex===artifact.frames.length-1?'最新记录':'REPLAY'}`;
}
function render(){
  refreshControls();updateEvidence();
  document.querySelectorAll('[data-view]').forEach(b=>b.classList.toggle('active',b.dataset.view===view));
  $('pattern-stage').hidden=view!=='pattern';$('three-stage').hidden=view==='pattern';$('camera-controls').hidden=view==='pattern';$('timeline-controls').hidden=view!=='timeline';
  $('view-label').textContent={pattern:'PATTERN / 二维纸样',designer:'DESIGNER / 人体与样衣',physics:'PHYSICS / 当前帧诊断',debugger:'DEBUGGER / 网格与源片',timeline:'TIMELINE / 已计算帧回放'}[view];
  $('view-revision').textContent=`REV ${String(artifact.revision).padStart(2,'0')}`;
  $('legend').hidden=view==='pattern'||display==='fabric'||!current();
  $('legend').innerHTML=display==='strain'?'最大主应变 ε = λmax − 1<div class="ramp"></div>0%　　　　　　　25%+<br>无单位 · 非应力 Pa':display==='fold'?'相邻面夹角 · 几何褶皱代理<div class="ramp"></div>0°　　　　　　　　60°+<br>依赖网格精度':display==='collision'?'红色：严格面穿三角形<br>仅当前已审计帧':'';
  if(view==='pattern')drawPattern();else draw3D();
  const token=++sequence;$('capture-state').textContent=`绘制中 ${token}`;
  requestAnimationFrame(()=>requestAnimationFrame(()=>{if(token===sequence)$('capture-state').textContent=`已呈现 ${token} · ${view} · ${cameraName} · REV ${artifact.revision} · F${current()?.step??'—'}`;}));
}
async function build(){
  terminate();selectedTriangle=null;const buildJob=job,rev=artifact.revision;artifact.status='BUILDING';artifact.frames=[];artifact.audit=null;artifact.native=null;render();
  try{
    const started=performance.now(),demo=buildDemo(settings());if(buildJob!==job||rev!==artifact.revision)return;
    artifact.draft=demo.draft;artifact.mesh=demo.mesh;artifact.pose={...demo.pose,positions:Array.from(demo.pose.positions)};artifact.inputs=demo.input;artifact.settings=settings();artifact.meshRevision=rev;artifact.status='INITIALIZED';
    addFrame(artifact,{step:0,positions:Array.from(demo.pose.positions),metrics:measure(demo.mesh,demo.pose.positions),mode:'INITIAL_ASSEMBLY'},rev);
    perf({kind:'draftAndMesh',ms:performance.now()-started,particles:demo.mesh.restXY.length,triangles:demo.mesh.triangles.length});
    log(`REV ${rev}：4 裁片 / ${demo.mesh.restXY.length} 粒子 / ${demo.mesh.seams.length} 道缝。`);
    worker=new Worker(URL.createObjectURL(new Blob([__WORKER__],{type:'text/javascript'})));
    worker.onmessage=({data})=>{
      if(buildJob!==job||data.revision!==artifact.revision)return;
      if(data.type==='ready'){workerReady=true;artifact.native=data.stats;artifact.status='READY';perf({kind:'engineInit',ms:data.initMS});log('Rapier 原生约束已建立；二维 rest 保留。');}
      if(data.type==='frame'){
        if(data.positions.length!==artifact.mesh.restXY.length*3||!data.positions.every(Number.isFinite)){artifact.status='ERROR';artifact.run={error:'NONFINITE_OR_INCOMPATIBLE_FRAME',revision:rev};terminate('已拒绝非有限值或长度错误的求解帧。');render();return;}
        const m=measure(artifact.mesh,data.positions);addFrame(artifact,{step:data.step,positions:data.positions,metrics:m,mode:'LIVE_SOLVE',solverMS:data.solverMS},rev);artifact.audit=null;artifact.native=data.stats??{...artifact.native,stepCount:data.step};
        if(data.final){busy=false;clearTimeout(timeout);artifact.status='COMPLETED';artifact.native=data.stats;artifact.run={steps:data.step,dt:1/120,solverCPUms:data.solverMS,revision:rev,engine:'Rapier 0.21.0',stopReason:'REQUESTED_STEPS',garmentVerdict:m.maxSeamGapMM>2||m.invalidTriangleCount?'FAIL':'NOT_VALIDATED'};perf({kind:'solverRun',...artifact.run});log(`实际求解到 F${data.step}；${fmt(data.solverMS,1)}ms（本次求解 CPU，不含绘制）。计算完成不等于成衣通过。`);}
      }
      if(data.type==='error'){busy=false;workerReady=false;clearTimeout(timeout);artifact.status='ERROR';artifact.run={error:data.message,revision:rev};log(`引擎错误：${data.message.slice(0,240)}`);perf({kind:'solverError',error:data.message});}
      render();
    };
    worker.onerror=event=>{if(buildJob!==job)return;busy=false;workerReady=false;clearTimeout(timeout);artifact.status='ERROR';log(`Worker 错误：${event.message}`);render();};
    worker.postMessage({type:'init',revision:rev,mesh:demo.mesh,positions:Array.from(demo.pose.positions),pins:demo.pose.pins,config:demo.pose.config??{particleRadius:.005,additionalSolverIterations:0,additionalPgsIterations:1}});
    render();
  }catch(error){artifact.status='ERROR';log(error.stack??String(error));render();}
}
function run(){
  if(!workerReady||busy)return;busy=true;artifact.status='RUNNING';artifact.audit=null;
  log(`计算 REV ${artifact.revision}，当前 F${current()?.step??0}，目标 +30 步。`);worker.postMessage({type:'step',steps:Math.min(30,600-(current()?.step??0))});
  timeout=setTimeout(()=>{artifact.status='TIMEOUT';artifact.run={stopReason:'30_SECOND_WALL_LIMIT',lastCompletedStep:current()?.step??0};terminate('计算超过 30 秒，已停止 Worker；保留实际完成帧。');render();},30000);render();
}
async function audit(){
  if(!current()||busy||auditBusy)return;const target=artifact,frame=current(),mesh=artifact.mesh,rev=artifact.revision,step=frame.step,token=++auditJob,runJob=job; auditBusy=true;log(`检查 REV ${rev} / F${step} 的顶点、人体面穿与自交。`);refreshControls();
  await new Promise(r=>setTimeout(r,40));
  try{if(token!==auditJob||target!==artifact||rev!==artifact.revision||frame!==current()||runJob!==job)return;const t=performance.now(),result=auditSurfaceCollisions({cloth:{positions:frame.positions,triangles:mesh.triangles.flat()},body:human,bodyCollider,seams:mesh.seams.flatMap(s=>s.pairs),maxExamples:12});
    if(token!==auditJob||target!==artifact||rev!==artifact.revision||frame!==current()||runJob!==job)return;artifact.audit=result;artifact.auditStep=step;artifact.auditRevision=rev;perf({kind:'surfaceAudit',step,ms:performance.now()-t,workCounts:result.workCounts});
    log(`F${step}：内部 ${result.vertexInside.count} / 人体面穿 ${result.bodySurface.strictCrossingPairs} / 自交 ${result.selfSurface.strictCrossingPairs}。`);display='collision';$('display').value=display;view='physics';
  }catch(error){log(`审计错误：${error.message}`);}finally{if(token===auditJob){auditBusy=false;render();}}
}
function download(name,content,type){const link=document.createElement('a'),url=URL.createObjectURL(new Blob([content],{type}));link.href=url;link.download=name;link.click();setTimeout(()=>URL.revokeObjectURL(url),2000);log(`已导出 ${name}`);}
function exportJSON(){const data={...liveExport(artifact),buildSourceSha256:__BUILD_ID__,performance:performanceEntries.filter(e=>e.instanceId===artifact.instanceId),logs:logEntries.filter(e=>e.instanceId===artifact.instanceId),canonicalSha256:GOLDEN_SHA,bodySource:human.source,bodyMeshIdentity:{positions:human.positions,triangles:human.triangles,transform:'identity in metres'}};download(`garment-${artifact.source.toLowerCase()}-r${artifact.revision}.json`,JSON.stringify(data), 'application/json');}
function pdf(){
  if(!artifact.draft||artifact.source!=='ENGINE_CONFORMANCE')return;
  let x=15,maxH=0;const layout=artifact.draft.panels.map(p=>{const xs=p.outlineMM.map(q=>q[0]),ys=p.outlineMM.map(q=>q[1]),minX=Math.min(...xs),minY=Math.min(...ys),w=Math.max(...xs)-minX,h=Math.max(...ys)-minY;const item={p,x:x-minX,y:30-minY};x+=w+25;maxH=Math.max(maxH,h);return item;});
  const doc=new jsPDF({orientation:'landscape',unit:'mm',format:[x,maxH+65],compress:true});doc.setFontSize(10);doc.text('ENGINE_CONFORMANCE / NET SEAMLINES / NO SEAM ALLOWANCE / mm / 100% print scale',15,15);
  for(const {p,x,y}of layout){doc.setDrawColor(45,75,49);doc.setLineWidth(.25);const pts=p.outlineMM.map(q=>[q[0]+x,q[1]+y]);for(let i=0;i<pts.length;i++){const a=pts[i],b=pts[(i+1)%pts.length];doc.line(...a,...b);}doc.text(p.id,x+p.outlineMM[0][0],maxH+44);}
  doc.setDrawColor(0);doc.line(15,maxH+55,115,maxH+55);doc.text('100 mm',15,maxH+52);download('teagan-engine-net-pattern-1to1.pdf',doc.output('arraybuffer'),'application/pdf');
}
function inputChanged(){
  $('waist-output').textContent=`${$('waist').value} mm`;$('sleeve-output').textContent=`${$('sleeve').value}%`;$('neck-output').textContent=`${$('neck').value}%`;
  terminate();invalidate(artifact,'PARAMETER_EDIT');artifact.settings=settings();log(`REV ${artifact.revision}：输入已修改，网格与全部物理结果 STALE。`);render();
}
$('source').addEventListener('change',()=>{terminate();artifact=newArtifact($('source').value);view='pattern';log(`切换来源：${artifact.source}。结果不跨来源继承。`);render();if(artifact.source==='ENGINE_CONFORMANCE')build();});
for(const id of ['waist','sleeve','neck','spacing','profile'])$(id).addEventListener('input',inputChanged);
document.querySelectorAll('[data-view]').forEach(b=>b.addEventListener('click',()=>{view=b.dataset.view;if(view==='physics'&&display==='fabric'){$('display').value=display='strain';}render();}));
document.querySelectorAll('[data-camera]').forEach(b=>b.addEventListener('click',()=>{cameraName=b.dataset.camera;document.querySelectorAll('[data-camera]').forEach(c=>c.classList.toggle('selected',c===b));render();}));
$('display').addEventListener('change',()=>{display=$('display').value;render();});$('wireframe').addEventListener('change',render);
$('timeline').addEventListener('input',()=>{artifact.frameIndex=Number($('timeline').value);artifact.audit=null;render();});
$('build').addEventListener('click',build);$('run').addEventListener('click',run);$('audit').addEventListener('click',audit);
$('stop').addEventListener('click',()=>{artifact.status='CANCELLED';artifact.run={stopReason:'USER_CANCELLED',lastCompletedStep:current()?.step??0};terminate('已停止；重新生成可建立新求解器。');render();});
$('export-json').addEventListener('click',exportJSON);$('export-svg').addEventListener('click',()=>download(artifact.source==='GOLDEN_YAML'?'golden-pattern-U.svg':'teagan-pattern-mm.svg',artifact.source==='GOLDEN_YAML'?goldenDrawing(golden).svg:artifact.draft?.svg??'','image/svg+xml'));$('export-pdf').addEventListener('click',pdf);
$('export-yaml').addEventListener('click',()=>download('golden-garment-1.1.yaml',__GOLDEN_YAML__,'application/yaml'));
$('import-json').addEventListener('click',()=>$('file-input').click());$('file-input').addEventListener('change',async()=>{
  try{const data=JSON.parse(await $('file-input').files[0].text());if(data.schema!=='garment-artifact-engine-lab-1')throw Error('不是本工作台的工程文件');
    if(!['GOLDEN_YAML','ENGINE_CONFORMANCE'].includes(data.source))throw Error('未知数据来源');
    if(data.source==='GOLDEN_YAML'&&data.sourceSha!==GOLDEN_SHA)throw Error('Golden 来源哈希不匹配');
    if(data.source==='ENGINE_CONFORMANCE'&&!validSettings(data.settings))throw Error('引擎工程需要完整有效且符合控件步长的 settings；未修改当前工程');
    terminate();artifact=newArtifact(data.source);$('source').value=data.source;
    if(data.source==='ENGINE_CONFORMANCE'){
      const s=data.settings;for(const [id,key,factor]of [['waist','waistDeltaMM',1],['sleeve','sleeveLength',100],['neck','necklineDepth',100],['spacing','spacingMM',1]])$(id).value=s[key]*factor;$('profile').value=s.profile;
      artifact.revision=Number.isInteger(data.revision)?Math.max(1,data.revision):1;view='pattern';await build();log('已载入输入并重新生成；未信任外部文件的旧 PASS 或物理帧。');
    }else{view='pattern';render();log('已载入 Golden 来源；U 标定状态仍未确认。');}
  }catch(error){log(`载入拒绝：${error.message}`);} });
$('help-button').addEventListener('click',()=>$('help').showModal());$('close-help').addEventListener('click',()=>$('help').close());
$('source-links').innerHTML=[['Rapier soft bodies','https://rapier.rs/docs/user_guides/javascript/soft_bodies/'],['FreeSewing','https://freesewing.dev/'],['MakeHuman 原始人体与许可','https://static.makehumancommunity.org/about/license.html'],['GarmentCode / Python 参考路线','https://github.com/maria-korosteleva/GarmentCode']].map(([t,u])=>`<a href="${u}" target="_blank" rel="noreferrer">${t}</a>`).join('<br>');
$('licenses').textContent=__LICENSES__;
initScene();log('原始 Golden YAML 已载入；未填补空值。');render();
new ResizeObserver(()=>{if(view!=='pattern')render();}).observe($('stage'));
