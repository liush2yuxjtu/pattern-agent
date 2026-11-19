import * as T from 'three/webgpu'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'
import { loadSolver } from './physics.mjs'
import { forAssembly } from './pattern.mjs'
import { decode, fingerprint, makeAssembly } from './assembly.mjs'
import { setupDiagnostics } from './diagnostics.mjs'
import { createIntegrator } from './gpu.mjs'

const get = id => document.getElementById(id)
const viewport=get('viewport'),readout=get('readout')
const root=get('carlton-input-explorer')
const steps=480
let renderer,scene,camera,controls,coat,solver,assemble,integrate,current
let diagnostics,frontCamera,avatar,floor,resize,displayMode='appearance'
let generation=0, timer=0, busy=false, pending=null
let active=false,runtimeFailed=false

const unpack = text => new Response(
  new Blob([decode(text.trim())]).stream().pipeThrough(new DecompressionStream('gzip'))
).json()

function createModel(positions,indices,color) {
  const geometry=new T.BufferGeometry()
  geometry.setAttribute('position',new T.BufferAttribute(positions,3))
  geometry.setIndex(new T.BufferAttribute(Uint32Array.from(indices),1))
  geometry.computeVertexNormals()
  return new T.Mesh(geometry,new T.MeshStandardMaterial({color,side:T.DoubleSide,roughness:.93}))
}

function draw(){
  if(displayMode==='line'){
    const x=solver.positions()
    let minY=Infinity,maxY=-Infinity,maxX=0
    for(let i=0;i<x.length;i+=3){
      minY=Math.min(minY,x[i+1]);maxY=Math.max(maxY,x[i+1]);maxX=Math.max(maxX,Math.abs(x[i]))
    }
    const half=Math.max((maxY-minY)/2,maxX)*1.14
    frontCamera.left=frontCamera.bottom=-half
    frontCamera.right=frontCamera.top=half
    frontCamera.position.set(0,(minY+maxY)/2,3)
    frontCamera.updateProjectionMatrix()
    renderer.render(scene,frontCamera)
    return
  }
  renderer.render(scene,camera)
}

function update(message, stats=solver.stats()) {
  Object.assign(viewport.dataset,{
    steps:String(stats.steps),finite:String(stats.finite),contacts:String(stats.contacts),
    movement:String(stats.movingMm),seamGap:String(stats.seamMm),waistGap:String(stats.waistGap),dartGap:String(stats.dartGap),pocketGap:String(stats.pocketGap),
    selfContacts:String(stats.selfContacts),selfTotal:String(stats.selfTotal),selfEnabled:String(stats.selfEnabled),
  })
  get('time').textContent=stats.seconds.toFixed(2)+' / 4.00 s'
  get('steps').textContent=stats.steps+' / '+steps
  get('contacts').textContent=String(stats.contacts)
  get('self-contacts').textContent=String(stats.selfTotal.toLocaleString())
  if(message)readout.textContent=message
  diagnostics.shell.attributes.position.array.set(solver.positions())
  diagnostics.shell.attributes.position.needsUpdate=true
  diagnostics.shell.computeVertexNormals()
  draw()
  return stats
}

function view(side){
  camera.position.set(...(side==='back'?[.04,1.12,-3.1]:side==='front'?[0,1.1,3.1]:[.83,1.16,3.08]))
  for(const button of ['front','angle','back'])get(button).setAttribute('aria-pressed',String(button===side))
  controls.target.set(0,.99,0)
  controls.update()
  draw()
}

function gpuFailure(error){
  runtimeFailed=true
  active=false
  console.warn(error)
  viewport.dataset.state='error'
  readout.textContent='WebGPU 启动或执行失败。2D 纸样仍可使用。'
  get('run').disabled=true
}

const nextFrame = () => new Promise(resolve=>requestAnimationFrame(resolve))

async function drain(){
  if(busy||!active||!pending)return
  busy=true
  try{
    while(active&&pending){
      const {job,draft,chest,length}=pending
      pending=null
      if(job!==generation)continue
      let assembly
      try {
        assembly=assemble(draft)
        solver.reset(assembly.position,assembly.flat)
      } catch (error) {
        console.warn(error)
        viewport.dataset.state='unsupported-pattern'
        readout.textContent='当前纸样超出 3D 参考装配的范围。2D 仍可查看和导出。'
        continue
      }
      const {position,flat,changedPanels}=assembly
      Object.assign(viewport.dataset,{
        state:'running',chest:String(chest),length:String(length),revision:String(job),
        restHash:fingerprint(flat),assemblyHash:fingerprint(position),resultHash:'',
        gpuSteps:'0',changedPanels:String(changedPanels.length),
      })
      get('geometry').textContent=(changedPanels.length?changedPanels.length+' 片更新 · ':'')+solver.faces.length/3+' 个三角面'
      update('正在模拟当前纸样…')
      const isCurrent=()=>active&&job===generation
      for(let step=1;step<=steps&&isCurrent();step++){
        if(!(await integrate(solver,isCurrent)))break
        if(step%8===0||step===steps){
          viewport.dataset.gpuSteps=String(step)
          if(!update().finite)throw Error('布料顶点出现无效坐标')
          if(step===steps){
            diagnostics.setReady(true)
            viewport.dataset.resultHash=fingerprint(solver.positions())
            viewport.dataset.state='complete'
            readout.textContent='模拟完成 · '+chest+' mm 胸围 / '+length+' mm 衣长'
          }else{
            await nextFrame()
          }
        }
      }
    }
  }catch(error){
    gpuFailure(error)
  }finally{
    busy=false
  }
}

function queue(detail,delay=190){
  const job=++generation
  pending=null
  clearTimeout(timer)
  current={...detail,job}
  if(runtimeFailed)return
  diagnostics?.setReady(false)
  viewport.dataset.state='queued'
  readout.textContent='正在更新纸样与装配…'
  timer=setTimeout(()=>{
    if(active){
      pending=current
      void drain()
    }
  },delay)
}
root.addEventListener('carlton-draft',event=>{
  const {pattern,chest,length}=event.detail
  queue({draft:forAssembly(pattern),chest,length})
})
root.addEventListener('carlton-invalid',()=>{
  ++generation
  current=pending=null
  clearTimeout(timer)
  if(runtimeFailed)return
  diagnostics?.setReady(false)
  viewport.dataset.state='invalid-pattern'
  readout.textContent='2D 输入尚未生成有效纸样，3D 暂停更新。'
})
get('run').addEventListener('click',()=>{if(current)queue(current,0)})

async function init(){
  const saved=await unpack(get('payload').textContent)
  solver=await loadSolver(saved.wasm,saved.mesh)
  assemble=makeAssembly(saved.mesh.cloth,solver.faces)
  const adapter=await navigator.gpu?.requestAdapter()
  if(!adapter)throw Error('没有可用的 WebGPU adapter')
  const device=await adapter.requestDevice()
  device.addEventListener('uncapturederror',event=>gpuFailure(event.error))
  void device.lost.then(info=>gpuFailure(Error(info.message || 'WebGPU device lost')))
  integrate=await createIntegrator(device,saved.mesh.cloth.vertices)
  renderer=new T.WebGPURenderer({device,antialias:true,alpha:false})
  renderer.setPixelRatio(Math.min(devicePixelRatio,1.5))
  renderer.setClearColor(0xe9ebe1)
  await renderer.init()
  if(!renderer.backend.isWebGPUBackend)throw Error('WebGPU renderer backend is unavailable')
  Object.assign(viewport.dataset,{engine:'rust-wasm',backend:'webgpu',integrator:'webgpu-compute'})
  viewport.append(renderer.domElement)
  scene=new T.Scene()
  camera=new T.PerspectiveCamera(39,1,.02,30)
  frontCamera=new T.OrthographicCamera(-1,1,1,-1,.02,30)
  controls=new OrbitControls(camera,renderer.domElement)
  controls.enablePan=false
  controls.minDistance=1.15
  controls.maxDistance=6
  controls.addEventListener('change',draw)
  const {body}=saved.mesh
  avatar=createModel(new Float32Array(decode(body.position)),new Int32Array(decode(body.faces)),0xc1b49e)
  scene.add(avatar)
  coat=createModel(Float32Array.from(solver.positions()),solver.faces,0x286557)
  coat.frustumCulled=false
  scene.add(coat)
  scene.add(new T.HemisphereLight(0xfffcf2,0x697e7b,2.35))
  const sun=new T.DirectionalLight(0xfff8eb,2.3)
  sun.position.set(2,3,3)
  scene.add(sun)
  const fill=new T.DirectionalLight(0xe3f1ff,.9)
  fill.position.set(-2,1.8,-2)
  scene.add(fill)
  floor=new T.Mesh(new T.CircleGeometry(1.15,64),new T.MeshStandardMaterial({color:0xdadfd0,roughness:1}))
  floor.rotation.x=-Math.PI/2
  scene.add(floor)
  resize=()=>{
    const rect=viewport.getBoundingClientRect()
    renderer.setSize(rect.width,rect.height,false)
    camera.aspect=rect.width/Math.max(1,rect.height)
    camera.updateProjectionMatrix()
    draw()
  }
  diagnostics=setupDiagnostics({coat,solver,get,onMode:mode=>{
    displayMode=mode
    const line=mode==='line'
    avatar.visible=floor.visible=controls.enabled=!line
    get('line-reference').hidden=!line
    get('viewer-row').classList.toggle('line-compare',line)
    for(const side of ['front','angle','back'])get(side).disabled=line
    renderer.setClearColor(line?0xffffff:0xe9ebe1)
    resize()
  }})
  diagnostics.setReady(false)
  view('angle')
  resize()
  new ResizeObserver(resize).observe(viewport)
  for(const side of ['front','angle','back']){
    get(side).disabled=false
    get(side).addEventListener('click',()=>view(side))
  }
  if(runtimeFailed)return
  get('run').disabled=false
  active=true
  if(current?.job===generation){
    pending=current
    void drain()
  }
}
init().catch(gpuFailure)
