'use strict';
(() => {
  const $=id=>document.getElementById(id),data=JSON.parse($('app-data').textContent),entries=[data.baseline,...data.cases],decoded=new Map();
  const bytes=encoded=>Uint8Array.from(atob(encoded),c=>c.charCodeAt(0));
  const text=record=>new TextDecoder('utf-8',{fatal:true}).decode(bytes(record.base64));
  const requestedCase=new URLSearchParams(location.search).get('case');
  const camera={yaw:-.40,pitch:.03,zoom:1};let selected=data.cases.find(entry=>entry.id===requestedCase)||data.cases[0],viewers=[];
  async function hash(raw){if(!crypto.subtle)return null;return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',raw))).map(v=>v.toString(16).padStart(2,'0')).join('');}
  async function check(record,encoded='base64',expected='sha256'){
    const raw=bytes(record[encoded]);if(raw.length!==record.byte_length)throw Error('内嵌文件长度不符');
    const actual=await hash(raw);if(actual&&actual!==record[expected])throw Error('内嵌文件摘要不符');return raw;
  }
  function current(side){return side==='input'?data.baseline:selected;}
  function drawAll(){viewers.forEach(v=>v.draw());}
  function summary(entry){return entry.summary_lines.join('\n');}
  function renderCase(id){
    selected=data.cases.find(c=>c.id===id);if(!selected)throw Error('未找到案例');
    $('case-select').value=id;$('intent').value=selected.intent;
    const before={...data.baseline,summary_lines:selected.input_summary_lines};
    $('input-summary').textContent=summary(before);$('output-summary').textContent=summary(selected);
    $('output-pattern').innerHTML='<div class="baseline-overlay" aria-hidden="true">'+data.baseline.twoD.svg+'</div><div class="actual">'+selected.twoD.svg+'</div>';
    viewers[1].setModel(decoded.get(id).model,selected.threeD.artifact_sha256);
    $('output-model-status').hidden=true;
    document.body.dataset.selectedCase=id;
  }
  function download(side,type){
    const entry=current(side),record=entry.files[type];if(!record)throw Error('此文件不存在');
    const blob=new Blob([bytes(record.base64)],{type:record.mime||'application/octet-stream'}),url=URL.createObjectURL(blob),a=document.createElement('a');
    a.href=url;a.download=record.name;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),30000);
  }
  function showDocument(side){
    const entry=current(side);$('document-title').textContent=side==='input'?'完整输入规格 YAML':'完整改版规格 YAML';
    $('document-pre').textContent=decoded.get(entry.id).yaml;$('document-dialog').dataset.fileSha=entry.files.yaml.sha256;$('document-dialog').showModal();
    $('document-dialog').querySelector('.dialog-content').scrollTop=0;
  }
  function showDiff(tab){
    document.querySelectorAll('[data-diff-tab]').forEach(b=>b.setAttribute('aria-selected',String(b.dataset.diffTab===tab)));
    const out=$('diff-content');out.replaceChildren();$('diff-dialog').querySelector('.dialog-content').scrollTop=0;
    if(tab==='measurements'){
      const table=document.createElement('table');table.className='diff-table';const head=table.createTHead().insertRow();
      for(const name of ['量测项目','修改前 U','修改后 U','变化 U']){const th=document.createElement('th');th.textContent=name;head.append(th);}
      const body=table.createTBody();for(const row of selected.changes){const tr=body.insertRow();for(const v of [row.name,row.before.toFixed(6),row.after.toFixed(6),(row.after-row.before).toFixed(6)])tr.insertCell().textContent=v;}
      out.append(table);const p=document.createElement('p');p.className='audit-line';p.textContent='二维规格与实际DXF互校通过；生产确认状态未变。';out.append(p);
    }else{const pre=document.createElement('pre');pre.className='doc-pre';pre.textContent=text(selected.files[tab]);out.append(pre);}
  }
  function sourceDialog(){
    const dl=$('source-detail');dl.replaceChildren();
    for(const [label,entry] of [['原型',data.baseline],['改版',selected]]){
      for(const [key,value] of [['案例',entry.id],['DXF SHA-256',entry.files.dxf.sha256],['YAML SHA-256',entry.files.yaml.sha256],['三维模型 SHA-256',entry.threeD.artifact_sha256]]){
        const dt=document.createElement('dt'),dd=document.createElement('dd');dt.textContent=label+' '+key;dd.textContent=value;dl.append(dt,dd);}
    }
    $('source-dialog').showModal();
  }
  async function boot(){
    for(const entry of entries){
      for(const file of Object.values(entry.files))await check(file);
      const raw=await check(entry.threeD,'artifact_base64','artifact_sha256'),model=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(raw));
      if(model.source_dxf_sha256!==entry.files.dxf.sha256||model.source_spec_sha256!==entry.files.yaml.sha256)throw Error('模型与二维文件不是同一版次');
      decoded.set(entry.id,{model,yaml:text(entry.files.yaml)});
    }
    const frame={min:[Infinity,Infinity,Infinity],max:[-Infinity,-Infinity,-Infinity]};
    for(const {model} of decoded.values())for(let k=0;k<3;k++){frame.min[k]=Math.min(frame.min[k],model.bounds_U.min[k]);frame.max[k]=Math.max(frame.max[k],model.bounds_U.max[k]);}
    viewers=[new PatternMeshViewer($('input-model'),camera,frame,drawAll,[.67,.71,.68]),new PatternMeshViewer($('output-model'),camera,frame,drawAll,[.48,.64,.55])];
    viewers[0].setModel(decoded.get(data.baseline.id).model,data.baseline.threeD.artifact_sha256);$('input-model-status').hidden=true;
    $('input-pattern').innerHTML='<div class="actual">'+data.baseline.twoD.svg+'</div>';
    for(const entry of data.cases){const opt=document.createElement('option');opt.value=entry.id;opt.textContent=entry.label;$('case-select').append(opt);}
    renderCase(selected.id);$('case-select').disabled=false;$('loading-note').hidden=true;document.body.dataset.ready='true';
  }
  $('case-select').addEventListener('change',e=>renderCase(e.target.value));
  document.querySelectorAll('[data-download]').forEach(b=>b.addEventListener('click',()=>download(b.dataset.side,b.dataset.download)));
  document.querySelectorAll('[data-document]').forEach(b=>b.addEventListener('click',()=>showDocument(b.dataset.document)));
  document.querySelectorAll('[data-view]').forEach(b=>b.addEventListener('click',()=>{camera.yaw=b.dataset.view==='front'?0:b.dataset.view==='back'?Math.PI:-.40;camera.pitch=b.dataset.view==='reset'?.03:0;camera.zoom=1;drawAll();}));
  document.querySelectorAll('[data-close]').forEach(b=>b.addEventListener('click',()=>$(b.dataset.close).close()));
  document.querySelectorAll('dialog').forEach(d=>d.addEventListener('click',e=>{if(e.target===d){const r=d.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)d.close();}}));
  $('show-diff').addEventListener('click',()=>{showDiff('measurements');$('diff-dialog').showModal();});
  document.querySelectorAll('[data-diff-tab]').forEach(b=>b.addEventListener('click',()=>showDiff(b.dataset.diffTab)));
  for(const [id,side] of [['input-pattern','input'],['output-pattern','output']]){
    const open=()=>{$('pattern-title').textContent=side==='input'?'输入二维纸样':'输出二维纸样';$('large-pattern').innerHTML=current(side).twoD.svg;$('pattern-dialog').showModal();};
    $(id).addEventListener('click',open);$(id).addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();open();}});
  }
  $('show-source').addEventListener('click',sourceDialog);
  boot().catch(error=>{$('fatal').hidden=false;$('fatal').textContent='页面数据未能完整载入：'+error.message;$('loading-note').hidden=true;document.body.dataset.ready='error';});
})();
