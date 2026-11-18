// Analytic hinges verify the measured turning convention, including >90° folds.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {inspectSleeveCreases} from '../src/crease-diagnostics.mjs';
import {inspectGarmentCreases} from '../src/garment-creases.mjs';
import {creaseAngleColor,makeCreaseOverlay} from '../src/crease-overlay.mjs';
const tests=[];
function check(name,ok){assert.ok(ok,name);tests.push(name);}
function hinge(deg){const t=deg*Math.PI/180;return{partId:'sleeve-hinge',vertices:[[-.1,0,0],[.1,0,0],[0,.1,0],[0,-.1*Math.cos(t),-.1*Math.sin(t)]],points2d:[{x:-100,y:0},{x:100,y:0},{x:0,y:100},{x:0,y:-100}],triangles:[[0,1,2],[1,0,3]],boundary:[{a:1,b:2,edge:'underarm-right'}]};}
for(const degree of [0,5,15,30,45,60,90,120,150,179,180]){
 const measured=inspectSleeveCreases([hinge(degree)],{underarmExclusionMm:0});
 check(`Analytic single-edge hinge ${degree}°`,Math.abs(measured.peak.angleDeg-degree)<1e-10);
}
const reversed=hinge(30);reversed.triangles[1]=[0,1,3];
check('Inconsistent triangle winding is invalid instead of disguised as a fold',inspectSleeveCreases([reversed],{underarmExclusionMm:0}).invalidCount>0);
const collapsed=hinge(30);collapsed.vertices[3]=collapsed.vertices[0];
check('Degenerate triangle is invalid instead of producing a zero angle',inspectSleeveCreases([collapsed],{underarmExclusionMm:0}).invalidCount>0);
function seam(deg,gap=0){const t=deg*Math.PI/180;return[
 {partId:'front',vertices:[[-.1,0,0],[.1,0,0],[0,.1,0]],triangles:[[0,1,2]],points2d:[{x:-100,y:0},{x:100,y:0},{x:0,y:100}],boundary:[{a:0,b:1,edge:'shoulder'}]},
 {partId:'back',vertices:[[.1,0,gap],[-.1,0,gap],[0,-.1*Math.cos(t),gap-.1*Math.sin(t)]],triangles:[[0,1,2]],points2d:[{x:100,y:0},{x:-100,y:0},{x:0,y:-100}],boundary:[{a:0,b:1,edge:'shoulder'}]},
 ];}
for(const degree of [0,15,60,90,120,179,180]){
 const r=inspectGarmentCreases(seam(degree));
 check(`Analytic paired seam ${degree}°, both sampling directions`,r.seams.samples.length===2&&r.seams.samples.every(e=>Math.abs(e.angleDeg-degree)<1e-10));
}
const gap=inspectGarmentCreases(seam(90,.002));
check('A 2 mm seam gap is reported unmatched, never assigned zero degrees',gap.seams.samples.length===0&&gap.seams.unmatched.length===2&&gap.seams.unmatched.every(e=>Math.abs(e.gapMm-2)<1e-10));
function cylinder(steps){
 const vertices=[],points2d=[],triangles=[];
 for(let i=0;i<=steps;i++)for(const z of[-.1,.1]){const t=i*Math.PI*2/steps;vertices.push([.1*Math.cos(t),.1*Math.sin(t),z]);points2d.push({x:t*100,y:z*1000});}
 for(let i=0;i<steps;i++){const a=i*2;triangles.push([a,a+2,a+1],[a+1,a+2,a+3]);}
 return{partId:'sleeve-cylinder',vertices,points2d,triangles,boundary:[{a:0,b:1,edge:'underarm-right'}]};
}
const cylinderResults=[16,64].map(n=>({segments:n,measuredMaxDeg:inspectSleeveCreases([cylinder(n)],{underarmExclusionMm:0}).peak.angleDeg,expectedMaxDeg:360/n}));
check('Same-radius cylinders demonstrate mesh-dependent edge angles',cylinderResults.every(r=>Math.abs(r.measuredMaxDeg-r.expectedMaxDeg)<1e-10));
check('Continuous color distinguishes small angles that formerly all looked green',new Set([0,1,3,5,10,15,20,25].map(v=>creaseAngleColor(v,180).getHexString())).size===8);
check('Full range distinguishes 60°, 90°, and 180°',new Set([60,90,180].map(v=>creaseAngleColor(v,180).getHexString())).size===3);
check('Detail scale explicitly saturates beyond 45°',creaseAngleColor(45,45).equals(creaseAngleColor(120,45)));
const cases={};
for(const id of ['before','after']){
 const data=JSON.parse(fs.readFileSync(new URL(`../dist/diagnostics/sleeve-${id}.json`,import.meta.url))),r=inspectGarmentCreases(data.garment);
 check(`All four garment panels and all six seam groups measured: ${id}`,r.parts.length===4&&r.seams.samples.length>0&&r.seams.missingGroups.length===0);
 check(`No unmatched seam samples: ${id}`,r.seams.unmatched.length===0);
 check(`Every seam sample has a unique panel-specific identity: ${id}`,new Set(r.seams.samples.map(e=>e.id)).size===r.seams.samples.length);
 const overlay=makeCreaseOverlay(data.garment,r,{colorMode:'angle',includeUnderarm:true,includeSeams:true,colorMaxDeg:180});
 check(`Every face of front, back and both sleeves receives a numeric color: ${id}`,overlay.group.children.filter(m=>m.name==='crease-faces').length===4&&overlay.group.children.filter(m=>m.name==='crease-faces').every(m=>m.userData.faceAngles.every(Number.isFinite)));
 check(`Opaque unlit colors do not blend with green cloth or lighting: ${id}`,overlay.group.children.filter(m=>m.name==='crease-faces').every(m=>!m.material.toneMapped&&m.material.opacity===1&&!m.material.transparent));
 overlay.dispose();cases[id]=r;
}
check('Historical sleeve defect still fails, fixed quality scope still passes',cases.before.status==='FAIL'&&cases.before.sharpCount===161&&cases.after.status==='PASS'&&cases.after.sharpCount===0);
check('Previously excluded >45° edges are now explicitly retained',cases.after.underarm.sharpCount===2&&Math.abs(cases.after.underarm.peak.angleDeg-58.864704548281615)<1e-8);
const output={status:'PASS',checks:tests,count:tests.length,cylinderResults,cases};
if(process.argv[2])fs.writeFileSync(process.argv[2],JSON.stringify(output));
console.log(JSON.stringify({status:'PASS',count:tests.length,cylinderResults,fullAfterMax:cases.after.full.peak.angleDeg,sleeveQualityMax:cases.after.peak.angleDeg,underarmMax:cases.after.underarm.peak.angleDeg}));
