import fs from 'node:fs';
import {buildDemo,human} from '../src/pipeline.mjs';
import {create} from '../probes/rapier/engine.mjs';
import {measure} from '../src/metrics.mjs';
import {auditSurfaceCollisions} from '../reference/benchmarks/collision/surface-audit.mjs';
import {MeshBodyCollider} from '../reference/src/mesh-collider.js';
const demo=buildDemo();console.log('mesh',demo.mesh.restXY.length,demo.mesh.triangles.length,'pins',demo.pose.pins);
const engine=await create({restXY:demo.mesh.restXY,triangles:demo.mesh.triangles,initialXYZ:demo.pose.positions,seams:demo.mesh.seams,pinnedIDs:demo.pose.pins,body:human});
const collider=new MeshBodyCollider(human),samples=[];
for(let step=0;step<=120;step+=30){
  if(step)engine.step(30);
  const positions=Array.from(engine.getPositions()),m=measure(demo.mesh,positions),a=auditSurfaceCollisions({cloth:{positions,triangles:demo.mesh.triangles.flat()},body:human,bodyCollider:collider,maxExamples:5});
  const sample={step,maxStretch:m.maxStretch,minStretch:m.minStretch,areaOver20Percent:m.areaOver20Percent,maxGapMM:m.maxSeamGapMM,inside:a.vertexInside.count,bodyCrossings:a.bodySurface.strictCrossingPairs,selfCrossings:a.selfSurface.strictCrossingPairs,examples:a.bodySurface.examples};samples.push(sample);console.log(JSON.stringify(sample));
}
fs.mkdirSync('evidence',{recursive:true});fs.writeFileSync('evidence/garment-run.json',JSON.stringify({source:'DEMO_ASSUMED',samples,native:engine.nativeStats(),positions:Array.from(engine.getPositions())},null,2));engine.dispose();
