import fs from 'node:fs';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {JSDOM} from 'jsdom';
import {Brian} from '@freesewing/brian';
import {pluginTheme} from '@freesewing/plugin-theme';
import {degreeMeasurements} from '@freesewing/config';
import {draftBrian,present,inputContract} from './sliders-engine.mjs';
const manifest=JSON.parse(fs.readFileSync('upstream-manifest.json','utf8'));
for(const file of manifest.files)assert.equal(createHash('sha256').update(fs.readFileSync('node_modules/@freesewing/brian/'+file.file)).digest('hex'),file.sha256,file.file);
const base={biceps:340,chest:1000,hpsToBust:280,hpsToWaistBack:450,neck:380,shoulderToShoulder:460,
  shoulderSlope:15,waistToArmpit:230,waistToHips:180,shoulderToWrist:600,wrist:180};
const view={complete:false,sa:0,paperless:false,scale:1};
const nativeRequired=Brian.patternConfig.measurements,nativeOptional=Brian.patternConfig.optionalMeasurements;
assert.deepEqual(inputContract.required,nativeRequired);assert.deepEqual(inputContract.optional,nativeOptional);
for(const key of [...nativeRequired,...nativeOptional])assert.equal(inputContract.units[key],degreeMeasurements.includes(key)?'°':'mm');
const nativeDefaultPattern=new Brian({...view,measurements:base}).use(pluginTheme).draft();
assert.deepEqual(inputContract.defaultOptions,nativeDefaultPattern.settings[0].options);
const parts=['brian.back','brian.front','library.sleeve'];
const curves=(root,name)=>[...root.querySelector(`[id="fs-stack-${name}-part-${name}"]`).querySelectorAll('path:not(.help)')].map(e=>e.getAttribute('d'));
const samples=[{label:'official-default',measurements:base},
  {label:'explicit-legacy-10-percent',measurements:base,options:{chestEase:.1}}];
// Preserve every old adult-boundary test as a regression vector, not a rule.
const legacyVectors={biceps:[200,500],chest:[700,1400],hpsToBust:[170,400],hpsToWaistBack:[300,600],
  neck:[280,520],shoulderToShoulder:[320,600],shoulderSlope:[0,35],waistToArmpit:[120,350],
  waistToHips:[100,300],shoulderToWrist:[420,780],wrist:[120,260]};
for(const key of nativeRequired){
  for(const value of legacyVectors[key])samples.push({label:key+'='+value,measurements:{...base,[key]:value}});
  samples.push({label:key+' fractional',measurements:{...base,[key]:base[key]+.123456}});
}
for(const factor of [.5,2])samples.push({label:'outside-old-adult-ranges x'+factor,measurements:Object.fromEntries(Object.entries(base).map(([k,v])=>[k,degreeMeasurements.includes(k)?v:v*factor]))});
samples.push(
  {label:'above-old-chest-limit',measurements:{...base,chest:2100.123456}},
  {label:'high-bust-provided-default-off',measurements:{...base,highBust:940}},
  {label:'high-bust-explicit-on',measurements:{...base,highBust:940},options:{draftForHighBust:true}},
  {label:'high-bust-fractional-active',measurements:{...base,highBust:975.123456},options:{draftForHighBust:true}},
  {label:'high-bust-absent-option-on',measurements:base,options:{draftForHighBust:true}},
  {label:'optional-zero-native-fallback',measurements:{...base,highBust:0},options:{draftForHighBust:true}},
  {label:'preserve-extra-native-bust-field',measurements:{...base,highBust:940,bust:1000},options:{draftForHighBust:true}},
  {label:'native-option-outside-menu-range',measurements:base,options:{chestEase:.4}},
);
for(const value of [-.04,.35])samples.push({label:'official chestEase bound '+value,measurements:base,options:{chestEase:value}});
let pointCoordinates=0,partComparisons=0;
const missingInput={...view,measurements:{...base,chest:undefined}};
const missingNative=new Brian(missingInput).use(pluginTheme).draft();
const missingAdapter=draftBrian(missingInput);
assert.equal(missingAdapter.svg,missingNative.render());
assert.equal(missingAdapter.submitted.measurements.chest,undefined);
assert.equal(missingAdapter.pattern.settings[0].measurements.chest,undefined);
for(const sample of samples){
  const input={...view,measurements:{...sample.measurements},options:{...sample.options}};
  const untouched=JSON.stringify(input);
  const direct=new Brian(input).use(pluginTheme).draft(),originalSvg=direct.render();
  const actual=draftBrian(input);
  assert.equal(JSON.stringify(input),untouched,sample.label+' changed caller input');
  assert.deepEqual(actual.submitted,input);
  assert.equal(actual.svg,originalSvg,sample.label+' native SVG differs');
  assert.deepEqual(actual.pattern.settings,direct.settings,sample.label+' option/default normalization differs');
  for(const name of parts){
    const a=actual.pattern.parts[0][name].points,b=direct.parts[0][name].points;
    assert.deepEqual(Object.keys(a),Object.keys(b));
    for(const key of Object.keys(b))for(const axis of ['x','y']){assert.equal(a[key][axis],b[key][axis],sample.label+' '+name+'.'+key+'.'+axis);pointCoordinates++;}
    partComparisons++;
  }
  const presented=present(actual),p=new JSDOM(presented.svg,{contentType:'image/svg+xml'}),o=new JSDOM(originalSvg,{contentType:'image/svg+xml'});
  for(const name of parts)assert.deepEqual(curves(p.window.document,name),curves(o.window.document,name),sample.label+' presentation changed cut paths');
  p.window.close();o.window.close();
}
const result={verdict:'PASS',version:'4.10.2',officialPackageFilesMatched:manifest.files.length,
  inputSchemaMatchesSource:true,allOptionDefaultsMatch:true,cases:samples.length,partComparisons,
  missingMeasurementsNotBackfilled:true,
  pointCoordinatesCompared:pointCoordinates,coordinateTolerance:0,nativeSvgByteIdentical:true,
  inputNotMutated:true,presentationCutPathsUnchanged:true,casesCovered:samples.map(s=>s.label)};
fs.mkdirSync('work',{recursive:true});fs.writeFileSync('work/fidelity.json',JSON.stringify(result,null,2)+'\n');
console.log(JSON.stringify({...result,casesCovered:undefined}));
