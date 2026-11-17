const {chromium}=require('playwright');
const fs=require('fs'),path=require('path'),assert=require('assert');
const {spawn}=require('child_process');
(async()=>{
 const dir=__dirname,port=process.env.PORT||'8872';
 const server=spawn('python',['-m','http.server',port,'--bind','127.0.0.1','--directory',dir],{stdio:'ignore'});
 let browser;
 try{
  for(let i=0;i<50;i++){try{const r=await fetch(`http://127.0.0.1:${port}/viewer.html`);if(r.ok)break;}catch{}await new Promise(r=>setTimeout(r,100));}
  browser=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
  const page=await browser.newPage({viewport:{width:1100,height:850},acceptDownloads:true}), errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  const base=`http://127.0.0.1:${port}`;
  await page.goto(base+'/before.html');
  await page.evaluate(()=>localStorage.setItem('synthetic-body-viewer',JSON.stringify({version:1,height:164,chest:78,waist:88,hip:84,depth_ratio:.70})));
  await page.reload();await page.screenshot({path:path.join(dir,'desktop-before.png'),fullPage:true});
  await page.goto(base+'/viewer.html');
  const initial=await page.evaluate(()=>evalState());
  const expected=JSON.parse(fs.readFileSync(path.join(dir,'body.json')));
  assert.deepStrictEqual(initial.params,expected);
  assert.equal(initial.version,2);
  const obj=fs.readFileSync(path.join(dir,'body.obj'),'utf8').split('\n').filter(l=>l.startsWith('v ')).map(l=>l.slice(2).split(/\s+/).map(Number));
  assert.equal(initial.vertices.length,obj.length);
  let maxObjError=0;initial.vertices.forEach((v,i)=>v.forEach((x,j)=>maxObjError=Math.max(maxObjError,Math.abs(x-obj[i][j]))));
  assert(maxObjError<1e-6);
  await page.screenshot({path:path.join(dir,'desktop-final-default.png'),fullPage:true});
  const snapshot=()=>page.evaluate(()=>({state:evalState(),pixels:Array.from(document.querySelector('canvas').getContext('2d').getImageData(0,0,600,720).data)}));
  const changes=[];
  for(const key of ['height','chest','waist','hip']){
   const before=await snapshot();
   await page.locator('#'+key).focus();
   for(let i=0;i<8;i++)await page.keyboard.press('ArrowRight');
   const after=await snapshot();
   let verticesChanged=0,pixelsChanged=0;
   before.state.vertices.forEach((v,i)=>{if(v.some((x,j)=>x!==after.state.vertices[i][j]))verticesChanged++});
   before.pixels.forEach((x,i)=>{if(i%4!==3 && x!==after.pixels[i])pixelsChanged++});
   assert(verticesChanged>0);assert(pixelsChanged>100);
   assert(after.state.vertices.every(v=>v.length===3&&v.every(Number.isFinite)));
   changes.push({slider:key,from:before.state.params[key],to:after.state.params[key],verticesChanged,changedColorChannels:pixelsChanged});
  }
  await page.screenshot({path:path.join(dir,'desktop-after.png'),fullPage:true});
  const edited=await page.evaluate(()=>evalState());
  await page.reload();assert.deepStrictEqual(await page.evaluate(()=>evalState()),edited);
  const downloadPromise=page.waitForEvent('download');await page.locator('#export').click();const download=await downloadPromise;
  await download.saveAs(path.join(dir,'current-body-state.json'));
  assert.deepStrictEqual(JSON.parse(fs.readFileSync(path.join(dir,'current-body-state.json'))),edited);
  const cameras=[];
  for(const angle of ['0','1.57079632679','3.14159265359']){
   await page.locator(`[data-angle="${angle}"]`).click();
   const val=await page.locator('#rotation').inputValue();
   assert(Math.abs(Number(val)-Number(angle)*180/Math.PI)<1);
   const image=await page.locator('canvas').screenshot();
   const hash=require('crypto').createHash('sha256').update(image).digest('hex');
   cameras.push({angle,hash});
  }
  assert(new Set(cameras.map(x=>x.hash)).size===3);
  const beforeRotate=(await snapshot()).pixels;
  await page.locator('#rotation').focus();for(let i=0;i<35;i++)await page.keyboard.press('ArrowLeft');
  const rotated=(await snapshot()).pixels;assert(beforeRotate.some((x,i)=>x!==rotated[i]));
  assert.deepStrictEqual(await page.evaluate(()=>evalState()),edited);
  await page.setViewportSize({width:375,height:812});
  await page.screenshot({path:path.join(dir,'mobile.png'),fullPage:true});
  const mobile=await page.evaluate(()=>({width:innerWidth,scrollWidth:document.documentElement.scrollWidth}));
  assert(mobile.scrollWidth<=mobile.width);
  assert.equal(errors.length,0);
  // Returned arrays cannot mutate live geometry, and the diagnostic cannot be replaced.
  await page.evaluate(()=>{const s=evalState();try{s.vertices[0][0]=99999;}catch{}try{window.evalState=()=>null;}catch{}});
  assert.deepStrictEqual(await page.evaluate(()=>evalState()),edited);
  const results={passed:true,initialVersion:initial.version,initialParams:initial.params,vertexCount:obj.length,maxObjError,changes,cameras,reloadExactMatch:true,exportExactMatch:true,rotationPixelsChanged:true,mobile,errors};
  fs.writeFileSync(path.join(dir,'browser-results.json'),JSON.stringify(results,null,2));console.log(JSON.stringify(results,null,2));
 }finally{if(browser)await browser.close();server.kill();}
})().catch(e=>{console.error(e);process.exitCode=1;});
