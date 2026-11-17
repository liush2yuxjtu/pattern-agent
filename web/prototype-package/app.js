'use strict';

const exampleIds = ['01-sleeve-length', '02-front-neckline', '03-movement-goal'];
const explanations = {
  '01-sleeve-length': '更新袖长目标，选择 ADJUST_LENGTH，并保留衣身、领口与袖山。执行时联动袖口、袖侧缝和折边。',
  '02-front-neckline': '前领深目标增加10 mm，选择 ADJUST_NECKLINE；保留后领深、领宽、肩部和衣身。重测净领圈，再按确认后的材料与配比适配领条。',
  '03-movement-goal': '记录活动体验目标，先明确不适的动作、位置和允许变化的部位。缺少这些信息时，不选定几何操作，也不虚构固定松量。',
};
let exampleRequest = 0;

async function readJson(path) {
  const response = await fetch(path);
  if (!response.ok) throw new Error(`无法读取参考文件 (${response.status})`);
  return response.json();
}

async function showExample(id, focus = false) {
  if (!exampleIds.includes(id)) return;
  const request = ++exampleRequest;
  const status = document.getElementById('example-status');
  status.textContent = '正在读取参考案例…';
  try {
    const folder = `package/examples/${id}/`;
    const [intent, patch] = await Promise.all([readJson(folder + 'intent.json'), readJson(folder + 'expected-spec-patch.json')]);
    if (request !== exampleRequest) return;
    const buttons = [...document.querySelectorAll('button[data-example]')];
    buttons.forEach(button => {
      const selected = button.dataset.example === id;
      button.setAttribute('aria-selected', String(selected));
      button.tabIndex = selected ? 0 : -1;
      if (selected) {
        document.getElementById('example-panel').setAttribute('aria-labelledby', button.id);
        if (focus) button.focus();
      }
    });
    document.getElementById('example-title').textContent = intent.title;
    document.getElementById('example-intent').textContent = intent.text;
    document.getElementById('example-explanation').textContent = explanations[id];
    document.getElementById('example-patch').textContent = JSON.stringify(patch, null, 2);
    document.getElementById('intent-download').href = folder + 'intent.txt';
    document.getElementById('patch-download').href = folder + 'expected-spec-patch.json';
    const image = document.getElementById('intent-image');
    const hasVisual = Boolean(intent.visual_ref);
    document.getElementById('intent-figure').hidden = !hasVisual;
    document.getElementById('movement-note').hidden = hasVisual;
    if (hasVisual) {
      image.src = folder + intent.visual_ref;
      image.alt = `参考案例：${intent.title}；仅为意图定位，不是已修改的纸样`;
    }
    status.textContent = '参考示例，尚未执行。目标单位为毫米，实际执行前须校准原图比例。';
    document.getElementById('example-panel').dataset.example = id;
  } catch (error) {
    if (request === exampleRequest) status.textContent = error.message + '。仍可下载完整原型包阅读。';
  }
}

document.querySelectorAll('button[data-example]').forEach(button => {
  button.addEventListener('click', () => showExample(button.dataset.example));
  button.addEventListener('keydown', event => {
    const index = exampleIds.indexOf(button.dataset.example);
    const next = event.key === 'ArrowRight' ? (index + 1) % 3 : event.key === 'ArrowLeft' ? (index + 2) % 3 : event.key === 'Home' ? 0 : event.key === 'End' ? 2 : null;
    if (next !== null) { event.preventDefault(); showExample(exampleIds[next], true); }
  });
});
showExample(exampleIds[0]);

readJson('package/design-spec.json').then(spec => {
  document.getElementById('baseline-spec').textContent = JSON.stringify(spec, null, 2);
}).catch(error => { document.getElementById('baseline-spec').textContent = error.message; });

const dialog = document.getElementById('prototype-dialog');
document.getElementById('open-prototype').addEventListener('click', () => dialog.showModal());
document.getElementById('close-prototype').addEventListener('click', () => dialog.close());

document.querySelectorAll('.flow-board iframe').forEach(frame => {
  frame.addEventListener('load', () => {
    const doc = frame.contentDocument;
    if (!doc) return;
    doc.body.style.padding = '0';
    const resize = () => {
      const root = doc.querySelector('[data-flow]');
      if (root) frame.style.height = Math.ceil(root.getBoundingClientRect().height + 2) + 'px';
    };
    resize();
    new ResizeObserver(resize).observe(doc.body);
  });
});

readJson('../build.json').then(build => {
  document.getElementById('page-build').textContent = `版本 ${build.commit.slice(0, 7)}`;
}).catch(() => { /* Local source previews may omit generated publication metadata. */ });
