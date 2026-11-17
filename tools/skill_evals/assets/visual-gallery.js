// Static adapter for the pinned Anthropic viewer. No benchmark or run edits.
(() => {
  const section=document.createElement('section');section.className='quick-review';section.id='quick-review';
  section.setAttribute('aria-label','Quick visual verification');
  section.innerHTML='<div class="quick-heading"><div><h2>Quick visual verification</h2><p>Input → Image Gen → simulation → overlay. Click an image to inspect it.</p></div><label>Case & configuration<br><select id="gallery-case" aria-label="Case and configuration"></select></label></div><div id="evidence-grid" class="evidence-grid"></div><p id="evidence-footnote" class="evidence-footnote"></p>';
  document.querySelector('#panel-outputs .main').prepend(section);
  const select=section.querySelector('select');
  EMBEDDED_DATA.runs.forEach((run,index)=>{const option=document.createElement('option');option.value=index;option.textContent=VISUAL_EVIDENCE[run.id].title;select.append(option);});
  const dialog=document.createElement('dialog');dialog.className='evidence-lightbox';dialog.setAttribute('aria-label','Evidence image viewer');
  dialog.innerHTML='<div class="lightbox-head"><strong id="lightbox-title"></strong><button id="lightbox-close" aria-label="Close image viewer">Close ×</button></div><img class="lightbox-image" id="lightbox-image" alt=""><p class="lightbox-caption" id="lightbox-caption"></p><div class="lightbox-controls"><button id="lightbox-prev">← Previous image</button><span id="lightbox-position"></span><button id="lightbox-next">Next image →</button><a id="lightbox-original" target="_blank" rel="noopener">Open original</a></div>';
  document.body.append(dialog);
  let gallery=[],position=0,returnFocus;
  function paint(){const item=gallery[position];dialog.querySelector('#lightbox-title').textContent=item.label;dialog.querySelector('img').src=item.src;dialog.querySelector('img').alt=item.label;dialog.querySelector('#lightbox-caption').textContent=item.caption;dialog.querySelector('#lightbox-original').href=item.src;dialog.querySelector('#lightbox-position').textContent=`${position+1} / ${gallery.length}`;dialog.querySelector('#lightbox-prev').disabled=position===0;dialog.querySelector('#lightbox-next').disabled=position===gallery.length-1;}
  function open(index,button){position=index;returnFocus=button;paint();dialog.showModal();}
  function close(){dialog.close();returnFocus?.focus();}
  dialog.querySelector('#lightbox-close').onclick=close;
  dialog.querySelector('#lightbox-prev').onclick=()=>{if(position>0){position--;paint();}};
  dialog.querySelector('#lightbox-next').onclick=()=>{if(position<gallery.length-1){position++;paint();}};
  dialog.addEventListener('click',event=>{if(event.target===dialog)close();});
  dialog.addEventListener('keydown',event=>{if(event.key==='ArrowLeft'||event.key==='ArrowRight'){event.preventDefault();event.stopPropagation();dialog.querySelector(event.key==='ArrowLeft'?'#lightbox-prev':'#lightbox-next').click();}else if(event.key==='Escape')event.stopPropagation();});
  // The upstream viewer also uses arrows; keep image navigation within the modal.
  document.addEventListener('keydown',event=>{if(dialog.open&&['ArrowLeft','ArrowRight','Escape'].includes(event.key)){event.preventDefault();event.stopImmediatePropagation();if(event.key==='Escape')close();else dialog.querySelector(event.key==='ArrowLeft'?'#lightbox-prev':'#lightbox-next').click();}},true);
  function imageButton(item,index,thumbnail=false){const button=document.createElement('button');button.type='button';button.className=thumbnail?'':'evidence-image';button.setAttribute('aria-label','Open '+item.label);const image=document.createElement('img');image.src=item.src;image.alt=item.label;image.decoding='async';button.append(image);button.onclick=()=>open(index,button);return button;}
  function render(index){
    const data=VISUAL_EVIDENCE[EMBEDDED_DATA.runs[index].id];select.value=index;gallery=[];
    const grid=section.querySelector('#evidence-grid');grid.replaceChildren();
    for(const stage of data.stages){
      const card=document.createElement('section');card.className='evidence-stage';card.dataset.stage=stage.key;
      const heading=document.createElement('h3');heading.textContent=stage.title;card.append(heading);
      const status=document.createElement('span');status.className='stage-status'+(stage.images.length?'':' unavailable');status.textContent=stage.status;card.append(status);
      if(!stage.images.length){const empty=document.createElement('div');empty.className='evidence-empty';const strong=document.createElement('strong');strong.textContent=stage.emptyTitle;empty.append(strong,document.createTextNode(stage.note));card.append(empty);}
      else{const start=gallery.length;gallery.push(...stage.images);const figure=document.createElement('figure');figure.append(imageButton(stage.images[0],start));const caption=document.createElement('figcaption');caption.textContent=stage.images[0].caption;figure.append(caption);card.append(figure);
        if(stage.images.length>1){const strip=document.createElement('div');strip.className='thumb-strip';stage.images.forEach((item,j)=>strip.append(imageButton(item,start+j,true)));card.append(strip);}
      }grid.append(card);
    }
    section.querySelector('#evidence-footnote').textContent=data.note;
  }
  const original=showRun;
  const selectionKey=STATIC_REVIEW_KEY+':visual-case';
  showRun=function(index){original(index);render(index);try{localStorage.setItem(selectionKey,String(index));}catch{}};
  select.onchange=()=>{saveCurrentFeedback();showRun(Number(select.value));};
  const prompt=document.querySelector('#prompt-text');const details=document.createElement('details');details.className='quick-prompt';const summary=document.createElement('summary');summary.textContent='Read full task prompt';prompt.parentElement.prepend(details);details.append(summary,prompt);
  const outputs=document.querySelector('#outputs-body').closest('.section');const raw=document.createElement('details');raw.className='quick-raw';const rawTitle=document.createElement('summary');rawTitle.textContent='All output files, metrics and execution traces';outputs.before(raw);raw.append(rawTitle,outputs);
  const firstVisual=EMBEDDED_DATA.runs.findIndex(run=>VISUAL_EVIDENCE[run.id].stages.some(stage=>stage.images.length));
  let remembered;
  try{const stored=localStorage.getItem(selectionKey);if(stored!==null)remembered=Number(stored);}catch{}
  if(Number.isInteger(remembered)&&remembered>=0&&remembered<EMBEDDED_DATA.runs.length)showRun(remembered);
  else if(currentIndex===0&&firstVisual>0)showRun(firstVisual);else render(currentIndex);
})();
