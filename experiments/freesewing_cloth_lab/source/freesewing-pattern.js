import {Sandy} from '@freesewing/sandy';
import {pluginTheme} from '@freesewing/plugin-theme';

export const FREESEWING_VERSION='4.10.2';

const xy=p=>[p.x,p.y];
function bezier(a,b,c,d,t){const u=1-t;return [0,1].map(k=>u*u*u*a[k]+3*u*u*t*b[k]+3*u*t*t*c[k]+t*t*t*d[k]);}

/** Draft the actual installed Sandy design at runtime. Millimetres in/out.
 * Sandy supplies a half-panel cut on fold. The adapter unfolds it into one
 * full panel; four such panels form the simulated skirt shell. Its optional
 * waistband is in the native SVG but is not part of the simulated shell.
 */
export function draftSandy({waist_mm,length_mm,circleRatio,panels=4}){
 if(!(waist_mm>500&&waist_mm<1500&&length_mm>=400&&length_mm<=650&&circleRatio>=.2&&circleRatio<=.8&&panels===4))throw new Error('Sandy shell parameters outside the supported profile');
 const settings={sa:10,measurements:{waist:waist_mm,hips:1000,waistToFloor:1000,waistToHips:200},options:{panels,waistbandPosition:0,waistbandShape:'straight',waistbandWidth:.02,lengthBonus:(length_mm+20)/1000,circleRatio,gathering:0,seamlessFullCircle:false}};
 const design=new Sandy(settings).use(pluginTheme).draft();
 const part=design.parts[0]['sandy.skirt'],p=part.points;
 const center=xy(p.center),fold=xy(p.in2Flipped),r0=Math.hypot(fold[0]-center[0],fold[1]-center[1]);
 const axis=fold.map((v,k)=>(v-center[k])/r0),right=[axis[1],-axis[0]];
 const inner=[['in2Flipped','in2cFlipped','in1cFlipped','in1'],['in1','in1c','in2c','in2']].map(names=>names.map(n=>xy(p[n])));
 const outer=[['ex2Flipped','ex2cFlipped','ex1cFlipped','ex1'],['ex1','ex1c','ex2c','ex2']].map(names=>names.map(n=>xy(p[n])));
 const canonical=q=>{const d=q.map((v,k)=>v-center[k]);return [d[0]*right[0]+d[1]*right[1],d[0]*axis[0]+d[1]*axis[1]-r0];};
 const sourceOps=part.paths.seam.ops.map(op=>Object.fromEntries(Object.entries(op).filter(([k])=>['type','to','cp1','cp2'].includes(k)).map(([k,v])=>[k,k==='type'?v:xy(v)])));
 const profile={engine:'FreeSewing',design:'Sandy',version:FREESEWING_VERSION,settings:JSON.parse(JSON.stringify(design.settings[0])),halfPanel:{center,fold,inner,outer,seamOps:sourceOps},adaptation:'Mirror actual Sandy half-panel across its cut-on-fold line; four full panels; skirt shell only',waistbandSimulated:false,assumedUnusedMeasurements:['hips','waistToHips'],length_mm,circleRatio};
 const end=canonical(inner[1][3]),panelAngle=2*Math.atan2(end[0],end[1]+r0);
 const sample=(rowFraction,panelFraction)=>{
  if(panelFraction<0||panelFraction>1){
   const cycle=Math.floor(panelFraction),q=sample(rowFraction,panelFraction-cycle),angle=cycle*panelAngle,c=Math.cos(angle),s=Math.sin(angle);
   return [q[0]*c+(q[1]+r0)*s,-q[0]*s+(q[1]+r0)*c-r0];
  }
  const signed=2*panelFraction-1,t=Math.min(1,Math.abs(signed)),segment=Math.min(1,Math.floor(t*2)),u=t*2-segment;
  const a=canonical(bezier(...inner[segment],u)),b=canonical(bezier(...outer[segment],u));
  return [(signed<0?-1:1)*(a[0]+rowFraction*(b[0]-a[0])),a[1]+rowFraction*(b[1]-a[1])];
 };
 const a=sample(0,1),b=sample(1,1);profile.sideLength_mm=Math.hypot(b[0]-a[0],b[1]-a[1]);profile.panelAngle_rad=panelAngle;
 if(Math.abs(profile.sideLength_mm-length_mm)>1e-6)throw new Error('FreeSewing length conversion differs from requested length');
 const nativeSVG=design.render();
 return {sample,profile,nativeSVG};
}
