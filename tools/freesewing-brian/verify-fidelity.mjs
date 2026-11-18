import fs from 'node:fs';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {JSDOM,VirtualConsole} from 'jsdom';
import {Brian} from '@freesewing/brian';
import {pluginTheme} from '@freesewing/plugin-theme';

// This reference deliberately calls the untouched published Brian directly.
// It does not import the demo's generate() wrapper or its measurement schema.
const manifest=JSON.parse(fs.readFileSync('upstream-manifest.json','utf8'));
for(const file of manifest.files) {
  const bytes=fs.readFileSync('node_modules/@freesewing/brian/'+file.file);
  assert.equal(createHash('sha256').update(bytes).digest('hex'),file.sha256,file.file);
}
const errors=[],vc=new VirtualConsole();vc.on('jsdomError',e=>errors.push(e.message));
const dom=new JSDOM(fs.readFileSync('../../web/freesewing/brian/index.html','utf8'),{
  runScripts:'dangerously',pretendToBeVisual:true,virtualConsole:vc,
});
const d=dom.window.document,w=dom.window;
const parts=['brian.back','brian.front','library.sleeve'];
const required=Brian.patternConfig.measurements;
assert.deepEqual(required.slice().sort(),[...d.querySelectorAll('#controls input:not(#highBust)')].map(e=>e.id).sort());
const raf=()=>new Promise(resolve=>w.requestAnimationFrame(resolve));
async function input(id,value) {
  const e=d.getElementById(id);e.value=String(value);
  e.dispatchEvent(new w.Event('input',{bubbles:true}));await raf();
}
const curves=(root,name)=>[...root.querySelector(`[id="fs-stack-${name}-part-${name}"]`).querySelectorAll('path:not(.help)')].map(e=>e.getAttribute('d'));
let cases=0,partComparisons=0;
async function compare(label) {
  const measurements=Object.fromEntries(required.map(key=>[
    key,Number(d.getElementById(key).value)*(key==='shoulderSlope'?1:10),
  ]));
  const highBust=d.getElementById('use-high-bust').checked;
  if(highBust) measurements.highBust=Number(d.getElementById('highBust').value)*10;
  const original=new Brian({
    measurements,options:{chestEase:.1,draftForHighBust:highBust},
    complete:false,sa:0,paperless:false,scale:1,
  }).use(pluginTheme).draft();
  const reference=new JSDOM(original.render(),{contentType:'image/svg+xml'});
  for(const part of parts) {
    assert.deepEqual(curves(d.querySelector('#preview'),part),curves(reference.window.document,part),label+' '+part);
    partComparisons++;
  }
  let blob;
  w.URL.createObjectURL=b=>{blob=b;return 'blob:verify';};
  w.URL.revokeObjectURL=()=>{};w.HTMLAnchorElement.prototype.click=function(){};
  d.getElementById('download-svg').click();assert(blob);
  const svg=await new Promise(resolve=>{
    const reader=new w.FileReader();reader.onload=()=>resolve(reader.result);reader.readAsText(blob);
  });
  const exported=new JSDOM(svg,{contentType:'image/svg+xml'});
  for(const part of parts) assert.deepEqual(curves(exported.window.document,part),curves(reference.window.document,part),label+' export '+part);
  assert.match(exported.window.document.documentElement.getAttribute('width'),/mm$/);
  cases++;reference.window.close();exported.window.close();
}
await compare('default');
for(const key of required) {
  const e=d.getElementById(key),start=e.value;
  for(const value of [e.min,e.max]) {await input(key,value);await compare(key+'='+value);}
  await input(key,start);
}
for(const value of [75,125]) {await input('overall',value);await compare('overall='+value);}
d.getElementById('reset').click();await raf();
d.getElementById('use-high-bust').checked=true;
d.getElementById('use-high-bust').dispatchEvent(new w.Event('change',{bubbles:true}));await raf();
for(const value of [94,97.5]) {await input('highBust',value);await compare('highBust='+value);}
assert.equal(errors.length,0,errors.join('\n'));
const result={
  verdict:'PASS',version:'4.10.2',officialPackageFilesMatched:manifest.files.length,
  independentReference:'Published Brian called directly without the demo wrapper',
  cases,partComparisons,allBackFrontSleevePathsMatch:true,allExportedPathsMatch:true,
  originalChestEaseDefault:.15,demoChestEase:.1,jsdomErrors:errors,
};
fs.mkdirSync('work',{recursive:true});
fs.writeFileSync('work/fidelity.json',JSON.stringify(result,null,2)+'\n');
console.log(JSON.stringify(result));w.close();
