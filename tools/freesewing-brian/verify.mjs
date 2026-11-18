import fs from 'node:fs';
import assert from 'node:assert/strict';
import {JSDOM,VirtualConsole} from 'jsdom';
import {fields,defaults,required,generate} from './sliders-engine.mjs';
const allPaths=doc=>[...doc.querySelectorAll('path')].map(p=>p.getAttribute('d'));
const svgDoc=svg=>new JSDOM(svg,{contentType:'image/svg+xml'});
const signature=svg=>{const d=svgDoc(svg);const paths=allPaths(d.window.document);d.window.close();return JSON.stringify(paths);};
assert.deepEqual(fields.filter(f=>!f.optional).map(f=>f.key).sort(),[...required].sort());
const base=generate(defaults);
assert.equal(base.quarterWidth,275);
const cases=[];
for(const f of fields.filter(f=>!f.optional)) {
  for(const value of [f.min,f.max]) {
    const r=generate({...defaults,[f.key]:value});
    assert.equal(r.settings.measurements[f.key],f.angle?value:value*10);
    assert.notEqual(signature(r.svg),signature(base.svg),`${f.key} must change a line, not just a label`);
    cases.push({field:f.key,value,finite:true,geometryChanged:true});
  }
}
assert.equal(generate({...defaults,chest:110}).quarterWidth,302.5);
assert.notEqual(signature(generate(defaults,true).svg),signature(base.svg));
assert.throws(()=>generate({...defaults,chest:NaN}));
const errors=[],vc=new VirtualConsole();vc.on('jsdomError',e=>errors.push(e.message));
const dom=new JSDOM(fs.readFileSync('../../web/freesewing/brian/index.html','utf8'),{runScripts:'dangerously',pretendToBeVisual:true,virtualConsole:vc});
const w=dom.window,d=w.document,one=s=>d.querySelector(s);
const settle=()=>new Promise(resolve=>w.requestAnimationFrame(()=>resolve()));
const input=async(key,value)=>{one('#'+key).value=String(value);one('#'+key).dispatchEvent(new w.Event('input',{bubbles:true}));await settle();};
assert.equal(d.querySelectorAll('input[type=range]').length,13);
assert(one('#highBust').disabled);
assert.equal(one('#status').dataset.state,'ready');
await input('chest',110);
assert.equal(Number(one('#preview').dataset.width),302.5);
assert.equal(one('#chest-value').textContent,'110 cm');
assert.equal(one('#overall').value,'100');
await input('overall',110);
assert.equal(one('#chest').value,'121');
assert.equal(one('#shoulderToShoulder').value,'50.5');
assert.equal(one('#shoulderSlope').value,'15');
assert.equal(Number(one('#preview').dataset.chest),1210);
one('#reset').click();await settle();
assert.equal(one('#chest').value,'100');
let active={...defaults};
for(const f of fields.filter(f=>!f.optional)) {
  const value=f.value+f.step;
  await input(f.key,value);active[f.key]=value;
  const actual=generate(active),nd=svgDoc(actual.svg);
  assert.deepEqual(allPaths(one('#preview')),allPaths(nd.window.document));nd.window.close();
  assert.equal(one('#status').dataset.state,'ready');
}
one('#use-high-bust').checked=true;one('#use-high-bust').dispatchEvent(new w.Event('change',{bubbles:true}));await settle();
assert(!one('#highBust').disabled);
await input('highBust',97.5);active.highBust=97.5;
const actual=generate(active,true),nd=svgDoc(actual.svg);
assert.deepEqual(allPaths(one('#preview')),allPaths(nd.window.document));nd.window.close();
let downloadBlob,filename;
w.URL.createObjectURL=blob=>{downloadBlob=blob;return 'blob:verified';};w.URL.revokeObjectURL=()=>{};
w.HTMLAnchorElement.prototype.click=function(){filename=this.download;};
one('#download-svg').click();assert(downloadBlob);
const exported=await new Promise(resolve=>{const r=new w.FileReader();r.onload=()=>resolve(r.result);r.readAsText(downloadBlob);});
assert.equal(exported,actual.svg);assert.match(filename,/\.svg$/);
assert(exported.includes('mm"')); // Native physical units retained for SVG export.
assert.equal(errors.length,0,errors.join('\n'));
assert(one('#preview>svg').getAttribute('aria-label'));
const result={engine:'@freesewing/brian@4.10.2',requiredFields:required.length,optionalFields:1,rangeControls:13,engineBoundaryCases:cases.length,allInputsAffectGeometry:true,liveChangesMatchBrian:true,masterChangesLengthsNotAngles:true,highBustWorks:true,svgDownloadMatchesCurrentInput:true,jsdomErrors:errors,cases};
fs.mkdirSync('work',{recursive:true});
fs.writeFileSync('work/sliders-verification.json',JSON.stringify(result,null,2));
console.log(JSON.stringify({...result,cases:undefined}));w.close();
