// DOM integration checks. This intentionally tests the WebGL fallback, not GPU rendering.
import {JSDOM,VirtualConsole} from 'jsdom';
import assert from 'node:assert/strict';
import fs from 'node:fs';
const html=fs.readFileSync('dist/index.html','utf8'), results=[],errors=[];
function boot(source=html,url='https://example.test/'){
  const downloads=[],objects=new Map(),vc=new VirtualConsole();
  vc.on('jsdomError',e=>errors.push(e.message));
  const dom=new JSDOM(source,{url,runScripts:'dangerously',pretendToBeVisual:true,virtualConsole:vc,beforeParse(w){
    w.HTMLCanvasElement.prototype.getContext=()=>null;
    w.matchMedia=()=>({matches:true,addEventListener(){},removeEventListener(){}});
    w.requestAnimationFrame=()=>0;
    w.HTMLDialogElement.prototype.showModal=function(){this.open=true;};
    w.HTMLDialogElement.prototype.close=function(){this.open=false;};
    w.Blob=Blob;w.URL.createObjectURL=b=>{const u='blob:test/'+objects.size;objects.set(u,b);return u;};w.URL.revokeObjectURL=()=>{};
    w.HTMLAnchorElement.prototype.click=function(){downloads.push({name:this.download,blob:objects.get(this.href)})};
  }});
  const w=dom.window,$=s=>w.document.querySelector(s);assert(w.Aster,'Application initialization failed');return {dom,w,$,downloads};
}
function pass(label){results.push({check:label,passed:true});}
const {dom,w,$,downloads}=boot();
assert.equal(w.Aster.getState().hasWebGL,false);assert.equal($('#webgl-error').hidden,false);assert.equal(w.document.querySelectorAll('#pattern-host [data-panel]').length,16);assert(w.Aster.verify().passed);pass('Initialization and functional 2D fallback when WebGL is unavailable');
$('[data-inspector="seams"]').click();$('[data-release="B01"]').click();assert.deepEqual([...w.Aster.getState().open],['B01']);
$('#seam-lines').checked=false;$('#seam-lines').dispatchEvent(new w.Event('change'));assert.equal(w.Aster.getState().open.length,1);pass('Individual seam release is distinct from hiding seam overlays');
$('#release-all').click();assert.equal(w.Aster.getState().open.length,24);$('#unfold').value=50;$('#unfold').dispatchEvent(new w.Event('input'));assert.equal(w.Aster.getState().unfold,.5);$('#restore').click();assert.equal(w.Aster.getState().open.length,0);assert.equal(w.Aster.getState().unfold,0);pass('Release all, assembly slider state, and reassembly');
$('#unfold-button').click();assert.equal(w.Aster.getState().view,'pattern');assert.equal(w.Aster.getState().unfold,1);pass('Unfold finishes at 2D with all seam connections released');
$('#panel-select').value='S06';$('#panel-select').dispatchEvent(new w.Event('change'));$('[data-view="compare"]').click();assert.equal(w.Aster.getState().selected,'S06');assert.equal(w.Aster.getState().view,'compare');assert($('#pattern-host [data-panel="S06"] .cut').getAttribute('stroke')==='#ba704d');pass('Compare and shared panel selection');
$('#dim-waist').value='80';$('#dim-waist').dispatchEvent(new w.Event('change'));assert.equal(w.Aster.getState().c.waist,800);$('#dim-bust').value='80';$('#dim-bust').dispatchEvent(new w.Event('change'));assert.equal(w.Aster.getState().c.bust,920);$('#allowance').value='20';$('#allowance').dispatchEvent(new w.Event('change'));assert.equal(w.Aster.getState().c.allowance,20);assert(w.Aster.verify().passed);pass('Dimension edits, invalid taper rejection and allowance recalculation');
$('[data-inspector="review"]').click();$('#review-note').value='Review this seam <img src=x onerror=alert(1)>.';$('#add-note').click();assert.equal(w.Aster.getState().notes.length,1);assert.equal($('#review-notes img'),null);$('#export-review').click();const review=JSON.parse(await downloads.at(-1).blob.text());assert.equal(review.notes[0].target,'S06');assert.equal(review.design.c.waist,800);pass('Review note save, safe text rendering and JSON export');
review.notes[0].text='Imported expert note';Object.defineProperty($('#review-file'),'files',{configurable:true,value:[{size:1000,text:async()=>JSON.stringify(review)}]});await $('#review-file').onchange({target:$('#review-file')});assert.equal(w.Aster.getState().notes[0].text,'Imported expert note');pass('Review JSON import restores notes and draft');
$('#download-svg').click();const svg=await downloads.at(-1).blob.text();assert.equal((svg.match(/data-panel=/g)||[]).length,16);assert(/width="[\d.]+mm"/.test(svg));assert(svg.includes('100 × 100'));assert(!svg.includes('NaN'));pass('SVG export has 16 panels, millimetre dimensions and calibration square');
$('[data-color="clay"]').click();$('#download-html').click();const offlineHTML=await downloads.at(-1).blob.text(),second=boot(offlineHTML,'file:///aster-studio.html');assert.equal(second.w.Aster.getState().c.waist,800);assert.equal(second.w.Aster.getState().color,'clay');second.$('#download-html').click();const third=boot(await second.downloads.at(-1).blob.text(),'file:///aster-studio-copy.html');assert(third.w.Aster);assert.equal(third.w.Aster.getState().color,'clay');pass('Downloaded HTML reopens offline with current settings and can be downloaded again');
$('#share').click();const reviewURL=$('#review-url').value;const shared=boot(html,reviewURL);assert.equal(shared.w.Aster.getState().view,'compare');assert.equal(shared.w.Aster.getState().inspector,'review');assert.equal(shared.w.Aster.getState().c.waist,800);assert.equal(shared.w.Aster.getState().notes.length,0);pass('Share link restores draft state and omits review notes');
const shortcut=boot(html,'https://example.test/#review');assert.equal(shortcut.w.Aster.getState().inspector,'review');assert.equal(shortcut.w.Aster.getState().view,'compare');pass('Direct expert review link');
assert.deepEqual(errors,[],'Unhandled DOM errors');pass('No unhandled DOM integration errors');
for(const d of [dom,second.dom,third.dom,shared.dom,shortcut.dom])d.window.close();
fs.writeFileSync('dist/dom-verification.json',JSON.stringify({environment:'Node.js + jsdom 26; WebGL unavailable by design. Not a real-browser visual test.',results,errors},null,2));
console.log(`PASS: ${results.length} DOM integration checks. GPU rendering and visual layout remain unverified.`);
