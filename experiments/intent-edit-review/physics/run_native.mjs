import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {spawnSync} from 'node:child_process';
import {createSelfContact} from './create-self-contact.mjs';
import {guardSelfStep} from './self_step_guard.mjs';
const dir=path.resolve(process.argv[2]),input=JSON.parse(fs.readFileSync(path.join(dir,'input.json'),'utf8'));
const jobStarted=performance.now();
const runtimeSourceSha=crypto.createHash('sha256').update(fs.readFileSync(new URL(import.meta.url))).digest('hex');
const contactAdapterSha=crypto.createHash('sha256').update(fs.readFileSync(new URL('./create-self-contact.mjs',import.meta.url))).digest('hex');
const selfSourceSha=crypto.createHash('sha256').update(fs.readFileSync(new URL('../../freesewing_cloth_lab/source/self-contact.js',import.meta.url))).digest('hex');
const meshSourceSha=crypto.createHash('sha256').update(fs.readFileSync(new URL('./mesh-contact.mjs',import.meta.url))).digest('hex');
const edgeSourceSha=crypto.createHash('sha256').update(fs.readFileSync(new URL('./swept-edge.mjs',import.meta.url))).digest('hex');
const vertexSourceSha=crypto.createHash('sha256').update(fs.readFileSync(new URL('./swept-vertex.mjs',import.meta.url))).digest('hex');
const guardSourceSha=crypto.createHash('sha256').update(fs.readFileSync(new URL('./self_step_guard.mjs',import.meta.url))).digest('hex');
const binary=fs.readFileSync(path.join(dir,'solver.wasm'));
const wasm=new WebAssembly.Instance(new WebAssembly.Module(binary),{}).exports;
const nv=input.positions.length,nt=input.triangles.length;
const copy=(pointer,bytes)=>new Uint8Array(wasm.memory.buffer,pointer,bytes.length).set(bytes);
for(const [name,method] of [['positions','body_ptr'],['normals','body_normal_ptr'],['indices','body_face_ptr'],['order','body_order_ptr'],['nodes','body_node_ptr']])copy(wasm[method](),Buffer.from(input.body[name],'base64'));
copy(wasm.body_edge_normal_ptr(),Buffer.from(input.body.edge_normals,'base64'));
wasm.configure_body(input.body.vertices,input.body.triangles,input.body.nodeCount);
const x=new Float32Array(wasm.memory.buffer,wasm.position_ptr(),nv*3),previous=new Float32Array(wasm.memory.buffer,wasm.previous_ptr(),nv*3);
new Float32Array(wasm.memory.buffer,wasm.uv_ptr(),nv*2).set(input.uv.flat());
new Int32Array(wasm.memory.buffer,wasm.face_ptr(),nt*3).set(input.triangles.flat());x.set(input.positions.flat());
const material=input.material;wasm.configure_material(material.Eu,material.Ev,material.G,material.nu,material.thickness,material.density);
wasm.configure_cloth(nv,nt);
const bending=input.config.弯曲;wasm.configure_bending(bending.二面角弯曲刚度估计_牛米,bending.试验二面角上限_度*Math.PI/180,bending.角约束每轮最大点修正_毫米/1000);
for(const [a,b] of input.seams)wasm.add_seam(a,b,1);
wasm.finalize_seams();for(const [a,b,rest] of input.bends)wasm.add_bend(a,b,rest);
for(const [a,b,c,d,weight] of input.hinges||[])wasm.add_hinge(a,b,c,d,weight);
if(wasm.seam_count()!==input.seams.length||wasm.bend_count()!==input.bends.length)throw Error('Native kernel omitted constraints');
if(wasm.hinge_count()!==(input.hinges||[]).length)throw Error('Native kernel omitted material hinges');
wasm.set_collision(1);wasm.set_cache(1);
wasm.set_projection_cap(input.config.数值条件.单轮接触最大修正_毫米/1000);
wasm.set_contact_margin(input.config.数值条件.接触间距_毫米/1000);
const features=input.solver_features||{},globalCount=Math.max(...input.global_ids)+1,first=new Int32Array(globalCount).fill(-1);
if(features.body_feature_contacts)wasm.set_body_feature_cap(input.config.数值条件.单轮接触最大修正_毫米/1000);
input.global_ids.forEach((id,i)=>{if(first[id]===-1)first[id]=i;});
const wp=new Float32Array(globalCount*3),wo=new Float32Array(wp.length),wi=new Float32Array(globalCount);
const inverse=new Float32Array(wasm.memory.buffer,wasm.invmass_ptr(),nv);
first.forEach((id,i)=>wi[i]=inverse[id]);
const weldedTriangles=Uint32Array.from(input.triangles.flat().map(id=>input.global_ids[id]));
const pull=()=>{first.forEach((id,i)=>{wp.set(x.subarray(id*3,id*3+3),i*3);wo.set(previous.subarray(id*3,id*3+3),i*3);});};
const push=()=>{input.global_ids.forEach((id,i)=>{x.set(wp.subarray(id*3,id*3+3),i*3);previous.set(wo.subarray(id*3,id*3+3),i*3);});};
const selfPasses=input.config.数值条件.布料接触求解迭代??1;
if(!Number.isInteger(selfPasses)||selfPasses<1)throw Error('Invalid explicit self-contact pass count');
const distanceTolerance=(input.config.数值条件.自接触距离计算分辨率_毫米??0)/1000;
pull();const self=features.self_contacts?createSelfContact(wp,weldedTriangles,input.config.数值条件.布料自接触间距_毫米/1000,
 {maxVertexCorrection:input.config.数值条件.布料接触单点修正上限_毫米/1000,
  sweptEdgeOptions:{distanceTolerance},sweptVertexOptions:{distanceTolerance}}):null;
let selfContacts=0,surfaceCalls=0;
const contactDiagnostics={vfConstraints:0,eeConstraints:0,uncertainEdges:0,conservativeEdges:0,uncertainVertices:0,conservativeVertices:0,maxPassVertexCorrection:0};
const bodyFeatureDiagnostics={calls:0,intersectingFaces:0,constraints:0,maxRoundRootPath:0};
const selfGuardDiagnostics={enabled:!!features.self_step_guard,calls:0,backtracked:0,stalledPhases:0,rejectedCandidates:0,minAlpha:1,maxVertexRollback:0,globalRollbackNormSum:0};
function bodyFeatures(){
 if(!features.body_feature_contacts)return;
 wasm.project_body_feature_contacts(1);const stats=new Float64Array(wasm.memory.buffer,wasm.body_feature_stats_ptr(),16);
 if(stats[6]||stats[12])throw Error('Actual body feature contact capacity exceeded; no completeness claim is allowed');
 bodyFeatureDiagnostics.calls++;bodyFeatureDiagnostics.intersectingFaces+=stats[4];bodyFeatureDiagnostics.constraints+=stats[5];
 bodyFeatureDiagnostics.maxRoundRootPath=Math.max(bodyFeatureDiagnostics.maxRoundRootPath,stats[7]);
}
function contacts(history){
 let safe=features.self_step_guard?history.slice():null;
 let phaseStalled=false;
 const acceptSelf=()=>{
  if(!safe)return;
  pull();const result=guardSelfStep(wp,safe,wo,wi,weldedTriangles,self?.tree);
  wp.set(result.positions);wo.set(result.previous);push();safe=result.positions.slice();
  phaseStalled ||= !result.accepted;
  selfGuardDiagnostics.calls++;selfGuardDiagnostics.backtracked+=result.alpha<1?1:0;
  selfGuardDiagnostics.stalledPhases+=result.status==='stalled'?1:0;
  selfGuardDiagnostics.rejectedCandidates+=result.rejectedCandidates;
  selfGuardDiagnostics.minAlpha=Math.min(selfGuardDiagnostics.minAlpha,result.alpha);
  selfGuardDiagnostics.maxVertexRollback=Math.max(selfGuardDiagnostics.maxVertexRollback,result.maxVertexRollback);
  selfGuardDiagnostics.globalRollbackNormSum+=result.globalRollbackNorm;
 };
 acceptSelf();
 for(let cycle=0;cycle<input.config.数值条件.身体与布料接触交替轮数;cycle++){
  if(features.surface_contacts){wasm.project_surface_contacts(input.config.数值条件.表面接触修正迭代);surfaceCalls++;}
  bodyFeatures();
  if(self){pull();self.order=Array.from({length:self.edges.length},(_,i)=>i);selfContacts+=self.solve(wp,wo,wi,selfPasses,history||wo);
   for(const key of ['vfConstraints','eeConstraints','uncertainEdges','conservativeEdges','uncertainVertices','conservativeVertices'])contactDiagnostics[key]+=self.lastProfile[key];
   contactDiagnostics.maxPassVertexCorrection=Math.max(contactDiagnostics.maxPassVertexCorrection,self.lastProfile.maxPassVertexCorrection);push();}
  acceptSelf();
 }
 if(features.surface_contacts){wasm.project_surface_contacts(input.config.数值条件.表面接触修正迭代);surfaceCalls++;}
 bodyFeatures();
 acceptSelf();
 wasm.contact_velocity(input.config.数值条件.每步数值速度保留比例,input.config.数值条件.接触摩擦系数估计);
 pull();return {stalled:phaseStalled,netPositionUnchanged:wp.every((value,i)=>Object.is(value,history[i]))};
}
if(process.argv[3]==='--resume'){
 const request=JSON.parse(fs.readFileSync(process.argv[4],'utf8')),f=request.frame;
 const unbase=value=>{const b=Buffer.from(value,'base64');return new Float32Array(b.buffer,b.byteOffset,b.byteLength/4);};
 x.set(unbase(f.positions));previous.set(unbase(f.previous));wasm.set_clock(f.step,f.time);pull();const history=wp.slice();
 wasm.step(1,0);if(contacts(history).stalled)throw Error('Formal physical step stalled: no stored position progress; clock advance is not accepted');wasm.analyze();
 const pack=array=>Buffer.from(array.buffer,array.byteOffset,array.byteLength).toString('base64');
 const result={positions:pack(x),previous:pack(previous),fields:pack(new Float32Array(wasm.memory.buffer,wasm.field_ptr(),nt*8)),
  contacts:pack(new Float32Array(wasm.memory.buffer,wasm.contacts_ptr(),nv)),step:wasm.get_frame(),time:wasm.get_time()};
 fs.writeFileSync(process.argv[5],JSON.stringify(result));self?.dispose();process.exit(0);
}
const preparation=[],preparationStarted=performance.now();
for(let i=0;i<(features.placement_relaxation_iterations||0);i++){
 const fraction=Math.min(1,(i+1)/input.config.数值条件.初始化接触距离过渡轮数);
 const margin=features.preparation_contact_start_m*(1-fraction)+input.config.数值条件.接触间距_毫米/1000*fraction;
 wasm.set_contact_margin(margin);
 previous.set(x);pull();const history=wp.slice();wasm.step(1,0);contacts(history);previous.set(x);
 if(i%10===0){wasm.analyze();const stats=Array.from(new Float32Array(wasm.memory.buffer,wasm.stats_ptr(),11));preparation.push({iteration:i+1,contact_margin_m:margin,stats});console.log(JSON.stringify({phase:'placement-relaxation',iteration:i+1,nativeVertexPenetrationMm:stats[3]*1000,maxStrain:stats[5]}));}
 if((i+1)%120===0)fs.writeFileSync(path.join(dir,`preparation-${i+1}.bin`),Buffer.from(x.buffer,x.byteOffset,x.byteLength));
}
wasm.set_contact_margin(input.config.数值条件.接触间距_毫米/1000);
const preparationElapsed=performance.now()-preparationStarted;
if(features.placement_relaxation_iterations){wasm.set_clock(0,0);previous.set(x);}
fs.writeFileSync(path.join(dir,'preparation-final.bin'),Buffer.from(x.buffer,x.byteOffset,x.byteLength));
let preparationGate='NOT_RUN';
if(features.placement_relaxation_iterations){
 const python=process.env.PHYSICS_PYTHON||'python';
 const gate=spawnSync(python,[new URL('./verify_preparation.py',import.meta.url).pathname,dir],{encoding:'utf8'});
 if(gate.stdout)process.stdout.write(gate.stdout);if(gate.stderr)process.stderr.write(gate.stderr);
 if(gate.error)throw gate.error;
 preparationGate=gate.status===0?'PASS':'FAIL';
 if(preparationGate!=='PASS'&&!process.argv.includes('--record-rejected-preparation')){
  fs.writeFileSync(path.join(dir,'preparation-rejected.json'),JSON.stringify({verdict:'FAIL',preparation,self_guard_diagnostics:selfGuardDiagnostics,preparation_elapsed_ms:preparationElapsed,reason:'Independent initial-state geometry gate failed; no formal physical trajectory recorded.'}));
  self?.dispose();process.exit(2);
 }
}
const pack=array=>Buffer.from(array.buffer,array.byteOffset,array.byteLength).toString('base64');
const frames=[],start=performance.now();let stepCalls=0;
const integrate=()=>{stepCalls++;wasm.step(1,0);};
for(let i=0;i<=input.config.数值条件.记录步数;i++){
  if(i){pull();const history=wp.slice();integrate();if(contacts(history).stalled){fs.writeFileSync(path.join(dir,'physical-step-rejected.json'),JSON.stringify({verdict:'FAIL',step:i,reason:'No stored position progress for a nonzero proposal; not accepted as physical time advance',self_guard_diagnostics:selfGuardDiagnostics}));throw Error('Formal physical step stalled');}}wasm.analyze();
  const fields=new Float32Array(wasm.memory.buffer,wasm.field_ptr(),nt*8),contactFlags=new Float32Array(wasm.memory.buffer,wasm.contacts_ptr(),nv),stats=Array.from(new Float32Array(wasm.memory.buffer,wasm.stats_ptr(),11));
  if(!Array.from(x).every(Number.isFinite)||!Array.from(fields).every(Number.isFinite))throw Error('Nonfinite real solver output');
  frames.push({step:wasm.get_frame(),time:wasm.get_time(),positions:pack(x),previous:pack(previous),fields:pack(fields),contacts:pack(contactFlags),stats});
  if(i%10===0)console.log(JSON.stringify({step:i,maxGapMm:stats[2]*1000,maxBodyPenetrationMm:stats[3]*1000,maxStrain:stats[5],maxStressPa:stats[6]}));
}
const finalPositions=Array.from(x),finalPrevious=Array.from(previous);pull();const continuationHistory=wp.slice();integrate();if(contacts(continuationHistory).stalled)throw Error('Continuation physical step stalled');const continued=Array.from(x);
x.set(finalPositions);previous.set(finalPrevious);wasm.set_clock(frames.at(-1).step,frames.at(-1).time);integrate();if(contacts(continuationHistory).stalled)throw Error('Restored continuation physical step stalled');
if(!Array.from(x).every((value,i)=>Object.is(value,continued[i])))throw Error('Saved state did not continue bit exactly');
const report={format:'intent-physical-recording/1',case:input.case,wasm_sha256:crypto.createHash('sha256').update(binary).digest('hex'),
 runtime_source_sha256:runtimeSourceSha,contact_adapter_sha256:contactAdapterSha,
 self_contact_source_sha256:selfSourceSha,verified_self_contact_triangles:self?.verifiedTriangleCount||0,
 mesh_contact_source_sha256:meshSourceSha,swept_edge_source_sha256:edgeSourceSha,swept_vertex_source_sha256:vertexSourceSha,contact_diagnostics:contactDiagnostics,
 body_feature_diagnostics:bodyFeatureDiagnostics,self_guard_diagnostics:selfGuardDiagnostics,self_guard_source_sha256:guardSourceSha,
 input_sha256:crypto.createHash('sha256').update(fs.readFileSync(path.join(dir,'input.json'))).digest('hex'),
 source_dxf_sha256:input.source_dxf_sha256,source_spec_sha256:input.source_spec_sha256,
 rest_uv:pack(new Float32Array(wasm.memory.buffer,wasm.uv_ptr(),nv*2)),
 frames,preparation,recorded_physical_steps:frames.length-1,integration_calls_total:stepCalls,placement_relaxation_iterations:features.placement_relaxation_iterations||0,
 preparation_gate:preparationGate,recording_role:preparationGate==='PASS'?'candidate':'failure benchmark; initial-state acceptance is not PASS',
 preparation_gate_sha256:fs.existsSync(path.join(dir,'preparation-gate.json'))?crypto.createHash('sha256').update(fs.readFileSync(path.join(dir,'preparation-gate.json'))).digest('hex'):null,
 surface_projection_calls:surfaceCalls,self_contact_corrections:selfContacts,continuation_bit_exact:true,elapsed_ms:performance.now()-start,
 preparation_elapsed_ms:preparationElapsed,total_elapsed_ms:performance.now()-jobStarted,
 physical_fit:'NOT_RUN',scope:'Actual native dynamics under explicitly synthetic experimental conditions; independent geometry/field audit required.'};
report.native_stats_scope='stats[3] reports vertex penetration only; independent surface samples and both triangle crossing directions are authoritative.';
fs.writeFileSync(path.join(dir,'trajectory.json'),JSON.stringify(report));
self?.dispose();
console.log(JSON.stringify({frames:frames.length,continuation_bit_exact:true,elapsed_ms:report.elapsed_ms}));
