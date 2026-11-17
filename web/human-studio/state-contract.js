// Shared import contract for local files and same-origin review links.
import {MODEL_VERSION,normalizeDimensions} from './body-engine.js';

export function validateModelState(saved,data,asset) {
  if(!saved||saved.version!==MODEL_VERSION||saved.asset!==asset)throw Error('This file belongs to a different model version.');
  if(saved.units!=='cm')throw Error('Model dimensions must use cm.');
  for(const c of data.controls){const value=saved.dimensions?.[c.key];if(typeof value!=='number'||!Number.isFinite(value)||value<c.min||value>c.max)throw Error('Invalid centimetre dimension: '+c.key);}
  if(!saved.poseDegrees||Array.isArray(saved.poseDegrees)||typeof saved.poseDegrees!=='object')throw Error('Joint pose must be an object.');
  const known=new Set(data.bones.map(b=>b.name)),pose={};
  for(const [name,angles] of Object.entries(saved.poseDegrees)){
    if(!known.has(name)||!Array.isArray(angles)||angles.length!==3||angles.some(v=>typeof v!=='number'||!Number.isFinite(v)||Math.abs(v)>180))throw Error('Invalid joint angles: '+name);
    pose[name]=angles.map(v=>Math.round(v*10)/10);
  }
  let weights=null;
  if(saved.morphWeights!==undefined){
    if(!Array.isArray(saved.morphWeights)||saved.morphWeights.length!==data.controls.length||saved.morphWeights.some(v=>typeof v!=='number'||!Number.isFinite(v)||Math.abs(v)>2))throw Error('Invalid morph coefficients.');
    weights=[...saved.morphWeights];
  }
  return {dimensions:normalizeDimensions(data,saved.dimensions),pose,weights};
}

export function resolveModelUrl(value,pageUrl) {
  const page=new URL(pageUrl),url=new URL(value,page);
  if(!value||!['http:','https:'].includes(url.protocol)||url.origin!==page.origin||url.username||url.password||!url.pathname.endsWith('.json'))throw Error('Use a same-origin JSON model link.');
  url.hash='';return url;
}
