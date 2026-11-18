"use strict";

const item = id => document.getElementById(id);
const controls = [...document.querySelectorAll("[data-mode]")];
const modes = ["patterns", "feedback"];
const params = new URLSearchParams(location.search);
const state = {mode: modes.includes(params.get("view")) ? params.get("view") : "patterns", page: 0};
const collection = new Map();
const perPage = 24;
const count = number => new Intl.NumberFormat("zh-CN").format(number);

function node(tag, text, className) {
  const result = document.createElement(tag);
  if (text) result.textContent = text;
  if (className) result.className = className;
  return result;
}

function link(target, caption) {
  const anchor = node("a", caption);
  anchor.href = target;
  return anchor;
}

async function read(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error("catalog request");
  return response.json();
}

function options(control, any, values) {
  const choices = Object.entries(values).sort((a, b) => a[1].localeCompare(b[1], "zh-CN"));
  control.replaceChildren(new Option(any, ""), ...choices.map(([key, label]) => new Option(label, key)));
}

function wrapRecords(rows, category, source, describe) {
  return rows.map(row => ({row, category: category(row), source: source(row), text: describe(row).toLowerCase()}));
}

async function dataFor(mode) {
  if (collection.has(mode)) return collection.get(mode);
  let data;
  if (mode === "patterns") {
    const cad = await read("cad.json");
    data = {
      sources: cad.sources,
      categories: Object.fromEntries([...new Set(cad.entries.flatMap(row => row.formats ?? [row.format]))].map(value => [value, value])),
      records: wrapRecords(cad.entries, row => row.formats ?? [row.format], row => row.source,
        row => [row.title, row.garment, row.format, cad.sources[row.source], row.name, row.member, row.role, row.id].join(" ")),
    };
  } else {
    const [feedback, notes] = await Promise.all([read("review-signals.json"), read("review-notes.json")]);
    const sources = Object.fromEntries(Object.entries(feedback.sources).map(([key, s]) => [key, s.title]));
    data = {
      details: feedback,
      sources: {...sources, manual: "人工整理 · 原评论与纸样评测"},
      categories: Object.fromEntries(Object.entries(feedback.parts).map(([key, value]) => [key, value.label])),
      records: wrapRecords([...notes, ...feedback.entries], row => [row.part], row => row.source_id,
        row => [row.garment, row.source_garment, row.evidence, row.review_id, row.id, feedback.parts[row.part]?.label,
          row.candidate ?? feedback.actions[row.action], sources[row.source_id]].join(" ")),
    };
  }
  collection.set(mode, data);
  return data;
}

function card() {
  const result = node("article", "", "card");
  result.setAttribute("role", "listitem");
  return result;
}

function patternCard(row, data) {
  const result = card();
  const footer = node("div", "", "card-footer");
  result.append(node("h2", row.title),
    node("p", [row.format, row.garment, data.sources[row.source], row.role].filter(Boolean).join(" · ")),
    node("p", row.sha256 ? "已归档 · " + count(row.bytes) + " 字节 · " + row.audit : row.audit));
  if (row.sha256) {
    const details = node("details");
    details.append(node("summary", "文件指纹与原名"), node("p", row.member || row.name), node("p", "SHA-256 " + row.sha256));
    result.append(details);
  }
  footer.append(link(row.url, "发布方来源 ↗"));
  if (row.preview) footer.append(link(row.preview, "二维裁片预览 ↗"));
  result.append(footer);
  return result;
}

function feedbackCard(row, data) {
  const result = card();
  const part = data.details.parts[row.part];
  const action = row.candidate ?? data.details.actions[row.action];
  const source = data.details.sources[row.source_id];
  const footer = node("div", "", "card-footer");
  result.append(node("h2", row.garment + " · " + part.label),
    node("p", row.evidence, "evidence"),
    node("p", "候选改法  " + action),
    node("p", "量法  " + (row.measurement ?? part.measurement) + " · 保留  " + (row.preserve ?? part.preserve)));
  footer.append(link(row.url ?? source.url, source ? source.title + " ↗" : row.publisher + " ↗"),
    node("span", row.locator ?? row.review_id, "locator"));
  result.append(footer);
  return result;
}

function applyFilters(reset = false) {
  const data = collection.get(state.mode);
  if (!data) return;
  if (reset) state.page = 0;
  const words = item("query").value.trim().toLowerCase().split(/\s+/).filter(Boolean);
  const category = item("category").value;
  const source = item("source").value;
  const filtered = data.records.filter(record => (!category || record.category.includes(category))
    && (!source || record.source === source) && words.every(word => record.text.includes(word)));
  const pages = Math.max(1, Math.ceil(filtered.length / perPage));
  state.page = Math.min(state.page, pages - 1);
  const begin = state.page * perPage;
  const end = Math.min(begin + perPage, filtered.length);
  const view = filtered.slice(begin, end).map(({row}) => state.mode === "patterns" ? patternCard(row, data) : feedbackCard(row, data));
  item("entries").replaceChildren(...view);
  item("results-count").textContent = filtered.length ? count(filtered.length) + " 项，显示 " + count(begin+1) + "–" + count(end) : "没有找到匹配项";
  item("pager").hidden = pages <= 1;
  item("page-number").textContent = (state.page+1) + " / " + pages;
  item("previous").disabled = state.page === 0;
  item("next").disabled = state.page >= pages - 1;
}

async function select(mode, initial = false) {
  state.mode = mode;
  for (const button of controls) button.setAttribute("aria-pressed", String(button.dataset.mode === mode));
  const parameters = new URLSearchParams(location.search);
  parameters.set("view", mode);
  history.replaceState(null, "", "?" + parameters);
  item("filters").hidden = true;
  item("pager").hidden = true;
  item("loading").textContent = "正在加载资料。";
  item("loading").hidden = false;
  item("entries").replaceChildren();
  item("scope").textContent = "";
  try {
    const data = await dataFor(mode);
    if (mode !== state.mode) return;
    const patterns = mode === "patterns";
    item("query").placeholder = patterns ? "如 ET、ZPRJ、连衣裙" : "如 袖长、口袋、腰围、WEC-000001";
    item("query").value = initial ? (params.get("q") ?? "") : "";
    options(item("category"), patterns ? "全部格式" : "全部部位", data.categories);
    options(item("source"), "全部来源", data.sources);
    item("category-label").textContent = patterns ? "文件格式" : "调整部位";
    item("download").href = patterns ? "cad-origins.csv" : "review-signals.csv";
    item("download").textContent = patterns ? "下载原件索引 CSV ↓" : "下载批量反馈 CSV ↓";
    item("download-extra").href = patterns ? "cad-publisher-links.csv" : "review-notes.csv";
    item("download-extra").textContent = patterns ? "下载发布方入口 CSV ↓" : "下载人工整理 CSV ↓";
    item("scope").textContent = patterns
      ? "已归档记录可核对原件指纹。带「发布方入口」的条目可在发布方获取，单独统计。变姿态工程共享款式。"
      : "人工条目附来源摘要。批量条目保留原评论片段。确认尺码、量法和目标数值后再应用改动。";
    item("filters").hidden = false;
    item("loading").hidden = true;
    applyFilters(true);
  } catch {
    if (mode === state.mode) item("loading").textContent = "暂时无法加载资料。可以返回图册下载备用清单。";
  }
}

for (const button of controls) button.addEventListener("click", () => select(button.dataset.mode));
item("query").addEventListener("input", () => applyFilters(true));
for (const id of ["category", "source"]) item(id).addEventListener("change", () => applyFilters(true));
for (const [id, delta] of [["previous", -1], ["next", 1]]) {
  item(id).addEventListener("click", () => {state.page += delta; applyFilters();});
}
read("summary.json").then(summary => {
  for (const [id, number] of Object.entries(summary)) {
    const target = item(id);
    if (target) target.textContent = count(number);
  }
}).catch(() => {});
select(state.mode, true);
