import assert from 'node:assert/strict';
import {existsSync} from 'node:fs';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import {MeshContact} from './mesh-contact.mjs';
import {gatherTriangleContacts,trianglePairOverlap} from './triangle-contact.mjs';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../../..');
const epsilon=1e-6,thickness=.001,cap=.0005,receipts=[],oracleCases=[];
const analytic={positions:[[-.02,-.02,0],[.02,-.02,0],[0,.02,0],[0,-.005,-.01],[0,-.005,.01],[0,.005,.01]],triangles:[[0,1,2],[3,4,5]],inverseMass:[1,1,1,1,1,1]};
// Six unchanged welded coordinates from blocked run28 preparation, faces
// 6531/6605. Their min VF/EE feature distances are 5.109/8.159mm, both >h.
const actual={sourceFaces:[6531,6605],positions:[
 [.36946216225624084,1.042889952659607,.1808759868144989],
 [.4054962992668152,1.0722401142120361,.18389423191547394],
 [.4335792660713196,1.055396556854248,.15022942423820496],
 [.4085386097431183,1.092690110206604,.16909736394882202],
 [.4193747043609619,1.105789303779602,.18925508856773376],
 [.3943803310394287,1.0815573930740356,.16987982392311096]
],triangles:[[0,2,4],[3,5,1]],inverseMass:[25831.134765625,16089.4580078125,23229.982421875,29426.634765625,25575.021484375,23886.501953125]};
const asPoints=(p,triangles)=>triangles.map(face=>face.map(id=>Array.from(p.slice(id*3,id*3+3))));
const distance=(a,b,id)=>Math.hypot(...[0,1,2].map(k=>a[id*3+k]-b[id*3+k]));
const recordOracle=(name,p,triangles,expected)=>oracleCases.push({name,vertices:Array.from({length:p.length/3},(_,id)=>Array.from(p.slice(id*3,id*3+3))),triangles,expected});

// Test-only injection leaves the production MeshContact source unchanged. Its
// real inverse-mass callback, averaging, per-PASS cap and previous sync apply.
// Triangle-only recovery is intentionally distinct from naive VF+EE addition.
class TriangleRecovery extends MeshContact{
 solve(p,previous,inverseMass,passes=2,history=previous){this.testInverseMass=inverseMass;this.triangleProfiles=[];return super.solve(p,previous,inverseMass,passes,history);}
 _gatherVertices(){return 0;}
 _gatherEdges(snapshot,history,add){const result=gatherTriangleContacts(snapshot,history,this.testInverseMass,this.faces,this.tree,this.thickness,add);this.triangleProfiles.push(result);return result.contacts;}
}
class NaiveCombined extends TriangleRecovery{
 _gatherVertices(...args){return MeshContact.prototype._gatherVertices.apply(this,args);}
 _gatherEdges(...args){return MeshContact.prototype._gatherEdges.apply(this,args)+super._gatherEdges(...args);}
}
function recover(fixture,passes,Type=Float64Array,masses=fixture.inverseMass){
 const p=Type.from(fixture.positions.flat()),before=p.slice(),history=p.slice(),historyBefore=history.slice(),previous=p.slice(),inverseMass=Float64Array.from(masses);
 const solver=new TriangleRecovery(p,fixture.triangles.flat(),thickness,{maxVertexCorrection:cap});
 const contacts=solver.solve(p,previous,inverseMass,passes,history);
 assert.deepEqual(history,historyBefore,'Recovery changed the caller-owned history');
 assert.ok(solver.lastPassMaxCorrections.every(x=>x<=cap),'Recovery exceeded the actual whole-pass displacement cap');
 for(let id=0;id<inverseMass.length;id++){
  if(inverseMass[id]===0){assert.equal(distance(p,before,id),0);assert.equal(distance(previous,before,id),0);}
  if(Type===Float64Array)for(let k=0;k<3;k++)assert.ok(Math.abs(previous[id*3+k]-before[id*3+k]-.8*(p[id*3+k]-before[id*3+k]))<1e-13);
 }
 const row={p,previous,history,contacts,batches:solver.lastProfile.batches,maxPass:solver.lastMaxVertexCorrection,profiles:solver.triangleProfiles};solver.dispose();return row;
}

// Narrow phase includes deep interior edge/face crossings, coplanar positive
// area and incident faces; it excludes geometric boundary-only contacts.
{
 const a=[[0,0,0],[.02,0,0],[0,.02,0]];
 const fixtures=[
  {name:'interior-crossing',b:[[.005,.005,-.01],[.015,.005,.01],[.005,.015,.01]],hit:true},
  {name:'coplanar-positive-area',b:[[.005,.005,0],[.015,.005,0],[.005,.015,0]],hit:true},
  {name:'shared-point-only',b:[[0,0,0],[-.02,0,.01],[0,-.02,.01]],hit:false},
  {name:'shared-edge-only',b:[[0,0,0],[.02,0,0],[.005,-.02,.01]],hit:false},
  {name:'edge-on-face-interior-only',b:[[.005,.005,0],[.01,.005,0],[.0075,.005,.01]],hit:false},
  {name:'coplanar-edge-only',b:[[0,0,0],[.02,0,0],[.005,-.02,0]],hit:false},
  {name:'parallel-separated',b:[[0,0,.001],[.02,0,.001],[0,.02,.001]],hit:false}
 ];
 for(const f of fixtures){const hit=trianglePairOverlap(a,f.b,epsilon);assert.equal(Boolean(hit),f.hit,f.name);recordOracle(f.name,Float64Array.from([...a,...f.b].flat()),[[0,1,2],[3,4,5]],f.hit?1:0);}
 receipts.push({narrowPhaseFixtures:fixtures.length,boundaryOnlyExcluded:true,coplanarAreaIncluded:true});
}

// Multiple leaves and every supported integer index representation reach all
// faces. The large translation also checks exact snapshot leaf bounds rather
// than relying on Float32 node min/max storage.
for(const IndexType of [Array,Uint8Array,Uint16Array,Uint32Array,Int32Array]){
 const positions=[],triangles=[];
 for(let copy=0;copy<20;copy++){
  const offset=positions.length/3;
  for(const p of analytic.positions)positions.push(p[0]+1e4+copy*.1,p[1],p[2]);
  triangles.push(...analytic.triangles.flat().map(id=>id+offset));
 }
 const p=Float64Array.from(positions),index=IndexType.from(triangles),solver=new MeshContact(p,index,thickness);
 const result=gatherTriangleContacts(p,p.slice(),new Float64Array(p.length/3).fill(1),index,solver.tree,thickness,()=>true);
 assert.equal(result.triangleCount,40);assert.equal(result.bvhTriangleCount,40);assert.equal(result.intersectingPairs,20,IndexType.name);
 assert.equal(result.shared0,20);assert.equal(result.shared1,0);assert.equal(result.contacts,40);
 solver.dispose();receipts.push({indexType:IndexType.name,bvhFaces:result.bvhTriangleCount,deepCrossings:result.intersectingPairs});
}

// Both independently certified deep fixtures are invisible to the old feature
// solver. New isolated triangle recovery must actually remove the strict pair.
for(const [name,fixture,passes] of [['analytic',analytic,40],['actual-6531-6605',actual,80]])for(const Type of [Float64Array,Float32Array]){
 const p=Type.from(fixture.positions.flat()),before=p.slice(),old=new MeshContact(p,fixture.triangles.flat(),thickness,{maxVertexCorrection:cap});
 assert.equal(old.solve(p,p.slice(),Float64Array.from(fixture.inverseMass),40,before),0,`${name} old proximity negative control`);
 assert.deepEqual(p,before);old.dispose();recordOracle(`${name}-${Type.name}-before`,before,fixture.triangles,1);
 const result=recover(fixture,passes,Type);assert.ok(result.contacts>0);recordOracle(`${name}-${Type.name}-triangle-recovery`,result.p,fixture.triangles,0);
 receipts.push({fixture:name,positionType:Type.name,oldContacts:0,recoveryContacts:result.contacts,requestedPasses:passes,actualBatches:result.batches,maxActualPassDisplacement_m:result.maxPass});
}

// A fixed target plane stays fixed, while the movable penetrating sheet is
// corrected. This uses the actual parent's inverse-mass callback.
{
 const fixed=recover(analytic,80,Float64Array,[1,1,1,0,0,0]);
 recordOracle('fixed-B-recovery',fixed.p,analytic.triangles,0);
 receipts.push({fixedTriangleVertices:[3,4,5],fixedCoordinatesPreserved:true,maxActualPassDisplacement_m:fixed.maxPass});
}

// Shared1 uses the one common material point as a plane anchor; no duplicate
// seam node is introduced, and the common point need not be thickness apart.
{
 const fixture={positions:[[0,0,0],[.02,0,0],[0,.02,0],[.02,.005,0],[.005,.02,0]],triangles:[[0,1,2],[0,3,4]],inverseMass:[0,1,1,0,0]};
 recordOracle('shared1-coplanar-before',Float64Array.from(fixture.positions.flat()),fixture.triangles,1);
 const result=recover(fixture,10);assert.equal(result.profiles[0].shared1,1);assert.equal(result.profiles[0].coplanarPairs,1);
 assert.deepEqual(Array.from(result.p.slice(0,3)),[0,0,0]);recordOracle('shared1-coplanar-after',result.p,fixture.triangles,0);
 receipts.push({sharedOneVertex:'anchored response',fixedCommonPoint:true,recoveryContacts:result.contacts});
}

// Shared2 fold-over is deliberately unsupported, not silently excluded and
// never counted as a successful response. Ordinary shared-edge contact is 0.
{
 const p=Float64Array.from([0,0,0,.02,0,0,0,.02,0,.005,.01,0]),faces=[0,1,2,0,1,3];let proposed=0;
 const result=gatherTriangleContacts(p,p,new Float64Array(4).fill(1),faces,null,thickness,()=>{proposed++;return true;});
 assert.equal(result.intersectingPairs,1);assert.equal(result.unsupportedShared2,1);assert.equal(result.contacts,0);assert.equal(proposed,0);assert.equal(result.pairs[0].supported,false);
 recordOracle('shared2-unsupported-positive-area',p,[[0,1,2],[0,1,3]],1);
 p[11]=-.01;
 const boundary=gatherTriangleContacts(p,p,new Float64Array(4).fill(1),faces,null,thickness,()=>true);assert.equal(boundary.intersectingPairs,0);
 receipts.push({sharedTwoVertexFoldOver:'UNSUPPORTED',ordinarySharedEdge:'excluded boundary contact'});
}

// Feasible historical sheet side is retained, otherwise the initial choice is
// always +B normal. These calls have no identity-based or hidden side cache.
{
 const fixture={positions:[[.002,.002,0],[.008,.002,0],[.002,.008,0],[0,0,0],[.02,0,0],[0,.02,0]],triangles:[[0,1,2],[3,4,5]]};
 const p=Float64Array.from(fixture.positions.flat()),history=p.slice(),inv=new Float64Array(6).fill(1);for(let id=0;id<3;id++)history[id*3+2]=-.01;
 const proposals=[];const old=gatherTriangleContacts(p,history,inv,fixture.triangles,null,thickness,(ids,coefficients,normal,residual)=>{proposals.push({ids,coefficients,normal,residual});return true;});
 assert.equal(old.historicalSides,1);assert.ok(proposals.every(x=>x.normal[2]===-1));
 for(const x of proposals){assert.ok(Math.abs(x.coefficients.reduce((a,b)=>a+b,0))<1e-14);assert.deepEqual(x.coefficients,[1,-1/3,-1/3,-1/3]);}
 const current=gatherTriangleContacts(p,p.slice(),inv,fixture.triangles,null,thickness,()=>true);assert.equal(current.initialPositiveBSides,1);assert.equal(current.pairs[0].side,1);
 const fresh=gatherTriangleContacts(p.slice(),history.slice(),inv.slice(),fixture.triangles.map(x=>x.slice()),null,thickness,()=>true);assert.deepEqual(fresh,old);
 receipts.push({historicalFeasibleNegativeSide:'retained',initialIntersectedSide:'+B normal',gradientTranslationSum:0,noHiddenPairState:true});
}

// Coordinates/history/masses remain immutable while gathering; stale BVH and
// incompatible topology are rejected. The callback only receives proposals.
{
 const p=Float64Array.from(analytic.positions.flat()),history=p.slice(),inv=new Float64Array(6).fill(1),pBefore=p.slice(),historyBefore=history.slice(),massBefore=inv.slice();
 const solver=new MeshContact(p,analytic.triangles.flat(),thickness);
 gatherTriangleContacts(p,history,inv,analytic.triangles,solver.tree,thickness,()=>true);
 assert.deepEqual(p,pBefore);assert.deepEqual(history,historyBefore);assert.deepEqual(inv,massBefore);
 const stale=p.slice();stale[0]+=.001;
 assert.throws(()=>gatherTriangleContacts(stale,history,inv,analytic.triangles,solver.tree,thickness,()=>true),/stale/);
 assert.throws(()=>gatherTriangleContacts(p,history,inv,[0,2,1,3,4,5],solver.tree,thickness,()=>true),/triangle indices/);
 assert.throws(()=>gatherTriangleContacts(p,history,Float64Array.from([1,1,1,-1,1,1]),analytic.triangles,null,thickness,()=>true),/nonnegative/);
 solver.dispose();receipts.push({gatherInputImmutability:'PASS',staleBVHRejected:true,incompatibleTopologyRejected:true});
}

// Resume a saved solve state in a new instance with exactly the same saved
// history. No pair-side warm state is needed to reproduce the next batch.
{
 const p=Float64Array.from(actual.positions.flat()),previous=p.slice(),history=p.slice(),inv=Float64Array.from(actual.inverseMass),a=new TriangleRecovery(p,actual.triangles.flat(),thickness,{maxVertexCorrection:cap});
 a.solve(p,previous,inv,10,history);const savedP=p.slice(),savedPrevious=previous.slice();
 a.solve(p,previous,inv,10,history);
 const q=savedP.slice(),qPrevious=savedPrevious.slice(),b=new TriangleRecovery(q,actual.triangles.flat(),thickness,{maxVertexCorrection:cap});
 b.solve(q,qPrevious,inv,10,history.slice());assert.deepEqual(q,p);assert.deepEqual(qPrevious,previous);assert.deepEqual(b.triangleProfiles,a.triangleProfiles);
 const script="import fs from 'node:fs';import {MeshContact} from './experiments/intent-edit-review/physics/mesh-contact.mjs';import {gatherTriangleContacts} from './experiments/intent-edit-review/physics/triangle-contact.mjs';class Recovery extends MeshContact{solve(p,prev,inv,passes,history){this.inv=inv;return super.solve(p,prev,inv,passes,history)}_gatherVertices(){return 0}_gatherEdges(s,h,add){return gatherTriangleContacts(s,h,this.inv,this.faces,this.tree,this.thickness,add).contacts}}const state=JSON.parse(fs.readFileSync(0,'utf8')),p=Float64Array.from(state.p),prev=Float64Array.from(state.previous),solver=new Recovery(p,state.triangles,.001,{maxVertexCorrection:.0005});solver.solve(p,prev,Float64Array.from(state.inverseMass),10,Float64Array.from(state.history));console.log(JSON.stringify({p:Array.from(p),previous:Array.from(prev)}));solver.dispose();";
 const processReplay=spawnSync(process.execPath,['--input-type=module','-e',script],{cwd:root,input:JSON.stringify({p:Array.from(savedP),previous:Array.from(savedPrevious),history:Array.from(history),triangles:actual.triangles.flat(),inverseMass:Array.from(inv)}),encoding:'utf8'});
 assert.equal(processReplay.status,0,processReplay.stderr);const replay=JSON.parse(processReplay.stdout);assert.deepEqual(replay.p,Array.from(p));assert.deepEqual(replay.previous,Array.from(previous));
 a.dispose();b.dispose();receipts.push({savedStateFreshInstanceReplay:'bit-exact',savedStateFreshProcessReplay:'bit-exact',hiddenPairCache:false});
}

// Preserve the integration failure as a negative control: blindly adding old
// VF+EE history-oriented constraints can oppose recovery. This test MUST NOT
// report that naive combined contact is a passing production solution.
for(const [name,fixture] of [['analytic',analytic],['actual-6531-6605',actual]]){
 const p=Float64Array.from(fixture.positions.flat()),history=p.slice(),solver=new NaiveCombined(p,fixture.triangles.flat(),thickness,{maxVertexCorrection:cap});
 solver.solve(p,p.slice(),Float64Array.from(fixture.inverseMass),160,history);assert.ok(solver.lastPassMaxCorrections.every(x=>x<=cap));
 recordOracle(`${name}-naive-VF-EE-triangle-negative-control`,p,fixture.triangles,1);solver.dispose();
 receipts.push({fixture:name,naiveCombinedContact:'FAIL retained',reason:'old proximity history directions oppose current-crossing recovery'});
}

// Independent NumPy/SciPy SAT oracle, not trianglePairOverlap, certifies each
// before/after geometry and all boundary controls. No threshold is changed.
const venv=path.join(root,'work/intent-physics/venv/bin/python'),python=process.env.PATTERN_ORACLE_PYTHON||(existsSync(venv)?venv:'python3');
const script="import json,sys,numpy as np;sys.path.insert(0,'experiments/oneshot_control');from independent_oracle_v2 import intersect_pairs;cases=json.load(sys.stdin);print(json.dumps([{'name':c['name'],'strictPairs':intersect_pairs(np.asarray(c['vertices'],float),np.asarray(c['triangles'],int),epsilon_m=1e-6)} for c in cases]))";
const audit=spawnSync(python,['-c',script],{cwd:root,input:JSON.stringify(oracleCases),encoding:'utf8',maxBuffer:4*1024*1024});
assert.equal(audit.status,0,`Independent oracle unavailable or failed: ${audit.stderr}`);const independent=JSON.parse(audit.stdout);
for(let i=0;i<oracleCases.length;i++)assert.equal(independent[i].strictPairs.length,oracleCases[i].expected,`Independent SAT: ${oracleCases[i].name}`);
console.log(JSON.stringify({verdict:'PASS',scope:'Current triangle-crossing gather and isolated bounded recovery controls; NOT a production combined-contact or garment acceptance verdict',intersectionEpsilon_m:epsilon,thickness_m:thickness,perPassVertexCap_m:cap,checks:receipts,independentOracle:independent,productionIntegration:'FAIL for naive addition; needs explicitly reconciled proximity directions',unsupported:'shared2/shared3 positive-area fold-over; general CCD/global untangling not claimed'},null,2));
