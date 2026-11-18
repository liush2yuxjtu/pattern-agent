import assert from 'node:assert/strict'
import { readFileSync,writeFileSync } from 'node:fs'
import { createHash } from 'node:crypto'
import { parse } from 'yaml'
import { cisFemaleAdult38 } from './package/src/index.mjs'
import { makeDraft } from './adapter.mjs'

const baseInput={mode:'ENGINE_CONFORMANCE',measurements:cisFemaleAdult38,options:{fitWaist:true},measurementSources:Object.fromEntries(Object.keys(cisFemaleAdult38).map(k=>[k,{kind:'OFFICIAL_TEST_MODEL',package:'@freesewing/models',version:'4.10.2',model:'cisFemaleAdult38',unit:k==='shoulderSlope'?'degree':'mm',goldenMeasurement:false}]))}
const base=makeDraft(baseInput)
const changedWaist=makeDraft({...baseInput,measurements:{...cisFemaleAdult38,waist:cisFemaleAdult38.waist+20}})
const changedSleeve=makeDraft({...baseInput,options:{...baseInput.options,sleeveLength:0.4}})
const changedNeck=makeDraft({...baseInput,options:{...baseInput.options,necklineDepth:0.3}})
const find=(draft,id)=>draft.panels.find(p=>p.id===id)
const diff=(a,b)=>JSON.stringify(a.outlineMM)!==JSON.stringify(b.outlineMM)
assert(base.panels.length===4)
assert(base.panels.every(p=>p.areaMM2>0))
assert(base.panels.every(p=>p.sourceNativeAreaMM2>0),'native seam areas are nonzero')
for(const p of base.panels){
 const expected=p.sourceNativeAreaMM2*(p.id==='front'||p.id==='back'?2:1)
 assert(Math.abs(p.areaMM2-expected)/expected<0.005,`${p.id} follows native seam area`)
}
assert(diff(find(base,'front'),find(changedWaist,'front')),'waist changes front outline')
assert(diff(find(base,'back'),find(changedWaist,'back')),'waist changes back outline')
assert(!diff(find(base,'sleeve-left'),find(changedWaist,'sleeve-left')),'waist does not change sleeve')
assert(diff(find(base,'sleeve-left'),find(changedSleeve,'sleeve-left')),'sleeveLength changes sleeve')
assert(!diff(find(base,'front'),find(changedSleeve,'front')),'sleeveLength does not change front')
assert(diff(find(base,'front'),find(changedNeck,'front')),'necklineDepth changes front')
assert(!diff(find(base,'back'),find(changedNeck,'back')),'front neck depth does not change back')
for(const seam of base.seams){
 assert(find(base,seam.a.panel).pathLabels[seam.a.edge])
 assert(find(base,seam.b.panel).pathLabels[seam.b.edge])
 assert(seam.a.direction===1)
 assert(seam.b.direction===(seam.id.startsWith('armhole.')?-1:1))
}
const canonicalPath='inputs/golden-garment-1.1.yaml'
const yaml=readFileSync(canonicalPath,'utf8')
const sha256=createHash('sha256').update(yaml).digest('hex')
assert.equal(sha256,'88a84e697273724cdb5b4a05116c00cd53b0cb75a4d7e6bdfa5d0b7fd34f181e')
const canonical=parse(yaml)
const blocked=makeDraft({canonical})
assert.equal(blocked.status,'UNKNOWN')
assert.equal(blocked.panels.length,0)
const result={status:'PASS',canonicalSha256:sha256,model:'cisFemaleAdult38',measurements:cisFemaleAdult38,baseOptions:baseInput.options,checks:{panelCount:base.panels.length,sourceAreasMM2:base.panels.map(p=>({id:p.id,areaMM2:p.areaMM2,vertexCount:p.outlineMM.length})),waistChangeMM:20,waistChangesBodyOnly:true,sleeveLengthChange:{from:0.3,to:0.4,changesSleeveOnly:true},necklineDepthChange:{from:0.25,to:0.3,changesFrontOnly:true},allSeamDirectionsExplicit:true,canonicalUnknownBlocked:true},seams:base.seams,limitations:base.validation}
writeFileSync('probes/pattern/official-model.json',JSON.stringify(cisFemaleAdult38,null,2))
writeFileSync('probes/pattern/conformance-result.json',JSON.stringify(result,null,2))
writeFileSync('probes/pattern/base-draft.json',JSON.stringify(base,null,2))
writeFileSync('probes/pattern/changed-waist-draft.json',JSON.stringify(changedWaist,null,2))
writeFileSync('probes/pattern/base.svg',base.svg)
writeFileSync('probes/pattern/changed-waist.svg',changedWaist.svg)
console.log(JSON.stringify(result,null,2))
