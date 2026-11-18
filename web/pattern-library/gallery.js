"use strict";

const $ = id => document.getElementById(id);
const sampleButtons = [...document.querySelectorAll("[data-sample]")];
const viewButtons = [...document.querySelectorAll("[data-view]")];
const editButtons = [...document.querySelectorAll("[data-edit]")];
const views = {angle: "斜前", front: "正面", back: "背面"};
const editLabels = {
  overlay: "改前与改后的二维裁片叠加",
  before: "改前二维裁片",
  after: "改后二维裁片",
};

function press(buttons, key, value) {
  for (const button of buttons) {
    button.setAttribute("aria-pressed", String(button.dataset[key] === value));
  }
}

function showDownload(id, file, label) {
  const link = $(id);
  link.href = file;
  link.textContent = label;
}

function showImage(img, path, description) {
  img.src = path;
  img.alt = description;
}

function initializeEditCanvas() {
  const canvas = $("edit-canvas");
  if (!canvas) return;

  function bindLayers() {
    const svgDocument = canvas.contentDocument;
    const before = svgDocument?.getElementById("pattern-before");
    const after = svgDocument?.getElementById("pattern-after");
    if (!before || !after) return;

    for (const button of editButtons) {
      button.disabled = false;
      button.onclick = () => {
        const mode = button.dataset.edit;
        before.setAttribute("display", mode === "after" ? "none" : "inline");
        after.setAttribute("display", mode === "before" ? "none" : "inline");
        canvas.setAttribute("aria-label", editLabels[mode]);
        press(editButtons, "edit", mode);
      };
    }
  }

  canvas.addEventListener("load", bindLayers);
  bindLayers();
}

initializeEditCanvas();

$("zoom-pattern")?.addEventListener("click", () => {
  const img = $("pattern-img");
  showImage($("enlarged-pattern"), img.src, img.alt);
  $("pattern-dialog").showModal();
});

async function initialize() {
  const response = await fetch("gallery/manifest.json");
  if (!response.ok) throw new Error("gallery manifest");
  const data = await response.json();
  const samples = new Map(data.samples.map(item => [item.id, item]));
  const args = new URLSearchParams(location.search);
  let selected = samples.get(args.get("sample")) ?? samples.get(sampleButtons[0].dataset.sample);
  let view = Object.hasOwn(views, args.get("view")) ? args.get("view") : "angle";

  function updateAddress() {
    const url = new URL(location.href);
    url.searchParams.set("sample", selected.id);
    url.searchParams.set("view", view);
    history.replaceState(null, "", url);
  }

  function showView() {
    showImage($("render-img"), selected.views[view], selected.name + "的三维" + views[view] + "渲染");
    press(viewButtons, "view", view);
  }

  function showSample() {
    showImage($("pattern-img"), selected.preview, selected.name + "的二维裁片");
    showDownload("pattern-download", selected.pattern, "下载纸样 SVG ↓");
    showDownload("source-download", selected.native, selected.nativeLabel);
    showDownload("model-download", selected.model, selected.modelLabel);
    $("evidence-link").href = selected.evidence;
    $("sample-name").textContent = selected.name;
    $("sample-scope").textContent = selected.scope;
    $("sample-measures").replaceChildren(...selected.metrics.map(([label, value]) => {
      const cell = document.createElement("div");
      const dt = document.createElement("dt");
      const dd = document.createElement("dd");
      dt.textContent = label;
      dd.textContent = value;
      cell.append(dt, dd);
      return cell;
    }));
    press(sampleButtons, "sample", selected.id);
    showView();
  }

  for (const button of sampleButtons) {
    button.addEventListener("click", () => {
      selected = samples.get(button.dataset.sample);
      showSample();
      updateAddress();
    });
  }
  for (const button of viewButtons) {
    button.addEventListener("click", () => {
      view = button.dataset.view;
      showView();
      updateAddress();
    });
  }
  showSample();
}

if (sampleButtons.length) initialize().catch(() => {
  $("gallery-problem").textContent = "切换资料暂时无法加载，当前展示 Sandy 基础款。";
  $("gallery-problem").hidden = false;
  for (const button of [...sampleButtons, ...viewButtons]) button.disabled = true;
});
