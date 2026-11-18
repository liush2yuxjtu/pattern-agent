import { Brian } from '@freesewing/brian';
import { pluginTheme } from '@freesewing/plugin-theme';
import { Path } from '@freesewing/core';
import { isDegreeMeasurement } from '@freesewing/config';

export const version='4.10.2';
// A labelled example, NOT defaults or measurement bounds supplied by Brian.
export const exampleMeasurements={biceps:340,chest:1000,hpsToBust:280,hpsToWaistBack:450,neck:380,shoulderToShoulder:460,shoulderSlope:15,waistToArmpit:230,waistToHips:180,shoulderToWrist:600,wrist:180};
export const exampleHighBust=940;
export const required=[...Brian.patternConfig.measurements];
export const optional=[...Brian.patternConfig.optionalMeasurements];
const labels={biceps:'上臂围',chest:'胸围',hpsToBust:'肩颈点→胸线',hpsToWaistBack:'肩颈点→后腰',neck:'颈围',shoulderToShoulder:'肩宽',shoulderSlope:'肩斜',waistToArmpit:'腰→腋下',waistToHips:'腰→臀',shoulderToWrist:'肩→腕',wrist:'腕围',highBust:'上胸围'};
export const fields=[...required,...optional].map(key=>({key,label:labels[key]||key,optional:optional.includes(key),unit:isDegreeMeasurement(key)?'°':'mm',example:exampleMeasurements[key]??(key==='highBust'?exampleHighBust:undefined)}));
export const viewSettings={complete:false,sa:0,paperless:false,scale:1};
const nativeDefaults=new Brian({measurements:exampleMeasurements}).draft().settings[0].options;
export const inputContract={design:'@freesewing/brian',version,required,optional,units:Object.fromEntries(fields.map(f=>[f.key,f.unit])),measurementBounds:null,measurementBoundsNote:'Brian declares no numeric min/max bounds for body measurements.',defaultOptions:{...nativeDefaults},source:'https://registry.npmjs.org/@freesewing/brian/-/brian-4.10.2.tgz'};

// No unit conversion, rounding, clamping, invented defaults, field filtering,
// or coupling highBust presence to draftForHighBust.
export function draftBrian(input){
  const submitted={...input,measurements:{...input.measurements},options:{...input.options}};
  const pattern=new Brian(input).use(pluginTheme).draft();
  const svg=pattern.render();
  return {submitted,pattern,svg,logs:pattern.getLogs()};
}

// Presentation is separate from the native adapter and original native SVG.
// Only arrangement and two guides change; native cut paths stay untouched.
export function present(result){
  const {pattern}=result;
  for(const name of ['brian.back','brian.front']){
    const part=pattern.parts[0]?.[name],p=part?.points;
    if(!p?.cbChest||!p?.chest||!p?.waist)continue;
    part.paths.chest=new Path().move(p.cbChest).line(p.chest).attr('class','fabric help');
    part.paths.waist=new Path().move(p.cfWaist||p.cbWaist).line(p.waist).attr('class','fabric help');
  }
  pattern.store.pack=bins=>{
    let x=0,height=0;
    for(const bin of bins){bin.x=x;bin.y=0;x+=bin.width+28;height=Math.max(height,bin.height);}
    return {width:Math.max(1,x-28),height};
  };
  return {...result,svg:pattern.render(),width:pattern.width,height:pattern.height,quarterWidth:pattern.parts[0]?.['brian.front']?.points?.armhole?.x};
}
