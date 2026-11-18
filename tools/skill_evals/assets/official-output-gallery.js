// Artifact renderer only: do not replace the official viewer's shell or feedback.
(() => {
  const dialog = document.createElement('dialog'); dialog.id = 'official-image-dialog';
  dialog.innerHTML = '<div class="og-dialog-head"><strong id="og-image-title"></strong><button id="og-close">Close ×</button></div><img id="og-image" alt=""><p id="og-caption"></p><div class="og-dialog-head"><button id="og-prev">← Previous image</button><button id="og-next">Next image →</button><a id="og-original" target="_blank" rel="noopener">Open original</a></div>';
  document.body.append(dialog);
  let images = [], position = 0, opener;
  const find = s => dialog.querySelector(s);
  function paint() {
    const item = images[position]; find('#og-image-title').textContent = item.label;
    find('#og-image').src = item.src; find('#og-image').alt = item.label;
    find('#og-caption').textContent = item.caption; find('#og-original').href = item.src;
    find('#og-prev').disabled = position === 0; find('#og-next').disabled = position === images.length - 1;
  }
  function close() {dialog.close(); opener?.focus();}
  find('#og-close').onclick = close;
  find('#og-prev').onclick = () => {if (position > 0) {position--; paint();}};
  find('#og-next').onclick = () => {if (position < images.length - 1) {position++; paint();}};
  document.addEventListener('keydown', event => {
    if (!dialog.open || !['ArrowLeft','ArrowRight','Escape'].includes(event.key)) return;
    event.preventDefault(); event.stopImmediatePropagation();
    if (event.key === 'Escape') close(); else find(event.key === 'ArrowLeft' ? '#og-prev' : '#og-next').click();
  }, true);
  function button(item, index) {
    const b = document.createElement('button'); b.type = 'button'; b.className = 'og-image';
    b.setAttribute('aria-label', 'Open ' + item.label);
    const image = document.createElement('img'); image.src = item.src; image.alt = item.label;
    b.append(image); b.onclick = () => {opener = b; position = index; paint(); dialog.showModal();};
    return b;
  }
  const originalOutputs = renderOutputs;
  renderOutputs = function(run) {
    originalOutputs(run);
    const data = OUTPUT_GALLERIES[run.id]; if (!data) return;
    const block = document.createElement('section'); block.id = 'official-case-gallery'; block.className = 'output-file';
    const heading = document.createElement('div'); heading.className = 'output-file-header';
    heading.textContent = data.title + ' · OVERALL ' + data.overall;
    const content = document.createElement('div'); content.className = 'og-content';
    const grid = document.createElement('div'); grid.className = 'og-grid'; images = [];
    for (const stage of data.stages) {
      const card = document.createElement('section'), title = document.createElement('h3'), status = document.createElement('p');
      title.textContent = stage.title; status.textContent = stage.status; card.append(title,status);
      if (!stage.images.length) {const empty = document.createElement('p'); empty.className = 'og-empty'; empty.textContent = '该版本未使用 Image Gen 引导；没有用渲染图替代生成图。'; card.append(empty);}
      else {
        const start = images.length; images.push(...stage.images); card.append(button(stage.images[0],start));
        const caption = document.createElement('p'); caption.textContent = stage.images[0].caption; card.append(caption);
        if (stage.images.length > 1) {const strip = document.createElement('div'); strip.className = 'og-thumbs'; stage.images.forEach((item,j)=>strip.append(button(item,start+j)));card.append(strip);}
      }
      grid.append(card);
    }
    const links = document.createElement('p'); links.className = 'og-links';
    for (const item of [{label:'打开此版本可调人体',href:data.model},...data.downloads,
      {label:'同画幅交互详情（当前候选）',href:'../pose-guided-fit/details.html'},
      {label:'历史六次技能执行及原始 Benchmark',href:'../single-state-evals/history.html'}]) {
      const a = document.createElement('a'); a.href = item.href; a.textContent = item.label;
      if (data.downloads.includes(item)) a.setAttribute('download',''); links.append(a,document.createTextNode(' · '));
    }
    const note = document.createElement('p'); note.textContent = '这是保存候选的实际证据。功能断言计数不是姿态准确率；请查看官方 Formal Grades，并在下方 Feedback 留言。';
    content.append(grid,note,links); block.append(heading,content);
    document.querySelector('#outputs-body').prepend(block);
  };
  // Preserve comments from the replaced custom form only for identical source hashes.
  let nativeDraftExists = false, migrated = false;
  try {nativeDraftExists = localStorage.getItem(STATIC_REVIEW_KEY) !== null;} catch {}
  for (const run of nativeDraftExists ? [] : EMBEDDED_DATA.runs) {
    const data = OUTPUT_GALLERIES[run.id];
    if (feedbackMap[run.id] || !data) continue;
    try {
      const draft = JSON.parse(localStorage.getItem(data.legacy_feedback_key) || 'null');
      if (!draft || JSON.stringify(draft.source_fingerprints) !== JSON.stringify(data.source_fingerprints)) continue;
      if (typeof draft.feedback !== 'string') continue;
      const labels = {needs_changes:'仍需改进',accepted:'可以接受'};
      const decision = labels[draft.acceptance];
      if (draft.feedback.trim() || decision) {
        feedbackMap[run.id] = (decision ? '[从旧表恢复，原人工判断：'+decision+']\n' : '') + draft.feedback;
        migrated = true;
      }
    } catch { /* A malformed draft is not a reviewed case. */ }
  }
  if (migrated) persistStaticFeedback();
  const priorShow = showRun, selectionKey = STATIC_REVIEW_KEY + ':official-case';
  showRun = function(index) {priorShow(index);try {localStorage.setItem(selectionKey,String(index));} catch {}};
  let selected = EMBEDDED_DATA.runs.findIndex(r => r.id.includes('-candidate-'));
  try {const saved = localStorage.getItem(selectionKey);if (saved !== null && Number.isInteger(Number(saved)) && Number(saved)>=0 && Number(saved)<EMBEDDED_DATA.runs.length) selected=Number(saved);} catch {}
  showRun(selected < 0 ? 0 : selected);
})();
