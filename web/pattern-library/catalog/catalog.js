"use strict";

const item = id => document.getElementById(id);
const controls = [...document.querySelectorAll("[data-mode]")];
const modes = ["patterns", "feedback"];
const params = new URLSearchParams(location.search);
const state = {
  mode: modes.includes(params.get("view")) ? params.get("view") : "patterns",
  page: 0,
  style: "",
};
const collection = new Map();
const perPage = 24;
const numberFormat = new Intl.NumberFormat("zh-CN");
const count = number => numberFormat.format(number);
const styleOrder = new Intl.Collator("zh-CN", {numeric: true});

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
    const [cad, gallery] = await Promise.all([
      read("cad.json"), read("../paper-gallery/manifest.json").catch(() => ({entries: []})),
    ]);
    const previews = new Map();
    for (const preview of gallery.entries) {
      for (const id of preview.catalogIds ?? []) {
        if (!previews.has(id)) previews.set(id, []);
        previews.get(id).push(preview);
      }
    }
    data = {
      sources: cad.sources,
      previews,
      categories: Object.fromEntries([...new Set(cad.entries.flatMap(row => row.formats ?? [row.format]))].map(value => [value, value])),
      records: wrapRecords(cad.entries, row => row.formats ?? [row.format], row => row.source,
        row => [row.title, row.garment, row.format, cad.sources[row.source], row.name, row.member, row.role, row.id].join(" ")),
    };
  } else {
    const [feedback, notes] = await Promise.all([read("review-signals.json"), read("review-notes.json")]);
    const sources = Object.fromEntries(Object.entries(feedback.sources).map(([key, s]) => [key, s.title]));
    const sourceKey = row => row.publisher ? "publisher:" + row.publisher : row.source_id;
    for (const note of notes) sources[sourceKey(note)] = note.publisher;
    data = {
      details: feedback,
      sources,
      categories: Object.fromEntries(Object.entries(feedback.parts).map(([key, value]) => [key, value.label])),
      records: wrapRecords([...notes, ...feedback.entries], row => [row.part], sourceKey,
        row => [row.garment, row.product_id, row.source_garment, row.locator, row.evidence, row.review_id, row.id,
          feedback.parts[row.part]?.label, row.candidate ?? feedback.actions[row.action], sources[sourceKey(row)]].join(" ")),
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
  for (const preview of data.previews.get(row.id) ?? []) {
    footer.append(link("../?pattern=" + encodeURIComponent(preview.id), "图册 · " + preview.title + " ↗"));
  }
  result.append(footer);
  return result;
}

function groupFeedback(records) {
  const publishers = new Map();
  for (const {row, source} of records) {
    if (!publishers.has(source)) publishers.set(source, new Map());
    const styles = publishers.get(source);
    const key = row.publisher ? row.garment.trim() : String(row.product_id);
    if (!styles.has(key)) styles.set(key, {key, source, curated: Boolean(row.publisher), reviews: new Map(), garments: new Set()});
    const style = styles.get(key);
    const review = row.review_id ?? row.id;
    if (!style.reviews.has(review)) style.reviews.set(review, []);
    style.reviews.get(review).push(row);
    if (row.garment) style.garments.add(row.garment);
  }
  return [...publishers.values()].flatMap(styles => [...styles.values()]
    .sort((a, b) => b.reviews.size - a.reviews.size || styleOrder.compare(a.key, b.key)));
}

function reviewCard(rows, data) {
  const [first] = rows;
  const review = node("li", "", "review");
  const header = node("div", "", "review-header");
  header.append(node("strong", first.locator ?? first.review_id), node("span", first.locator ? first.id : "商品 " + first.product_id));
  review.append(header);
  for (const row of rows) {
    const part = data.details.parts[row.part];
    const action = row.candidate ?? data.details.actions[row.action];
    const signal = node("div", "", "review-signal");
    signal.append(node("p", part.label + " · " + action, "review-action"), node("p", row.evidence, "evidence"),
      node("p", "量法  " + (row.measurement ?? part.measurement) + " · 保留  " + (row.preserve ?? part.preserve)));
    review.append(signal);
  }
  const dataset = data.details.sources[first.source_id];
  const footer = node("div", "", "card-footer");
  footer.append(link(first.url ?? dataset.url, dataset ? "原始数据集 ↗" : "原反馈页面 ↗"));
  if (dataset) footer.append(node("span", "源记录 " + first.source_index, "locator"));
  review.append(footer);
  return review;
}

function feedbackStyle(group, data, expanded) {
  const result = card();
  result.classList.add("style-group");
  result.dataset.source = group.source;
  result.dataset.style = group.key;
  const title = group.curated ? group.key : "商品 " + group.key;
  const header = node("div", "", "style-header");
  const heading = node("h3", title);
  const permalink = new URLSearchParams({view: "feedback", source: group.source, style: group.key});
  header.append(heading, link("?" + permalink, "款式链接 ↗"));
  result.append(header);
  if (!group.curated) result.append(node("p", [...group.garments].join(" · ")));

  const list = node("ul", "", "review-list");
  const showMore = node("button", "", "quiet more-reviews");
  showMore.type = "button";
  const reviews = [...group.reviews.values()];
  let visible = 0;
  function appendReviews() {
    const end = Math.min(visible + 8, reviews.length);
    list.append(...reviews.slice(visible, end).map(rows => reviewCard(rows, data)));
    visible = end;
    showMore.hidden = visible >= reviews.length;
    showMore.textContent = "再显示 " + Math.min(8, reviews.length - visible) + " 条";
  }

  const details = node("details");
  const label = count(reviews.length) + (group.curated ? " 条观察" : " 条评论");
  details.append(node("summary", label), list, showMore);
  details.addEventListener("toggle", () => {
    if (details.open && !visible) appendReviews();
  });
  showMore.addEventListener("click", appendReviews);
  if (expanded) {
    details.open = true;
    appendReviews();
  }
  result.append(details);
  return result;
}

function renderFeedback(groups, data, expanded) {
  const sections = new Map();
  for (const group of groups) {
    if (!sections.has(group.source)) {
      const section = node("section", "", "source-group");
      section.dataset.source = group.source;
      const heading = node("h2", data.sources[group.source]);
      heading.id = "source-group-" + sections.size;
      section.setAttribute("aria-labelledby", heading.id);
      const list = node("div", "", "style-list");
      list.setAttribute("role", "list");
      section.append(heading, list);
      sections.set(group.source, section);
    }
    sections.get(group.source).lastChild.append(feedbackStyle(group, data, expanded));
  }
  return [...sections.values()];
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
  const feedback = state.mode === "feedback";
  const records = feedback
    ? groupFeedback(filtered).filter(group => !state.style || group.key === state.style)
    : filtered;
  const pages = Math.max(1, Math.ceil(records.length / perPage));
  state.page = Math.min(state.page, pages - 1);
  const begin = state.page * perPage;
  const end = Math.min(begin + perPage, records.length);
  const subset = records.slice(begin, end);
  const view = feedback
    ? renderFeedback(subset, data, records.length === 1 && (words.length > 0 || Boolean(state.style)))
    : subset.map(({row}) => patternCard(row, data));
  item("entries").replaceChildren(...view);
  item("results-count").textContent = records.length
    ? count(records.length) + (feedback ? " 个来源内款式" : " 项") + "，显示 " + count(begin + 1) + "–" + count(end)
    : "没有找到匹配项";
  item("style-reset").hidden = !state.style;
  item("pager").hidden = pages <= 1;
  item("page-number").textContent = (state.page + 1) + " / " + pages;
  item("previous").disabled = state.page === 0;
  item("next").disabled = state.page >= pages - 1;
}

function setLocation() {
  const url = new URL(location.href);
  url.searchParams.set("view", state.mode);
  for (const [key, value] of [["source", item("source").value], ["style", state.style], ["q", item("query").value.trim()]]) {
    if (value) url.searchParams.set(key, value);
    else url.searchParams.delete(key);
  }
  history.replaceState(null, "", url);
}

async function select(mode, initial = false) {
  state.mode = mode;
  for (const button of controls) button.setAttribute("aria-pressed", String(button.dataset.mode === mode));
  const entries = item("entries");
  entries.classList.toggle("feedback-entries", mode === "feedback");
  entries.setAttribute("aria-label", mode === "feedback" ? "按来源和款式分组的用户反馈" : "CAD 纸样记录");
  if (mode === "feedback") entries.removeAttribute("role");
  else entries.setAttribute("role", "list");
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
    item("query").placeholder = patterns ? "如 ET、ZPRJ、连衣裙" : "如 袖长、Dickies、商品 ID、C-05";
    item("query").value = initial ? (params.get("q") ?? "") : "";
    options(item("category"), patterns ? "全部格式" : "全部部位", data.categories);
    options(item("source"), "全部来源", data.sources);
    item("source").value = initial && Object.hasOwn(data.sources, params.get("source")) ? params.get("source") : "";
    state.style = !patterns && initial && item("source").value ? (params.get("style") ?? "") : "";
    setLocation();
    item("category-label").textContent = patterns ? "文件格式" : "调整部位";
    item("download").href = patterns ? "cad-origins.csv" : "review-signals.csv";
    item("download").textContent = patterns ? "下载原件索引 CSV ↓" : "下载批量反馈 CSV ↓";
    item("download-extra").href = patterns ? "cad-publisher-links.csv" : "review-notes.csv";
    item("download-extra").textContent = patterns ? "下载发布方入口 CSV ↓" : "下载人工整理 CSV ↓";
    item("scope").textContent = patterns
      ? "已归档记录可核对原件指纹。带「发布方入口」的条目可在发布方获取，单独统计。变姿态工程共享款式。"
      : "展开款式查看原反馈与候选改法。人工观察保留发布方和原款式名，匿名评论用各数据集内的商品 ID 归组。";
    item("filters").hidden = false;
    item("loading").hidden = true;
    applyFilters(true);
  } catch {
    if (mode === state.mode) item("loading").textContent = "暂时无法加载资料。可以返回图册下载备用清单。";
  }
}

for (const button of controls) button.addEventListener("click", () => select(button.dataset.mode));
item("query").addEventListener("input", () => applyFilters(true));
item("category").addEventListener("change", () => applyFilters(true));
item("query").addEventListener("change", setLocation);
item("source").addEventListener("change", () => {
  state.style = "";
  setLocation();
  applyFilters(true);
});
item("style-reset").addEventListener("click", () => {
  state.style = "";
  setLocation();
  applyFilters(true);
  item("source").focus();
});
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
