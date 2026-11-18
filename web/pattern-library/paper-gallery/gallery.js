"use strict";

async function showPaperGallery() {
  const params = new URLSearchParams(location.search);
  if (params.has("sample") && params.has("view")) {
    const legacy = new URL("rendered.html", location.href);
    legacy.search = location.search;
    legacy.hash = location.hash;
    location.replace(legacy.href);
    return;
  }

  const response = await fetch("paper-gallery/manifest.json");
  if (!response.ok) throw new Error("2D pattern manifest");
  const {entries, sources} = await response.json();
  const element = id => document.getElementById(id);
  const grid = element("paper-grid");
  const dialog = element("paper-dialog");
  const source = element("paper-source");
  const garment = element("paper-garment");
  const query = element("paper-query");

  for (const [key, title] of Object.entries(sources)) source.add(new Option(title, key));
  for (const value of new Set(entries.map(item => item.garment))) garment.add(new Option(value, value));

  function setPattern(id) {
    const url = new URL(location.href);
    url.searchParams.delete("sample");
    if (id) url.searchParams.set("pattern", id);
    else url.searchParams.delete("pattern");
    history.replaceState(null, "", url);
  }

  function open(item) {
    element("paper-title").textContent = item.title;
    const image = element("paper-image");
    image.src = item.preview;
    image.alt = item.title + "的二维裁片排版";
    element("paper-details").textContent = [
      sources[item.source], item.kind, item.sourceMember, "预览采用适屏缩放，请按原件确认裁剪比例。",
    ].filter(Boolean).join(" · ");
    element("paper-origin").href = item.sourceUrl;
    element("paper-full").href = item.preview;
    const download = element("paper-download");
    download.hidden = !item.download;
    if (item.download) {
      download.href = item.download;
      download.textContent = item.downloadLabel + " ↓";
    }
    dialog.showModal();
    setPattern(item.id);
  }

  function card(item, position) {
    const listItem = document.createElement("li");
    const anchor = document.createElement("a");
    anchor.className = "paper-card";
    anchor.href = "?pattern=" + encodeURIComponent(item.id);
    anchor.dataset.pattern = item.id;
    const image = document.createElement("img");
    image.className = "paper-thumb";
    image.src = item.preview;
    image.alt = "";
    image.width = 400;
    image.height = 270;
    image.loading = position < 8 ? "eager" : "lazy";
    image.decoding = "async";
    const label = document.createElement("span");
    label.className = "paper-label";
    const title = document.createElement("strong");
    title.textContent = item.title;
    const meta = document.createElement("span");
    meta.textContent = [sources[item.source], item.garment, item.kind].join(" · ");
    label.append(title, meta);
    anchor.append(image, label);
    anchor.addEventListener("click", event => {
      if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
      event.preventDefault();
      open(item);
    });
    listItem.append(anchor);
    return listItem;
  }

  function show() {
    const terms = query.value.trim().toLowerCase().split(/\s+/).filter(Boolean);
    const filtered = entries.filter(item => {
      const text = [
        item.title, item.garment, item.kind, sources[item.source], item.sourceMember, ...(item.catalogIds ?? []),
      ].join(" ").toLowerCase();
      return (!source.value || source.value === item.source)
        && (!garment.value || garment.value === item.garment)
        && terms.every(term => text.includes(term));
    });
    grid.replaceChildren(...filtered.map(card));
    element("paper-status").textContent = filtered.length ? filtered.length + " 张二维纸样" : "没有匹配的纸样。请调整筛选条件。";
  }

  query.addEventListener("input", show);
  source.addEventListener("change", show);
  garment.addEventListener("change", show);
  dialog.addEventListener("close", () => setPattern(null));
  element("paper-filters").hidden = false;
  show();
  const requested = entries.find(item => item.id === (params.get("pattern") ?? params.get("sample")));
  if (requested) open(requested);
}

showPaperGallery().catch(() => {
  document.getElementById("paper-status").textContent = "暂时无法加载纸样预览。请通过 CAD 索引查看原件。";
});
