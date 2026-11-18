import {fields,required,exampleMeasurements,exampleHighBust,inputContract,viewSettings,draftBrian,present} from './sliders-engine.mjs';
const $=s=>document.querySelector(s);
let values={...exampleMeasurements,highBust:exampleHighBust},current=null,frame=0,revision=0;
const windows=Object.fromEntries(fields.map(f=>[f.key,{min:0,max:Math.max(1,f.example*2)}]));
for(const f of fields){
  const row=document.createElement('div');row.className='field'+(f.optional?' optional':'');
  row.innerHTML=`<div class="field-title"><label for="${f.key}-number" title="${f.key}">${f.label}</label><span class="number-unit"><input type="number" id="${f.key}-number" name="${f.key}" step="any" ${f.optional?'':'required'} aria-describedby="units" title="${f.key}"><span>${f.unit}</span></span></div><input id="${f.key}" type="range" step="any" aria-label="${f.label}滑条" aria-describedby="slider-note">`;
  $('#controls').append(row);
  $('#'+f.key+'-number').addEventListener('input',e=>{values[f.key]=e.target.value===''?undefined:e.target.valueAsNumber;updateControls(e.target);schedule();});
  $('#'+f.key).addEventListener('input',e=>{values[f.key]=e.target.valueAsNumber;updateControls();schedule();});
}
function updateControls(editing=null){
  for(const f of fields){
    const numeric=$('#'+f.key+'-number'),slider=$('#'+f.key),value=values[f.key],win=windows[f.key];
    const provided=!f.optional||$('#provide-high-bust').checked;
    numeric.disabled=slider.disabled=!provided;
    // Leave the active editor alone: rewriting it would eat a typed decimal
    // separator, trailing zero or exponent, and move the caret.
    if(numeric!==editing)numeric.value=Number.isFinite(value)?String(value):'';
    // Only the slider's viewport changes. Numeric inputs have no min/max.
    if(Number.isFinite(value)){
      if(value<win.min)win.min=value-Math.max(1,Math.abs(value)/2);
      if(value>win.max)win.max=value+Math.max(1,Math.abs(value)/2);
    }
    slider.min=String(win.min);slider.max=String(win.max);
    if(Number.isFinite(value))slider.value=String(value);
    slider.setAttribute('aria-valuetext',Number.isFinite(value)?`${value} ${f.unit}`:'未填写');
  }
}
function rawInput(){
  const measurements={...values};
  if(!$('#provide-high-bust').checked)delete measurements.highBust;
  for(const key of Object.keys(measurements))if(measurements[key]===undefined)delete measurements[key];
  const options={};if($('#draft-for-high-bust').checked)options.draftForHighBust=true;
  return {...viewSettings,measurements,options};
}
function schedule(){
  current=null;$('#download-svg').disabled=true;$('#download-input').disabled=true;
  $('#preview').setAttribute('aria-busy','true');$('#status').textContent='正在重画…';
  $('#native-input').textContent=JSON.stringify(rawInput(),null,2);
  if(!frame)frame=requestAnimationFrame(()=>{frame=0;render();});
}
function render(){
  const input=rawInput();$('#native-input').textContent=JSON.stringify(input,null,2);
  try{
    // Follow required-field declarations. Never backfill a missing body size.
    // Native Brian can otherwise produce NaN without recording an error.
    const missing=required.find(key=>!Number.isFinite(input.measurements[key]));
    if(missing)throw new Error('请填写'+fields.find(f=>f.key===missing).label);
    const native=draftBrian(input);
    const errors=[...native.logs.pattern.error,...native.logs.sets.flatMap(s=>s.error)];
    if(errors.length||/NaN|Infinity/.test(native.svg))throw new Error('此输入未生成有效纸样，请检查尺寸');
    const result=present(native);
    if(/NaN|Infinity/.test(result.svg))throw new Error('此输入未生成有效纸样，请检查尺寸');
    const doc=new DOMParser().parseFromString(result.svg,'image/svg+xml');
    if(doc.querySelector('parsererror'))throw new Error('SVG 生成失败');
    const svg=doc.documentElement;
    svg.setAttribute('role','img');svg.setAttribute('aria-label','Brian 原生人体尺寸生成的后片、前片和袖片');
    svg.setAttribute('viewBox',`-18 -18 ${Math.max(1470,result.width+36)} ${Math.max(850,result.height+36)}`);
    svg.removeAttribute('width');svg.removeAttribute('height');
    for(const style of svg.querySelectorAll('style'))style.textContent=style.textContent;
    $('#preview').replaceChildren(document.importNode(svg,true));
    current=result;$('#download-svg').disabled=false;$('#download-input').disabled=false;
    const warnings=[...result.logs.pattern.warn,...result.logs.sets.flatMap(s=>s.warn)];
    $('#status').textContent=warnings.length?'已更新 · 原库有提示':'已实时更新';
    $('#status').dataset.state=warnings.length?'warning':'ready';
    $('#preview').dataset.chest=String(input.measurements.chest);
    $('#preview').dataset.effectiveChest=String(result.pattern.settings[0].measurements.chest);
    $('#preview').dataset.width=String(result.quarterWidth);
  }catch(error){
    current=null;$('#preview').replaceChildren();
    for(const key of ['chest','effectiveChest','width'])delete $('#preview').dataset[key];
    $('#status').textContent=error.message;$('#status').dataset.state='error';
    $('#download-svg').disabled=true;$('#download-input').disabled=true;
  }finally{$('#status').dataset.revision=String(++revision);$('#preview').setAttribute('aria-busy','false');}
}
for(const id of ['provide-high-bust','draft-for-high-bust'])$('#'+id).addEventListener('change',()=>{updateControls();schedule();});
$('#reset').addEventListener('click',()=>{values={...exampleMeasurements,highBust:exampleHighBust};$('#provide-high-bust').checked=false;$('#draft-for-high-bust').checked=false;updateControls();schedule();});
function download(content,type,filename){
  const url=URL.createObjectURL(new Blob([content],{type})),a=document.createElement('a');
  a.href=url;a.download=filename;document.body.append(a);a.click();a.remove();
  setTimeout(()=>URL.revokeObjectURL(url),1000);
}
$('#download-svg').addEventListener('click',()=>{if(current)download(current.svg,'image/svg+xml;charset=utf-8',`brian-chest-${current.submitted.measurements.chest}mm.svg`);});
$('#download-input').addEventListener('click',()=>{if(current)download(JSON.stringify(current.submitted,null,2)+'\n','application/json','brian-input.json');});
$('#default-ease').textContent=String(inputContract.defaultOptions.chestEase*100)+'%';
updateControls();render();
