import * as T from '../../human-studio/vendor/three.webgpu.js';
import {WebGLRenderer} from '../../human-studio/vendor/three.module.js';

// Both pinned renderer builds import the same three.core.js. Scene objects and
// the exported physics arrays therefore retain one identity on either backend.
export function createRendering(S,{floatView,onAvailabilityChange=()=>{}}){
  const {$,payload,decode,NV,NT,M}=S;
  const requested=new URLSearchParams(location.search).get('renderer')||'auto';
  let adapter=null,firstRenderComplete=false,renderedFrames=0,fallbackReason=null;
  let switching=null,blocked=false,initializingFrame=false,resizeObserver;
  let antialiasInfo=null;
  let viewportRenderable=false,viewportWidth=0,viewportHeight=0,skippedDraws=0;
  const deviceErrors=[];
  const nextFrame=()=>new Promise(requestAnimationFrame);
  const message=error=>String(error?.message||error);
  const isWebGPU=()=>S.renderer?.backend?.isWebGPUBackend===true;
  const isSoftwareAdapter=info=>Boolean(info?.isFallbackAdapter||adapter?.isFallbackAdapter||/swiftshader|llvmpipe|lavapipe|software/i.test([info?.vendor,info?.architecture,info?.device,info?.description].filter(Boolean).join(' ')));

  function adapterInfo(){
    const device=S.renderer?.backend?.device;
    // The adapter is the actual source of this backend's device, not a separate
    // capability probe that could have selected another physical adapter.
    const info=device?.adapterInfo||adapter?.info;
    if(!device||!info)return null;
    const out={};
    for(const key of ['vendor','architecture','device','description','subgroupMinSize','subgroupMaxSize','isFallbackAdapter']){
      if(info[key]!==undefined)out[key]=info[key];
    }
    if(out.isFallbackAdapter===undefined&&adapter?.isFallbackAdapter!==undefined)out.isFallbackAdapter=adapter.isFallbackAdapter;
    return out;
  }
  function rendererDiagnostics(){
    const renderer=S.renderer,backend=renderer?.backend,device=backend?.isWebGPUBackend?backend.device:null;
    const limits={};
    if(device)for(const key of ['maxTextureDimension2D','maxBufferSize','maxStorageBufferBindingSize','maxBindGroups'])limits[key]=device.limits[key];
    return {
      requested,api:backend?.isWebGPUBackend?'WebGPU':renderer?.isWebGLRenderer?'WebGL2':null,
      backend:backend?.isWebGPUBackend?'WebGPUBackend':renderer?.isWebGLRenderer?'WebGLRenderer':null,
      isWebGPURenderer:renderer?.isWebGPURenderer===true,
      isWebGPUBackend:backend?.isWebGPUBackend===true,isWebGLRenderer:renderer?.isWebGLRenderer===true,
      initialized:renderer?.isWebGLRenderer===true||renderer?._initialized===true,
      firstRenderComplete,renderedFrames,blocked:blocked||!!S.renderBlocked,pending:!!S.renderPending,fallbackReason,antialias:antialiasInfo?{...antialiasInfo}:null,
      gpuString:S.gpuString,rendererClass:S.rendererClass,
      viewport:{renderable:viewportRenderable,cssWidth:viewportWidth,cssHeight:viewportHeight,drawingBufferWidth:renderer?.domElement.width||0,drawingBufferHeight:renderer?.domElement.height||0,skippedDraws},
      device:device?{label:device.label,features:[...device.features].sort(),limits,adapterInfo:adapterInfo()}:null,
      deviceErrors:deviceErrors.map(e=>({...e}))
    };
  }
  function updateRendererInfo(){
    const d=rendererDiagnostics();
    const fallback=fallbackReason?`WebGPU 不可用，已回退 WebGL2：${fallbackReason}。`:'';
    $('renderer-info').textContent=`实际渲染 API：${d.api} · ${S.gpuString}。${fallback}${S.rendererClass==='software'?'软件渲染性能不代表真实 GPU。':''}灰色为完整人体；棕色或热图区域为实际布料。`;
  }
  function configureRenderer(){
    const renderer=S.renderer;
    if(isWebGPU()){
      const info=adapterInfo();
      S.gpuString=[info?.vendor,info?.architecture,info?.device,info?.description].filter(Boolean).join(' · ')||'WebGPU adapter identity unavailable';
      S.rendererClass=isSoftwareAdapter(info)?'software':'hardware-or-unknown';
      antialiasInfo={enabled:renderer.samples>0,samples:renderer.samples,method:renderer.samples>0?'MSAA':'none',reason:S.rendererClass==='software'?'Software adapter: transparent MSAA edge artifacts observed locally':null};
    }else{
      const gl=renderer.getContext(),ext=gl.getExtension('WEBGL_debug_renderer_info');
      S.gpuString=String(ext?gl.getParameter(ext.UNMASKED_RENDERER_WEBGL):gl.getParameter(gl.RENDERER));
      S.rendererClass=/swiftshader|llvmpipe|lavapipe|software/i.test(S.gpuString)?'software':'hardware-or-unknown';
      antialiasInfo={enabled:gl.getContextAttributes().antialias,samples:gl.getParameter(gl.SAMPLES),method:gl.getContextAttributes().antialias?'MSAA':'none',reason:null};
    }
    renderer.setPixelRatio(S.rendererClass==='software'?.8:Math.min(devicePixelRatio,1.5));
    renderer.outputColorSpace=T.SRGBColorSpace;
    // WebGPU presents a premultiplied-alpha canvas, so transparent clear
    // samples use zero RGB. WebGLRenderer premultiplies its clear color itself.
    renderer.setClearColor(isWebGPU()?0x000000:0xe9ece0,0);
    S.camera.coordinateSystem=renderer.coordinateSystem;S.camera.updateProjectionMatrix();
    // This app owns its drawing loop. Keep the most recent frame's real draw
    // counters available while paused instead of letting Three reset them on
    // its unrelated animation tick.
    if(isWebGPU())renderer.info.autoReset=false;
    renderer.domElement.setAttribute('aria-label',`实际布料与完整人体，${isWebGPU()?'WebGPU':'WebGL2'} 渲染`);
    $('viewport').appendChild(renderer.domElement);
    bindCameraInput(renderer.domElement);
    resize();
    updateRendererInfo();
  }
  async function createWebGPU(){
    if(!navigator.gpu)throw new Error('WebGPU API is unavailable in this browser or secure context');
    adapter=await navigator.gpu.requestAdapter();
    if(!adapter)throw new Error('WebGPU adapter is unavailable');
    const device=await adapter.requestDevice({label:'Cloth Lab WebGPU device'});
    let renderer;
    try{
      // SwiftShader's observed transparent MSAA output has white edge/line
      // artifacts. Use the actual software adapter identity for this rendering
      // adaptation; geometry, opacity, depth and all physics stay unchanged.
      renderer=new T.WebGPURenderer({antialias:!isSoftwareAdapter(device.adapterInfo||adapter.info),alpha:true,device});
      // r180 normally silently falls back to its internal WebGL backend. The
      // app owns that decision so forced WebGPU can never report a GL success.
      renderer._getFallback=null;
      renderer.onDeviceLost=info=>{
        renderer._isDeviceLost=true;
        if(S.renderer!==renderer)return;
        deviceErrors.push({stage:'device-lost',message:info.message,reason:info.reason});
        if(firstRenderComplete&&!initializingFrame)handleDrawFailure(new Error('WebGPU device lost: '+info.message));
      };
      S.renderer=renderer;
      await renderer.init();
      if(renderer.backend.isWebGPUBackend!==true||renderer.backend.device!==device)throw new Error('WebGPU backend/device mismatch');
      device.addEventListener('uncapturederror',event=>{
        const error=event.error;
        deviceErrors.push({stage:'uncaptured',message:message(error)});
        if(firstRenderComplete&&!initializingFrame&&S.renderer===renderer)handleDrawFailure(error);
      });
    }catch(error){
      if(renderer?._initialized)renderer.dispose();
      device.destroy();
      S.renderer=undefined;
      throw error;
    }
  }
  function createWebGL(){
    adapter=null;
    S.renderer=new WebGLRenderer({antialias:true,alpha:true,preserveDrawingBuffer:true});
    if(S.renderer.getContext().isContextLost())throw new Error('WebGL2 context is lost');
  }
  function disposeRenderer(){
    const old=S.renderer;
    if(!old)return;
    S.renderer=undefined;
    S.drag=null;
    old.domElement.remove();
    old.dispose();
    old.backend?.device?.destroy();
    adapter=null;
  }
  function markBlocked(error){
    blocked=true;firstRenderComplete=false;S.running=false;S.playing=false;
    S.renderBlocked=true;S.renderPending=false;S.renderError=message(error);
    if(window.clothLab)window.clothLab.ready=false;
    window.clothLabError=message(error);
    $('verdict').textContent='BLOCKED · 渲染失败';$('verdict').className='fail';
    $('activity').textContent=message(error);
    $('renderer-info').textContent=`BLOCKED · ${requested} · ${message(error)}`;
    onAvailabilityChange();
  }
  async function fallbackToWebGL(error){
    fallbackReason=message(error);firstRenderComplete=false;
    S.renderPending=true;S.running=false;S.playing=false;
    if(window.clothLab)window.clothLab.ready=false;
    onAvailabilityChange();
    disposeRenderer();createWebGL();configureRenderer();
    await renderFirstFrame();
    S.renderPending=false;
    if(window.clothLab)window.clothLab.ready=true;
    onAvailabilityChange();
  }
  function handleDrawFailure(error){
    if(blocked||switching)return;
    if(requested==='auto'&&isWebGPU()){
      switching=fallbackToWebGL(error).catch(markBlocked).finally(()=>switching=null);
    }else markBlocked(error);
  }
  async function setupScene(){
    if(!['auto','webgpu','webgl'].includes(requested))throw new Error('Invalid renderer; use auto, webgpu or webgl');
    S.scene=new T.Scene();S.camera=new T.PerspectiveCamera(35,1,.01,20);
    if(requested==='webgl')createWebGL();
    else try{await createWebGPU();}catch(error){
      if(requested==='webgpu')throw new Error('WebGPU required: '+message(error));
      fallbackReason=message(error);createWebGL();
    }
    configureRenderer();
    S.scene.add(new T.HemisphereLight(0xfff9e8,0x7c8d7b,2.2));
    const key=new T.DirectionalLight(0xfff8e4,2.5);key.position.set(2,3,3);S.scene.add(key);
    const rim=new T.DirectionalLight(0xc4e0e0,1.4);rim.position.set(-2,1,-2);S.scene.add(rim);
    const bodyPos=new Float32Array(decode(payload.body.positions).buffer),bodyFaces=new Int32Array(decode(payload.body.indices).buffer);
    const geom=new T.BufferGeometry();geom.setAttribute('position',new T.Float32BufferAttribute(bodyPos,3));geom.setIndex(Array.from(bodyFaces));geom.computeVertexNormals();
    const colors=new Float32Array(bodyPos.length),color=new T.Color();
    for(let i=0;i<bodyPos.length/3;i++){color.set(0xc6c6b9);color.toArray(colors,3*i);}
    geom.setAttribute('color',new T.Float32BufferAttribute(colors,3));
    S.bodyMesh=new T.Mesh(geom,new T.MeshStandardMaterial({vertexColors:true,roughness:.93}));S.scene.add(S.bodyMesh);
    const floor=new T.Mesh(new T.CircleGeometry(.68,64),new T.MeshStandardMaterial({color:0xd8ddce,roughness:1}));floor.rotation.x=-Math.PI/2;floor.position.y=-.005;S.scene.add(floor);
    const grid=new T.GridHelper(1.5,15,0xa5b59f,0xd2dacb);grid.position.y=-.003;S.scene.add(grid);
    const canvas=document.createElement('canvas');canvas.width=canvas.height=128;const ctx=canvas.getContext('2d');ctx.fillStyle='#ac715b';ctx.fillRect(0,0,128,128);
    for(let i=0;i<128;i+=4){ctx.fillStyle=i%8?'#b78066':'#a66b56';ctx.fillRect(i,0,1,128);ctx.fillStyle='#c18a70';ctx.fillRect(0,i,128,1);}
    S.texture=new T.CanvasTexture(canvas);S.texture.wrapS=S.texture.wrapT=T.RepeatWrapping;S.texture.repeat.set(8,8);S.texture.colorSpace=T.SRGBColorSpace;
    updateCamera();
    resizeObserver=new ResizeObserver(()=>{resize();draw();});resizeObserver.observe($('viewport'));
    $('asset-info').textContent=`MakeHuman 成人女性 · ${(payload.body.heightMeters*100).toFixed(1)} cm · ${payload.body.triangles.toLocaleString()} 个人体三角形 · CC0`;
  }
  function resize(){
    viewportRenderable=false;
    if(!S.renderer||!S.camera)return false;
    const r=$('viewport').getBoundingClientRect();
    const width=r.width,height=r.height,pixelRatio=S.renderer.getPixelRatio();
    const bufferWidth=Math.floor(width*pixelRatio),bufferHeight=Math.floor(height*pixelRatio);
    viewportWidth=width;viewportHeight=height;
    // Three r180 floors CSS size * pixel ratio before creating GPU textures.
    // A 1px CSS minimum still becomes a zero-width texture at software DPR .8.
    // Keep the last valid canvas while layout is hidden or smaller than one
    // backing pixel. A later ResizeObserver notification redraws the real state.
    if(!Number.isFinite(width)||!Number.isFinite(height)||!Number.isFinite(pixelRatio)||pixelRatio<=0||bufferWidth<1||bufferHeight<1)return false;
    const size=S.renderer.getSize(new T.Vector2()),canvas=S.renderer.domElement;
    if(size.x!==width||size.y!==height||canvas.width!==bufferWidth||canvas.height!==bufferHeight)S.renderer.setSize(width,height);
    if(canvas.width<1||canvas.height<1)return false;
    S.camera.aspect=width/height;S.camera.updateProjectionMatrix();
    viewportRenderable=true;
    return true;
  }
  async function waitForRenderableViewport(renderer){
    while(true){
      if(S.renderer!==renderer||blocked||S.renderBlocked)throw new Error('Renderer changed while waiting for a visible viewport');
      if(renderer.backend?.isWebGPUBackend&&renderer._isDeviceLost)throw new Error('WebGPU device was lost while waiting for a visible viewport');
      if(resize())return;
      await nextFrame();
    }
  }
  function updateCamera(){
    S.camera.position.set(Math.sin(S.cameraAngle)*S.cameraDistance,.8+S.cameraElevation*S.cameraDistance,Math.cos(S.cameraAngle)*S.cameraDistance+.055);S.camera.lookAt(0,.8,.055);
  }
  function bindCameraInput(target){
    target.addEventListener('pointerdown',e=>{S.drag=[e.clientX,e.clientY];target.setPointerCapture(e.pointerId);});
    target.addEventListener('pointerup',()=>S.drag=null);
    target.addEventListener('pointercancel',()=>S.drag=null);
    target.addEventListener('pointermove',e=>{if(!S.drag)return;S.cameraAngle-=(e.clientX-S.drag[0])*.008;S.cameraElevation=Math.max(-.12,Math.min(.6,S.cameraElevation+(e.clientY-S.drag[1])*.003));S.drag=[e.clientX,e.clientY];updateCamera();draw();});
    target.addEventListener('wheel',e=>{e.preventDefault();S.cameraDistance=Math.max(1.65,Math.min(4.5,S.cameraDistance+e.deltaY*.002));updateCamera();draw();},{passive:false});
  }
  function setupClothSurface(){
    const {scene,positions,triangles,restUV}=S;
    S.bodyMesh.position.x=S.parameters.bodyOffsetMm/1000;
    if(S.cloth){scene.remove(S.cloth,S.seamLines);S.clothGeometry.dispose();S.cloth.material.dispose();S.seamLines.geometry.dispose();S.seamLines.material.dispose();}
    const geometry=new T.BufferGeometry();geometry.setAttribute('position',new T.Float32BufferAttribute(positions,3));geometry.setIndex(Array.from(triangles));geometry.setAttribute('uv',new T.Float32BufferAttribute(Array.from({length:NV*2},(_,i)=>i%2?restUV[i]/.6:restUV[i]/.65),2));geometry.setAttribute('color',new T.Float32BufferAttribute(new Float32Array(NV*3).fill(1),3));geometry.computeVertexNormals();
    S.clothGeometry=geometry;
    S.cloth=new T.Mesh(geometry,new T.MeshStandardMaterial({map:S.texture,roughness:.93,side:T.DoubleSide}));scene.add(S.cloth);
    const lineGeom=new T.BufferGeometry();lineGeom.setAttribute('position',new T.Float32BufferAttribute(new Float32Array(M*2*2*3),3));lineGeom.setAttribute('color',new T.Float32BufferAttribute(new Float32Array(M*2*2*3),3));S.seamLines=new T.LineSegments(lineGeom,new T.LineBasicMaterial({vertexColors:true,depthTest:false}));S.seamLines.renderOrder=2;scene.add(S.seamLines);
  }
  function applyMode(value){
    S.mode=value;if(!S.cloth)return;
    S.cloth.material.map=S.mode==='fabric'?S.texture:null;S.cloth.material.vertexColors=S.mode!=='fabric';S.cloth.material.needsUpdate=true;
    for(const b of document.querySelectorAll('[data-mode]'))b.setAttribute('aria-pressed',String(b.dataset.mode===S.mode));
    const desc={fabric:['程序化织纹','无外部贴图','织纹只影响外观。物理计算在 WASM 中进行。'],strain:['0 %','≥ 12 %','工程最大主应变：√λmax(FᵀF) − 1；未变形为 0%。'],stress:['0 kPa','≥ 15 kPa','最大主柯西应力；正交各向异性 StVK，合成材料参数。非接触压力。'],contact:['≤ 0 mm','≥ 15 mm','相对实际人体三角网格的有符号最近距离。红色为穿透或接触，蓝色为有间隙。'],pressure:['0 kPa','≥ 0.100 kPa','法向接触压力 p=λ/(Δt² A)，来自实际接触乘子；合成接触层，未经实物标定。']}[S.mode];
    $('legend-min').textContent=desc[0];$('legend-max').textContent=desc[1];$('map-definition').textContent=desc[2];updateSurface();draw();
  }
  function updateSurface(){
    if(!S.cloth)return;
    const {positions,clothGeometry,triangles,fields,mode,bodyDistances,seamLines,seamMap,lastStats,wasm}=S;
    clothGeometry.attributes.position.array.set(positions);clothGeometry.attributes.position.needsUpdate=true;clothGeometry.computeVertexNormals();
    const scalar=new Float32Array(NV),counts=new Uint16Array(NV);
    if(mode==='strain'||mode==='stress'){const c=mode==='strain'?0:3;for(let t=0;t<NT;t++)for(let j=0;j<3;j++){const v=triangles[t*3+j];scalar[v]+=fields[t*8+c];counts[v]++;}for(let i=0;i<NV;i++)scalar[i]/=counts[i]||1;}
    const colors=clothGeometry.attributes.color.array,color=new T.Color(),pressures=floatView(wasm.pressure_ptr(),NV);
    for(let i=0;i<NV;i++){let a=mode==='strain'?scalar[i]/.12:mode==='stress'?scalar[i]/15000:mode==='contact'?1-bodyDistances[i]/.015:mode==='pressure'?pressures[i]/100:0;a=Math.max(0,Math.min(1,a));color.setHSL(.61*(1-a),.64,.54);color.toArray(colors,3*i);}clothGeometry.attributes.color.needsUpdate=true;
    const lp=seamLines.geometry.attributes.position.array,lc=seamLines.geometry.attributes.color.array;let n=0;const okay=lastStats.orientationValid&&!lastStats.missingSeam&&lastStats.lengthMismatchMm<1;
    for(const name of ['S1','S2']){const pairs=seamMap.filter(s=>s.name===name);for(let j=0;j<M;j++)for(const s of [pairs[j],pairs[j+1]]){lp.set(positions.subarray(s.a*3,s.a*3+3),n);lc.set(okay?[.74,.88,.38]:[.83,.2,.15],n);n+=3;}}
    seamLines.geometry.attributes.position.needsUpdate=true;seamLines.geometry.attributes.color.needsUpdate=true;seamLines.geometry.computeBoundingSphere();clothGeometry.computeBoundingSphere();
  }
  function draw(){
    if(!S.renderer||!S.cloth||blocked)return;
    updateSurface();
    if(!firstRenderComplete||switching)return;
    if(!resize()){skippedDraws++;return;}
    try{if(isWebGPU())S.renderer.info.reset();S.renderer.render(S.scene,S.camera);renderedFrames++;}catch(error){handleDrawFailure(error);}
  }
  async function renderFirstFrame(){
    updateSurface();initializingFrame=true;
    const renderer=S.renderer,device=isWebGPU()?renderer.backend.device:null;
    const previousDeviceErrors=deviceErrors.length;
    await waitForRenderableViewport(renderer);
    const errors=[];
    if(device)for(const kind of ['validation','internal','out-of-memory'])device.pushErrorScope(kind);
    try{
      if(device&&renderer._isDeviceLost)throw new Error('WebGPU device was lost before the first render');
      if(device){
        S.scene.updateMatrixWorld();S.camera.updateMatrixWorld();
        await renderer.compileAsync(S.scene,S.camera);
        // r180's compilation updates node values for its current frame. Render
        // on the next real frame so camera, light and material uniforms are
        // refreshed together rather than reusing the compilation frame values.
        await nextFrame();
      }
      await waitForRenderableViewport(renderer);
      if(device)renderer.info.reset();
      renderer.render(S.scene,S.camera);renderedFrames++;
      if(device)await device.queue.onSubmittedWorkDone();
      if(device&&renderer._isDeviceLost)throw new Error('WebGPU device was lost during the first render');
    }finally{
      if(device)for(let i=0;i<3;i++){
        const error=await device.popErrorScope();
        if(error){errors.push(error);deviceErrors.push({stage:'first-render',message:message(error)});}
      }
      initializingFrame=false;
    }
    if(errors.length)throw new Error('WebGPU first render: '+errors.map(message).join('; '));
    // A queue completion is not a presented canvas. Wait through presentation
    // before exposing ready, including when the user saves/reopens offline HTML.
    await nextFrame();await nextFrame();
    if(S.renderer!==renderer||blocked||device&&(renderer._isDeviceLost||deviceErrors.length!==previousDeviceErrors))throw new Error('Renderer failed before the first frame was presented');
    firstRenderComplete=true;
  }
  async function firstRender(){
    try{await renderFirstFrame();}catch(error){
      if(requested==='auto'&&isWebGPU())await fallbackToWebGL(error);
      else throw new Error(`${requested==='webgpu'?'WebGPU required':'Renderer'}: ${message(error)}`);
    }
  }
  function sceneAudit(){
    const {bodyMesh,cloth,renderer}=S;
    return {bodyVisible:bodyMesh.visible,bodyOpacity:bodyMesh.material.opacity,bodyDepthTest:bodyMesh.material.depthTest,clothDepthTest:cloth.material.depthTest,bodyPositions:Array.from(bodyMesh.geometry.attributes.position.array),bodyColors:Array.from(bodyMesh.geometry.attributes.color.array),bodyIndices:Array.from(bodyMesh.geometry.index.array),clippingPlanes:renderer.clippingPlanes?.length||0,viewport:{width:$('viewport').clientWidth,height:$('viewport').clientHeight}};
  }
  function pointToPixel(p){const v=new T.Vector3(...p).project(S.camera);return [(v.x+1)/2*$('viewport').clientWidth,(1-v.y)/2*$('viewport').clientHeight];}
  function surface(){return {mode:S.mode,colors:Array.from(S.clothGeometry.attributes.color.array),positions:Array.from(S.clothGeometry.attributes.position.array)};}
  function performanceInfo(){
    const d=rendererDiagnostics(),r=S.renderer;
    return {renderer:S.gpuString,gpuString:S.gpuString,rendererClass:S.rendererClass,pixelRatio:r.getPixelRatio(),drawCalls:r.info.render.drawCalls??r.info.render.calls,geometries:r.info.memory.geometries,textures:r.info.memory.textures,rendererApi:d.api,rendererBackend:d.backend,rendererRequested:requested,rendererDiagnostics:d};
  }
  return {setupScene,setupClothSurface,updateCamera,updateSurface,draw,applyMode,firstRender,sceneAudit,pointToPixel,surface,performanceInfo,rendererDiagnostics};
}
