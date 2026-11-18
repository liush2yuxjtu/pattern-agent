import fs from 'node:fs';
import crypto from 'node:crypto';
import os from 'node:os';
import {performance} from 'node:perf_hooks';
import {buildDemo,human} from '../src/pipeline.mjs';
import {create} from '../probes/rapier/engine.mjs';
import {measure} from '../src/metrics.mjs';
const claim='Measure cold first-30-step native CPU cost for the declared 485-particle open-seam experiment. No comparison with the old PBD garment and no garment qualification.';
const runs=[];
for(let repeat=1;repeat<=5;repeat++){
 const start=performance.now();const demo=buildDemo({spacingMM:40,profile:'planar-gentle'}),draftMeshMS=performance.now()-start;
 const init=performance.now();const engine=await create({restXY:demo.mesh.restXY,triangles:demo.mesh.triangles,initialXYZ:demo.pose.positions,seams:demo.mesh.seams,pinnedIDs:demo.pose.pins,body:human,...demo.pose.config}),initMS=performance.now()-init;
 let solverMS=0;
 for(let step=0;step<30;step++){const t=performance.now();engine.step();solverMS+=performance.now()-t;}
 const positions=engine.getPositions(),metrics=measure(demo.mesh,positions),native=engine.nativeStats();
 const row={repeat,draftMeshMS,initMS,solverMS,endToEndMS:performance.now()-start,steps:native.stepCount,particles:native.particles,triangles:demo.mesh.triangles.length,joints:native.nativeSeamJoints,positionSha256:crypto.createHash('sha256').update(new Uint8Array(positions.buffer,positions.byteOffset,positions.byteLength)).digest('hex'),finite:metrics.finite,errors:0,maxSeamGapMM:metrics.maxSeamGapMM,garmentVerdict:'FAIL'};
 runs.push(row);engine.dispose();console.log(JSON.stringify(row));
}
const times=runs.map(r=>r.solverMS).sort((a,b)=>a-b),output={claim,environment:{node:process.version,cpu:os.cpus()[0].model,cores:os.cpus().length,load:os.loadavg()},method:{runs:5,warmupSteps:0,whyNoWarmup:'Measures actual first requested segment, including cold first physics step. WASM init and mesh generation are separately timed.',stepsPerRun:30,dt:1/120,renderer:'NOT_INCLUDED',accuracy:'Open seam >2mm FAIL'},runs,summary:{medianSolverMS:times[2],rangeSolverMS:[times[0],times.at(-1)],sameFinalPositions:runs.every(r=>r.positionSha256===runs[0].positionSha256),errors:0}};
fs.mkdirSync('evidence',{recursive:true});fs.writeFileSync('evidence/native-performance.json',JSON.stringify(output,null,2));console.log(JSON.stringify(output.summary));
