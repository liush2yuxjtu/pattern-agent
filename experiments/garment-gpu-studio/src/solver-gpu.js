import {expandPositions}from './constraints.js';
import {createCorrector}from './corrector.js';
const predictionWGSL=`
struct Params {dt:f32,gravity:f32,damping:f32,wind:f32};
@group(0) @binding(0) var<storage,read_write> p:array<vec4f>;
@group(0) @binding(1) var<storage,read_write> prev:array<vec4f>;
@group(0) @binding(2) var<uniform> cfg:Params;
@compute @workgroup_size(64) fn main(@builtin(global_invocation_id) id:vec3u){let i=id.x;if(i>=arrayLength(&p)){return;}let x=p[i];if(x.w==0){prev[i]=x;return;}let v=(x.xyz-prev[i].xyz)*cfg.damping;prev[i]=x;p[i]=vec4f(x.xyz+v+vec3f(cfg.wind,-cfg.gravity,0)*cfg.dt*cfg.dt,x.w);}`;
const constraintsWGSL=`
struct Edge {a:u32,b:u32,rest:f32,compliance:f32};
@group(0) @binding(0) var<storage,read_write> p:array<vec4f>;
@group(0) @binding(1) var<storage,read> edges:array<Edge>;
@compute @workgroup_size(64) fn main(@builtin(global_invocation_id) id:vec3u){let i=id.x;if(i>=arrayLength(&edges)){return;}let e=edges[i];let a=p[e.a];let b=p[e.b];let d=a.xyz-b.xyz;let len=length(d);let w=a.w+b.w;if(len<1e-8||w==0){return;}let alpha=e.compliance*14400.0;let delta=d*((len-e.rest)/(len*(w+alpha)));p[e.a]=vec4f(a.xyz-delta*a.w,a.w);p[e.b]=vec4f(b.xyz+delta*b.w,b.w);}`;
const contactsWGSL=`
struct Plane {normal:vec4f,anchor:vec4f};
@group(0) @binding(0) var<storage,read_write> p:array<vec4f>;
@group(0) @binding(1) var<storage,read> planes:array<Plane>;
@compute @workgroup_size(64) fn main(@builtin(global_invocation_id) id:vec3u){let i=id.x;if(i>=arrayLength(&p)){return;}var x=p[i];if(x.w==0){return;}for(var j=1u;j<8u;j++){let plane=planes[i*8u+j];if(plane.normal.w>0.0){let d=dot(x.xyz-plane.anchor.xyz,plane.normal.xyz);if(d<0.0){x=vec4f(x.xyz-plane.normal.xyz*min(-d,0.002),x.w);}}}let surface=planes[i*8u];if(surface.normal.w>0.0){let d=dot(x.xyz-surface.anchor.xyz,surface.normal.xyz);if(d<0.0){x=vec4f(x.xyz-surface.normal.xyz*d,x.w);}}p[i]=x;}`;
const limitMotionWGSL=`
@group(0) @binding(0) var<storage,read_write> p:array<vec4f>;
@group(0) @binding(1) var<storage,read> previous:array<vec4f>;
@compute @workgroup_size(64) fn main(@builtin(global_invocation_id) id:vec3u){let i=id.x;if(i>=arrayLength(&p)){return;}let delta=p[i].xyz-previous[i].xyz;let distance=length(delta);if(distance>0.001){p[i]=vec4f(previous[i].xyz+delta*(0.001/distance),p[i].w);}}`;

export class GPUSolver {
  static async create(model,contact,options={}){
    if(!globalThis.isSecureContext)throw new Error('WebGPU 需要安全上下文。请在 Chrome/Edge 中直接打开下载的 HTML，或使用 localhost / HTTPS。');
    if(!navigator.gpu)throw new Error('当前浏览器没有 WebGPU。请使用支持 WebGPU 的 Chrome/Edge。');
    const adapter=await navigator.gpu.requestAdapter({powerPreference:'high-performance'});if(!adapter)throw new Error('WebGPU 未提供可用适配器。');
    const device=await adapter.requestDevice(),solver=new GPUSolver(device,adapter,model,contact,options);try{await solver.init();return solver;}catch(error){solver.dispose();throw error;}
  }
  constructor(device,adapter,model,contact,options){Object.assign(this,{device,adapter,model,contact});this.options={gravity:9.81,wind:0,iterations:128,pinned:false,...options};this.steps=0;this.dispatches=0;this.dt=1/120;this.errors=[];this.destroyed=false;this.generation=0;this.p=model.initial.slice();this.info={...Object.fromEntries(['vendor','architecture','device','description','isFallbackAdapter'].map(k=>[k,adapter.info?.[k]??null])),backend:'Hybrid WebGPU PBD predictor + CPU XPBD collision/self-contact corrector',iterations:this.options.iterations,gpuIterations:4,predictorMotionLimitMm:1,render:'Three.js WebGL2',hybrid:'GPU integration, colored stretch/bend and vertex-contact predictor. CPU XPBD corrects actual mesh contacts, self contacts and seam equalities. WASM f64 diagnostics.'};device.addEventListener('uncapturederror',e=>this.errors.push(String(e.error)));device.lost.then(x=>{if(!this.destroyed)this.errors.push('GPU lost: '+x.message);});this.buffers=[];}
  buffer(data,usage){const b=this.device.createBuffer({size:Math.max(16,data.byteLength),usage:usage|GPUBufferUsage.COPY_DST});this.device.queue.writeBuffer(b,0,data);this.buffers.push(b);return b;}
  async pipeline(code,label){const module=this.device.createShaderModule({code,label}),info=await module.getCompilationInfo();const errors=info.messages.filter(x=>x.type==='error');if(errors.length)throw new Error(errors.map(x=>x.message).join('\n'));return this.device.createComputePipelineAsync({label,layout:'auto',compute:{module,entryPoint:'main'}});}
  bind(pipeline,buffers){return this.device.createBindGroup({layout:pipeline.getBindGroupLayout(0),entries:buffers.map((buffer,binding)=>({binding,resource:{buffer}}))});}
  async init(){
    if(!this.options.document||!this.options.body)throw new Error('Hybrid corrector requires canonical garment and body');
    this.corrector=await createCorrector(this.options.document,this.options.body,{iterations:this.options.iterations,gravity:0,pinned:this.options.pinned,selfContact:true,clearance:.005});
    this.info.correctorThread=this.corrector.thread;
    this.device.pushErrorScope('validation');
    this.pos=this.buffer(this.p,GPUBufferUsage.STORAGE|GPUBufferUsage.COPY_SRC);this.prev=this.buffer(this.p,GPUBufferUsage.STORAGE);this.config=this.buffer(new Float32Array([this.dt,this.options.gravity,.96,this.options.wind]),GPUBufferUsage.UNIFORM);
    this.planes=this.buffer(this.contact.planes(this.p),GPUBufferUsage.STORAGE);
    this.predict=await this.pipeline(predictionWGSL,'verlet-integrate');this.solve=await this.pipeline(constraintsWGSL,'colored-distance');this.project=await this.pipeline(contactsWGSL,'body-contact');this.limitMotion=await this.pipeline(limitMotionWGSL,'predictor-trust-region');
    this.predictBind=this.bind(this.predict,[this.pos,this.prev,this.config]);this.projectBind=this.bind(this.project,[this.pos,this.planes]);this.limitMotionBind=this.bind(this.limitMotion,[this.pos,this.prev]);
    this.colorBinds=this.model.colors.map((group,i)=>{const raw=new ArrayBuffer(group.length*16),v=new DataView(raw);group.forEach((e,j)=>{v.setUint32(j*16,e.a,true);v.setUint32(j*16+4,e.b,true);v.setFloat32(j*16+8,e.rest,true);v.setFloat32(j*16+12,e.compliance,true);});const b=this.buffer(new Uint8Array(raw),GPUBufferUsage.STORAGE);return {bind:this.bind(this.solve,[this.pos,b]),count:group.length};});
    this.read=this.device.createBuffer({size:this.p.byteLength,usage:GPUBufferUsage.COPY_DST|GPUBufferUsage.MAP_READ});this.buffers.push(this.read);
    this.setPinned(this.options.pinned);await this.device.queue.onSubmittedWorkDone();const e=await this.device.popErrorScope();if(e)throw new Error(e.message);
  }
  setPinned(value){this.options.pinned=value;for(let i=0;i<this.model.nodeCount;i++)this.p[i*4+3]=value&&this.model.pins.includes(i)?0:1;this.device.queue.writeBuffer(this.pos,0,this.p);this.device.queue.writeBuffer(this.prev,0,this.p);}
  async step(count=1){if(this.destroyed)throw new Error('Disposed GPU solver');
    for(let s=0;s<count;s++){
      const start=performance.now(),before=this.p.slice();this.device.queue.writeBuffer(this.config,0,new Float32Array([this.dt,this.options.gravity,.96,this.options.wind]));
      this.device.queue.writeBuffer(this.planes,0,this.contact.planes(this.p));
      const encoder=this.device.createCommandEncoder({label:`cloth-step-${this.steps+1}`});const pass=encoder.beginComputePass();
      const run=(pipeline,bind,n)=>{pass.setPipeline(pipeline);pass.setBindGroup(0,bind);pass.dispatchWorkgroups(Math.ceil(n/64));this.dispatches++;};
      run(this.predict,this.predictBind,this.model.nodeCount);
      for(let i=0;i<4;i++){for(const group of this.colorBinds)run(this.solve,group.bind,group.count);run(this.project,this.projectBind,this.model.nodeCount);}
      run(this.limitMotion,this.limitMotionBind,this.model.nodeCount);
      pass.end();encoder.copyBufferToBuffer(this.pos,0,this.read,0,this.p.byteLength);this.device.queue.submit([encoder.finish()]);
      await this.read.mapAsync(GPUMapMode.READ);this.p=new Float32Array(this.read.getMappedRange()).slice();this.read.unmap();
      this.lastGpuDeltaMm=0;
      for(let i=0;i<before.length;i+=4){
        const delta=Math.hypot(this.p[i]-before[i],this.p[i+1]-before[i+1],this.p[i+2]-before[i+2]);
        this.lastGpuDeltaMm=Math.max(this.lastGpuDeltaMm,1000*delta);
      }
      if(!this.p.every(Number.isFinite)||this.p.some(x=>Math.abs(x)>10))throw new Error('GPU 布料状态发散，已停止。请重新生成。');
      // Local CPU narrow phase and XPBD projection refine the real GPU candidate.
      // Gravity is zero in this projection stage: physical integration occurs once.
      const corrected=await this.corrector.step(expandPositions(this.model,this.p),this.options.pinned);for(let i=0;i<this.model.groups.length;i++){const group=this.model.groups[i];for(let a=0;a<3;a++)this.p[i*4+a]=group.reduce((sum,node)=>sum+corrected[node*3+a],0)/group.length;}
      this.device.queue.writeBuffer(this.pos,0,this.p);
      this.steps++;this.lastStepMs=performance.now()-start;
    }
    if(this.errors.length)throw new Error(this.errors.join('\n'));return this.positions();
  }
  positions(){return expandPositions(this.model,this.p);}
  async poke(node,dx=.015,dy=0,dz=.025){const at=node*4;this.p[at]+=dx;this.p[at+1]+=dy;this.p[at+2]+=dz;this.device.queue.writeBuffer(this.pos,at*4,this.p.subarray(at,at+4));}
  dispose(){this.destroyed=true;this.generation++;this.corrector?.dispose();for(const b of this.buffers)b.destroy();this.device.destroy();}
}
export const gpuShaderSources={predictionWGSL,constraintsWGSL,contactsWGSL,limitMotionWGSL};
