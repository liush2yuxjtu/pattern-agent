import assert from 'node:assert/strict';
import fs from 'node:fs';
import crypto from 'node:crypto';
import {guardSelfStep} from '../../../experiments/intent-edit-review/physics/self_step_guard.mjs';

const runtimeUrl=new URL('../../../experiments/intent-edit-review/physics/run_native.mjs',import.meta.url);
const guardUrl=new URL('../../../experiments/intent-edit-review/physics/self_step_guard.mjs',import.meta.url);
const runtime=fs.readFileSync(runtimeUrl,'utf8');
const begin=runtime.indexOf('function contacts(history){'),end=runtime.indexOf("\nif(process.argv[3]==='--resume')",begin);
assert.ok(begin>=0&&end>begin,'The current contacts function must be present');
const contactsSource=runtime.slice(begin,end);

// Execute the CURRENT private runtime function unchanged. Only its external
// native/body phases are supplied synthetic proposals; the guard is the real
// imported implementation. This is an acceptance-policy control, not a WASM
// cloth simulation or a whole-garment verification.
const runCurrent=new Function('guardSelfStep','reference','proposal','bodyProposal','triangles',`
 const wp=proposal.slice(),wo=reference.slice(),wi=new Float32Array(reference.length/3).fill(1),weldedTriangles=triangles;
 const features={self_step_guard:true,surface_contacts:true},self=null;
 const input={config:{数值条件:{身体与布料接触交替轮数:1,表面接触修正迭代:1,每步数值速度保留比例:.2,接触摩擦系数估计:.3}}};
 const pull=()=>{},push=()=>{},bodyFeatures=()=>{};
 const wasm={project_surface_contacts:()=>wp.set(bodyProposal),contact_velocity:()=>{}};
 let surfaceCalls=0,selfContacts=0;const selfPasses=1,contactDiagnostics={};
 const selfGuardDiagnostics={calls:0,backtracked:0,stalledPhases:0,rejectedCandidates:0,minAlpha:1,maxVertexRollback:0,globalRollbackNormSum:0};
 ${contactsSource}
 const result=contacts(reference);
 return {result,positions:Array.from(wp),previous:Array.from(wo),diagnostics:selfGuardDiagnostics};
`);
const flat=p=>Float32Array.from(p.flat());
const summarize=r=>({accepted:r.accepted,status:r.status,alpha:r.alpha,
 proposedDisplacementNorm:r.proposedDisplacementNorm,acceptedDisplacementNorm:r.acceptedDisplacementNorm});

// Approximately one-metre world coordinates, not a large-coordinate-only
// numerical corner. The two triangles legally touch along a geometric edge;
// one positive f32 y-ulp introduces positive-area coplanar overlap.
const reference=flat([[1,1,0],[1.02,1,0],[1,1.02,0],[1.01,.98,0],[1.02,1,0]]);
const proposal=reference.slice();proposal[13]=Math.fround(1+2**-23);
const triangles=[0,1,2,0,3,4],mass=new Float32Array(5).fill(1);
const rejected=guardSelfStep(proposal,reference,reference.slice(),mass,triangles);
assert.equal(rejected.accepted,false);assert.equal(rejected.status,'stalled');
assert.equal(rejected.alpha,.5);assert.equal(rejected.acceptedDisplacementNorm,0);
const bodyProposal=rejected.positions.slice();for(let i=2;i<bodyProposal.length;i+=3)bodyProposal[i]=.0001;
const body=guardSelfStep(bodyProposal,rejected.positions,rejected.previous,mass,triangles);
const oldFalseNegative=(rejected.proposedDisplacementNorm>0||body.proposedDisplacementNorm>0)&&body.positions.every((v,i)=>Object.is(v,reference[i]));
assert.equal(oldFalseNegative,false);
const currentRejected=runCurrent(guardSelfStep,reference,proposal,bodyProposal,triangles);
assert.equal(currentRejected.result.stalled,true,'A later legal phase must not hide any earlier rejected phase');
assert.equal(currentRejected.result.netPositionUnchanged,false);

// A support reaction can legitimately restore a whole physical step's initial
// coordinates. Both guard phases make progress and are accepted; the net-zero
// position is not itself a quantized/stalled guard proposal.
const rest=flat([[0,.001,0],[.02,.001,0],[0,.001,.02]]),down=rest.slice();
for(let i=1;i<down.length;i+=3)down[i]-=.00001;
const simple=[0,1,2],free=new Float32Array(3).fill(1);
const falling=guardSelfStep(down,rest,rest.slice(),free,simple);
const supported=guardSelfStep(rest,falling.positions,falling.previous,free,simple);
assert.ok(falling.accepted&&supported.accepted);
assert.ok(falling.acceptedDisplacementNorm>0&&supported.acceptedDisplacementNorm>0);
const oldFalsePositive=(falling.proposedDisplacementNorm>0||supported.proposedDisplacementNorm>0)&&supported.positions.every((v,i)=>Object.is(v,rest[i]));
assert.equal(oldFalsePositive,true);
const currentSupported=runCurrent(guardSelfStep,rest,down,rest,simple);
assert.equal(currentSupported.result.stalled,false,'A legal zero-net-position support equilibrium must remain accepted');
assert.equal(currentSupported.result.netPositionUnchanged,true);

const report={verdict:'PASS for the corrected acceptance policy only',
 scope:'Actual guard plus unchanged extracted runtime contacts; synthetic external phase proposals, not native cloth physics or garment acceptance.',
 runtime_sha256:crypto.createHash('sha256').update(runtime).digest('hex'),
 guard_sha256:crypto.createHash('sha256').update(fs.readFileSync(guardUrl)).digest('hex'),
 cases:[
  {name:'rejected_native_phase_masked_by_later_body_progress',
   reference:Array.from(reference),proposal:Array.from(proposal),bodyProposal:Array.from(bodyProposal),triangles,
   firstGuard:summarize(rejected),bodyGuard:summarize(body),
   oldWholeStepPredicateStalled:oldFalseNegative,currentRuntime:currentRejected},
  {name:'valid_supported_equilibrium_wrongly_rejected',
   reference:Array.from(rest),proposal:Array.from(down),bodyProposal:Array.from(rest),triangles:simple,
   firstGuard:summarize(falling),bodyGuard:summarize(supported),
   oldWholeStepPredicateStalled:oldFalsePositive,currentRuntime:currentSupported}
 ]};
console.log(JSON.stringify(report,null,2));
