import * as T from '../../human-studio/vendor/three.module.js';

const $ = id => document.getElementById(id);
const payload = JSON.parse($('payload').textContent);
const originalHTML = '<!doctype html>\n'+document.documentElement.outerHTML;
const decode = b64 => Uint8Array.from(atob(b64), c => c.charCodeAt(0));
const materials = {
  woven: {Eu:200000, Ev:120000, G:30000, nu:.2, thickness:.0005, density:.22},
  soft: {Eu:45000, Ev:25000, G:6000, nu:.2, thickness:.0005, density:.18}
};
const N=16, M=24, K=(N+1)*(M+1), NV=2*K, NT=4*N*M;
const idx=(p,i,j)=>p*K+j*(N+1)+i;
let wasm,positions,previous,restUV,triangles,fields,invMass,bodyDistances;
let scene,camera,renderer,cloth,clothGeometry,bodyMesh,seamLines,texture;
let cameraAngle=.36,cameraElevation=.1,cameraDistance=2.8,drag=null;
let seamMap=[],parameters,mode='fabric',running=false,busy=false,stepMs=0;
let frameTimes=[],history=[],lastStats={},lastDraw=0,droppedSeconds=0,accumulator=0,lastAnalyze=0;
let gpuString='',rendererClass='unknown',allocationBaseline;

function getParameters(){return {bottomMm:+$('width').value,topMm:420,lengthsMm:[+$('length').value,+$('length').value+($('fault').value==='mismatch'?40:0)],fault:$('fault').value,material:$('material').value,bodyOffsetMm:+$('body-shift').value,collision:$('collision').checked,wind:$('wind').checked};}
function material(){return materials[parameters.material];}
function copyTo(ptr,bytes){new Uint8Array(wasm.memory.buffer,ptr,bytes.length).set(bytes);}
function floatView(ptr,n){return new Float32Array(wasm.memory.buffer,ptr,n);}
function intView(ptr,n){return new Int32Array(wasm.memory.buffer,ptr,n);}
function updateCamera(){camera.position.set(Math.sin(cameraAngle)*cameraDistance,.8+cameraElevation*cameraDistance,Math.cos(cameraAngle)*cameraDistance+.055);camera.lookAt(0,.8,.055);}
function setRunning(value){running=value;$('run').textContent=running?'暂停仿真':'开始仿真';accumulator=0;}
function download(name,text,type='application/json'){const url=URL.createObjectURL(new Blob([text],{type})),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
function sideLength(p){return Math.hypot(parameters.lengthsMm[p],(parameters.bottomMm-parameters.topMm)/2);}
function topologyAudit(){
  let missing=false,orientationValid=true;
  for(const name of ['S1','S2']){
    const pairs=seamMap.filter(s=>s.name===name),row=k=>Math.floor((k%K)/(N+1));
    missing ||= pairs.filter(s=>s.active).length!==M+1;
    orientationValid &&= pairs.slice(1).every((s,i)=>(row(s.a)-row(pairs[i].a))*(row(s.b)-row(pairs[i].b))>0);
  }
  return {missingSeam:missing,orientationValid,lengthMismatchMm:Math.abs(sideLength(0)-sideLength(1))};
}
function setupScene(){
  scene=new T.Scene();camera=new T.PerspectiveCamera(35,1,.01,20);
  renderer=new T.WebGLRenderer({antialias:true,alpha:true,preserveDrawingBuffer:true});
  const gl=renderer.getContext(),ext=gl.getExtension('WEBGL_debug_renderer_info');
  gpuString=String(ext?gl.getParameter(ext.UNMASKED_RENDERER_WEBGL):gl.getParameter(gl.RENDERER));
  rendererClass=/swiftshader|llvmpipe|software/i.test(gpuString)?'software':'hardware-or-unknown';
  renderer.setPixelRatio(rendererClass==='software'?.8:Math.min(devicePixelRatio,1.5));
  renderer.outputColorSpace=T.SRGBColorSpace;renderer.setClearColor(0xe9ece0,0);
  $('viewport').appendChild(renderer.domElement);scene.add(new T.HemisphereLight(0xfff9e8,0x7c8d7b,2.2));
  const key=new T.DirectionalLight(0xfff8e4,2.5);key.position.set(2,3,3);scene.add(key);
  const rim=new T.DirectionalLight(0xc4e0e0,1.4);rim.position.set(-2,1,-2);scene.add(rim);
  const bodyPos=new Float32Array(decode(payload.body.positions).buffer),bodyFaces=new Int32Array(decode(payload.body.indices).buffer);
  const geom=new T.BufferGeometry();geom.setAttribute('position',new T.Float32BufferAttribute(bodyPos,3));geom.setIndex(Array.from(bodyFaces));geom.computeVertexNormals();
  const colors=new Float32Array(bodyPos.length),color=new T.Color();
  for(let i=0;i<bodyPos.length/3;i++){color.set(bodyPos[3*i+1]>1.02&&bodyPos[3*i+1]<1.32?0x53675d:0xc6c6b9);color.toArray(colors,3*i);}
  geom.setAttribute('color',new T.Float32BufferAttribute(colors,3));
  bodyMesh=new T.Mesh(geom,new T.MeshStandardMaterial({vertexColors:true,roughness:.93}));scene.add(bodyMesh);
  const floor=new T.Mesh(new T.CircleGeometry(.68,64),new T.MeshStandardMaterial({color:0xd8ddce,roughness:1}));floor.rotation.x=-Math.PI/2;floor.position.y=-.005;scene.add(floor);
  const grid=new T.GridHelper(1.5,15,0xa5b59f,0xd2dacb);grid.position.y=-.003;scene.add(grid);
  const canvas=document.createElement('canvas');canvas.width=canvas.height=128;const ctx=canvas.getContext('2d');ctx.fillStyle='#ac715b';ctx.fillRect(0,0,128,128);
  for(let i=0;i<128;i+=4){ctx.fillStyle=i%8?'#b78066':'#a66b56';ctx.fillRect(i,0,1,128);ctx.fillStyle='#c18a70';ctx.fillRect(0,i,128,1);}
  texture=new T.CanvasTexture(canvas);texture.wrapS=texture.wrapT=T.RepeatWrapping;texture.repeat.set(8,8);texture.colorSpace=T.SRGBColorSpace;
  updateCamera();new ResizeObserver(()=>{const r=$('viewport').getBoundingClientRect();renderer.setSize(r.width,r.height);camera.aspect=r.width/r.height;camera.updateProjectionMatrix();draw();}).observe($('viewport'));
  const target=renderer.domElement;target.addEventListener('pointerdown',e=>{drag=[e.clientX,e.clientY];target.setPointerCapture(e.pointerId);});target.addEventListener('pointerup',()=>drag=null);target.addEventListener('pointermove',e=>{if(!drag)return;cameraAngle-=(e.clientX-drag[0])*.008;cameraElevation=Math.max(-.12,Math.min(.6,cameraElevation+(e.clientY-drag[1])*.003));drag=[e.clientX,e.clientY];updateCamera();draw();});target.addEventListener('wheel',e=>{e.preventDefault();cameraDistance=Math.max(1.65,Math.min(4.5,cameraDistance+e.deltaY*.002));updateCamera();draw();},{passive:false});
  $('asset-info').textContent=`MakeHuman 成人女性 · ${(payload.body.heightMeters*100).toFixed(1)} cm · ${payload.body.triangles.toLocaleString()} 个人体三角形 · CC0`;
  $('renderer-info').textContent=`实际渲染器：${gpuString}。${rendererClass==='software'?'软件渲染性能不代表真实 GPU。':''}人体深色区域仅为显示用颜色。`;
}
// Uniform arc-length samples on a fixed ellipse, scaled to the pattern waist.
function waistRing(){const pts=[],cumulative=[0];for(let j=0;j<=2048;j++){const a=2*Math.PI*j/2048;pts.push([.158*Math.cos(a),.108*Math.sin(a)]);if(j)cumulative.push(cumulative[j-1]+Math.hypot(pts[j][0]-pts[j-1][0],pts[j][1]-pts[j-1][1]));}const total=cumulative.at(-1),scale=parameters.topMm*2/1000/total,result=[];let k=0;for(let i=0;i<=2*N;i++){const d=i/(2*N)*total;while(k<2047&&cumulative[k+1]<d)k++;const t=(d-cumulative[k])/(cumulative[k+1]-cumulative[k]||1);result.push([(pts[k][0]*(1-t)+pts[k+1][0]*t)*scale,(pts[k][1]*(1-t)+pts[k+1][1]*t)*scale]);}return result;}
function setupCloth(){
  parameters=getParameters();setRunning(false);history=[];droppedSeconds=0;
  const mat=material();wasm.configure_material(mat.Eu,mat.Ev,mat.G,mat.nu,mat.thickness,mat.density);
  positions=floatView(wasm.position_ptr(),NV*3);previous=floatView(wasm.previous_ptr(),NV*3);restUV=floatView(wasm.uv_ptr(),NV*2);triangles=intView(wasm.face_ptr(),NT*3);fields=floatView(wasm.field_ptr(),NT*8);invMass=floatView(wasm.invmass_ptr(),NV);bodyDistances=floatView(wasm.body_distance_ptr(),NV);
  const ring=waistRing();let faceIndex=0;
  for(let p=0;p<2;p++)for(let j=0;j<=M;j++)for(let i=0;i<=N;i++){
    const k=idx(p,i,j),ratio=j/M,w=parameters.topMm+(parameters.bottomMm-parameters.topMm)*ratio,flaring=w/parameters.topMm;
    positions.set([ring[p*N+i][0]*flaring,1-ratio*parameters.lengthsMm[p]/1000,.06+ring[p*N+i][1]*flaring],3*k);
    // Material U follows the vertical grain arrow; V is across the panel.
    restUV.set([ratio*parameters.lengthsMm[p]/1000,(i/N-.5)*w/1000],2*k);
    if(i<N&&j<M){const a=k,b=k+1,c=k+N+1,d=c+1;triangles.set([a,b,c,b,d,c],faceIndex);faceIndex+=6;}
  }
  wasm.configure_cloth(NV,NT);for(let p=0;p<2;p++)for(let i=0;i<=N;i++)wasm.set_pin(idx(p,i,0));
  seamMap=[];for(let j=0;j<=M;j++){
    seamMap.push({name:'S1',a:idx(0,N,j),b:idx(1,0,j),active:true});
    seamMap.push({name:'S2',a:idx(0,0,j),b:idx(1,N,parameters.fault==='reverse'?M-j:j),active:parameters.fault!=='open'});
  }
  for(const s of seamMap)wasm.add_seam(s.a,s.b,+s.active);wasm.finalize_seams();
  for(let p=0;p<2;p++)for(let j=0;j<=M;j++)for(let i=0;i<=N;i++){
    const k=idx(p,i,j);for(const end of [i<N-1?idx(p,i+2,j):-1,j<M-1?idx(p,i,j+2):-1])if(end>=0){const d=Math.hypot(restUV[2*k]-restUV[2*end],restUV[2*k+1]-restUV[2*end+1]);wasm.add_bend(k,end,d);}
  }
  wasm.set_collision(+parameters.collision);wasm.set_body_offset(parameters.bodyOffsetMm/1000);bodyMesh.position.x=parameters.bodyOffsetMm/1000;
  if(cloth){scene.remove(cloth,seamLines);clothGeometry.dispose();cloth.material.dispose();seamLines.geometry.dispose();seamLines.material.dispose();}
  clothGeometry=new T.BufferGeometry();clothGeometry.setAttribute('position',new T.Float32BufferAttribute(positions,3));clothGeometry.setIndex(Array.from(triangles));clothGeometry.setAttribute('uv',new T.Float32BufferAttribute(Array.from({length:NV*2},(_,i)=>i%2?restUV[i]/.6:restUV[i]/.65),2));clothGeometry.setAttribute('color',new T.Float32BufferAttribute(new Float32Array(NV*3).fill(1),3));clothGeometry.computeVertexNormals();
  cloth=new T.Mesh(clothGeometry,new T.MeshStandardMaterial({map:texture,roughness:.93,side:T.DoubleSide}));scene.add(cloth);
  const lineGeom=new T.BufferGeometry();lineGeom.setAttribute('position',new T.Float32BufferAttribute(new Float32Array(M*2*2*3),3));lineGeom.setAttribute('color',new T.Float32BufferAttribute(new Float32Array(M*2*2*3),3));seamLines=new T.LineSegments(lineGeom,new T.LineBasicMaterial({vertexColors:true,depthTest:false}));seamLines.renderOrder=2;scene.add(seamLines);
  $('width-value').value=parameters.bottomMm+' mm';$('length-value').value=parameters.lengthsMm[0]+' mm';$('shift-value').value=parameters.bodyOffsetMm+' mm';
  $('material-values').textContent=`E经 ${mat.Eu/1000} kPa · E纬 ${mat.Ev/1000} kPa · G ${mat.G/1000} kPa · ν ${mat.nu}\n厚 ${mat.thickness*1000} mm · ${mat.density*1000} g/m²。合成参数，未经标定。`;
  $('patterns').innerHTML=patternSVG();$('activity').textContent='就绪。可单步观察，或运行 2 秒。';applyMode(mode);analyze();draw();
}
function patternSVG(){const {topMm:top,bottomMm:bottom,lengthsMm:lengths}=parameters,W=bottom*2+120,H=Math.max(...lengths)+105;
  const groups=lengths.map((L,p)=>{const slope=(bottom-top)/2/L,off=10*Math.sqrt(1+slope*slope),tx=bottom/2+25+p*(bottom+55),points=[[-top/2+slope*10-off,-10],[top/2-slope*10+off,-10],[bottom/2+slope*10+off,L+10],[-bottom/2-slope*10-off,L+10]].map(a=>a.join(',')).join(' ');return `<g transform="translate(${tx},25)"><polygon points="${points}" fill="#e7ebdf" stroke="#425e4b" stroke-width="1"/><path d="M ${-top/2} 0 H ${top/2} L ${bottom/2} ${L} H ${-bottom/2} Z" fill="none" stroke="#738677" stroke-dasharray="7 5"/><text x="0" y="40" text-anchor="middle" font-size="17">${p?'B 后片':'A 前片'} · CUT 1</text><text x="0" y="66" text-anchor="middle" font-size="14">${top} / ${bottom} × ${L} mm</text><path d="M 0 120 v ${L-240} m -8 -14 l 8 14 8 -14" stroke="#425e4b" fill="none" stroke-width="2"/><path d="M ${-(top+bottom)/4-10} ${L/2} h 17 M ${(top+bottom)/4-7} ${L/2} h 17" stroke="#a36249" stroke-width="2"/></g>`;}).join('');return `<svg xmlns="http://www.w3.org/2000/svg" width="${W}mm" height="${H}mm" viewBox="0 0 ${W} ${H}"><rect width="100%" height="100%" fill="#fffdf6"/>${groups}<path d="M 20 ${H-28} h 100 m -100 -5 v 10 m 100 -10 v 10" stroke="#263d37"/><text x="135" y="${H-23}" font-size="14">100 mm · 缝份 10 mm · 测试纸样 / 无腰头开合结构</text></svg>`;}
function analyze(){wasm.analyze();const s=floatView(wasm.stats_ptr(),16),topo=topologyAudit();lastStats={frame:s[0],simulationSeconds:s[1],maxSeamGapMm:s[2]*1000,maxBodyPenetrationMm:s[3]*1000,minBodyClearanceMm:s[4]*1000,maxPrincipalStrainPercent:s[5]*100,maxPrincipalStressKPa:s[6]/1000,contacts:s[7],finite:!!s[8]&&positions.every(Number.isFinite),membraneEnergyJ:s[9],collisionEnabled:!!s[10],...topo,stepMs,bodyOffsetMm:parameters.bodyOffsetMm,droppedWallSeconds:droppedSeconds};
  const fail=!lastStats.finite||topo.missingSeam||!topo.orientationValid||topo.lengthMismatchMm>1||lastStats.maxSeamGapMm>2||lastStats.maxBodyPenetrationMm>.2;
  const settled=s[0]>=240;let text=fail?'FAIL · 缝合或碰撞检查未通过':!parameters.collision?'未验证 · 已关闭碰撞':settled?'PASS · 当前数值检查':'待验证 · 请推进至少 2 秒';
  const strainWarning=!fail&&settled&&lastStats.maxPrincipalStrainPercent>20;if(strainWarning)text='几何通过 · 局部应变偏大';
  $('verdict').textContent=text;$('verdict').className=fail?'fail':!settled||!parameters.collision||strainWarning?'pending':'';
  const rows=[['缝合长度差',topo.lengthMismatchMm.toFixed(2)+' mm'],['方向 / 缺失',`${topo.orientationValid?'同向':'反向'} / ${topo.missingSeam?'漏缝':'完整'}`],['最大接缝间隙',lastStats.maxSeamGapMm.toFixed(3)+' mm'],['人体网格穿透',lastStats.maxBodyPenetrationMm.toFixed(3)+' mm'],['最小人体距离',lastStats.minBodyClearanceMm.toFixed(2)+' mm'],['最大主应变',lastStats.maxPrincipalStrainPercent.toFixed(2)+' %'],['最大主柯西应力',lastStats.maxPrincipalStressKPa.toFixed(2)+' kPa'],['接触点 / 总顶点',`${s[7]} / ${NV}`]];
  $('metrics').innerHTML=rows.map(([a,b])=>`<div><dt>${a}</dt><dd>${b}</dd></div>`).join('');$('time').textContent=s[1].toFixed(2)+' s';$('solver-time').textContent=stepMs.toFixed(2)+' ms';
  if(history.at(-1)?.frame!==lastStats.frame){history.push({...lastStats});if(history.length>120)history.shift();}
  return {...lastStats};
}
function applyMode(value){mode=value;if(!cloth)return;cloth.material.map=mode==='fabric'?texture:null;cloth.material.vertexColors=mode!=='fabric';cloth.material.needsUpdate=true;for(const b of document.querySelectorAll('[data-mode]'))b.setAttribute('aria-pressed',String(b.dataset.mode===mode));
  const desc={fabric:['程序化织纹','无外部贴图','织纹只影响外观。物理计算在 WASM 中进行。'],strain:['0 %','≥ 12 %','工程最大主应变：√λmax(FᵀF) − 1；未变形为 0%。'],stress:['0 kPa','≥ 15 kPa','最大主柯西应力；正交各向异性 StVK，合成材料参数。非接触压力。'],contact:['≤ 0 mm','≥ 15 mm','相对实际人体三角网格的有符号最近距离。红色为穿透或接触，蓝色为有间隙。']}[mode];$('legend-min').textContent=desc[0];$('legend-max').textContent=desc[1];$('map-definition').textContent=desc[2];updateSurface();draw();
}
function updateSurface(){if(!cloth)return;clothGeometry.attributes.position.array.set(positions);clothGeometry.attributes.position.needsUpdate=true;clothGeometry.computeVertexNormals();
  const scalar=new Float32Array(NV),counts=new Uint16Array(NV);if(mode==='strain'||mode==='stress'){const c=mode==='strain'?0:3;for(let t=0;t<NT;t++)for(let j=0;j<3;j++){const v=triangles[t*3+j];scalar[v]+=fields[t*8+c];counts[v]++;}for(let i=0;i<NV;i++)scalar[i]/=counts[i]||1;}
  const colors=clothGeometry.attributes.color.array,color=new T.Color();for(let i=0;i<NV;i++){let a=mode==='strain'?scalar[i]/.12:mode==='stress'?scalar[i]/15000:mode==='contact'?1-bodyDistances[i]/.015:0;a=Math.max(0,Math.min(1,a));color.setHSL(.61*(1-a),.64,.54);color.toArray(colors,3*i);}clothGeometry.attributes.color.needsUpdate=true;
  const lp=seamLines.geometry.attributes.position.array,lc=seamLines.geometry.attributes.color.array;let n=0;const okay=lastStats.orientationValid&&!lastStats.missingSeam&&lastStats.lengthMismatchMm<1;
  for(const name of ['S1','S2']){const pairs=seamMap.filter(s=>s.name===name);for(let j=0;j<M;j++){for(const s of [pairs[j],pairs[j+1]]){lp.set(positions.subarray(s.a*3,s.a*3+3),n);lc.set(okay?[.74,.88,.38]:[.83,.2,.15],n);n+=3;}}}
  seamLines.geometry.attributes.position.needsUpdate=true;seamLines.geometry.attributes.color.needsUpdate=true;seamLines.geometry.computeBoundingSphere();clothGeometry.computeBoundingSphere();
}
function draw(){if(!renderer||!cloth)return;updateSurface();renderer.render(scene,camera);}
function takeSteps(n){const t=performance.now();wasm.step(n,parameters.wind?.8:0);stepMs=(performance.now()-t)/Math.max(n,1);}
async function advance(n){if(busy)throw new Error('A simulation operation is already running');setRunning(false);busy=true;$('activity').textContent='正在推进固定时间步…';try{for(let k=0;k<n;k+=20){takeSteps(Math.min(20,n-k));await new Promise(requestAnimationFrame);}analyze();draw();$('activity').textContent=`已完成 ${n} 步；检查结果见右侧。`;return {...lastStats};}finally{busy=false;}}
function project(){analyze();return {schema:'pattern-agent.cloth-lab.v1',fingerprint:payload.buildFingerprint,units:{pattern:'mm',geometry:'m',stress:'Pa'},parameters:{...parameters},material:{...material(),calibration:'synthetic-not-measured'},grid:[N,M],positions:Array.from(positions),previous:Array.from(previous),pinPositions:Array.from(floatView(wasm.pin_ptr(),NV*3)),restUV:Array.from(restUV),triangles:Array.from(triangles),seams:seamMap,triangleFields:Array.from(fields),fieldOrder:['principalEngineeringStrain','warpEngineeringStrain','weftEngineeringStrain','maxPrincipalCauchyPa','vonMisesPa','GreenE11','GreenE22','GreenE12'],body:{positions:Array.from(floatView(wasm.body_ptr(),payload.body.vertices*3)),triangles:Array.from(intView(wasm.body_face_ptr(),payload.body.triangles*3)),offsetX:parameters.bodyOffsetMm/1000,sourceSha256:payload.body.sourceSha256,license:'CC0-1.0'},mode,diagnostics:{...lastStats},limitations:['synthetic material','rigid body','no cloth self collision','no CCD','approximate distance bending','not manufacturing approval']};}
function restore(data){if(data.schema!=='pattern-agent.cloth-lab.v1'||data.fingerprint!==payload.buildFingerprint)throw new Error('Incompatible project or source fingerprint');for(const key of ['positions','previous','pinPositions'])if(data[key]?.length!==NV*3||!data[key].every(v=>Number.isFinite(v)&&Math.abs(v)<10))throw new Error('Invalid saved vertex array');const p=data.parameters;$('width').value=p.bottomMm;$('length').value=p.lengthsMm[0];$('fault').value=p.fault;$('material').value=p.material;$('collision').checked=p.collision;$('wind').checked=p.wind;$('body-shift').value=p.bodyOffsetMm;setupCloth();positions.set(data.positions);previous.set(data.previous);floatView(wasm.pin_ptr(),NV*3).set(data.pinPositions);wasm.set_clock(data.diagnostics.frame,data.diagnostics.simulationSeconds);applyMode(data.mode||'fabric');analyze();draw();}
function sceneOBJ(){const lines=['# Pattern Agent scene snapshot; units metres. Surface meshes, not 3D-print solids.','o cloth'];for(let i=0;i<NV;i++)lines.push(`v ${positions[3*i]} ${positions[3*i+1]} ${positions[3*i+2]}`);for(let t=0;t<NT;t++)lines.push('f '+[0,1,2].map(j=>triangles[t*3+j]+1).join(' '));lines.push('o MakeHuman_CC0');const bv=floatView(wasm.body_ptr(),payload.body.vertices*3),bf=intView(wasm.body_face_ptr(),payload.body.triangles*3);for(let i=0;i<payload.body.vertices;i++)lines.push(`v ${bv[3*i]+parameters.bodyOffsetMm/1000} ${bv[3*i+1]} ${bv[3*i+2]}`);for(let t=0;t<payload.body.triangles;t++)lines.push('f '+[0,1,2].map(j=>bf[3*t+j]+NV+1).join(' '));return lines.join('\n');}
function performanceLog(){return {stats:{...lastStats},frameTimesMs:[...frameTimes],history:[...history],renderer:gpuString,rendererClass,pixelRatio:renderer.getPixelRatio(),drawCalls:renderer.info.render.calls,geometries:renderer.info.memory.geometries,textures:renderer.info.memory.textures,wasmBytes:decode(payload.wasm).length,wasmMemoryBytes:wasm.memory.buffer.byteLength,fingerprint:payload.buildFingerprint,droppedWallSeconds:droppedSeconds};}
function wireUI(){for(const id of ['width','length','material','fault'])$(id).addEventListener('input',()=>{if(!busy)setupCloth();});$('body-shift').addEventListener('input',()=>{parameters.bodyOffsetMm=+$('body-shift').value;$('shift-value').value=parameters.bodyOffsetMm+' mm';wasm.set_body_offset(parameters.bodyOffsetMm/1000);bodyMesh.position.x=parameters.bodyOffsetMm/1000;analyze();draw();});$('collision').onchange=()=>{parameters.collision=$('collision').checked;wasm.set_collision(+parameters.collision);analyze();};$('wind').onchange=()=>parameters.wind=$('wind').checked;$('run').onclick=()=>{if(!busy)setRunning(!running);};$('single-step').onclick=()=>advance(1);$('settle').onclick=()=>advance(240);$('reset').onclick=()=>{if(!busy)setupCloth();};
  for(const b of document.querySelectorAll('[data-mode]'))b.onclick=()=>applyMode(b.dataset.mode);for(const b of document.querySelectorAll('[data-camera]'))b.onclick=()=>{cameraAngle={front:0,side:Math.PI/2,back:Math.PI}[b.dataset.camera];updateCamera();draw();};$('export-svg').onclick=()=>download('cloth-patterns.svg',patternSVG(),'image/svg+xml');$('export-obj').onclick=()=>download('cloth-body-scene.obj',sceneOBJ(),'text/plain');$('export-json').onclick=()=>download('cloth-project.json',JSON.stringify(project()));$('export-log').onclick=()=>download('cloth-diagnostics.json',JSON.stringify(performanceLog(),null,2));$('save-html')?.remove();const button=document.createElement('button');button.id='save-html';button.textContent='当前状态单文件 HTML ↓';button.style.gridColumn='1 / -1';button.onclick=()=>{const html=originalHTML.replace(/<script id="initial-state" type="application\/json">[\s\S]*?<\/script>/,()=>`<script id="initial-state" type="application/json">${JSON.stringify(project()).replaceAll('<','\\u003c')}</script>`);download('cloth-lab-snapshot.html',html,'text/html');};document.querySelector('.export-grid').appendChild(button);
}
function animate(now){const elapsed=lastDraw?(now-lastDraw)/1000:0;lastDraw=now;if(running&&!busy){frameTimes.push(elapsed*1000);if(frameTimes.length>600)frameTimes.shift();const use=Math.min(elapsed,.05);droppedSeconds+=Math.max(0,elapsed-use);accumulator+=use;let steps=Math.min(6,Math.floor(accumulator*120));if(steps){takeSteps(steps);accumulator-=steps/120;}if(now-lastAnalyze>150){analyze();lastAnalyze=now;const samples=frameTimes.slice(-90),avg=samples.reduce((a,b)=>a+b,0)/(samples.length||1);$('fps').textContent=`${(1000/avg).toFixed(1)} / ${avg.toFixed(0)} ms`;}draw();}requestAnimationFrame(animate);}

async function boot(){
  const result=await WebAssembly.instantiate(decode(payload.wasm),{});wasm=result.instance.exports;
  for(const [key,method] of [['positions','body_ptr'],['normals','body_normal_ptr'],['indices','body_face_ptr'],['order','body_order_ptr'],['nodes','body_node_ptr']])copyTo(wasm[method](),decode(payload.body[key]));
  wasm.configure_body(payload.body.vertices,payload.body.triangles,payload.body.nodeCount);setupScene();setupCloth();wireUI();
  const saved=JSON.parse($('initial-state').textContent);if(saved)restore(saved);
  document.querySelector('.chip')?.remove();const badge=document.createElement('span');badge.className='chip';badge.textContent='WASM 已加载 · 离线可运行';document.querySelector('.header-right').prepend(badge);
  window.clothLab={ready:true,advance,setCollisionCache:enabled=>wasm.set_cache(+enabled),stats:()=>analyze(),project,restore,performanceLog,patternSVG,setRunning,setMode:applyMode,reset:setupCloth,
    clearPerformance:()=>{frameTimes=[];history=[];droppedSeconds=0;},
    materialProbe:(u,v)=>{wasm.material_probe(...u,...v);return Array.from(floatView(wasm.probe_ptr(),8));},
    collisionProbe:p=>{wasm.collision_probe(...p);return Array.from(floatView(wasm.probe_ptr(),7));},
    injectVertex:(index,point)=>{wasm.inject_vertex(index,...point);analyze();draw();return {...lastStats};},
    surface:()=>({mode,colors:Array.from(clothGeometry.attributes.color.array),positions:Array.from(clothGeometry.attributes.position.array)}),
    source:{fingerprint:payload.buildFingerprint,wasmSha256:payload.wasmSha256,bodySourceSha256:payload.body.sourceSha256},
    allocationBaseline:()=>allocationBaseline};
  allocationBaseline=performanceLog();requestAnimationFrame(animate);
}
boot().catch(error=>{window.clothLabError=String(error);$('verdict').textContent='BLOCKED · 初始化失败';$('verdict').className='fail';$('activity').textContent=String(error);const p=document.createElement('p');p.className='fatal';p.textContent=String(error);$('viewport').appendChild(p);console.error(error);});
