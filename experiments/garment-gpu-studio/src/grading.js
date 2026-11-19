import {draft} from './pattern.js';
import {makeBody} from './body.js';
export function gradeSizes(size,input){return [-1,0,1].map((step,i)=>{const bodySize={...size,chestMm:size.chestMm+40*step,waistMm:size.waistMm+40*step,hipMm:size.hipMm+40*step},body=makeBody(bodySize),doc=draft({...input,chestMm:body.measurements.chest.circumference*1000},body);return {label:['S','M','L'][i],bodySize,doc,mode:'Each size is redrafted by FreeSewing; not a uniform scale of a paper drawing.'};});}
