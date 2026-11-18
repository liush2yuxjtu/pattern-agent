import fs from 'node:fs';
import crypto from 'node:crypto';
import vm from 'node:vm';
import YAML from 'yaml';
import {goldenDrawing} from './src/golden.mjs';
import {triangleStretch} from './src/metrics.mjs';
import {newArtifact,invalidate,addFrame,validSettings,GOLDEN_SHA} from './src/domain.mjs';
import {buildDemo,human} from './src/pipeline.mjs';
import {create} from './probes/rapier/engine.mjs';
const checks=[],assert=(name,condition,detail)=>{checks.push({name,status:condition?'PASS':'FAIL',detail});if(!condition)console.error(name,'FAIL');};
const hash=data=>crypto.createHash('sha256').update(data).digest('hex');
const goldenBytes=fs.readFileSync('inputs/golden-garment-1.1.yaml'),golden=YAML.parse(goldenBytes.toString()),drawing=goldenDrawing(golden);
assert('canonical exact bytes',hash(goldenBytes)===GOLDEN_SHA,hash(goldenBytes));
assert('complete Golden geometry and text',JSON.stringify(drawing.stats)===JSON.stringify({parts:4,polylines:126,lines:78,texts:27,vertices:1487}),drawing.stats);
assert('Golden original placements',Object.entries(golden['完整二维几何']).every(([name,p])=>drawing.svg.includes(`translate(${p['排版放置点']['横']},${-p['排版放置点']['高']})`)),drawing.bounds);
assert('Golden scale remains unknown',newArtifact().scaleToMM===null&&newArtifact().status==='BLOCKED');
assert('MakeHuman mesh identity',hash(fs.readFileSync('reference/assets/makehuman.json'))==='405d3cc8d5ba299b241892d80782cd9faf194da66ce611748ccb8423ab82331d',{vertices:human.positions.length/3,triangles:human.triangles.length/3});
const unit=[[0,0],[1000,0],[0,1000]];
for(const [name,x,y]of [['identity',1,1],['warp',1.2,1],['weft',1,.8],['near-collapse',1,1e-9]]){
  const m=triangleStretch(unit,[[0,0,0],[x,0,0],[0,y,0]]);assert(`strain ${name}`,m.valid&&Math.abs(m.max-Math.max(x,y))<1e-12&&Math.abs(m.min-Math.min(x,y))<1e-12,m);
}
const a=newArtifact('ENGINE_CONFORMANCE');a.meshRevision=a.revision;a.native={stepCount:30};a.inputs={old:true};const first=a.revision;addFrame(a,{step:1},first);invalidate(a,'test');assert('edits invalidate all results',a.status==='STALE'&&a.frames.length===0&&a.meshRevision===null&&a.native===null&&a.inputs===null&&!addFrame(a,{step:2},first));
assert('sources get distinct instance IDs',newArtifact().instanceId!==newArtifact('ENGINE_CONFORMANCE').instanceId);
const good={waistDeltaMM:0,sleeveLength:.3,necklineDepth:.25,spacingMM:40,profile:'planar-gentle'};
assert('complete supported import settings',validSettings(good));
assert('missing settings rejected',!validSettings({waistDeltaMM:0}));
assert('off-step settings rejected',!validSettings({...good,waistDeltaMM:5})&&!validSettings({...good,sleeveLength:.25}));
const html=fs.readFileSync('dist/index.html','utf8'),encoded=html.match(/atob\('([A-Za-z0-9+/=]+)'\)/)?.[1];
try{new vm.Script(Buffer.from(encoded,'base64').toString());assert('exact shipped script syntax',true);}catch(e){assert('exact shipped script syntax',false,e.message);}
assert('no runtime source URLs',!/<script\b[^>]*\bsrc=/i.test(html)&&!/<link\b[^>]*href="https?:/i.test(html)&&html.includes("connect-src 'none'"));
const report=JSON.parse(fs.readFileSync('probes/rapier/engine-report.json'));
assert('native probe receipt matches current sources',Object.entries(report.sourceHashes).every(([p,h])=>fs.existsSync(p)&&hash(fs.readFileSync(p))===h),report.sourceHashes);
const demo=buildDemo(good),engine=await create({restXY:demo.mesh.restXY,triangles:demo.mesh.triangles,initialXYZ:demo.pose.positions,seams:demo.mesh.seams,pinnedIDs:demo.pose.pins,body:human,...demo.pose.config});
engine.step(30);const positions=Array.from(engine.getPositions()),native=engine.nativeStats();
assert('actual native work and rest preservation',native.stepCount===30&&native.structuralRestLengthsUnchanged&&positions.every(Number.isFinite),{stepCount:native.stepCount,version:native.version,particles:native.particles,joints:native.nativeSeamJoints});
const browserPath=process.env.ENGINE_CLOTH_BROWSER_ARTIFACT??'evidence/browser/browser-run-final.json';
assert('actual browser artifact is present',fs.existsSync(browserPath),browserPath);
if(fs.existsSync(browserPath)){const browser=JSON.parse(fs.readFileSync(browserPath)),frame=browser.frames.at(-1),manifest=JSON.parse(fs.readFileSync('dist/build-manifest.json'));assert('browser artifact source binding',browser.buildSourceSha256===manifest.sourceSha256,{browser:browser.buildSourceSha256,manifest:manifest.sourceSha256});assert('browser/Node full-array reproducibility',frame.positions.length===positions.length&&frame.positions.every((p,i)=>p===positions[i]),{nodeHash:hash(new Float32Array(positions)),browserHash:hash(new Float32Array(frame.positions)),step:frame.step});assert('open seam remains garment FAIL',browser.run.garmentVerdict==='FAIL'&&frame.metrics.maxSeamGapMM>2,{gapMM:frame.metrics.maxSeamGapMM,bodyCrossings:browser.audit.bodySurface.strictCrossingPairs});}
engine.dispose();
const output={schema:'engine-cloth-node-verification-1',htmlSha256:hash(html),checks,verdict:checks.every(x=>x.status==='PASS')?'PASS':'FAIL',scope:'Data integrity, native-engine execution and diagnostic honesty; garment physics remains FAIL, Golden physics BLOCKED.'};
fs.mkdirSync('evidence',{recursive:true});fs.writeFileSync('evidence/node-checks.json',JSON.stringify(output,null,2));console.log(JSON.stringify({verdict:output.verdict,checks:checks.length,failures:checks.filter(c=>c.status==='FAIL'),scope:output.scope},null,2));process.exitCode=output.verdict==='PASS'?0:1;
