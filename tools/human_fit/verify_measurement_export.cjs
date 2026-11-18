// Real Human Studio consumer: independent measurements from renderer and OBJ.
const {chromium}=require('playwright');
const fs=require('fs'),path=require('path'),http=require('http'),crypto=require('crypto');
const args={};for(let i=2;i<process.argv.length;i+=2)args[process.argv[i].slice(2)]=process.argv[i+1];
const root=path.resolve(__dirname,'../..'),out=path.resolve(args.out||'work/model-measurement-export-browser');fs.mkdirSync(out,{recursive:true});
const checks=[],errors=[],sha=v=>crypto.createHash('sha256').update(v).digest('hex'),clone=v=>JSON.parse(JSON.stringify(v));
let server,browser;
function check(value,name,evidence){checks.push({name,passed:!!value,evidence});if(!value)throw Error(name);}
function independentMeasures(asset,positions){
 const values={};for(const control of asset.controls){
  if(control.key==='height'){const ys=asset.bodyVertexIds.map(i=>positions[i*3+1]);values.height=Math.max(...ys)-Math.min(...ys);}
  else{let length=0;for(let j=1;j<control.path.length;j++){const a=control.path[j-1]*3,b=control.path[j]*3;length+=Math.hypot(...[0,1,2].map(k=>positions[a+k]-positions[b+k]));}values[control.key]=length;}
 }return values;
}
function maxDifference(a,b){return Math.max(...Object.keys(a).map(k=>Math.abs(a[k]-b[k])));}
function csvLine(line){const cells=[];let value='',inside=false;for(let i=0;i<line.length;i++){const ch=line[i];if(ch==='"'){if(inside&&line[i+1]==='"'){value+='"';i++;}else inside=!inside;}else if(ch===','&&!inside){cells.push(value);value='';}else value+=ch;}cells.push(value);return cells;}
(async()=>{try{
 let url=args.url;
 if(!url){server=http.createServer((req,res)=>{let file=path.resolve(root,'.'+decodeURIComponent(new URL(req.url,'http://local').pathname));if(!file.startsWith(root+path.sep)){res.writeHead(403);return res.end();}try{if(fs.statSync(file).isDirectory())file=path.join(file,'index.html');res.setHeader('Content-Type',({'.js':'text/javascript','.json':'application/json','.html':'text/html','.css':'text/css','.svg':'image/svg+xml'})[path.extname(file)]||'application/octet-stream');fs.createReadStream(file).pipe(res);}catch{res.writeHead(404);res.end();}});await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  const state=path.resolve(args.state||'web/garment-body/commerce-evals/artifacts/iteration-2/eval-2-everlane-pocket-pose/with_skill/run-1/outputs/final-state.json');url='http://127.0.0.1:'+server.address().port+'/web/human-studio/?model='+encodeURIComponent('/'+path.relative(root,state).split(path.sep).join('/'));
 }
 browser=await chromium.launch({executablePath:process.env.CHROMIUM_BIN||'/usr/bin/chromium',headless:true,args:['--no-sandbox','--enable-unsafe-swiftshader']});const page=await browser.newPage({viewport:{width:1440,height:1050},acceptDownloads:true});page.on('pageerror',e=>errors.push(e.message));
 await page.goto(url);await page.waitForFunction(()=>window.humanStudio?.ready);
 if(new URL(url).searchParams.has('model')){await page.locator('#model-source[data-state=loaded]').waitFor();check(await page.locator('#model-source').getAttribute('data-state')==='loaded','Actual linked case state loaded');}
 const snapshot=()=>page.evaluate(()=>humanStudio.getSnapshot()),geometry=()=>page.evaluate(()=>humanStudio.getGeometry()),measure=()=>page.evaluate(()=>humanStudio.getMeasurements());
 const asset=await page.evaluate(()=>humanStudio.getAsset()),initial=await snapshot(),before=await geometry(),initialOutput=await measure();
 const poseText=JSON.stringify(initial.poseDegrees),reference=independentMeasures(asset,before.rest);
 check(initialOutput.schema==='model-derived-measurements-v1'&&initialOutput.measurement_source==='neutral_mesh','Explicit mesh-derived output schema');
 check(maxDifference(initialOutput.measured_values_cm,reference)<1e-10,'All12 output sizes independently equal actual renderer rest-buffer measurements',{max_difference_cm:maxDifference(initialOutput.measured_values_cm,reference)});
 check(initialOutput.measurements.length===12&&initialOutput.measurements.every(m=>m.basis==='mesh_measurement'&&m.mesh_checked&&m.person_accuracy_verified===false&&['neutral_mesh_y_extent','closed_neutral_surface_tape_polyline','neutral_surface_landmark_distance'].includes(m.method)&&Array.isArray(m.source_vertices)&&Array.isArray(m.source_mesh_vertex_indices)&&Array.isArray(m.path_vertices_cm)),'Every size has mesh basis, definition, vertex source and limited person claim');
 check(JSON.stringify(initialOutput.target_dimensions_cm)===JSON.stringify(initial.dimensions),'Targets are retained separately from measured output');
 const names=asset.controls.map(c=>c.key);await page.locator('#advanced-dimensions').evaluate(e=>e.open=true);
 check((await page.locator('.measured').allTextContents()).every(s=>s.startsWith('Model measured ')),'All12 actual measured values shown separately below shape targets');
 await page.screenshot({path:path.join(out,'desktop.png')});
 async function download(id,name){const [item]=await Promise.all([page.waitForEvent('download'),page.locator('#'+id).click()]);const file=path.join(out,name);await item.saveAs(file);return file;}
 const jsonPath=await download('export-measurements','initial-measurements.json'),csvPath=await download('export-measurements-csv','initial-measurements.csv'),objPath=await download('export-neutral-obj','initial-neutral.obj');
 const actual=JSON.parse(fs.readFileSync(jsonPath)),obj=fs.readFileSync(objPath,'utf8'),vertices=obj.split('\n').filter(l=>l.startsWith('v ')).map(l=>l.trim().split(/\s+/).slice(1).map(Number));
 check(vertices.length===asset.bodyVertexIds.length&&sha(obj)===actual.model_fingerprints.neutral_mesh_sha256,'Actual downloaded neutral OBJ is hash-bound to measurement JSON');
 const reconstructed=Array(asset.vertices.length).fill(NaN);asset.bodyVertexIds.forEach((id,i)=>vertices[i].forEach((v,k)=>reconstructed[id*3+k]=v));
 const objMeasures=independentMeasures(asset,reconstructed);
 check(maxDifference(actual.measured_values_cm,objMeasures)<1e-7,'Downloaded OBJ independently remeasures all12 primary sizes',{max_difference_cm:maxDifference(actual.measured_values_cm,objMeasures)});
 check(sha(JSON.stringify(actual.source_state,null,2))===actual.model_fingerprints.state_sha256&&sha(JSON.stringify(actual.source_state.poseDegrees))===actual.model_fingerprints.pose_sha256,'Complete captured source state and pose hashes match downloaded JSON');
 const rows=fs.readFileSync(csvPath,'utf8').trim().split(/\r?\n/).map(csvLine),columns=rows.shift(),valueColumn=columns.indexOf('value_cm');
 check(rows.length===12&&rows.every(row=>Math.abs(Number(row[valueColumn])-actual.measured_values_cm[row[0]])<1e-10),'Actual CSV contains the same model-derived sizes');
 // A falsified measurement cache in an import must not determine the result.
 const forged=clone(initial);for(const key of names)forged.measuredNeutral[key]=1000;forged.maximumTargetErrorCm=0;
 await page.locator('#state-file').setInputFiles({name:'false-cached-measurements.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(forged))});await page.waitForFunction(()=>document.getElementById('state-file').value===''&&!document.getElementById('export-state').disabled);
 const afterForged=await measure();check(maxDifference(afterForged.measured_values_cm,reference)<.002&&names.every(k=>afterForged.measured_values_cm[k]!==1000),'False cached measuredNeutral cannot contaminate actual mesh measurements');
 const busyProbe=await page.evaluate(()=>{const input=document.getElementById('size-waist');input.value=String(humanStudio.getSnapshot().dimensions.waist+2);input.dispatchEvent(new Event('change'));const disabled=['export-measurements','export-measurements-csv','export-neutral-obj'].every(id=>document.getElementById(id).disabled);return humanStudio.getMeasurements().then(()=>({disabled,rejected:false}),e=>({disabled,rejected:true,message:e.message}));});
 check(busyProbe.disabled&&busyProbe.rejected,'Pending65ms body rebuild blocks stale measurement exports and read API',busyProbe);
 await page.waitForFunction(value=>humanStudio.getSnapshot().dimensions.waist===value&&!document.getElementById('export-state').disabled,initial.dimensions.waist+2);
 const changed=await measure(),changedGeometry=await geometry(),changedState=await snapshot();
 check(Math.abs(changed.measured_values_cm.waist-initialOutput.measured_values_cm.waist)>1&&sha(JSON.stringify(changedGeometry.rest))!==sha(JSON.stringify(before.rest)),'Actual cm edit changes neutral mesh and exported measured waist');
 check(JSON.stringify(changedState.poseDegrees)===poseText,'Body size edit preserves the entire supplied target pose');
 check(maxDifference(changed.measured_values_cm,independentMeasures(asset,changedGeometry.rest))<1e-10,'After size edit every measured value still comes from current geometry');
 await page.locator('#tab-pose').click();await page.locator('#mirror-pose').uncheck();await page.locator('#joint-select').selectOption('upperarm01.L');const angle=(changedState.poseDegrees['upperarm01.L']||[0,0,0])[0]+7;await page.locator('#angle-0').fill(String(angle));await page.locator('#angle-0').press('Tab');
 const posed=await measure(),posedGeometry=await geometry();
 check(sha(JSON.stringify(posedGeometry.posed))!==sha(JSON.stringify(changedGeometry.posed))&&sha(JSON.stringify(posedGeometry.rest))===sha(JSON.stringify(changedGeometry.rest)),'Actual joint UI edit changes posed vertices without changing neutral mesh');
 check(maxDifference(posed.measured_values_cm,changed.measured_values_cm)===0&&posed.model_fingerprints.neutral_mesh_sha256===changed.model_fingerprints.neutral_mesh_sha256&&posed.model_fingerprints.pose_sha256!==changed.model_fingerprints.pose_sha256,'Posed bounding-box changes do not alter primary neutral dimensions');
 await page.screenshot({path:path.join(out,'edited-pose.png')});
 const saved=await download('export-state','edited-state.json'),expectedPose=JSON.stringify((await snapshot()).poseDegrees);await page.locator('#tab-body').click();await download('export-measurements','edited-measurements.json');await download('export-neutral-obj','edited-neutral.obj');
 await page.locator('#tab-body').click();await page.locator('#reset-body').click();await page.locator('#state-file').setInputFiles(saved);await page.waitForFunction(v=>humanStudio.getSnapshot().dimensions.waist===v&&!document.getElementById('export-state').disabled,changedState.dimensions.waist);
 check(JSON.stringify((await snapshot()).poseDegrees)===expectedPose&&maxDifference((await measure()).measured_values_cm,changed.measured_values_cm)<.002,'Saved edited state reimport restores measured body and full pose');
 const stable=await snapshot(),stableGeometry=await geometry(),bad={...stable,units:'m'};await page.locator('#state-file').setInputFiles({name:'wrong-unit.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(bad))});await page.locator('#toast').filter({hasText:'Could not import'}).waitFor();
 check(JSON.stringify(await snapshot())===JSON.stringify(stable)&&sha(JSON.stringify((await geometry()).rest))===sha(JSON.stringify(stableGeometry.rest)),'Wrong-unit import rejected without changing measured geometry');
 // Force a supported-range combination with residuals: target labels must not
 // overwrite primary mesh values when the morph basis cannot hit every target.
 await page.evaluate(()=>humanStudio.setDimensions(Object.fromEntries(humanStudio.getAsset().controls.map(c=>[c.key,c.max]))));
 const extreme=await measure(),extremeGeometry=await geometry(),maxResidual=Math.max(...names.map(k=>Math.abs(extreme.measured_values_cm[k]-extreme.target_dimensions_cm[k])));
 check(maxResidual>.01&&maxDifference(extreme.measured_values_cm,independentMeasures(asset,extremeGeometry.rest))<1e-10,'Unreachable target combination exports actual mesh residuals instead of target labels',{maximum_target_difference_cm:maxResidual});
 await download('export-measurements','residual-measurements.json');await download('export-neutral-obj','residual-neutral.obj');
 await page.locator('#state-file').setInputFiles(saved);await page.waitForFunction(v=>humanStudio.getSnapshot().dimensions.waist===v&&!document.getElementById('export-state').disabled,changedState.dimensions.waist);
 await page.setViewportSize({width:375,height:812});check(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Actual375px mobile viewport has no horizontal overflow');await page.screenshot({path:path.join(out,'mobile.png'),fullPage:true});check(errors.length===0,'No browser runtime errors',errors);
 fs.writeFileSync(path.join(out,'report.json'),JSON.stringify({verdict:'PASS',scope:'Actual model-derived dimension exports and edit/import lifecycle; no photograph/person accuracy or physical fit claim',url,checks,errors,initial_measured_values_cm:actual.measured_values_cm,edited_measured_values_cm:changed.measured_values_cm},null,2)+'\n');console.log(JSON.stringify({verdict:'PASS',checks:checks.length,out}));
}catch(error){fs.writeFileSync(path.join(out,'report.json'),JSON.stringify({verdict:'FAIL',error:String(error),checks,errors},null,2)+'\n');throw error;}finally{if(browser)await browser.close();if(server)await new Promise(resolve=>server.close(resolve));}})().catch(e=>{console.error(e);process.exitCode=1});
