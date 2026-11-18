import assert from 'node:assert/strict';import fs from 'node:fs';import path from 'node:path';import {gzipSync} from 'node:zlib';import {createHash} from 'node:crypto';import * as THREE from 'three';
import {triangleDeformation,heatRgb,summarizeDeformation} from '../src/deformation.mjs';import {makeAssembly} from '../src/assembly.mjs';import {humanPositions} from '../src/human.mjs';import {draftPrototype,initialSpec,presets,sampleOps} from '../src/pattern.mjs';
const kernel=(await WebAssembly.instantiate(fs.readFileSync('dist/pattern-kernel.wasm'))).instance.exports;
assert.equal(typeof kernel.principal_max,'function');assert.equal(typeof kernel.principal_min,'function');
const cases=[],checks=[];const near=(a,b,t=1e-8)=>assert(Math.abs(a-b)<=t,`${a} != ${b}`);
function gridIntegrity(assembly,pattern){
 let maxBoundaryGapMm=0;
 for(const mesh of assembly.meshes){
  const d=mesh.userData,edges=new Map();
  for(const t of d.triangles)for(let i=0;i<3;i++){const key=[t[i],t[(i+1)%3]].sort((a,b)=>a-b).join(':');edges.set(key,(edges.get(key)||0)+1);}
  let sampled=sampleOps(pattern.parts[d.sourceId].seamOps,22);
  if(d.sourceId!=='sleeve')sampled=sampled.filter(s=>pattern.parts[d.sourceId].seamOps[s.opIndex].edge!=='fold');
  const lines=sampled.flatMap(s=>s.points.slice(1).map((b,i)=>[s.points[i],b]));
  if(d.sourceId!=='sleeve')lines.push(...lines.map(([a,b])=>[{x:-a.x,y:a.y},{x:-b.x,y:b.y}]));
  for(const [edge,count]of edges){
   assert(count<=2,'Non-manifold edge');if(count!==1)continue;
   const [a,b]=edge.split(':').map(i=>d.points2d[+i]),mid={x:(a.x+b.x)/2,y:(a.y+b.y)/2};
   const distance=Math.min(...lines.map(([a,b])=>{const x=b.x-a.x,y=b.y-a.y,t=Math.max(0,Math.min(1,((mid.x-a.x)*x+(mid.y-a.y)*y)/(x*x+y*y)));return Math.hypot(mid.x-a.x-t*x,mid.y-a.y-t*y);}));
   // Contact meshing collapses near-collinear short edges within 0.01 mm; the source Beziers are unchanged.
   const tolerance=d.meshing.boundaryToleranceMm??.00003;assert(tolerance<=.01);assert(distance<=tolerance,'Interior crack or boundary exceeds declared meshing tolerance');maxBoundaryGapMm=Math.max(maxBoundaryGapMm,distance);
  }
 }
 return {nonManifoldEdges:0,interiorCracks:0,maxBoundaryGapMm};
}
const rest=[[0,0],[.2,0],[0,.3]],affine=(m,p=rest)=>p.map(([x,y])=>m.map((r,k)=>r[0]*x+r[1]*y+[.8,-.4,1.3][k]));
for(const [name,m,expected]of[
 ['identity',[[1,0],[0,1],[0,0]],[0,0,0,0]],['rigid-3d-rotation',[[0,0],[1,0],[0,1]],[0,0,0,0]],
 ['20-percent-isotropic-stretch',[[1.2,0],[0,1.2],[0,0]],[20,20,44,0]],['20-percent-compression',[[.8,0],[0,.8],[0,0]],[-20,-20,-36,0]],
 ['anisotropic-stretch',[[1.2,0],[0,.8],[0,0]],[20,-20,-4,0]],['simple-shear',[[1,.5],[0,1],[0,0]],[null,null,0,Math.atan(.5)*180/Math.PI]],
 ['reflection-is-isometric',[[1,0],[0,-1],[0,0]],[0,0,0,0]]]){
 const current=affine(m),field=triangleDeformation(rest,current,kernel);assert(field.valid);['maxStrain','minStrain','area','shear'].forEach((k,i)=>{if(expected[i]!==null)near(field[k],expected[i]);});cases.push({id:name,rest,current,grainAngle:0,field});checks.push(name);
}
let seed=217;function random(){seed=(seed*1664525+1013904223)>>>0;return seed/4294967296;}
for(let i=0;i<100;i++){const r=[[0,0],[.1+random(),.1*random()],[.1*random(),.1+random()]],m=Array.from({length:3},()=>[random()*2-.5,random()*2-.5]),angle=random()*180;const current=affine(m,r),a=triangleDeformation(r,current,kernel,angle),b=triangleDeformation(r,current,null,angle);for(const k of['maxStrain','minStrain','area','shear'])near(a[k],b[k],1e-8);cases.push({id:'random-'+i,rest:r,current,grainAngle:angle,field:a});}
checks.push('100 deterministic general affine cases; WASM / JavaScript parity');
const bad=triangleDeformation([[0,0],[1,0],[2,0]],[[0,0,0],[1,0,0],[2,0,0]],kernel);assert(!bad.valid);const collapsed=triangleDeformation(rest,[[0,0,0],[0,0,0],[0,0,0]],kernel);assert(!collapsed.valid&&collapsed.collapsed);checks.push('Degenerate reference and collapsed current geometry are flagged');
assert.deepEqual(heatRgb(-100,30),heatRgb(-30,30));assert.deepEqual(heatRgb(100,30),heatRgb(30,30));assert.notDeepEqual(heatRgb(-15,30),heatRgb(15,30));const stat=summarizeDeformation([{valid:true,restArea:1,maxStrain:10},{valid:true,restArea:3,maxStrain:30}]);near(stat.mean,25);near(stat.p95,30);checks.push('Fixed color clamping and reference-area weighted statistics');
const summaries=[];
for(const key of Object.keys(presets)){
 const p=draftPrototype(key,initialSpec(key)),a=makeAssembly(p,kernel,new THREE.MeshStandardMaterial());a.setHeatmap(true);const topology=gridIntegrity(a,p);checks.push(key+': grid has no interior cracks or non-manifold edges; boundary within declared 0.01mm remeshing tolerance');
 const original=a.deformationReport();assert.equal(original.invalidFaces,0);assert.equal(original.collapsedFaces,0);
 const right=a.meshes.find(m=>m.userData.partId==='sleeve-right'),left=a.meshes.find(m=>m.userData.partId==='sleeve-left');right.userData.deformation.forEach((f,i)=>near(f.maxStrain,left.userData.deformation[i].maxStrain));
 for(const unfold of [0,.5,1]){a.morph(unfold);const report=a.deformationReport();assert.equal(report.invalidFaces,0);if(unfold===1){assert(Math.max(Math.abs(report.min),Math.abs(report.max))<1e-6);for(const mesh of a.meshes)for(const f of mesh.userData.deformation){near(f.minStrain,0,1e-6);near(f.area,0,1e-6);near(f.shear,0,1e-6);}}
 for(const mesh of a.meshes){const d=mesh.userData;for(let i=0;i<d.triangles.length;i++){const t=d.triangles[i];cases.push({id:key+'/'+unfold+'/'+d.partId+'/'+i,rest:t.map(j=>[d.points2d[j].x/1000,d.points2d[j].y/1000]),current:t.map(j=>d.current[j].toArray()),grainAngle:p.parts[d.sourceId].grainlineAngle||0,field:d.deformation[i]});}}
 }
 a.morph(0);near(a.deformationReport().mean,original.mean);a.select('sleeve');assert.equal(a.deformationReport().validFaces,right.userData.triangles.length*2);a.setHeatmap(false);a.morph(1);near(a.deformationReport().mean,0,1e-6);summaries.push({variant:key,faces:original.allFaces,invalidFaces:original.invalidFaces,maxStrainMeanPercent:original.mean,topology});a.dispose();checks.push(key+': all current faces finite; mirror, selection, unfold zero, roundtrip, stale-field refresh');
}
const human=JSON.parse(fs.readFileSync('dist/models/makehuman-body.json')),hv=humanPositions(human),bounds=k=>[Math.min(...hv.map(p=>p[k])),Math.max(...hv.map(p=>p[k]))];assert.equal(human.license,'CC0-1.0');assert.equal(human.sourceSha256,createHash('sha256').update(fs.readFileSync('dist/models/makehuman-base.obj')).digest('hex'));assert.equal(human.sourceSha256,'8e761e6624b8f54536409135d1636da63b32486a90d4897f84e121d144f6fb4c');assert.equal(hv.length,13380);for(const v of hv)for(const n of v)assert(Number.isFinite(n));const by=bounds(1);near(by[1]-by[0],1.75,1e-8);for(let i=0;i<hv.length;i++)if(human.vertices[i][1]<0){near(hv[i][0],human.vertices[i][0]*.96/human.chestSection.circumferenceSourceUnits);}
const circ=human.chestSection.segments.reduce((s,[a,b])=>s+Math.hypot(...a.map((n,i)=>n-b[i]))*.96/human.chestSection.circumferenceSourceUnits,0);near(circ,.96);checks.push('CC0 asset identity; finite posed vertices; 175cm height; legs not posed as arms; chest-section 96cm');
const output=path.resolve(process.argv[2]||'/tmp/pattern-deformation-cases.json.gz');fs.mkdirSync(path.dirname(output),{recursive:true});fs.writeFileSync(output,gzipSync(JSON.stringify({schema:'independent-deformation-input/1',cases,checks,summaries,human:{revision:human.revision,sourceSha256:human.sourceSha256,chestCircumferenceM:circ}})));
console.log(JSON.stringify({status:'PASS',checks:checks.length,independentInputCases:cases.length,summaries,output}));
