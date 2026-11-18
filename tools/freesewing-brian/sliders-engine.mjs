import { Brian } from '@freesewing/brian';
import { pluginTheme } from '@freesewing/plugin-theme';
import { Path } from '@freesewing/core';

// Lengths in this UI are cm. Brian accepts mm, except shoulderSlope (degrees).
export const fields = [
  { key:'chest', label:'胸围', value:100, min:70, max:140, step:.5 },
  { key:'neck', label:'颈围', value:38, min:28, max:52, step:.5 },
  { key:'shoulderToShoulder', label:'肩宽', value:46, min:32, max:60, step:.5 },
  { key:'shoulderSlope', label:'肩斜', value:15, min:0, max:35, step:1, angle:true },
  { key:'biceps', label:'上臂围', value:34, min:20, max:50, step:.5 },
  { key:'wrist', label:'腕围', value:18, min:12, max:26, step:.5 },
  { key:'shoulderToWrist', label:'肩→腕', value:60, min:42, max:78, step:.5 },
  { key:'hpsToBust', label:'肩颈点→胸线', value:28, min:17, max:40, step:.5 },
  { key:'hpsToWaistBack', label:'肩颈点→后腰', value:45, min:30, max:60, step:.5 },
  { key:'waistToArmpit', label:'腰→腋下', value:23, min:12, max:35, step:.5 },
  { key:'waistToHips', label:'腰→臀', value:18, min:10, max:30, step:.5 },
  { key:'highBust', label:'上胸围', value:94, min:65, max:140, step:.5, optional:true },
];
export const defaults = Object.fromEntries(fields.map(f=>[f.key,f.value]));
export const required = Brian.patternConfig.measurements;

export function generate(values, useHighBust=false) {
  const measurements = {};
  for (const f of fields) {
    if(f.optional && !useHighBust) continue;
    const value = Number(values[f.key]);
    if(!Number.isFinite(value) || value < f.min || value > f.max)
      throw new Error('尺寸超出范围');
    measurements[f.key] = f.angle ? value : Math.round(value*10);
  }
  const settings = {
    measurements,
    options:{ chestEase:.1, draftForHighBust:useHighBust },
    complete:false, sa:0, paperless:false, scale:1,
  };
  const pattern = new Brian(settings).use(pluginTheme).draft();
  const logs = pattern.getLogs();
  const errors = [...logs.pattern.error, ...logs.sets.flatMap(s=>s.error)];
  if(errors.length) throw new Error('此组合无法制图，请回调尺寸');

  // Show the native chest/waist reference points without technical annotations.
  // hpsToBust locates the chest guide; it does not widen the block outline.
  for(const name of ['brian.back','brian.front']) {
    const part=pattern.parts[0][name],p=part.points;
    part.paths.chest=new Path().move(p.cbChest).line(p.chest).attr('class','fabric help');
    part.paths.waist=new Path().move(p.cfWaist||p.cbWaist).line(p.waist).attr('class','fabric help');
  }

  // Only change page arrangement; Brian still computes every pattern curve.
  // A stable left-to-right layout makes input changes easy to see.
  pattern.store.pack = bins => {
    let x=0, height=0;
    for(const bin of bins) {
      bin.x=x; bin.y=0;
      x += bin.width + 28;
      height = Math.max(height, bin.height);
    }
    return {width:Math.max(1,x-28),height};
  };
  const svg = pattern.render();
  if(/(?:NaN|Infinity)/.test(svg)) throw new Error('此组合无法制图，请回调尺寸');
  const warnings = [...logs.pattern.warn,...logs.sets.flatMap(s=>s.warn)];
  const front=pattern.parts[0]['brian.front'];
  return {
    svg, settings, width:pattern.width, height:pattern.height,
    frontPath:front.paths.seam.asPathstring(),
    quarterWidth:front.points.armhole.x,
    warning: warnings.length>0,
  };
}
