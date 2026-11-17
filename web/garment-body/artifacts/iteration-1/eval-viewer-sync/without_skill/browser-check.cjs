// Run from outputs/: node browser-check.cjs http://127.0.0.1:8767
// Serve the run directory: python -m http.server 8767 --bind 127.0.0.1
const {chromium}=require('playwright');
const fs=require('fs');
const path=require('path');
const assert=require('assert/strict');
(async()=>{
 const base=process.argv[2]||'http://127.0.0.1:8767';
 const browser=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
 const context=await browser.newContext({viewport:{width:1100,height:900}});
 const page=await context.newPage();
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 const results={};
 const pixels=async()=>Buffer.from(await page.evaluate(()=>(()=>{const bytes=document.querySelector('canvas').getContext('2d').getImageData(0,0,600,720).data;let s='';for(let i=0;i<bytes.length;i+=8192)s+=String.fromCharCode(...bytes.subarray(i,i+8192));return btoa(s)})()),'base64');
 const diff=(a,b)=>a.reduce((n,x,i)=>n+(x!==b[i]),0);
 const state=()=>page.evaluate(()=>window.evalState());
 try {
 await page.goto(base+'/inputs/index.html');
 await page.evaluate(()=>localStorage.setItem('synthetic-body-viewer',JSON.stringify({version:1,height:164,chest:78,waist:88,hip:84,depth_ratio:.70})));
 await page.reload();
 await page.screenshot({path:path.join(__dirname,'original-stale.png'),fullPage:true});
 await page.goto(base+'/outputs/viewer.html');
 const initial=await state();
 const final=JSON.parse(fs.readFileSync(path.join(__dirname,'body.json'),'utf8'));
 assert.deepEqual(initial.params,final);assert.equal(initial.version,2);
 const obj=fs.readFileSync(path.join(__dirname,'body.obj'),'utf8').split('\n').filter(l=>l.startsWith('v ')).map(l=>l.slice(2).trim().split(/\s+/).map(Number));
 assert.equal(initial.vertices.length,obj.length);
 let maxDelta=0;initial.vertices.forEach((v,i)=>v.forEach((x,k)=>maxDelta=Math.max(maxDelta,Math.abs(x-obj[i][k]))));
 assert.ok(maxDelta<.000001);results.objMaxCoordinateDelta=maxDelta;results.vertices=initial.vertices.length;
 await page.screenshot({path:path.join(__dirname,'desktop-before.png'),fullPage:true});
 fs.writeFileSync(path.join(__dirname,'initial-state.json'),JSON.stringify(initial,null,2));
 // Returned objects cannot mutate the live mesh or controls.
 await page.evaluate(()=>{const copy=window.evalState();copy.params.height=0;copy.vertices[0][0]=99999});
 assert.deepEqual(await state(),initial);
 results.sliders={};
 for(const key of ['height','chest','waist','hip']){
  const before=await state(), imageBefore=await pixels();
  await page.locator('#'+key).focus();await page.keyboard.press('ArrowRight');
  const after=await state(), imageAfter=await pixels();
  assert.equal(after.params[key],before.params[key]+1);
  assert.ok(after.vertices.every(v=>v.length===3&&v.every(Number.isFinite)));
  const changedVertices=after.vertices.filter((v,i)=>v.some((x,k)=>x!==before.vertices[i][k])).length;
  const changedChannels=diff(imageBefore,imageAfter);
  assert.ok(changedVertices>0);assert.ok(changedChannels>0);
  results.sliders[key]={changedVertices,changedCanvasChannels:changedChannels,value:after.params[key]};
 }
 // Make the after image visibly distinct with a further real keyboard interaction.
 await page.locator('#chest').focus();await page.keyboard.press('End');
 await page.locator('#waist').focus();await page.keyboard.press('End');
 await page.screenshot({path:path.join(__dirname,'desktop-after.png'),fullPage:true});
 const saved=await state();
 fs.writeFileSync(path.join(__dirname,'edited-state.json'),JSON.stringify(saved,null,2));
 const front=await pixels();
 await page.locator('[data-angle="1.57079632679"]').click();const side=await pixels();
 await page.locator('[data-angle="3.14159265359"]').click();const back=await pixels();
 await page.locator('[data-angle="0"]').click();assert.equal(diff(front,await pixels()),0);
 assert.ok(diff(front,side)>0);assert.ok(diff(side,back)>0);
 results.cameras={frontToSide:diff(front,side),sideToBack:diff(side,back)};
 await page.locator('#rotation').focus();await page.keyboard.press('ArrowRight');
 results.rotationChangedCanvasChannels=diff(front,await pixels());assert.ok(results.rotationChangedCanvasChannels>0);
 assert.deepEqual(await state(),saved);
 await page.reload();assert.deepEqual(await state(),saved);
 for(const key of ['height','chest','waist','hip'])assert.equal(await page.locator('#'+key).inputValue(),String(saved.params[key]));
 results.reloadPreservedState=true;
 results.desktopOverflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth);assert.equal(results.desktopOverflow,false);
 await page.setViewportSize({width:375,height:812});
 await page.screenshot({path:path.join(__dirname,'mobile.png'),fullPage:true});
 results.mobileOverflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth);assert.equal(results.mobileOverflow,false);
 // Fresh storage independently gets final defaults.
 await page.evaluate(()=>localStorage.clear());await page.reload();assert.deepEqual((await state()).params,final);
 // Malformed storage recovers, too.
 await page.evaluate(()=>localStorage.setItem('synthetic-body-viewer','{broken'));await page.reload();assert.deepEqual((await state()).params,final);
 results.freshAndMalformedCachePassed=true;results.errors=errors;assert.deepEqual(errors,[]);
 fs.writeFileSync(path.join(__dirname,'browser-results.json'),JSON.stringify(results,null,2));
 console.log(JSON.stringify(results,null,2));
 } finally {await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
