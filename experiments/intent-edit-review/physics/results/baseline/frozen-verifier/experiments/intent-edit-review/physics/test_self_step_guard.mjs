import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';
import {guardSelfStep,InvalidSelfStepReferenceError} from './self_step_guard.mjs';
import {MeshContact} from './mesh-contact.mjs';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../../..'),flat=p=>Float32Array.from(p.flat()),oracleCases=[],checks=[];
const faces=[0,1,2,3,4,5],candidate=flat([[-.02,-.02,0],[.02,-.02,0],[0,.02,0],[0,-.005,-.01],[0,-.005,.01],[0,.005,.01]]),reference=candidate.slice();reference[9]=reference[12]=reference[15]=.06;
const mass=Float32Array.from([0,0,0,1,1,1]),record=(name,positions,triangles,pairs=0,degenerate=0)=>oracleCases.push({name,positions:Array.from(positions),triangles:Array.from(triangles),pairs,degenerate});
const bytes=a=>Buffer.from(a.buffer,a.byteOffset,a.byteLength);
const serialize=result=>({...result,positions:Array.from(result.positions),previous:result.previous?Array.from(result.previous):null});
function assertSync(result,proposed,previous){for(let i=0;i<proposed.length;i++){const delta=result.positions[i]-Math.fround(proposed[i]);const expected=delta===0?previous[i]:previous instanceof Float32Array?Math.fround(previous[i]+.8*delta):previous[i]+.8*delta;assert.ok(Object.is(result.previous[i],expected),`Previous sync index${i}`);}}
function assertInterpolation(result,proposed,origin,inverseMass){for(let id=0;id<inverseMass.length;id++)for(let k=0;k<3;k++){const i=id*3+k,expected=inverseMass[id]===0?Math.fround(proposed[i]):Math.fround(Math.fround(origin[i])+result.alpha*(Math.fround(proposed[i])-Math.fround(origin[i])));assert.ok(Object.is(result.positions[i],expected),`Interpolation index${i}`);}}

// Pure mode owns its returned coordinates. Nothing, including the supplied BVH
// geometry and native node bounds, is rewritten while inspecting references.
{
 const p=candidate.slice(),r=reference.slice(),prev=p.slice(),inv=mass.slice(),indices=faces.slice(),old=[p.slice(),r.slice(),prev.slice(),inv.slice(),indices.slice()];
 const treeOwner=new MeshContact(p,indices,.001),geometryBefore=treeOwner.vertices.slice(),boundsBefore=[];treeOwner.tree.traverse((depth,leaf,bounds)=>boundsBefore.push(Array.from(bounds)));
 const result=guardSelfStep(p,r,prev,inv,indices,treeOwner.tree);assert.equal(result.accepted,true);assert.equal(result.status,'backtracked');assert.equal(result.alpha,.5);assert.equal(result.referenceReport.pairCount,0);assert.equal(result.rejected[0].pairCount,1);assert.equal(result.acceptedReport.pairCount,0);assert.equal(result.triangleCount,2);assert.equal(result.bvhTriangleCount,2);
 assertInterpolation(result,p,r,inv);assertSync(result,p,prev);assert.ok(result.globalRollbackNorm>0);assert.ok(result.maxVertexRollback>.0005,'This safeguard is not a per-vertex contact cap');assert.ok(result.acceptedDisplacementNorm>0&&result.proposedDisplacementNorm>result.acceptedDisplacementNorm);assert.equal(result.fallbackToReference,false);assert.equal(result.zeroStoredProgress,false);
 for(let id=0;id<3;id++)assert.deepEqual(result.positions.slice(id*3,id*3+3),p.slice(id*3,id*3+3));
 [p,r,prev,inv,indices].forEach((value,i)=>assert.deepEqual(value,old[i]));assert.deepEqual(treeOwner.vertices,geometryBefore);const boundsAfter=[];treeOwner.tree.traverse((depth,leaf,bounds)=>boundsAfter.push(Array.from(bounds)));assert.deepEqual(boundsAfter,boundsBefore);
 result.positions[0]=10;assert.deepEqual(p,old[0]);treeOwner.dispose();
 const accepted=guardSelfStep(candidate,reference,null,mass,faces);record('analytic-reference',reference,faces);record('analytic-proposed-crossing',candidate,faces,1);record('analytic-accepted',accepted.positions,faces);
 checks.push({pureInputsAndBVHUnchanged:true,alpha:accepted.alpha,globalRollbackNorm:accepted.globalRollbackNorm,maxVertexRollback:accepted.maxVertexRollback,allFacesRetained:accepted.triangleCount});
}

// One scalar alpha is applied to the WHOLE movable mesh, including an unrelated
// third triangle; this does not selectively hide or freeze colliding faces.
{
 const p=Float32Array.from([...candidate,2,0,0,2.02,0,0,2,.02,0]),r=Float32Array.from([...reference,2.1,0,0,2.12,0,0,2.1,.02,0]),inv=new Float32Array(9).fill(1),triangles=[...faces,6,7,8],result=guardSelfStep(p,r,null,inv,triangles);
 assert.equal(result.alpha,.5);assertInterpolation(result,p,r,inv);assert.equal(result.triangleCount,3);assert.ok(result.positions[18]!==p[18]);record('whole-movable-mesh-accepted',result.positions,triangles);checks.push({globalInterpolationIncludingUnrelatedFace:true});
}

for(const IndexType of [Array,Uint8Array,Uint16Array,Uint32Array,Int32Array]){
 const p=[],r=[],triangles=[];
 for(let copy=0;copy<20;copy++){
  const offset=p.length/3;for(let id=0;id<6;id++)for(let k=0;k<3;k++){p.push(candidate[id*3+k]+(k===0?copy*.2:0));r.push(reference[id*3+k]+(k===0?copy*.2:0));}
  triangles.push(...faces.map(id=>id+offset));
 }
 const index=IndexType.from(triangles),indexBefore=Array.from(index),result=guardSelfStep(Float32Array.from(p),Float32Array.from(r),null,new Float32Array(p.length/3).fill(1),index);
 assert.equal(result.triangleCount,40);assert.equal(result.bvhTriangleCount,40);assert.equal(result.rejected[0].pairCount,20);assert.equal(result.acceptedReport.pairCount,0);assert.deepEqual(Array.from(index),indexBefore);record('multi-leaf-'+IndexType.name,result.positions,index);checks.push({indexType:IndexType.name,actualBVHFaces:40,rejectedCrossings:20});
}

// Explicit in-place mode changes only candidate/previous. Zero deltas preserve
// signed zeros, including fixed previous values, byte-for-byte.
{
 const p=candidate.slice(),r=reference.slice(),previous=p.slice();p[2]=-0;r[2]=-0;previous[2]=-0;
 const oldP=p.slice(),oldPrevious=previous.slice(),oldReference=r.slice(),result=guardSelfStep(p,r,previous,mass,faces,null,{inPlace:true});
 assert.deepEqual(p,result.positions);assert.deepEqual(previous,result.previous);assert.deepEqual(r,oldReference);assertSync(result,oldP,oldPrevious);assert.ok(Object.is(previous[2],-0));assert.deepEqual(p.slice(0,9),oldP.slice(0,9));checks.push({explicitInPlacePreviousSynchronization:true,fixedSignedZeroPreserved:true});
}

// Reference is a hard precondition, not an untangling target. Errors are explicit
// and occur before any output buffer can be changed.
{
 const p=candidate.slice(),prev=p.slice(),before=p.slice();
 assert.throws(()=>guardSelfStep(p,p.slice(),prev,new Float32Array(6).fill(1),faces,null,{inPlace:true}),error=>error instanceof InvalidSelfStepReferenceError&&error.code==='INVALID_REFERENCE'&&error.referenceReport.pairCount===1);assert.deepEqual(p,before);assert.deepEqual(prev,before);
 const badFixed=reference.slice();badFixed[0]+=.001;assert.throws(()=>guardSelfStep(candidate,badFixed,null,mass,faces),/Fixed nodes/);
 const same=reference.slice();assert.throws(()=>guardSelfStep(same,same,same,new Float32Array(6).fill(1),faces,null,{inPlace:true}),/aliases/);
 const packed=new Float32Array(reference.length*2),overlapA=packed.subarray(0,reference.length),overlapB=packed.subarray(3,3+reference.length);overlapA.set(reference);assert.throws(()=>guardSelfStep(overlapA,reference,overlapB,new Float32Array(6).fill(1),faces,null,{inPlace:true}),/aliases/);
 checks.push({invalidReferenceThrowsWithoutMutation:true,fixedMismatchRejected:true,overlappingOutputBuffersRejected:true});
}

// Shared2 positive-area fold-over and a degenerate midpoint both reject. No
// topology exclusion is allowed to turn those cases into an accepted mesh.
{
 const r=flat([[0,0,0],[.02,0,0],[0,.02,0],[.005,-.02,0]]),p=r.slice();p[10]=.02;const triangles=[0,1,2,1,0,3],result=guardSelfStep(p,r,null,new Float32Array(4).fill(1),triangles);
 assert.equal(result.alpha,.25);assert.equal(result.rejected[0].unsupportedShared2,1);assert.equal(result.rejected[1].degenerateTriangles,1);assert.equal(result.rejectedCandidates,2);assert.equal(result.triangleCount,2);record('shared2-proposed-overlap',p,triangles,1);record('shared2-accepted',result.positions,triangles);
 const duplicate=flat([[0,0,0],[.02,0,0],[0,.02,0]]);assert.throws(()=>guardSelfStep(duplicate,duplicate,null,new Float32Array(3).fill(1),[0,1,2,2,1,0]),error=>error instanceof InvalidSelfStepReferenceError&&error.referenceReport.unsupportedShared3===1);
 const degenerate=duplicate.slice();degenerate[7]=0;assert.throws(()=>guardSelfStep(duplicate,degenerate,null,new Float32Array(3).fill(1),[0,1,2]),error=>error instanceof InvalidSelfStepReferenceError&&error.referenceReport.degenerateTriangles===1);
 const nondegenerate=guardSelfStep(degenerate,duplicate,null,new Float32Array(3).fill(1),[0,1,2]);assert.equal(nondegenerate.rejected[0].degenerateTriangles,1);assert.equal(nondegenerate.alpha,.5);record('degenerate-proposal-rejected',degenerate,[0,1,2],0,1);record('nondegenerate-accepted',nondegenerate.positions,[0,1,2]);
 checks.push({sharedTwoPositiveAreaRejected:true,sharedThreeReferenceRejected:true,degenerateCandidateAndReferenceRejected:true});
}

// A budget-limited alpha0 return is geometrically safe but explicitly NOT an
// accepted nonzero physical step; the caller must not advance a frozen clock.
{
 const p=candidate.slice(),prev=p.slice(),result=guardSelfStep(p,reference,prev,mass,faces,null,{maxBacktracks:0,inPlace:true});
 assert.equal(result.alpha,0);assert.equal(result.fallbackToReference,true);assert.equal(result.zeroStoredProgress,true);assert.equal(result.accepted,false);assert.equal(result.status,'stalled');assert.equal(result.acceptedDisplacementNorm,0);assert.ok(result.proposedDisplacementNorm>0);assert.deepEqual(result.positions,reference);assert.deepEqual(p,reference);assertSync(result,candidate,candidate);
 record('budget-reference-fallback',result.positions,faces);checks.push({budgetFallbackAccepted:false,status:result.status,alpha:0});
}

// Positive alpha can still round all stored Float32 coordinates back to the
// reference. That stalled case must not masquerade as physical progress.
{
 const base=1048576,r=flat([[base,base,0],[base+.125,base,0],[base,base+.125,0]]),p=r.slice();p[7]=base;
 const result=guardSelfStep(p,r,null,new Float32Array(3).fill(1),[0,1,2]);assert.ok(result.alpha>0);assert.equal(result.zeroStoredProgress,true);assert.equal(result.accepted,false);assert.equal(result.status,'stalled');assert.equal(result.fallbackToReference,false);assert.equal(result.acceptedDisplacementNorm,0);record('f32-stalled-reference',result.positions,[0,1,2]);checks.push({positiveAlphaFloat32StallDetected:true,alpha:result.alpha});
}

{
 const result=guardSelfStep(reference,reference,null,mass,faces);assert.equal(result.accepted,true);assert.equal(result.alpha,1);assert.equal(result.proposedDisplacementNorm,0);assert.equal(result.zeroStoredProgress,true);assert.equal(result.globalRollbackNorm,0);assert.equal(result.continuousCollisionDetection,false);assert.equal(result.physicalAcceptance,'NOT_EVALUATED');
 assert.throws(()=>guardSelfStep(candidate,reference,null,mass,faces,null,{maxBacktracks:-1}),RangeError);assert.throws(()=>guardSelfStep(candidate,reference,null,mass,faces,null,{intersectionEpsilon:1e-3}),RangeError);const bad=reference.slice();bad[0]=NaN;assert.throws(()=>guardSelfStep(candidate,bad,null,mass,faces),TypeError);checks.push({unchangedProposalAccepted:true,thresholdCannotBeWeakened:true});
}

// A whole new Node process gets exactly the same returned state and meaningful
// diagnostics. No pair-side, tree-identity or cross-physical-step cache is needed.
function assertFreshProcess(p,r,prev,inv,triangles,result){
 const script="import fs from 'node:fs';import {guardSelfStep} from './experiments/intent-edit-review/physics/self_step_guard.mjs';const s=JSON.parse(fs.readFileSync(0,'utf8')),result=guardSelfStep(Float32Array.from(s.candidate),Float32Array.from(s.reference),s.previous?Float32Array.from(s.previous):null,Float32Array.from(s.inverseMass),s.triangles);console.log(JSON.stringify({...result,positions:Array.from(result.positions),previous:result.previous?Array.from(result.previous):null}));";
 const replay=spawnSync(process.execPath,['--input-type=module','-e',script],{cwd:root,input:JSON.stringify({candidate:Array.from(p),reference:Array.from(r),previous:prev?Array.from(prev):null,inverseMass:Array.from(inv),triangles:Array.from(triangles)}),encoding:'utf8',maxBuffer:16*1024*1024});assert.equal(replay.status,0,replay.stderr);assert.deepEqual(JSON.parse(replay.stdout),JSON.parse(JSON.stringify(serialize(result))));
}
assertFreshProcess(candidate,reference,candidate,mass,faces,guardSelfStep(candidate,reference,candidate,mass,faces));checks.push({newProcessReplay:'bit-exact including state and geometry diagnostics'});

let actual33='SKIP: work fixture unavailable';
const fixture=process.env.SELF_GUARD_REAL_FIXTURE||path.join(root,'work/intent-physics/baseline-run33');
if(fs.existsSync(path.join(fixture,'input.json'))&&fs.existsSync(path.join(fixture,'preparation-final.bin'))&&fs.existsSync(path.join(fixture,'solver.wasm'))){
 const data=JSON.parse(fs.readFileSync(path.join(fixture,'input.json'))),raw=fs.readFileSync(path.join(fixture,'preparation-final.bin')),all=new Float32Array(raw.buffer,raw.byteOffset,raw.byteLength/4),count=Math.max(...data.global_ids)+1,first=new Int32Array(count).fill(-1);data.global_ids.forEach((id,i)=>{if(first[id]===-1)first[id]=i;});
 const r=new Float32Array(count*3),p=new Float32Array(count*3),triangles=data.triangles.flat().map(id=>data.global_ids[id]);first.forEach((id,i)=>{r.set(data.positions[id],i*3);p.set(all.subarray(id*3,id*3+3),i*3);});
 const w=new WebAssembly.Instance(new WebAssembly.Module(fs.readFileSync(path.join(fixture,'solver.wasm'))),{}).exports,nv=data.positions.length,nt=data.triangles.length;new Float32Array(w.memory.buffer,w.position_ptr(),nv*3).set(data.positions.flat());new Float32Array(w.memory.buffer,w.uv_ptr(),nv*2).set(data.uv.flat());new Int32Array(w.memory.buffer,w.face_ptr(),nt*3).set(data.triangles.flat());const material=data.material;w.configure_material(material.Eu,material.Ev,material.G,material.nu,material.thickness,material.density);w.configure_cloth(nv,nt);for(const [a,b] of data.seams)w.add_seam(a,b,1);w.finalize_seams();const nativeMass=new Float32Array(w.memory.buffer,w.invmass_ptr(),nv),inverse=Float32Array.from(first,i=>nativeMass[i]);
 const previous=p.slice(),before=[p.slice(),r.slice(),previous.slice(),inverse.slice(),triangles.slice()],treeOwner=new MeshContact(p,triangles,.001),treeBefore=treeOwner.vertices.slice(),result=guardSelfStep(p,r,previous,inverse,triangles,treeOwner.tree);
 assert.equal(result.referenceReport.pairCount,0);assert.equal(result.rejected[0].pairCount,6);assert.equal(result.acceptedReport.pairCount,0);assert.equal(result.acceptedReport.degenerateTriangles,0);assert.equal(result.triangleCount,7186);assert.equal(result.bvhTriangleCount,7186);assert.ok(result.positions instanceof Float32Array);assertInterpolation(result,p,r,inverse);assertSync(result,p,previous);[p,r,previous,inverse,triangles].forEach((value,i)=>assert.deepEqual(value,before[i]));assert.deepEqual(treeOwner.vertices,treeBefore);assertFreshProcess(p,r,previous,inverse,triangles,result);
 assert.throws(()=>guardSelfStep(p,p,previous,inverse,triangles),error=>error instanceof InvalidSelfStepReferenceError&&error.referenceReport.pairCount===6);record('actual33-complete-reference',r,triangles);record('actual33-complete-candidate',p,triangles,6);record('actual33-complete-guarded',result.positions,triangles);treeOwner.dispose();actual33='PASS';checks.push({actual33CompleteMesh:true,referencePairs:0,proposedPairs:6,returnedPairs:0,triangleCount:7186,alpha:result.alpha,globalRollbackNorm:result.globalRollbackNorm,proposedDisplacementNorm:result.proposedDisplacementNorm,acceptedDisplacementNorm:result.acceptedDisplacementNorm,fallbackToReference:result.fallbackToReference,zeroStoredProgress:result.zeroStoredProgress,newProcessReplay:'bit-exact'});
}else checks.push({actual33CompleteMesh:'SKIP',reason:'Set SELF_GUARD_REAL_FIXTURE to the complete frozen run directory; synthetic tests do not replace this actual-mesh check'});

// Independent NumPy/SciPy SAT and topology oracle. It imports no guard module,
// production collision detector, solver or recovery implementation.
const venv=path.join(root,'work/intent-physics/venv/bin/python'),python=process.env.PATTERN_ORACLE_PYTHON||(fs.existsSync(venv)?venv:'python3');
const script="import json,sys,numpy as np;sys.path.insert(0,'experiments/oneshot_control');from independent_oracle_v2 import intersect_pairs,mesh_audit;cases=json.load(sys.stdin);out=[]\nfor c in cases:\n p=np.asarray(c['positions'],float).reshape(-1,3);f=np.asarray(c['triangles'],int).reshape(-1,3);a=mesh_audit(p,f);out.append({'name':c['name'],'strictPairs':len(intersect_pairs(p,f,epsilon_m=1e-6)),'degenerate':a['degenerate_triangles'],'triangleCount':a['triangle_count']})\nprint(json.dumps(out))";
const audit=spawnSync(python,['-c',script],{cwd:root,input:JSON.stringify(oracleCases),encoding:'utf8',maxBuffer:4*1024*1024});assert.equal(audit.status,0,audit.stderr);const independent=JSON.parse(audit.stdout);
for(let i=0;i<oracleCases.length;i++){assert.equal(independent[i].strictPairs,oracleCases[i].pairs,oracleCases[i].name);assert.equal(independent[i].degenerate,oracleCases[i].degenerate,oracleCases[i].name);assert.equal(independent[i].triangleCount,oracleCases[i].triangles.length/3);}
console.log(JSON.stringify({verdict:'PASS',actual33,checks,independentOracle:independent,scope:'Discrete full-mesh Float32 accepted-step controls only. Body/arm/material/physical accuracy and continuous collisions are not approved; alpha0 or zero stored progress is an explicit rejected/stalled physical-step boundary.'},null,2));
