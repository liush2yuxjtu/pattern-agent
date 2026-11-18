import assert from 'node:assert/strict';import fs from 'node:fs';import * as THREE from 'three';
import {makeAssembly} from '../src/assembly.mjs';import {ellipseSection} from '../src/arc-length.mjs';import {solveSleevePose} from '../src/sleeve-pose.mjs';import {draftPrototype,initialSpec} from '../src/pattern.mjs';
const kernel=(await WebAssembly.instantiate(fs.readFileSync('dist/pattern-kernel.wasm'))).instance.exports,results=[];
// An arclength parameter has unit speed. This catches the former 22.5% center gain.
for(const t of [0,.1,.35,.8,.98]){const eps=1e-5,a=ellipseSection(t-eps),b=ellipseSection(t+eps),speed=Math.hypot(a.x-b.x,a.z-b.z)/(2*eps);assert(Math.abs(speed-1)<.0002,'Ellipse parameter is not based on source arclength');}
for(const key of ['basic','relaxed','cropped']){
 const p=draftPrototype(key,initialSpec(key)),source=JSON.stringify(p),rows=[];
 for(const step of [9,4.5]){
  const a=makeAssembly(p,kernel,new THREE.MeshStandardMaterial(),{meshStep:step});a.setHeatmap(true);const r=a.deformationReport();assert.equal(r.invalidFaces,0);assert.equal(r.collapsedFaces,0);assert(r.sleevePose.meetsEndpointConstraints);assert(r.sleevePose.sideChordResidualMm<.000001);
  const w=p.parts.front.points.armhole.x,y=p.parts.front.points.armhole.y;
  for(const t of [0,.25,.6,.9]){const dx=.001,u=a.bodyMap({x:t*w-dx,y},'front'),v=a.bodyMap({x:t*w+dx,y},'front');assert(Math.abs(u.distanceTo(v)*1000/(2*dx)-1)<.0002,'Body map creates an artificial circumferential strain');}
  const sp=p.parts.sleeve.points,dx=.001;
  for(const t of [.05,.25,.5,.85]){const x=sp.hemLeft.x+t*(sp.hemRight.x-sp.hemLeft.x),u=a.sleeveMap({x:x-dx,y:sp.hemLeft.y},false),v=a.sleeveMap({x:x+dx,y:sp.hemLeft.y},false);assert(Math.abs(u.distanceTo(v)*1000/(2*dx)-1)<.00001,'Cuff mapping changes the hem metric');}
  for(const side of ['Left','Right']){const actual=a.sleeveMap(sp['hem'+side],false).distanceTo(a.sleeveMap(sp['biceps'+side],false))*1000,target=Math.hypot(sp['hem'+side].x-sp['biceps'+side].x,sp['hem'+side].y-sp['biceps'+side].y);assert(Math.abs(actual-target)<.000001,'Underarm endpoint distance is not preserved');}
  rows.push({stepMm:step,faces:r.allFaces,peakPercent:r.max,areaWeightedMeanPercent:r.mean,p95Percent:r.p95,meshSensitiveFaces:r.meshSensitiveFaces,meshSensitiveAreaPercent:r.meshSensitiveAreaPercent,parts:r.parts.map(p=>({part:p.partId,peakPercent:p.max,meanPercent:p.mean})),sleevePose:r.sleevePose});a.dispose();
 }
 assert.equal(JSON.stringify(p),source,'Assembly mutated the source pattern');
 const maxChange=Math.abs(rows[0].peakPercent-rows[1].peakPercent),meanChange=Math.abs(rows[0].areaWeightedMeanPercent-rows[1].areaWeightedMeanPercent);assert(maxChange<5,'Peak is not stable under 9→4.5mm refinement');assert(meanChange<.5,'Area-weighted mean is not stable under refinement');results.push({variant:key,status:'PASS',samples:rows,peakChangePercentagePoints:maxChange,meanChangePercentagePoints:meanChange});
}
// Impossible endpoint constraints remain explicit rather than silently declared solved.
const impossible=solveSleevePose({shoulder:{x:0,y:0},underarm:{x:0,y:10},radius:.05,length:.2,sideLength:.01});assert(!impossible.meetsEndpointConstraints&&!impossible.rootFound);
const legacy=JSON.parse(fs.readFileSync('scripts/fixtures/heat-legacy-high-values.json'));
const ellipseSamples=Array.from({length:101},(_,i)=>({fraction:i/100,...ellipseSection(i/100)}));
const report={metric:"maxStrain",ellipseSamples,status:'PASS',scope:'Numerical mapping and mesh-refinement verification; physical strain NOT_VALIDATED',assemblyAlgorithm:'source-length-assembly-v2',physicalStrain:'NOT_VALIDATED',limits:{peakChangePercentagePoints:5,areaMeanChangePercentagePoints:.5,note:'Numerical mesh-stability thresholds, not fabric limits'},checks:['Ellipse and actual body mapping use source arclength','Cuff uses source hem arclength','Sleeve placement preserves endpoint chords','Impossible placement is reported','Assembly does not mutate source points or paths','Independent 9mm / 4.5mm meshes have stable peak and area mean'],variants:results,legacyEvidence:legacy};
const out=process.argv[2]||'/tmp/pattern-high-value-audit.json';fs.writeFileSync(out,JSON.stringify(report,null,2));console.log(JSON.stringify({status:'PASS',variants:results.map(r=>({variant:r.variant,max:r.samples[0].peakPercent,fineMax:r.samples[1].peakPercent,delta:r.peakChangePercentagePoints}))}));
