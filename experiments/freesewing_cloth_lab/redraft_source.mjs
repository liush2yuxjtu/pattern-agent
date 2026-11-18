/** Independent consumer of the pinned upstream design; imports no app adapter. */
import fs from 'node:fs';
import {Sandy} from '@freesewing/sandy';
import {pluginTheme} from '@freesewing/plugin-theme';
const {waist_mm,length_mm,circleRatio}=JSON.parse(fs.readFileSync(0,'utf8'));
const design=new Sandy({sa:10,measurements:{waist:waist_mm,hips:1000,waistToFloor:1000,waistToHips:200},options:{panels:4,waistbandPosition:0,waistbandShape:'straight',waistbandWidth:.02,lengthBonus:(length_mm+20)/1000,circleRatio,gathering:0,seamlessFullCircle:false}}).use(pluginTheme).draft();
const part=design.parts[0]['sandy.skirt'];
const points=Object.fromEntries(Object.entries(part.points).filter(([key])=>!key.startsWith('_')).map(([key,p])=>[key,[p.x,p.y]]));
console.log(JSON.stringify({settings:design.settings[0],points,nativeSVG:design.render()}));
