const fs=require('fs'),path=require('path'),http=require('http');
const {chromium}=require('playwright');
const dir=__dirname;
const server=http.createServer((req,res)=>{const f=path.join(dir,decodeURIComponent(req.url.split('?')[0]));if(!f.startsWith(dir+path.sep)){res.writeHead(403);return res.end()}fs.readFile(f,(e,d)=>{res.writeHead(e?404:200,{'Content-Type':f.endsWith('.html')?'text/html':'application/octet-stream'});res.end(e?'Missing':d)})});
const stale={version:1,height:164,chest:78,waist:88,hip:84,depth_ratio:0.70};
function assert(ok,msg){if(!ok)throw Error(msg)}
(async()=>{let browser;try{
 await new Promise(r=>server.listen(0,'127.0.0.1',r));const base=`http://127.0.0.1:${server.address().port}`;
 browser=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
 const page=await browser.newPage({viewport:{width:1280,height:900}});const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto(base+'/viewer-before.html');await page.evaluate(s=>localStorage.setItem('synthetic-body-viewer',JSON.stringify(s)),stale);await page.reload();await page.screenshot({path:path.join(dir,'desktop-before.png')});
 const pixels=()=>page.evaluate(()=>(()=>{const d=document.querySelector('canvas').getContext('2d').getImageData(0,0,600,720).data;let s='';for(let i=0;i<d.length;i+=8192)s+=String.fromCharCode(...d.subarray(i,i+8192));return btoa(s)})());
 const difference=(a,b)=>{a=Buffer.from(a,'base64');b=Buffer.from(b,'base64');let n=0;for(let i=0;i<a.length;i+=4)if(a[i]!==b[i]||a[i+1]!==b[i+1]||a[i+2]!==b[i+2])n++;return n};
 const beforePixels=await pixels();await page.goto(base+'/viewer.html');const initial=await page.evaluate(()=>evalState());
 const expected=fs.readFileSync(path.join(dir,'body.obj'),'utf8').split('\n').filter(l=>l.startsWith('v ')).map(l=>l.split(/\s+/).slice(1).map(Number));
 const maxError=Math.max(...expected.flatMap((v,i)=>v.map((x,k)=>Math.abs(x-initial.vertices[i][k]))));
 assert(initial.version===2&&initial.params.chest===98&&initial.params.waist===74,'stale cache migration');assert(expected.length===initial.vertices.length&&maxError<1e-10,'actual OBJ synchronization');
 const defaultPixels=await pixels();const migrationPixelDiff=difference(beforePixels,defaultPixels);assert(migrationPixelDiff>100,'migration visible');await page.screenshot({path:path.join(dir,'desktop-after.png')});
 const sliders={};for(const key of ['height','chest','waist','hip']){
 const old=await page.evaluate(()=>evalState());const p1=await pixels();const slider=page.locator('#'+key);await slider.click();await slider.press('Home');await slider.press('ArrowRight');const next=await page.evaluate(()=>evalState());const diff=difference(p1,await pixels());
 const moved=next.vertices.reduce((n,v,i)=>n+(v.some((x,k)=>Math.abs(x-old.vertices[i][k])>1e-8)?1:0),0);
 assert(moved>0&&diff>100,key+' must deform actual vertices and pixels');sliders[key]={value:next.params[key],changedVertices:moved,changedPixels:diff};
 }
 await page.screenshot({path:path.join(dir,'desktop-slider-after.png')});const changed=await page.evaluate(()=>evalState());await page.reload();const reloaded=await page.evaluate(()=>evalState());assert(JSON.stringify(changed)===JSON.stringify(reloaded),'reload persistence');
 const cameraPixels={};for(const angle of ['0','1.57079632679','3.14159265359']){await page.locator(`button[data-angle="${angle}"]`).click();cameraPixels[angle]=await pixels()}
 const cameraDiff={side:difference(cameraPixels['0'],cameraPixels['1.57079632679']),back:difference(cameraPixels['0'],cameraPixels['3.14159265359'])};assert(cameraDiff.side>100&&cameraDiff.back>100,'camera pixel changes');
 const prev=await pixels();await page.locator('#rotation').click();await page.locator('#rotation').press('Home');await page.locator('#rotation').press('ArrowRight');const rotateDiff=difference(prev,await pixels());assert(rotateDiff>100,'rotation pixels');
 // Diagnostic is detached from live geometry.
 await page.evaluate(()=>{const s=evalState();s.vertices[0][0]=1e9;s.params.height=0;try{window.evalState=()=>null}catch(e){}});assert((await page.evaluate(()=>evalState())).params.height===changed.params.height,'read-only diagnostic');
 // Fresh mobile context shows authoritative default.
 const mobile=await browser.newPage({viewport:{width:390,height:844},isMobile:true,deviceScaleFactor:1});await mobile.goto(base+'/viewer.html');const mobileWidth=await mobile.evaluate(()=>innerWidth);assert(mobileWidth===390,'mobile viewport actual width');const overflow=await mobile.evaluate(()=>document.documentElement.scrollWidth>innerWidth);assert(!overflow,'mobile horizontal overflow');await mobile.screenshot({path:path.join(dir,'mobile.png'),fullPage:true});
 assert(errors.length===0,'runtime errors');const result={passed:true,chromium:await browser.version(),maxDefaultVertexError:maxError,vertexCount:expected.length,migrationPixelDiff,sliders,cameraDiff,rotationChangedPixels:rotateDiff,reloadExact:true,mobileOverflow:overflow,errors};fs.writeFileSync(path.join(dir,'browser-results.json'),JSON.stringify(result,null,2));fs.writeFileSync(path.join(dir,'diagnostic-initial.json'),JSON.stringify(initial));fs.writeFileSync(path.join(dir,'diagnostic-slider-reloaded.json'),JSON.stringify(reloaded));console.log(JSON.stringify(result,null,2));
 }finally{if(browser)await browser.close();await new Promise(r=>server.close(r))}})().catch(e=>{console.error(e);process.exitCode=1});
