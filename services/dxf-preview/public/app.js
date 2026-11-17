'use strict';
(() => {
 const $=id=>document.getElementById(id);let lastInput=null,renderer=null,urls=[],currentCanvas=$('model-canvas');
 const status=(text,state='info')=>{$('status').textContent=text;$('status').dataset.state=state;};
 function busy(value){$('submit').disabled=value;$('sample').disabled=value;$('download-bundle').disabled=value;}
 function cleanup(){renderer?.dispose();renderer=null;urls.forEach(u=>URL.revokeObjectURL(u));urls=[];$('result').hidden=true;$('controls').hidden=true;$('viewer-error').hidden=true;currentCanvas.hidden=true;$('empty-preview').hidden=false;}
 function url(blob){const u=URL.createObjectURL(blob);urls.push(u);return u;}
 async function convert(bytes,name,units){
  if(!units){cleanup();lastInput=null;status('请先明确选择纸样单位。','error');return;}
  if(!bytes.byteLength||bytes.byteLength>524288){cleanup();lastInput=null;status('文件为空或超过512千字节限制。','error');return;}
  cleanup();lastInput=null;busy(true);status('正在校验纸样结构并生成三维模型…');const start=performance.now();
  try{
   const response=await fetch('/api/preview?units='+encodeURIComponent(units)+'&profile=fitted-tshirt-v1&format=json',{method:'POST',headers:{'Content-Type':'application/dxf'},body:bytes});const data=await response.json();
   if(!response.ok)throw Error(data.error?.message||'转换失败，请稍后重试。');
   const verification=data.report.connection_verification;if(verification?.verdict!=='PASS'||data.report.strict_seam_and_intersection_release!=='PASS')throw Error('该模型尚未通过裁片连接验收，已停止展示。');const seam=verification.checks;
   const model=Uint8Array.from(atob(data.glb_base64),c=>c.charCodeAt(0));const digest=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',model))).map(x=>x.toString(16).padStart(2,'0')).join('');if(digest!==data.report.output_sha256)throw Error('模型校验不一致，请重试。');
   const modelURL=url(new Blob([model],{type:'model/gltf-binary'}));$('download-model').href=modelURL;$('download-report').href=url(new Blob([JSON.stringify(data.report,null,2)],{type:'application/json'}));$('result-file').textContent=name;$('seam-verdict').textContent='修正版通过';$('original-seams').textContent=seam.flat_patterns.original_pattern_connection.verdict==='FAIL'?'存在差异，已另存修正':'当前缝长检查通过';$('seam-gap').textContent=seam.max_seam_gap_mm.toFixed(3)+'毫米';$('intersection-count').textContent=seam.proper_self_intersections+'对';$('pattern-edit').textContent=data.report.pattern_revision.max_vertex_edit_mm.toFixed(2)+'毫米';$('match').textContent=data.report.matching.matched_polylines+'条多段线已匹配';$('elapsed').textContent=((performance.now()-start)/1000).toFixed(2)+'秒';$('result').hidden=false;lastInput={bytes,name,units,id:data.report.conversion_id};
   const replacement=currentCanvas.cloneNode(false);currentCanvas.replaceWith(replacement);currentCanvas=replacement;currentCanvas.hidden=false;$('empty-preview').hidden=true;
   try{renderer=await window.createGarmentRenderer(currentCanvas,modelURL,$('wireframe'));renderer.draw();$('controls').hidden=false;status('转换完成，修正版裁片连接验证通过；模型与报告均可下载。');}
   catch(e){currentCanvas.hidden=true;$('empty-preview').hidden=false;$('viewer-error').textContent='当前浏览器不能显示三维，但模型已经生成，可下载到兼容查看器中打开。';$('viewer-error').hidden=false;status('模型已生成；本浏览器三维显示不可用。');}
  }catch(e){cleanup();status(e.message,'error');}finally{busy(false);}
 }
 $('convert-form').addEventListener('submit',async e=>{e.preventDefault();const f=$('dxf-file').files[0];if(!f){cleanup();lastInput=null;status('请选择需要转换的纸样文件。','error');return;}if(f.size>524288){cleanup();lastInput=null;status('文件超过512千字节限制。','error');return;}await convert(await f.arrayBuffer(),f.name,$('units').value);});
 async function reusePattern(){
  cleanup();lastInput=null;$('dxf-file').value='';busy(true);status('正在载入已有纸样…');
  try{const r=await fetch('/assets/sample.dxf');if(!r.ok)throw Error('已有纸样暂时无法读取，请稍后重试。');const bytes=await r.arrayBuffer();const selection=new DataTransfer();selection.items.add(new File([bytes],'女紧身款T恤.dxf',{type:'application/dxf'}));$('dxf-file').files=selection.files;$('units').value='mm';await convert(bytes,'女紧身款T恤.dxf','mm');}
  catch(e){cleanup();lastInput=null;$('dxf-file').value='';status(e.message,'error');}finally{busy(false);}
 }
 $('sample').addEventListener('click',reusePattern);
 $('wireframe').addEventListener('change',()=>renderer?.draw());$('reset-model').addEventListener('click',()=>renderer?.reset());
 $('download-bundle').addEventListener('click',async()=>{if(!lastInput)return;const input=lastInput;$('download-bundle').disabled=true;try{const r=await fetch('/api/preview?units='+encodeURIComponent(input.units)+'&format=bundle',{method:'POST',headers:{'Content-Type':'application/dxf'},body:input.bytes});if(!r.ok){const d=await r.json();throw Error(d.error?.message||'预览包生成失败。');}if(r.headers.get('X-Conversion-Id')!==input.id)throw Error('转换版本发生变化，请重新生成预览。');const u=url(await r.blob());const a=document.createElement('a');a.href=u;a.download='pattern-agent-preview.zip';a.click();status('离线预览包已生成并下载。');}catch(e){status(e.message,'error');}finally{$('download-bundle').disabled=false;}});
 const reusable=new URLSearchParams(location.search).get('reuse');
 if(reusable==='fitted-tshirt-v1')reusePattern();
 else if(reusable)status('没有找到这份已有纸样，请选择上方纸样或上传文件。','error');
})();
