import fs from 'node:fs';
import assert from 'node:assert/strict';
import {JSDOM,VirtualConsole} from 'jsdom';
import {fields,required,optional,exampleMeasurements,inputContract,draftBrian,present,viewSettings} from './sliders-engine.mjs';
assert.deepEqual(fields.map(f=>f.key),[...required,...optional]);
assert.equal(inputContract.defaultOptions.chestEase,.15);
assert.equal(inputContract.measurementBounds,null);
const errors=[],vc=new VirtualConsole();vc.on('jsdomError',e=>errors.push(e.message));
const dom=new JSDOM(fs.readFileSync('../../web/freesewing/brian/index.html','utf8'),{runScripts:'dangerously',pretendToBeVisual:true,virtualConsole:vc});
const w=dom.window,d=w.document,$=s=>d.querySelector(s);
const settle=()=>new Promise(resolve=>w.requestAnimationFrame(resolve));
async function input(key,value,type='number') {
  const e=$('#'+key+(type==='number'?'-number':''));e.value=String(value);
  e.dispatchEvent(new w.Event('input',{bubbles:true}));await settle();
}
async function toggle(id,value){$('#'+id).checked=value;$('#'+id).dispatchEvent(new w.Event('change',{bubbles:true}));await settle();}
const submitted=()=>JSON.parse($('#native-input').textContent);
const paths=root=>[...root.querySelectorAll('path')].map(p=>p.getAttribute('d'));
const doc=svg=>new JSDOM(svg,{contentType:'image/svg+xml'});
assert.equal(d.querySelectorAll('input[type=range]').length,12);
assert.equal(d.querySelectorAll('input[type=number]').length,12);
assert.equal($('#overall'),null);
assert.deepEqual(submitted().measurements,exampleMeasurements);
assert.deepEqual(submitted().options,{});
assert.equal(Number($('#preview').dataset.width),287.5);
const editing=$('#chest-number');editing.value='1000.1234560';
editing.dispatchEvent(new w.Event('input',{bubbles:true}));
assert($('#download-svg').disabled&&$('#download-input').disabled,'Pending edits can export stale data');
await settle();assert.equal(editing.value,'1000.1234560','Input handler rewrote the active editor');
assert.equal(submitted().measurements.chest,1000.123456);
await input('chest',1000);
for(const f of fields){
  const e=$('#'+f.key+'-number');
  assert.equal(e.name,f.key);assert.equal(e.step,'any');
  assert(!e.hasAttribute('min')&&!e.hasAttribute('max'),f.key+' has invented bounds');
  assert.equal(e.required,!f.optional);
}
const active={...exampleMeasurements};
for(const key of required){
  const value=active[key]+.123456;
  await input(key,value);active[key]=value;
  assert.equal(submitted().measurements[key],value,key+' was rounded or converted');
  assert.equal($('#'+key+'-number').value,String(value));
  const actual=present(draftBrian({...viewSettings,measurements:{...active},options:{}}));
  const reference=doc(actual.svg);
  assert.deepEqual(paths($('#preview')),paths(reference.window.document));reference.window.close();
}
await input('chest',2100.123456);
assert.equal(submitted().measurements.chest,2100.123456);
assert(Number($('#chest').max)>2100.123456);
await input('chest',650.123456);assert.equal(submitted().measurements.chest,650.123456);
await input('chest',1100.125,'range');assert.equal(submitted().measurements.chest,1100.125);
// Declared missing fields must not be silently replaced with an example.
for(const key of required){
  const old=$('#'+key+'-number').value;
  await input(key,'');assert(!Object.hasOwn(submitted().measurements,key));
  assert($('#download-svg').disabled);assert.equal($('#preview svg'),null);
  await input(key,old);assert(!$('#download-svg').disabled,key+' did not recover');
}
$('#reset').click();await settle();
await toggle('provide-high-bust',true);
assert.equal(submitted().measurements.highBust,940);
assert.deepEqual(submitted().options,{});
assert.equal(Number($('#preview').dataset.width),287.5,'Providing highBust must not activate the option');
await toggle('draft-for-high-bust',true);
assert.equal(submitted().measurements.chest,1000,'Original chest input was mutated');
assert.equal($('#preview').dataset.effectiveChest,'940');
assert.equal(Number($('#preview').dataset.width),270.25);
await input('highBust',975.123456);
assert.equal(submitted().measurements.highBust,975.123456);
await toggle('provide-high-bust',false);
assert(!Object.hasOwn(submitted().measurements,'highBust'));
assert.equal(submitted().options.draftForHighBust,true);
assert.equal(Number($('#preview').dataset.width),287.5,'Match native fallback when highBust is absent');
let blob,filename;
w.URL.createObjectURL=b=>{blob=b;return 'blob:verified';};w.URL.revokeObjectURL=()=>{};
w.HTMLAnchorElement.prototype.click=function(){filename=this.download;};
async function readBlob(){return new Promise(resolve=>{const r=new w.FileReader();r.onload=()=>resolve(r.result);r.readAsText(blob);});}
$('#download-input').click();
assert.equal(filename,'brian-input.json');assert.deepEqual(JSON.parse(await readBlob()),submitted());
$('#download-svg').click();
assert.match(filename,/1000mm\.svg$/);
const actualSVG=await readBlob(),expected=present(draftBrian(submitted()));
assert.equal(actualSVG,expected.svg);
assert(actualSVG.includes('mm"'));assert.equal(errors.length,0,errors.join('\n'));
const result={verdict:'PASS',requiredFields:required.length,optionalFields:optional.length,rangeControls:12,
  nativeNumberInputs:12,allNativeNames:true,allUnitsNative:true,noArtificialMeasurementBounds:true,
  activeNumericEditorNotRewritten:true,pendingEditsDisableStaleDownloads:true,
  decimalInputsPreserved:required.length,missingFieldControls:required.length,
  providedHighBustDoesNotEnableDraftMode:true,independentHighBustOption:true,
  officialDefaultChestEase:.15,overallParameterRemoved:true,svgAndInputDownloadsMatch:true,jsdomErrors:errors};
fs.mkdirSync('work',{recursive:true});fs.writeFileSync('work/sliders-verification.json',JSON.stringify(result,null,2)+'\n');
console.log(JSON.stringify(result));w.close();
