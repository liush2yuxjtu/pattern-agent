import assert from 'node:assert/strict';
import {createSelfContact} from './create-self-contact.mjs';
import {contactExclusions} from './topology-contact.mjs';

const receipts=[];
for(const inputType of ['Array','Uint16Array','Uint32Array'])for(const targetZ of [.001,-.004]){
 const p=new Float32Array([-1,-1,0,1,-1,0,0,1,0,0,0,targetZ]),history=p.slice();history[11]=.01;
 const Type=inputType==='Array'?Array:globalThis[inputType],tri=Type.from([0,1,2]);
 const contact=createSelfContact(p,tri,.003,{...contactExclusions(tri,4),maxVertexCorrection:.02});
 assert.equal(contact.verifiedTriangleCount,1);
 const hits=contact.solve(p,history.slice(),new Float32Array([0,0,0,1]),1,history);
 assert.ok(hits>0,`${inputType} must activate actual vertex/triangle response`);
 assert.ok(p[11]>=.003-2e-8);assert.equal(history[11],new Float32Array([.01])[0]);
 receipts.push({inputType,targetZ,actualTriangleVisits:contact.verifiedTriangleCount,contacts:hits,finalZ:p[11]});contact.dispose();
}
// Preserve the old explicit custom-exclusion API on an intentionally under-
// resolved 0.2mm-high sheet with 1mm contact thickness. The real experiment no
// longer enables this one-ring hook; this is not default-contact acceptance.
const tri=[0,1,2,1,3,2],options=contactExclusions(tri,5);
assert.ok(options.excludeVertexFace(0,1));assert.ok(!options.excludeVertexFace(4,0));
const flat=new Float32Array([0,0,0,.01,0,0,0,.0002,0,.01,.0002,0]);
const contact=createSelfContact(flat,tri,.001,{...contactExclusions(tri,4),useCustomExclusions:true});const before=flat.slice();
assert.equal(contact.solve(flat,flat.slice(),new Float32Array([1,1,1,1]),1),0);assert.deepEqual(flat,before);contact.dispose();
const weighted=new Float32Array([0,0,0,1,0,0,0,1,0,.01,.01,.0001]),original=weighted.slice();
const bounded=createSelfContact(weighted,[0,1,2],.003,{maxVertexCorrection:.0005});
bounded.solve(weighted,weighted.slice(),new Float32Array([0,1000,0,0]),1);
const maximumMove=Math.max(...Array.from({length:4},(_,i)=>Math.hypot(...[0,1,2].map(k=>weighted[i*3+k]-original[i*3+k]))));
assert.ok(maximumMove>0&&maximumMove<=.000500001,'Bound the actual inverse-mass-weighted vertex move, not just the constraint residual');bounded.dispose();
console.log(JSON.stringify({verdict:'PASS',typedIndexProximityAndSweptControls:receipts,legacyCustomExclusionFlatSheetPreserved:true,nonlocalFaceNotExcluded:true,
 inverseMassWeightedMaximumMove_m:maximumMove,unboundedFormulaWouldMove_m:.29},null,2));
