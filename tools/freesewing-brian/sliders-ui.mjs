import {fields,defaults,generate} from './sliders-engine.mjs';
const $ = s=>document.querySelector(s);
const form=$('#controls');
let values={...defaults}, baseline={...values}, current=null, frame=0, revision=0;
const fmt=n=>Number(Number(n).toFixed(1)).toString();
for(const f of fields) {
  const row=document.createElement('div');
  row.className='field'+(f.optional?' optional':'');
  row.innerHTML=`<div class="field-title"><label for="${f.key}">${f.label}</label><output id="${f.key}-value" for="${f.key}"></output></div><input id="${f.key}" name="${f.key}" type="range" min="${f.min}" max="${f.max}" step="${f.step}" value="${f.value}" aria-describedby="units">`;
  form.append(row);
  $('#'+f.key).addEventListener('input',e=>{
    values[f.key]=Number(e.target.value);
    baseline={...values};
    $('#overall').value='100';
    setOverallBounds();
    updateControls();
    schedule();
  });
}
function setOverallBounds() {
  const lengths=fields.filter(f=>!f.angle && (!f.optional || $('#use-high-bust').checked));
  $('#overall').min=String(Math.max(75,...lengths.map(f=>Math.ceil(f.min/baseline[f.key]*100))));
  $('#overall').max=String(Math.min(125,...lengths.map(f=>Math.floor(f.max/baseline[f.key]*100))));
}
function updateControls() {
  for(const f of fields) {
    const input=$('#'+f.key);
    input.value=String(values[f.key]);
    input.disabled=!!(f.optional&&!$('#use-high-bust').checked);
    input.setAttribute('aria-valuetext',fmt(values[f.key])+(f.angle?'度':'厘米'));
    $('#'+f.key+'-value').textContent=fmt(values[f.key])+(f.angle?'°':' cm');
  }
  $('#overall-value').textContent=$('#overall').value+'%';
}
function schedule() {
  $('#download-svg').disabled=true;
  $('#preview').setAttribute('aria-busy','true');
  $('#status').textContent='正在重画…';
  if(!frame) frame=requestAnimationFrame(()=>{ frame=0; render(); });
}
function render() {
  try {
    const result=generate(values,$('#use-high-bust').checked);
    const doc=new DOMParser().parseFromString(result.svg,'image/svg+xml');
    if(doc.querySelector('parsererror')) throw new Error('SVG 生成失败');
    const svg=doc.documentElement;
    svg.setAttribute('role','img');
    svg.setAttribute('aria-label','Brian 后片、前片和袖片；按当前人体尺寸实时重画');
    // Preview framing stays fixed for normal sizes, so resizing remains visible.
    svg.setAttribute('viewBox',`-18 -18 ${Math.max(1470,result.width+36)} ${Math.max(850,result.height+36)}`);
    svg.removeAttribute('width'); svg.removeAttribute('height');
    // HTML documents cannot import XML CDATA nodes; retain their CSS as text.
    for(const style of svg.querySelectorAll('style')) style.textContent=style.textContent;
    $('#preview').replaceChildren(document.importNode(svg,true));
    current=result;
    $('#download-svg').disabled=false;
    $('#status').textContent=result.warning?'已更新 · 此组合需复核':'已实时更新';
    $('#status').dataset.state=result.warning?'warning':'ready';
    $('#status').dataset.revision=String(++revision);
    $('#preview').dataset.chest=String(result.settings.measurements.chest);
    $('#preview').dataset.width=String(result.quarterWidth);
  } catch(error) {
    current=null;
    $('#status').textContent=error.message;
    $('#status').dataset.state='error';
    $('#download-svg').disabled=true;
  } finally {
    $('#preview').setAttribute('aria-busy','false');
  }
}
$('#overall').addEventListener('input',e=>{
  const factor=Number(e.target.value)/100;
  for(const f of fields) if(!f.angle && (!f.optional || $('#use-high-bust').checked))
    values[f.key]=Math.max(f.min,Math.min(f.max,Math.round(baseline[f.key]*factor/f.step)*f.step));
  updateControls(); schedule();
});
$('#use-high-bust').addEventListener('change',()=>{
  baseline={...values}; $('#overall').value='100';
  setOverallBounds(); updateControls(); schedule();
});
$('#reset').addEventListener('click',()=>{
  values={...defaults}; baseline={...defaults};
  $('#use-high-bust').checked=false; $('#overall').value='100';
  setOverallBounds(); updateControls(); schedule();
});
$('#download-svg').addEventListener('click',()=>{
  if(!current) return;
  const blob=new Blob([current.svg],{type:'image/svg+xml;charset=utf-8'});
  const url=URL.createObjectURL(blob),a=document.createElement('a');
  a.href=url; a.download=`brian-chest-${fmt(current.settings.measurements.chest/10)}cm.svg`;
  document.body.append(a); a.click(); a.remove();
  setTimeout(()=>URL.revokeObjectURL(url),1000);
});
setOverallBounds(); updateControls(); render();
