'use strict';
(() => {
  const byId=id=>document.getElementById(id),data=JSON.parse(byId('gallery-data').textContent),sewing=JSON.parse(byId('sewing-data').textContent);
  const entries=[data.baseline,...data.cases],models=new Map(),viewers=new Map(),cards=new Map();
  const titles={baseline:'原型','01_sleeve_length':'袖子加长','02_body_length':'衣身缩短','03_cuff_width':'袖口加宽','04_front_neck':'前领加深'};
  const summaries={baseline:'女士贴身长袖圆领T恤','01_sleeve_length':'袖长 +20U，袖山保持不变','02_body_length':'前后衣身 −15U','03_cuff_width':'袖口展开宽 +10U','04_front_neck':'前领深 +10U，领条联动'};
  const arrow='<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12h14 m-6-6 6 6-6 6"/></svg>';
  const bytes=encoded=>Uint8Array.from(atob(encoded),c=>c.charCodeAt(0)),text=record=>new TextDecoder('utf-8',{fatal:true}).decode(bytes(record.base64));
  let filter='all',preview='3d',current=null,detailViewer=null;
  const detailCamera={yaw:-.4,pitch:.03,zoom:1},frame={min:[Infinity,Infinity,Infinity],max:[-Infinity,-Infinity,-Infinity]};
  const accepted=entry=>sewing.cases[entry.id]==='PASS';
  function showView(view,updateHash=true){
    byId('gallery-view').hidden=view!=='gallery';byId('readme-view').hidden=view!=='readme';
    document.querySelectorAll('[data-view]').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.view===view)));
    if(updateHash)history.replaceState(null,'',view==='readme'?'#readme':'#gallery');
    if(view==='gallery')requestAnimationFrame(()=>viewers.forEach(viewer=>{if(!viewer.canvas.closest('[hidden]'))viewer.draw();}));
  }
  function applyFilters(){
    const query=byId('case-search').value.trim().toLocaleLowerCase();let count=0;
    for(const entry of entries){
      const matches=(!query||(titles[entry.id]+' '+summaries[entry.id]+' '+(entry.intent||'')).toLocaleLowerCase().includes(query))&&
        (filter==='all'||(filter==='sewn'?accepted(entry):!accepted(entry)));
      cards.get(entry.id).hidden=!matches;if(matches)count++;
    }
    byId('empty-state').hidden=count>0;byId('results-count').textContent=`显示 ${count} 个案例`;
    requestAnimationFrame(()=>viewers.forEach(viewer=>{if(!viewer.canvas.closest('[hidden]'))viewer.draw();}));
  }
  function download(kind){
    const record=current.files[kind];if(!record)throw Error('此案例没有该文件');
    const blob=new Blob([bytes(record.base64)],{type:record.mime}),url=URL.createObjectURL(blob),link=document.createElement('a');
    link.href=url;link.download=record.name;document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),30000);
  }
  function openCase(id){
    current=entries.find(entry=>entry.id===id);if(!current||!models.has(id))return;
    byId('case-dialog').dataset.caseId=id;byId('case-title').textContent=titles[id];
    byId('case-intent').textContent=current.intent||'原始女士贴身长袖圆领T恤纸样。完整中文规格与原始DXF均可阅读和下载。';
    byId('case-pattern').innerHTML=current.twoD.svg;byId('case-spec').textContent=text(current.files.yaml);byId('case-spec').scrollTop=0;byId('full-spec').open=false;
    document.querySelectorAll('[data-case-file]').forEach(button=>button.hidden=!current.files[button.dataset.caseFile]);
    byId('case-compare').href='../'+(id==='baseline'?'':'?case='+encodeURIComponent(id));
    byId('case-sewing-status').textContent=accepted(current)?'修正缝合外壳已独立验证，可打开实际缝合模型。':'二维规格与DXF已互校；此改版的严格缝合仍需新配置（BLOCKED）。';
    byId('case-sewn-link').hidden=!accepted(current);byId('case-sewn-link').href='../sewn/'+id+'/files/preview.html';
    Object.assign(detailCamera,{yaw:-.4,pitch:.03,zoom:1});
    byId('case-dialog').showModal();byId('case-dialog').scrollTop=0;document.body.style.overflow='hidden';
    if(!detailViewer)detailViewer=new PatternMeshViewer(byId('case-model'),detailCamera,frame,()=>detailViewer.draw(),[.48,.64,.55]);
    detailViewer.setModel(models.get(id),current.threeD.artifact_sha256);
  }
  function createCard(entry){
    const card=document.createElement('article');card.className='case-card';card.dataset.caseId=entry.id;
    const media=document.createElement('div');media.className='case-media';
    const canvas=document.createElement('canvas');canvas.tabIndex=0;canvas.setAttribute('aria-label',titles[entry.id]+'的三维示意，可拖动旋转');media.append(canvas);
    for(const cls of ['pattern-thumb','pattern-full']){const node=document.createElement('div');node.className=cls;node.innerHTML=entry.twoD.svg;if(cls==='pattern-thumb')node.setAttribute('aria-hidden','true');media.append(node);}
    const info=document.createElement('div');info.className='card-info';
    const h=document.createElement('h2');h.textContent=titles[entry.id];const summary=document.createElement('p');summary.className='card-intent';summary.textContent=summaries[entry.id];
    const bottom=document.createElement('div');bottom.className='card-bottom';const status=document.createElement('span');status.className='card-status'+(accepted(entry)?' accepted':'');
    status.textContent=accepted(entry)?'缝合外壳已验证':'二维已互校 · 缝合待配置';
    const open=document.createElement('button');open.type='button';open.className='button';open.dataset.openCase=entry.id;open.setAttribute('aria-label','打开'+titles[entry.id]+'实验');open.innerHTML='打开实验'+arrow;open.addEventListener('click',()=>openCase(entry.id));
    bottom.append(status,open);info.append(h,summary,bottom);card.append(media,info);byId('case-gallery').append(card);cards.set(entry.id,card);
    const camera={yaw:-.4,pitch:.03,zoom:1};let viewer;
    viewer=new PatternMeshViewer(canvas,camera,frame,()=>viewer.draw(),entry.id==='baseline'?[.67,.71,.68]:[.48,.64,.55]);
    viewer.setModel(models.get(entry.id),entry.threeD.artifact_sha256);viewers.set(entry.id,viewer);
  }
  async function check(raw,length,expected){
    if(raw.length!==length)throw Error('案例文件长度不符');
    if(crypto.subtle){const actual=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',raw))).map(value=>value.toString(16).padStart(2,'0')).join('');if(actual!==expected)throw Error('案例文件摘要不符');}
  }
  async function boot(){
    for(const entry of entries){
      for(const record of Object.values(entry.files))await check(bytes(record.base64),record.byte_length,record.sha256);
      const raw=bytes(entry.threeD.artifact_base64);await check(raw,entry.threeD.byte_length,entry.threeD.artifact_sha256);
      const model=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(raw));
      if(model.source_dxf_sha256!==entry.files.dxf.sha256||model.source_spec_sha256!==entry.files.yaml.sha256)throw Error('模型来源不是本案例');
      models.set(entry.id,model);for(let k=0;k<3;k++){frame.min[k]=Math.min(frame.min[k],model.bounds_U.min[k]);frame.max[k]=Math.max(frame.max[k],model.bounds_U.max[k]);}
    }
    entries.forEach(createCard);byId('case-search').disabled=false;byId('prototype-input').disabled=false;byId('load-status').hidden=true;
    byId('results-count').textContent='显示 5 个案例';document.body.dataset.galleryReady='true';
  }
  document.querySelectorAll('[data-view]').forEach(button=>button.addEventListener('click',()=>showView(button.dataset.view)));
  byId('prototype-input').addEventListener('click',()=>openCase('baseline'));byId('case-search').addEventListener('input',applyFilters);
  document.querySelectorAll('[data-filter]').forEach(button=>button.addEventListener('click',()=>{filter=button.dataset.filter;document.querySelectorAll('[data-filter]').forEach(other=>other.setAttribute('aria-pressed',String(other===button)));applyFilters();}));
  document.querySelectorAll('[data-preview]').forEach(button=>{if(button.tagName!=='BUTTON')return;button.addEventListener('click',()=>{preview=button.dataset.preview;byId('case-gallery').dataset.preview=preview;document.querySelectorAll('button[data-preview]').forEach(other=>other.setAttribute('aria-pressed',String(other===button)));if(preview==='3d')requestAnimationFrame(()=>viewers.forEach(viewer=>{if(!viewer.canvas.closest('[hidden]'))viewer.draw();}));});});
  byId('clear-filters').addEventListener('click',()=>{byId('case-search').value='';document.querySelector('[data-filter="all"]').click();});
  document.querySelectorAll('[data-case-file]').forEach(button=>button.addEventListener('click',()=>download(button.dataset.caseFile)));
  byId('close-case').addEventListener('click',()=>byId('case-dialog').close());
  byId('case-dialog').addEventListener('close',()=>{document.body.style.overflow='';});
  byId('reset-case-view').addEventListener('click',()=>{Object.assign(detailCamera,{yaw:-.4,pitch:.03,zoom:1});detailViewer.draw();});
  document.querySelector('.brand').addEventListener('click',()=>showView('gallery'));
  window.addEventListener('hashchange',()=>{if(location.hash==='#gallery')showView('gallery',false);else if(location.hash==='#readme')showView('readme',false);});
  showView(location.hash&&location.hash!=='#gallery'?'readme':'gallery',false);
  boot().catch(error=>{byId('load-status').textContent='案例加载失败，请刷新重试。';byId('load-status').className='app-error';console.error(error);});
})();
