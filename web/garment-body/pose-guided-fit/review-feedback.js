/* Human review of actual saved outputs; local-only, scoped by source fingerprints. */
(() => {
  const root = document.querySelector('#pose-review');
  const find = s => root.querySelector(s);
  const status = find('#pr-feedback-status');
  let manifest, selected = 'model', current;
  const accepted = new Set(['not_reviewed', 'needs_changes', 'accepted']);
  const drafts = new Map();
  const evidenceNames = {
    'Fresh source calibration and FK/LBS reproduce the saved actual body mesh.': '实际厘米校准和骨骼能重建保存的人体',
    'Canonical front/side/back and photo PNGs use the same real pose/mesh and declared cameras.': '正、侧、背和原相机图共享同一模型与姿态',
    'Every frozen critical body region and waist/hip center scanline satisfies the regional protocol.': '所有关键身体区域与腰臀中心符合协议',
    'Original visible wrists and coarse limb directions do not contradict the reference action.': '可见手腕及前臂方向符合参考动作',
    'Actual three-dimensional renders reproduce the original opposing shirt-hem grasp.': '真实三维手部还原原图提衣握持动作'
  };
  function fingerprints(version) {
    return {
      reference_sha256: manifest.files['reference/original-product.jpg'],
      state_sha256: manifest.files[version + '/final-state.json'],
      posed_obj_sha256: manifest.files[version + '/posed.obj'],
      camera_sha256: manifest.files[version + '/camera.json']
    };
  }
  function identity(version) {
    return 'pose-guided-fit:' + version + ':' + Object.values(fingerprints(version)).join(':');
  }
  function storageKey(version) { return 'pattern-agent:human-review:v1:' + identity(version); }
  function fresh(version) {
    return {run_id: identity(version), feedback: '', timestamp: null,
      acceptance: 'not_reviewed', version, source_fingerprints: fingerprints(version)};
  }
  function read(version) {
    const empty = fresh(version);
    if (drafts.has(empty.run_id)) return drafts.get(empty.run_id);
    try {
      const record = JSON.parse(localStorage.getItem(storageKey(version)) || 'null');
      if (!record || record.run_id !== empty.run_id || typeof record.feedback !== 'string' ||
          !accepted.has(record.acceptance) || (record.timestamp !== null && typeof record.timestamp !== 'string') ||
          JSON.stringify(record.source_fingerprints) !== JSON.stringify(empty.source_fingerprints)) return empty;
      return {...empty, feedback: record.feedback, acceptance: record.acceptance, timestamp: record.timestamp};
    } catch { return empty; }
  }
  function badge(value) {
    const node = document.createElement('span');
    node.className = 'pr-status ' + (value === 'PASS' ? 'PASS' : value === 'FAIL' ? 'FAIL' : 'NOT_RUN');
    node.textContent = value;
    return node;
  }
  function renderGrades() {
    const grade = manifest.grades[selected === 'model' ? 'final' : 'baseline'] || {};
    const title = find('#pr-assertion-version');
    title.replaceChildren(document.createTextNode((selected === 'model' ? '当前候选' : '修改前基线') + ' · 整体结论 '),
      badge(grade.overall_verdict || grade.visual_alignment_2d?.verdict || 'NOT_RUN'));
    const list = find('#pr-expectations');
    list.replaceChildren();
    for (const item of grade.expectations || []) {
      const row = document.createElement('li'), heading = document.createElement('strong');
      heading.textContent = evidenceNames[item.text] || item.text;
      const evidence = document.createElement('p'); evidence.textContent = item.evidence || '无证据，不能判通过。';
      row.append(badge(item.passed === true ? 'PASS' : 'FAIL'), document.createTextNode(' '), heading, evidence);
      try {
        const raw = JSON.parse(item.evidence), wrists = raw.original_visible_wrist_errors_px;
        if (wrists && Number.isFinite(wrists.wrist_image_left) && Number.isFinite(wrists.wrist_image_right)) {
          evidence.textContent = `原图左腕偏差 ${wrists.wrist_image_left.toFixed(2)} px；右腕 ${wrists.wrist_image_right.toFixed(2)} px。动作检查：${raw.verdict}。`;
          const detail = document.createElement('details'), summary = document.createElement('summary'), original = document.createElement('pre');
          summary.textContent = '原始评分证据'; original.textContent = item.evidence;
          detail.append(summary, original); row.append(detail);
        }
      } catch { /* Plain text evidence remains unchanged. */ }
      list.append(row);
    }
    if (!list.children.length) list.textContent = '此历史版本没有逐项断言记录；不补造成绩。请查看原始评分。';
    find('#pr-eval-critique').replaceChildren();
    for (const item of grade.eval_feedback?.suggestions || []) {
      const row = document.createElement('li'), heading = document.createElement('strong');
      heading.textContent = item.assertion; const why = document.createElement('p'); why.textContent = item.reason;
      row.append(heading, why); find('#pr-eval-critique').append(row);
    }
    find('#pr-expectations-source').href = root.dataset.prefix + 'review/' + (selected === 'model' ? 'final' : 'baseline') + '/grading.json';
  }
  function select(version) {
    if (!manifest) return;
    selected = version; current = read(version); renderGrades();
    find('#pr-feedback-version').textContent = (version === 'model' ? '当前候选' : '修改前基线') +
      ' · 状态 ' + fingerprints(version).state_sha256.slice(0, 12);
    find('#pr-human-feedback').value = current.feedback;
    find('#pr-human-acceptance').value = current.acceptance;
    status.textContent = current.timestamp ? '已恢复此版本的本地反馈；不代表模型已通过。' : '尚未评阅此版本。反馈仅保存在本浏览器。';
  }
  function save() {
    if (!manifest) return;
    current = {...fresh(selected), feedback: find('#pr-human-feedback').value,
      acceptance: find('#pr-human-acceptance').value, timestamp: new Date().toISOString()};
    drafts.set(current.run_id, current);
    try {
      localStorage.setItem(storageKey(selected), JSON.stringify(current));
      status.textContent = '已保存此版本的本地反馈；导出文件后可用于下一轮。';
    } catch { status.textContent = '浏览器存储不可用；当前内容仍可导出，请先下载。'; }
  }
  function download() {
    save();
    const reviews = ['baseline', 'model'].map(v => v === selected ? current : read(v));
    const candidate = reviews.find(r => r.version === 'model');
    const output = {reviews: reviews.filter(r => r.timestamp), status: candidate.acceptance === 'not_reviewed' ? 'in_progress' : 'complete',
      scope: 'Human feedback only; not an automatic grade, native Claude benchmark, or proof of real-person dimensions.'};
    const href = URL.createObjectURL(new Blob([JSON.stringify(output, null, 2) + '\n'], {type: 'application/json'}));
    const a = document.createElement('a'); a.href = href; a.download = 'feedback.json'; a.click();
    setTimeout(() => URL.revokeObjectURL(href), 1000);
    status.textContent = '已导出 feedback.json。未明确评阅的候选仍保持未评阅状态。';
  }
  find('#pr-human-feedback').addEventListener('input', save);
  find('#pr-human-acceptance').addEventListener('change', save);
  find('#pr-export-feedback').addEventListener('click', download);
  for (const id of ['#pr-before', '#pr-modal-before']) find(id).addEventListener('click', () => select('baseline'));
  for (const id of ['#pr-after', '#pr-modal-after']) find(id).addEventListener('click', () => select('model'));
  fetch(root.dataset.prefix + 'manifest.json').then(r => {if (!r.ok) throw Error('无法读取评阅版本'); return r.json();})
    .then(data => {manifest = data; for (const id of ['#pr-human-acceptance', '#pr-human-feedback', '#pr-export-feedback']) find(id).disabled = false; select(find('#pr-before').getAttribute('aria-pressed') === 'true' ? 'baseline' : manifest.files['model/posed.obj'] ? 'model' : 'baseline');})
    .catch(error => {status.textContent = error.message; find('#pr-export-feedback').disabled = true;});
})();
