import {makeDraft} from '../probes/pattern/adapter.mjs';
import {makeMesh} from '../probes/pattern/mesh.mjs';
import {assemble} from './pose.mjs';
import model from '../probes/pattern/official-model.json' with {type:'json'};
import human from '../reference/assets/makehuman.json' with {type:'json'};
export {human};
export function demoInput(changes={}){
  const original=model.measurements??model;
  const ratio=human.landmarks.chestCM*10/original.chest;
  const measurements=Object.fromEntries(Object.entries(original).map(([k,v])=>[k,k==='shoulderSlope'?v:v*ratio]));
  measurements.waist+=Number(changes.waistDeltaMM??0);
  return {mode:'ENGINE_CONFORMANCE',measurements,options:{fitWaist:true,sleeveLength:Number(changes.sleeveLength??.3),necklineDepth:Number(changes.necklineDepth??.25)},sampleStepMM:3,
    measurementSources:{status:'DEMO_ASSUMED',model:'@freesewing/models 4.10.2 cisFemaleAdult38',uniformLinearRatio:ratio,ratioBasis:'MakeHuman geometric chest section / official sample chest',angleExcluded:'shoulderSlope',actualBodyFit:'NOT_VALIDATED'}};
}
export function buildDemo(changes={}){
  const input=demoInput(changes),draft=makeDraft(input),mesh=makeMesh(draft,{spacingMM:Number(changes.spacingMM??40)}),pose=assemble(mesh,draft,human,changes.profile??'planar-gentle');
  return {input,draft,mesh,pose};
}
