export const GOLDEN_SHA='88a84e697273724cdb5b4a05116c00cd53b0cb75a4d7e6bdfa5d0b7fd34f181e';
let instanceCounter=0;
export function newArtifact(source='GOLDEN_YAML'){
  return {schema:'garment-artifact-engine-lab-1',id:source==='GOLDEN_YAML'?'golden-fitted-tshirt-1.1':'teagan-engine-conformance-1',source,
    instanceId:`artifact-instance-${++instanceCounter}`,revision:1,sourceSha:source==='GOLDEN_YAML'?GOLDEN_SHA:null,unit:source==='GOLDEN_YAML'?'U':'mm',scaleToMM:source==='GOLDEN_YAML'?null:1,
    status:source==='GOLDEN_YAML'?'BLOCKED':'NOT_RUN',draft:null,mesh:null,meshRevision:null,frames:[],frameIndex:0,run:null,audit:null,
    material:{status:'DEMO_ASSUMED',physicalStress:'UNKNOWN',pressure:'UNKNOWN'},fit:'NOT_VALIDATED',history:[]};
}
export function invalidate(artifact,reason){
  artifact.revision++;artifact.status='STALE';artifact.meshRevision=null;artifact.run=null;artifact.audit=null;artifact.native=null;artifact.inputs=null;artifact.auditStep=null;artifact.auditRevision=null;
  artifact.history.push({revision:artifact.revision,reason,oldFrames:artifact.frames.length});
  artifact.frames=[];artifact.frameIndex=0;return artifact;
}
export function addFrame(artifact,frame,revision){
  if(revision!==artifact.revision||artifact.meshRevision!==revision)return false;
  artifact.frames.push({...frame,revision});artifact.frameIndex=artifact.frames.length-1;return true;
}
export function liveExport(artifact){
  return {...artifact,viewRevisions:Object.fromEntries(['pattern','designer','physics','debugger','timeline'].map(k=>[k,artifact.revision])),
    claims:{goldenPhysics:artifact.source==='GOLDEN_YAML'?'BLOCKED':'NOT_APPLICABLE',engine:'Rapier 0.21.0 / WASM',realFit:'NOT_VALIDATED',continuousCollisionAudit:'NOT_RUN'}};
}
export function validSettings(s){
  const stepped=(v,min,max,step)=>Number.isFinite(v)&&v>=min-1e-10&&v<=max+1e-10&&Math.abs((v-min)/step-Math.round((v-min)/step))<1e-7;
  return !!s&&stepped(s.waistDeltaMM,-40,40,10)&&stepped(s.sleeveLength,.2,.6,.1)&&stepped(s.necklineDepth,.2,.4,.05)&&[40,26].includes(s.spacingMM)&&['planar-gentle','wrapped-spherical'].includes(s.profile);
}
