import fs from 'node:fs';
import vm from 'node:vm';
import crypto from 'node:crypto';
import YAML from 'yaml';
import {goldenDrawing} from '../src/golden.mjs';
import {triangleStretch} from '../src/metrics.mjs';
import {newArtifact,invalidate,addFrame,validSettings} from '../src/domain.mjs';

const hash=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const source=fs.readFileSync('src/app.mjs','utf8');
const golden=YAML.parse(fs.readFileSync('inputs/golden-garment-1.1.yaml','utf8'));
const drawing=goldenDrawing(golden);
const translated=[...drawing.svg.matchAll(/<g transform="translate\(([-\d.e]+),([-\d.e]+)\)"/g)].map(m=>[Number(m[1]),Number(m[2])]);
const placement=Object.values(golden['完整二维几何']).map(p=>[p['排版放置点']['横'],-p['排版放置点']['高']]);
const deltas=placement.slice(1).map((p,i)=>({expected:p.map((v,k)=>v-placement[0][k]),actual:translated[i+1]?.map((v,k)=>v-translated[0][k])}));
const layoutMatches=translated.length===4&&deltas.every(d=>d.actual&&d.actual.every((v,k)=>Math.abs(v-d.expected[k])<1e-6));
const result={sourceHashes:Object.fromEntries(['src/app.mjs','src/golden.mjs','src/domain.mjs','src/metrics.mjs','dist/index.html'].map(p=>[p,hash(p)])),checks:[]};
result.checks.push({id:'golden-relative-placement',status:layoutMatches?'PASS':'FAIL',counts:drawing.stats,deltas});

const identity=triangleStretch([[0,0],[100,0],[0,100]],[[0,0,0],[.1,0,0],[0,.1,0]]);
const stretched=triangleStretch([[0,0],[100,0],[0,100]],[[0,0,0],[.12,0,0],[0,.08,0]]);
result.checks.push({id:'mm-to-m-dimensionless-stretch',status:Math.abs(identity.max-1)<1e-12&&Math.abs(stretched.max-1.2)<1e-12&&Math.abs(stretched.min-.8)<1e-12?'PASS':'FAIL',identity,stretched});

const model=newArtifact('ENGINE_CONFORMANCE');model.meshRevision=1;addFrame(model,{step:1},1);invalidate(model,'review-edit');
result.checks.push({id:'domain-stale-frame-rejection',status:!addFrame(model,{step:2},1)&&model.frames.length===0&&model.status==='STALE'?'PASS':'FAIL'});

const auditFunction=source.slice(source.indexOf('async function audit(){'),source.indexOf('\nfunction download('));
for(const scenario of ['unchanged','frame','source','job','auditJob']){
  const elements=new Map();let scheduled,calls=0;
  const context=vm.createContext({
    artifact:{revision:1,source:'ENGINE_CONFORMANCE',frameIndex:0,mesh:{triangles:[[0,1,2]],seams:[]},frames:[{step:0,positions:[0]},{step:10,positions:[10]}]},
    busy:false,job:1,auditJob:0,auditBusy:false,display:'fabric',view:'physics',human:{},bodyCollider:{},performance:{now:()=>1},
    $:id=>{if(!elements.has(id))elements.set(id,{});return elements.get(id);},
    log:()=>{},perf:()=>{},render:()=>{},refreshControls:()=>{},
    setTimeout:fn=>{scheduled=fn;},
    auditSurfaceCollisions:({cloth})=>{calls++;return {marker:cloth.positions[0],vertexInside:{count:0},bodySurface:{strictCrossingPairs:0},selfSurface:{strictCrossingPairs:0},workCounts:{}};}
  });
  try{
    vm.runInContext('const current=()=>artifact.frames[artifact.frameIndex];'+auditFunction,context);
    const pending=vm.runInContext('audit()',context);
    if(scenario==='frame')context.artifact.frameIndex=1;
    if(scenario==='source')context.artifact={...context.artifact,source:'GOLDEN_YAML'};
    if(scenario==='job')context.job++;
    if(scenario==='auditJob')context.auditJob++;
    scheduled();await pending;
    const pass=scenario==='unchanged'?context.artifact.audit?.marker===0&&context.artifact.auditStep===0&&calls===1:!context.artifact.audit&&calls===0;
    result.checks.push({id:`audit-${scenario}`,status:pass?'PASS':'FAIL',calls,auditedMarker:context.artifact.audit?.marker??null,reportedStep:context.artifact.auditStep??null});
  }catch(error){result.checks.push({id:`audit-${scenario}`,status:'BLOCKED',error:String(error)});}
}
const probe=JSON.parse(fs.readFileSync('probes/rapier/engine-report.json','utf8'));
const matchingSources=Object.entries(probe.sourceHashes).map(([p,h])=>({path:p,matches:hash(p)===h}));
result.checks.push({id:'current-native-probe-source-hashes',status:matchingSources.every(s=>s.matches)?'PASS':'FAIL',matchingSources,cases:probe.cases.map(c=>({name:c.name,status:c.status}))});
try{
  const valid={waistDeltaMM:0,sleeveLength:.3,necklineDepth:.25,spacingMM:40,profile:'planar-gentle'};
  const invalid=[undefined,{}, {...valid,profile:undefined},{...valid,spacingMM:36},{...valid,waistDeltaMM:Infinity},{...valid,waistDeltaMM:5},{...valid,sleeveLength:.25},{...valid,necklineDepth:.23}];
  const rejected=invalid.filter(s=>!validSettings(s)).length;
  result.checks.push({id:'import-incomplete-settings-rejected',status:validSettings(valid)&&rejected===invalid.length?'PASS':'FAIL',rejected,total:invalid.length});
}catch(error){result.checks.push({id:'import-incomplete-settings-rejected',status:'BLOCKED',error:String(error)});}
try{
  const identity=source.slice(source.indexOf('const identity='),source.indexOf('\nfunction terminate('));
  const logNodes=new Map(),c=vm.createContext({artifact:{source:'ENGINE_CONFORMANCE',id:'a',instanceId:'first',revision:1},job:7,logEntries:[],performanceEntries:[],$:id=>{if(!logNodes.has(id))logNodes.set(id,{});return logNodes.get(id);}});
  vm.runInContext(identity+"\nlog('old');perf({kind:'old'});",c);
  c.artifact={source:'GOLDEN_YAML',id:'b',instanceId:'second',revision:1};
  vm.runInContext("log('new');perf({kind:'new'});",c);
  const pass=!logNodes.get('log').textContent.includes('old')&&!logNodes.get('performance-log').textContent.includes('old')&&c.logEntries[0].instanceId==='first'&&c.logEntries[1].instanceId==='second';
  result.checks.push({id:'log-source-isolation',status:pass?'PASS':'FAIL'});
}catch(error){result.checks.push({id:'log-source-isolation',status:'BLOCKED',error:String(error)});}
try{
  const guard=source.slice(source.indexOf('if(data.positions.length!=='),source.indexOf('\n        const m=measure',source.indexOf('if(data.positions.length!==')));
  const cases=[[],[NaN,0,0],[Infinity,0,0],[0,0,0]];
  const outcomes=cases.map(positions=>{const c=vm.createContext({data:{positions},artifact:{mesh:{restXY:[[0,0]]}},rev:1,terminate:()=>{},render:()=>{}});vm.runInContext('(function(){'+guard+'})()',c);return c.artifact.status==='ERROR';});
  result.checks.push({id:'invalid-frame-rejection',status:JSON.stringify(outcomes)==='[true,true,true,false]'?'PASS':'FAIL',outcomes});
}catch(error){result.checks.push({id:'invalid-frame-rejection',status:'BLOCKED',error:String(error)});}

fs.writeFileSync('review/advisor-checks-result.json',JSON.stringify(result,null,2));
console.log(JSON.stringify(result,null,2));
