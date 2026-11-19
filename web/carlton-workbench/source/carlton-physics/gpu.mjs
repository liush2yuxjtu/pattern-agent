// Predict motion per vertex on WebGPU. Rust applies the coupled constraints to
// the predicted positions before the next dispatch.
const shader = `
struct Particle {
  position: vec3f,
  inverseMass: f32,
  previous: vec3f,
}
@group(0) @binding(0) var<storage, read> particles: array<Particle>;
@group(0) @binding(1) var<storage, read_write> predicted: array<vec4f>;

@compute @workgroup_size(64)
fn integrate(@builtin(global_invocation_id) invocation: vec3u) {
  let i = invocation.x;
  if (i >= arrayLength(&particles)) { return; }
  let p = particles[i];
  if (p.inverseMass == 0.0) {
    predicted[i] = vec4f(p.position, 0.0);
    return;
  }
  let dt = 1.0 / 120.0;
  let velocity = (p.position - p.previous) * 0.993;
  let limited = velocity * min(1.0, 0.025 / max(length(velocity), 1e-12));
  predicted[i] = vec4f(p.position + limited + vec3f(0.0, -9.81 * dt * dt, 0.0), 0.0);
}
`

export async function createIntegrator(device,count){
  const input=new Float32Array(count*8)
  const size=count*16
  const make=(label,size,usage)=>device.createBuffer({label,size,usage})
  const particles=make('Cloth particles',input.byteLength,GPUBufferUsage.STORAGE|GPUBufferUsage.COPY_DST)
  const predicted=make('Predicted cloth positions',size,GPUBufferUsage.STORAGE|GPUBufferUsage.COPY_SRC)
  const result=make('Rust constraint solver transfer',size,GPUBufferUsage.COPY_DST|GPUBufferUsage.MAP_READ)
  const pipeline=await device.createComputePipelineAsync({
    label:'Carlton cloth gravity and inertia',layout:'auto',
    compute:{module:device.createShaderModule({code:shader}),entryPoint:'integrate'},
  })
  const group=device.createBindGroup({layout:pipeline.getBindGroupLayout(0),entries:[
    {binding:0,resource:{buffer:particles}},
    {binding:1,resource:{buffer:predicted}},
  ]})
  return async function integrate(solver,isCurrent){
    const positions=solver.positions(), previous=solver.previous(), masses=solver.inverseMass()
    for(let i=0;i<count;i++){
      const a=3*i,b=8*i
      input[b]=positions[a];input[b+1]=positions[a+1];input[b+2]=positions[a+2]
      input[b+3]=masses[i]
      input[b+4]=previous[a];input[b+5]=previous[a+1];input[b+6]=previous[a+2]
    }
    device.queue.writeBuffer(particles,0,input)
    const commands=device.createCommandEncoder()
    const pass=commands.beginComputePass()
    pass.setPipeline(pipeline)
    pass.setBindGroup(0,group)
    pass.dispatchWorkgroups(Math.ceil(count/64))
    pass.end()
    commands.copyBufferToBuffer(predicted,0,result,0,size)
    device.queue.submit([commands.finish()])
    await result.mapAsync(GPUMapMode.READ)
    try{
      if(!isCurrent())return false
      const output=new Float32Array(result.getMappedRange())
      previous.set(positions)
      for(let i=0;i<count;i++){
        const a=3*i,b=4*i
        positions[a]=output[b];positions[a+1]=output[b+1];positions[a+2]=output[b+2]
      }
      solver.finishPredictedStep()
      return true
    }finally{
      result.unmap()
    }
  }
}
