// Independent real-browser consumer probe for the fixed-action cm-edit task.
const {chromium}=require('playwright');
const fs=require('fs'),path=require('path'),http=require('http'),crypto=require('crypto');
const root=path.resolve(__dirname,'../..'),args={};
for(let i=2;i<process.argv.length;i+=2)args[process.argv[i].slice(2)]=process.argv[i+1];
if(!args.source||!args.final||!args.out)throw Error('--source SOURCE_JSON --final FINAL_JSON --out DIR');
const output=path.resolve(args.out);fs.mkdirSync(output,{recursive:true});
const sha=v=>crypto.createHash('sha256').update(JSON.stringify(v)).digest('hex');
const fullPose=(s,names)=>Object.fromEntries(names.map(n=>[n,s.poseDegrees[n]||[0,0,0]]));
const distance=(a,b)=>Math.hypot(...a.map((x,i)=>x-b[i]));
const checks=[],errors=[];let server,browser;
const check=(ok,name,evidence)=>{checks.push({passed:!!ok,name,evidence});if(!ok)throw Error(name);};
(async()=>{try{
 const source=JSON.parse(fs.readFileSync(args.source)),expected=JSON.parse(fs.readFileSync(args.final));
 server=http.createServer((req,res)=>{
  const filename=path.resolve(root,'.'+decodeURIComponent(new URL(req.url,'http://local').pathname));
  if(!filename.startsWith(root+path.sep)){res.writeHead(403);res.end();return;}
  let file=filename;try{if(fs.statSync(file).isDirectory())file=path.join(file,'index.html');
   const types={'.js':'text/javascript','.json':'application/json','.css':'text/css','.html':'text/html','.svg':'image/svg+xml'};
   res.setHeader('Content-Type',types[path.extname(file)]||'application/octet-stream');fs.createReadStream(file).pipe(res);
  }catch{res.writeHead(404);res.end();}
 });await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 const base='http://127.0.0.1:'+server.address().port;
 const sourcePath='/'+path.relative(root,path.resolve(args.source)).split(path.sep).join('/');
 const url=base+'/web/human-studio/?model='+encodeURIComponent(sourcePath);
 browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_BIN||'/usr/bin/chromium',args:['--no-sandbox','--enable-unsafe-swiftshader']});
 const page=await browser.newPage({viewport:{width:1440,height:1000},acceptDownloads:true});page.on('pageerror',e=>errors.push(e.message));
 await page.goto(url);await page.waitForFunction(()=>window.humanStudio?.ready);
 const snapshot=()=>page.evaluate(()=>humanStudio.getSnapshot()),geometry=()=>page.evaluate(()=>humanStudio.getGeometry());
 const initial=await snapshot(),before=await geometry(),names=before.bones.map(b=>b.name),pose0=fullPose(source,names);
 check(JSON.stringify(fullPose(initial,names))===JSON.stringify(pose0),'Actual supplied target action loaded');
 if(args['consume-only']==='true'){
  check(JSON.stringify(initial.dimensions)===JSON.stringify(expected.dimensions),'Actual saved photo-fit cm state loaded');
  const expectedVertices=fs.readFileSync(args.mesh,'utf8').split('\n').filter(l=>l.startsWith('v ')).map(l=>l.trim().split(/\s+/).slice(1).map(Number));
  const maxDelta=Math.max(...before.posed.map((v,i)=>distance(v,expectedVertices[i])));check(maxDelta<.002,'Actual browser loaded mesh agrees with graded posed OBJ',{max_delta_cm:maxDelta});
  const fingerprint=sha(before.posed);
  for(const view of ['front','side','back']){
   await page.getByRole('button',{name:view[0].toUpperCase()+view.slice(1),exact:true}).click();
   check(sha((await geometry()).posed)===fingerprint&&JSON.stringify(fullPose(await snapshot(),names))===JSON.stringify(pose0),'Actual photo-fit '+view+' camera keeps one saved body/action');
  }
  const waist=initial.dimensions.waist+.1;await page.locator('#size-waist').fill(String(waist));await page.locator('#size-waist').press('Tab');
  check((await snapshot()).dimensions.waist===waist&&sha((await geometry()).rest)!==sha(before.rest)&&JSON.stringify(fullPose(await snapshot(),names))===JSON.stringify(pose0),'Actual imported photo-fit remains cm adjustable without action reset');
  await page.screenshot({path:path.join(output,'consumed-photo-fit.png')});check(errors.length===0,'No photo-fit consumer runtime errors',errors);
  fs.writeFileSync(path.join(output,'browser.json'),JSON.stringify({verdict:'PASS',mode:'consume-only',checks,source:path.resolve(args.source),executor_final:path.resolve(args.final),max_pose_obj_delta_cm:maxDelta,errors},null,2)+'\n');console.log(JSON.stringify({verdict:'PASS',checks:checks.length,mode:'consume-only'}));return;
 }
 await page.locator('#advanced-dimensions > summary').click();
 const desired={...source.dimensions,waist:source.dimensions.waist+3,upperArmLength:source.dimensions.upperArmLength+2,forearmLength:source.dimensions.forearmLength+1};
 for(const key of ['waist','upperArmLength','forearmLength']){
  const input=page.locator('#size-'+key);await input.fill(String(desired[key]));await input.press('Tab');
  await page.waitForFunction(({key,value})=>humanStudio.getSnapshot().dimensions[key]===value&&!document.getElementById('export-state').disabled,{key,value:desired[key]});
 }
 const final=await snapshot(),after=await geometry();
 check(JSON.stringify(final.dimensions)===JSON.stringify(desired),'Actual three cm UI edits match required targets');
 check(JSON.stringify(fullPose(final,names))===JSON.stringify(pose0),'Complete target pose unchanged after cm edits');
 const maxVertex=Math.max(...after.posed.map((v,i)=>distance(v,before.posed[i])));
 check(maxVertex>.1,'Cm edits changed actual anatomical vertices',{max_cm:maxVertex});
 const boneLengths=g=>{const b=Object.fromEntries(g.bones.map(v=>[v.name,v.position]));return Object.fromEntries(['L','R'].flatMap(s=>[['upperArm.'+s,distance(b['upperarm01.'+s],b['lowerarm01.'+s])],['forearm.'+s,distance(b['lowerarm01.'+s],b['wrist.'+s])]]));};
 const lb=boneLengths(before),la=boneLengths(after);check(Object.keys(lb).every(k=>Math.abs(la[k]-lb[k])>.2),'Actual bone-head segment lengths respond',{before_cm:lb,after_cm:la});
 check(Object.keys(desired).every(k=>Math.abs(final.measuredNeutral[k]-desired[k])<=.2),'Neutral tape measurements match edited cm');
 check(Object.keys(desired).every(k=>Math.abs(expected.dimensions[k]-desired[k])<1e-9)&&JSON.stringify(fullPose(expected,names))===JSON.stringify(pose0),'Executor final state matches independently repeated task');
 const finalMeshHash=sha(after.posed),viewPixels={};
 for(const view of ['front','side','back']){
  await page.getByRole('button',{name:view[0].toUpperCase()+view.slice(1),exact:true}).click();await page.waitForTimeout(80);
  const s=await snapshot(),g=await geometry();check(JSON.stringify(s.dimensions)===JSON.stringify(final.dimensions)&&JSON.stringify(fullPose(s,names))===JSON.stringify(pose0)&&sha(g.posed)===finalMeshHash,'Actual '+view+' camera preserves the one body/pose/mesh');
  await page.screenshot({path:path.join(output,view+'.png')});
  const image=await page.locator('canvas').screenshot({path:path.join(output,view+'-canvas.png')});viewPixels[view]=crypto.createHash('sha256').update(image).digest('hex');
 }
 check(new Set(Object.values(viewPixels)).size===3,'Actual camera screenshots differ');
 const download=page.waitForEvent('download');await page.locator('#export-state').click();await(await download).saveAs(path.join(output,'saved.json'));
 const saved=JSON.parse(fs.readFileSync(path.join(output,'saved.json')));check(JSON.stringify(saved)===JSON.stringify(await snapshot()),'Actual downloaded JSON is current state');
 await page.locator('#state-file').setInputFiles(path.resolve(args.source));await page.waitForFunction(v=>humanStudio.getSnapshot().dimensions.waist===v,source.dimensions.waist);
 await page.locator('#state-file').setInputFiles(path.join(output,'saved.json'));await page.waitForFunction(v=>humanStudio.getSnapshot().dimensions.waist===v,desired.waist);
 check(JSON.stringify(fullPose(await snapshot(),names))===JSON.stringify(pose0),'Actual JSON reimport preserves target action');
 await page.goto(base+'/web/human-studio/');await page.waitForFunction(()=>window.humanStudio?.ready);
 const reloaded=await snapshot();check(JSON.stringify(reloaded.dimensions)===JSON.stringify(desired)&&JSON.stringify(fullPose(reloaded,names))===JSON.stringify(pose0),'Bare URL reload restores saved cm and action');
 const good=JSON.stringify(await snapshot()),bad={...JSON.parse(good),dimensions:{...desired,waist:'invalid'}};
 await page.locator('#state-file').setInputFiles({name:'invalid.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(bad))});await page.waitForTimeout(100);
 check(JSON.stringify(await snapshot())===good,'Invalid typed state rejected without model mutation');
 await page.locator('#size-waist').fill(String(desired.waist+.047));await page.locator('#size-waist').press('Tab');
 check((await snapshot()).dimensions.waist===desired.waist&&JSON.stringify(fullPose(await snapshot(),names))===JSON.stringify(pose0),'Off-step cm input normalized without action reset');
 await page.setViewportSize({width:375,height:812});check(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Actual 375px viewport has no overflow');
 await page.screenshot({path:path.join(output,'mobile.png')});check(errors.length===0,'No real browser runtime errors',errors);
 fs.writeFileSync(path.join(output,'browser.json'),JSON.stringify({verdict:'PASS',checks,source:path.resolve(args.source),executor_final:path.resolve(args.final),pose_sha256:sha(pose0),max_vertex_displacement_cm:maxVertex,bones_before_cm:lb,bones_after_cm:la,errors},null,2)+'\n');
 console.log(JSON.stringify({verdict:'PASS',checks:checks.length}));
 }catch(error){fs.writeFileSync(path.join(output,'browser.json'),JSON.stringify({verdict:'FAIL',error:String(error),checks,errors},null,2)+'\n');throw error;}
 finally{if(browser)await browser.close();if(server)await new Promise(r=>server.close(r));}
})().catch(e=>{console.error(e);process.exitCode=1;});
