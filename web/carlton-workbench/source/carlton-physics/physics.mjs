const bytes = text => Uint8Array.from(atob(text), c => c.charCodeAt(0))
export async function loadSolver(binary, mesh) {
  const {instance} = await WebAssembly.instantiate(bytes(binary))
  const k=instance.exports
  const copy=(method,encoded)=>{
    const data=bytes(encoded)
    new Uint8Array(k.memory.buffer,k[method](),data.length).set(data)
  }
  const {cloth,body}=mesh
  copy('body_ptr',body.position); copy('body_normal_ptr',body.normals)
  copy('body_face_ptr',body.faces); copy('body_order_ptr',body.order); copy('body_node_ptr',body.nodes)
  k.configure_body(body.vertices,body.triangles,body.nodeCount)
  const faces=new Int32Array(bytes(cloth.faces).buffer)
  const reference=new Float32Array(bytes(cloth.position).buffer)
  let start=reference
  let pockets=cloth.pockets
  const bends=[]
  const edges=new Map()
  for(let i=0;i<faces.length;i+=3) for(let j=0;j<3;j++){
    const a=faces[i+j],b=faces[i+(j+1)%3],c=faces[i+(j+2)%3]
    const id=Math.min(a,b)+':'+Math.max(a,b)
    if(edges.has(id)){
      const p=edges.get(id)
      if(p!==c)bends.push([p,c])
      edges.delete(id)
    }else edges.set(id,c)
  }
  const flat=new Float32Array(bytes(cloth.uv).buffer)
  const previous=()=>new Float32Array(k.memory.buffer,k.previous_ptr(),cloth.vertices*3)
  const inverseMass=()=>new Float32Array(k.memory.buffer,k.invmass_ptr(),cloth.vertices)
  function reset(position=reference, uv=null, selfCollision=true, pocketStitches=cloth.pockets){
    start=position
    pockets=pocketStitches
    positions().set(position)
    new Float32Array(k.memory.buffer,k.uv_ptr(),flat.length).set(uv??flat)
    copy('face_ptr',cloth.faces)
    k.configure_material(550000,550000,90000,.22,.0013,.40)
    if(uv) k.configure_cloth(cloth.vertices,cloth.triangles)
    else k.configure_placed_cloth(cloth.vertices,cloth.triangles)
    for(const [a,b] of cloth.pairs)k.add_seam(a,b,1)
    for(const [p,a,b,t] of [...cloth.stitches,...cloth.darts,...Object.values(cloth.collars).flat()])k.add_edge_stitch(p,a,b,t)
    for(const stitch of [...pockets,...cloth.pocketTurnbacks])k.add_surface_stitch(...stitch)
    for(const pin of cloth.anchored)k.set_pin(pin)
    for(const [a,b] of bends)k.add_bend(a,b,Math.hypot(start[3*a]-start[3*b],start[3*a+1]-start[3*b+1],start[3*a+2]-start[3*b+2]))
    k.finalize_seams()
    k.set_collision(1)
    k.set_self_collision(Number(selfCollision))
  }
  function positions(){return new Float32Array(k.memory.buffer,k.position_ptr(),cloth.vertices*3)}
  function stats(){
    k.analyze()
    const s=new Float32Array(k.memory.buffer,k.stats_ptr(),16)
    const pos=positions()
    let displacement=0
    for(let i=0;i<pos.length;i+=3)displacement=Math.max(displacement,Math.hypot(pos[i]-start[i],pos[i+1]-start[i+1],pos[i+2]-start[i+2]))
    const gaps=stitches=>stitches.map(([p,a,b,t])=>Math.hypot(...[0,1,2].map(d=>pos[3*p+d]-(1-t)*pos[3*a+d]-t*pos[3*b+d])))
    const surfaceGap=stitches=>1000*Math.max(0,...stitches.map(([p,a,b,c,u,v,w])=>Math.hypot(
      ...[0,1,2].map(i=>pos[3*p+i]-u*pos[3*a+i]-v*pos[3*b+i]-w*pos[3*c+i])
    )))
    const pocketGap=surfaceGap(pockets)
    const turnbackGap=surfaceGap(cloth.pocketTurnbacks)
    const collarGaps=Object.fromEntries(Object.entries(cloth.collars).map(([name,stitches])=>{
      const values=gaps(stitches).sort((a,b)=>a-b)
      return [name,{samples:values.length,max:1000*values.at(-1),p95:1000*values[Math.floor(.95*(values.length-1))]}]
    }))
    const dartGap=1000*Math.max(0,...gaps(cloth.darts))
    const stitchGaps=gaps(cloth.stitches)
    stitchGaps.sort((a,b)=>a-b)
    const waistGap=1000*(stitchGaps[Math.floor(.95*(stitchGaps.length-1))]??0)
    return {waistGap,pocketGap,turnbackGap,collarGaps,dartGap,selfContacts:s[12],selfTotal:s[13],selfEnabled:!!s[14],steps:s[0],seconds:s[1],seamMm:s[2]*1000,penetrationMm:s[3]*1000,contacts:s[7],finite:!!s[8],movingMm:displacement*1000,collision:!!s[10],strain:s[5]*100}
  }
  reset()
  const fields=()=>new Float32Array(k.memory.buffer,k.field_ptr(),cloth.triangles*8)
  const rest=()=>new Float32Array(k.memory.buffer,k.uv_ptr(),cloth.vertices*2)
  const pressure=()=>new Float32Array(k.memory.buffer,k.pressure_ptr(),cloth.vertices)
  return {fields,pressure,rest,positions,previous,inverseMass,finishPredictedStep:k.finish_predicted_step,stats,reset,faces,step:(count=1)=>{k.step(count,0)}}
}
