import fs from 'node:fs';
const request=JSON.parse(fs.readFileSync(process.argv[2],'utf8')),input=request.input;
const binary=fs.readFileSync(request.wasm);
function kernel(){
 const e=new WebAssembly.Instance(new WebAssembly.Module(binary),{}).exports;
 for(const [key,name] of [['positions','body_ptr'],['normals','body_normal_ptr'],['indices','body_face_ptr'],['order','body_order_ptr'],['nodes','body_node_ptr']]){
  const bytes=Buffer.from(input.body[key],'base64');new Uint8Array(e.memory.buffer,e[name](),bytes.length).set(bytes);
 }e.configure_body(input.body.vertices,input.body.triangles,input.body.nodeCount);
 if(input.body.edge_normals){const bytes=Buffer.from(input.body.edge_normals,'base64');new Uint8Array(e.memory.buffer,e.body_edge_normal_ptr(),bytes.length).set(bytes);}
 const m=input.material;e.configure_material(m.Eu,m.Ev,m.G,m.nu,m.thickness,m.density);
 e.set_contact_margin(input.config.数值条件.接触间距_毫米/1000);
 if(e.set_projection_cap)e.set_projection_cap((input.config.数值条件.单轮接触最大修正_毫米||.5)/1000);
 return e;
}
const probe=kernel(),coupons=request.coupons.map(c=>{probe.material_probe(...c.F);return Array.from(new Float32Array(probe.memory.buffer,probe.probe_ptr(),8));});
const collisions=request.points.map(p=>{probe.collision_probe(...p);return Array.from(new Float32Array(probe.memory.buffer,probe.probe_ptr(),7));});
const dense=kernel(),nv=1400;
new Float32Array(dense.memory.buffer,dense.position_ptr(),nv*3).set(Array.from({length:nv*3},(_,i)=>i%3===0?i/300:0));
new Float32Array(dense.memory.buffer,dense.uv_ptr(),nv*2).set([0,0,1,0,0,1]);
new Int32Array(dense.memory.buffer,dense.face_ptr(),3).set([0,1,2]);dense.configure_cloth(nv,1);
for(let i=0;i<700;i++)dense.add_seam(i,i+700,1);dense.finalize_seams();dense.inject_vertex(699,.1,.2,.3);
const positions=new Float32Array(dense.memory.buffer,dense.position_ptr(),nv*3);
const aliasExact=[0,1,2].every(k=>Object.is(positions[699*3+k],positions[1399*3+k]));
for(let i=0;i<12000;i++)dense.add_bend(0,1,.01);
const free=kernel(),xyz=new Float32Array(free.memory.buffer,free.position_ptr(),9),previous=new Float32Array(free.memory.buffer,free.previous_ptr(),9);
xyz.set([0,0,10,1,0,10,0,1,10]);new Float32Array(free.memory.buffer,free.uv_ptr(),6).set([0,0,1,0,0,1]);new Int32Array(free.memory.buffer,free.face_ptr(),3).set([0,1,2]);free.configure_cloth(3,1);free.set_collision(0);
const initial=Array.from(xyz);free.step(12,0);const fallen=Array.from(xyz),oldPrevious=Array.from(previous);
free.contact_velocity(.2,.3);const dampedPrevious=Array.from(previous),dampedPositions=Array.from(xyz);
// Incoming normal motion on a real body face must be removed without moving x.
const point=request.contactPoint;free.collision_probe(...point);const hit=Array.from(new Float32Array(free.memory.buffer,free.probe_ptr(),7));
const q=hit.slice(1,4),n=hit.slice(4,7),clearance=input.config.数值条件.接触间距_毫米/1000;for(let i=0;i<3;i++)for(let k=0;k<3;k++){xyz[3*i+k]=q[k]+n[k]*clearance;previous[3*i+k]=xyz[3*i+k]+n[k]*.001;}
const beforeContact=Array.from(xyz);free.contact_velocity(1,.3);const afterContact=Array.from(xyz),afterPrevious=Array.from(previous);
console.log(JSON.stringify({coupons,collisions,capacity:{seams:dense.seam_count(),bends:dense.bend_count(),lastAliasExact:aliasExact},
 gravity:{initial,fallen,oldPrevious,dampedPrevious,dampedPositions},normalContact:{beforeContact,afterContact,afterPrevious,normal:n}}));
