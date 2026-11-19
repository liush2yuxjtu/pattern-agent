// Standalone artifact verifier. Requires Node.js 22+ and playwright@1.62.1.
// Usage: node verify-garment.js garment-gpu-studio.html

// scripts/verify-artifact-entry.js
import fs4 from "node:fs";
import path3 from "node:path";
import os from "node:os";
import { createServer } from "node:http";
import { createHash as createHash3 } from "node:crypto";

// tests/browser-verification.js
import fs2 from "node:fs";
import path from "node:path";
import { createHash } from "node:crypto";

// tests/playwright-runtime.js
import { pathToFileURL } from "node:url";
import fs from "node:fs";
async function loadPlaywright() {
  try {
    return await import("playwright");
  } catch (e) {
    const directory = process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES || "/opt/codex/runtimes/codex-primary-runtime/dependencies/node/node_modules";
    const p = directory + "/playwright/index.mjs";
    if (!fs.existsSync(p)) throw new Error("Install verification dependency: npm install --save-dev playwright@1.62.1");
    return import(pathToFileURL(p).href);
  }
}
function launchSettings() {
  const software = process.platform === "linux";
  const executable = process.env.GARMENT_CHROMIUM || "/usr/lib/chromium/chromium";
  return { headless: true, ...fs.existsSync(executable) ? { executablePath: executable } : {}, args: software ? ["--no-sandbox", "--enable-unsafe-webgpu", "--use-angle=vulkan", "--use-vulkan=swiftshader", "--enable-features=Vulkan", "--disable-vulkan-surface"] : [] };
}

// tests/browser-verification.js
async function verifyBrowser(root, { steps = 180, url = "http://127.0.0.1:8047/garment-gpu-studio.html" } = {}) {
  const dir = path.join(root, "evidence"), report = { status: "RUNNING", checks: [], errors: [], cases: {}, htmlSha256: createHash("sha256").update(fs2.readFileSync(path.join(root, "dist/garment-gpu-studio.html"))).digest("hex") };
  const save = () => fs2.writeFileSync(path.join(dir, "browser-report-js.json"), JSON.stringify(report, null, 2));
  const check = (name, value, detail = null) => {
    report.checks.push({ name, status: value ? "PASS" : "FAIL", detail });
    save();
    console.log(`${value ? "PASS" : "FAIL"} ${name}`, detail ?? "");
  };
  const snap = async (page, file) => {
    const value = await page.evaluate(() => ({ project: window.garmentAPI.getProject(), positions: window.garmentAPI.getPositions() }));
    fs2.writeFileSync(path.join(dir, file), JSON.stringify(value));
  };
  save();
  const { chromium } = await loadPlaywright();
  let browser;
  try {
    browser = await chromium.launch(launchSettings());
    const context = await browser.newContext({ viewport: { width: 1440, height: 1050 }, acceptDownloads: true }), page = await context.newPage(), requests = [];
    page.on("pageerror", (e) => report.errors.push(e.message));
    page.on("request", (r) => requests.push(r.url()));
    await page.goto(url, { waitUntil: "load" });
    await page.waitForFunction(() => window.garmentState && !window.garmentState.busy, {}, { timeout: 9e4 });
    const state = () => page.evaluate(() => window.garmentState);
    report.initial = await state();
    report.adapter = report.initial.backend;
    save();
    check("full anatomical mesh and real 3D canvas", report.initial.bodyVertices === 4002 && report.initial.bodyFaces === 8e3 && await page.locator("canvas").count() === 1);
    check("WASM f64 functions active", report.initial.wasm.active && report.initial.wasm.exports.includes("principal_min"));
    check("WebGPU adapter/device available", !!report.adapter, report.adapter);
    if (!report.adapter) throw new Error("No compute device");
    const before = await page.evaluate(() => window.garmentAPI.getPositions());
    await page.locator("#step").click();
    await page.waitForFunction(() => window.garmentState.step === 1 && !window.garmentState.busy, {}, { timeout: 9e4 });
    let st = await state();
    check("GPU queue dispatch and raw read-back candidate changes", st.dispatches > 0 && st.gpuCandidateDeltaMm > 0, { dispatches: st.dispatches, deltaMm: st.gpuCandidateDeltaMm });
    check("GPU predictor stays inside 1 mm trust region", st.gpuCandidateDeltaMm <= 1.001, st.gpuCandidateDeltaMm);
    check("final hybrid state changes", JSON.stringify(before) !== JSON.stringify(await page.evaluate(() => window.garmentAPI.getPositions())));
    check("GPU shader validation produces no errors", st.errors.length === 0, st.errors);
    async function settle(label) {
      for (let i = 0; i < steps / 30; i++) {
        await page.evaluate(async () => {
          await window.garmentAPI.advance(30);
        });
        const s2 = await state();
        if (s2.stale) throw new Error("Solver stopped: " + s2.errors.join("; "));
        console.log(label, "step", s2.step);
      }
      await page.locator("#verify").click();
      const s = await state();
      check(`${label}: finite positions`, s.metrics.finite);
      check(`${label}: seam gap <= 2 mm`, s.metrics.seamGapMm <= 2, s.metrics.seamGapMm);
      check(`${label}: no internal body vertices or samples`, s.metrics.penetratingVertices === 0 && s.metrics.penetratingSamples === 0);
      check(`${label}: no complete body-face crossing`, s.metrics.bodyFaceCrossings === 0, s.metrics.bodyFaceCrossings);
      check(`${label}: no nonadjacent cloth-face crossing`, s.metrics.selfFaceCrossings === 0, s.metrics.selfFaceCrossings);
      check(`${label}: p95 principal strain <= 10%`, s.metrics.strainP95 <= 0.1, s.metrics.strainP95);
      check(`${label}: max principal strain <= 25%`, s.metrics.strainMax <= 0.25, s.metrics.strainMax);
      check(`${label}: full discrete geometry verdict`, s.verdict.geometry === "PASS", s.verdict.geometry);
      return s;
    }
    report.settled = await settle("baseline");
    await snap(page, "gpu-snapshot-js.json");
    save();
    for (const mode of ["pattern", "strain", "stress", "folds", "collision", "debug", "fabric"]) {
      await page.locator(`[data-mode="${mode}"]`).click();
      check("view " + mode, (await state()).mode === mode);
    }
    await page.locator('[data-view="front"]').click();
    const front = await page.locator("#viewport").screenshot();
    await page.locator('[data-view="back"]').click();
    const back = await page.locator("#viewport").screenshot();
    check("front/back cameras render distinct real images", !front.equals(back));
    await page.locator('[data-view="iso"]').click();
    const liveStep = (await state()).step;
    await page.evaluate(() => window.garmentAPI.seek(0));
    check("replay seek does not integrate physics", (await state()).step === liveStep);
    check("replay exact recorded Float32 coordinates", await page.evaluate(() => JSON.stringify(window.garmentAPI.getPositions()) === JSON.stringify(Array.from(window.garmentAPI.getState().frames.frames[0].positions))));
    await page.locator("#next").click();
    check("next recorded frame control", (await state()).cursor === 1);
    await page.locator("#chestMm").fill("935");
    check("size edit invalidates old mesh/physics/export", (await state()).stale && !await page.locator("#obj").isEnabled());
    check("size edit removes old PASS labels", (await page.locator("#diagnostics").innerText()).includes("STALE"));
    await page.locator("#apply").click();
    await page.waitForFunction(() => !window.garmentState.stale && !window.garmentState.busy, {}, { timeout: 9e4 });
    st = await state();
    check("resized document has new version and clean timeline", st.version !== report.initial.version && st.step === 0 && st.frameCount === 1);
    check("actual morphed chest remeasured within 1 mm", Math.abs(st.measurements.chest) < 1, st.measurements);
    await page.locator("#step").click();
    await page.waitForFunction(() => window.garmentState.step === 1 && !window.garmentState.busy, {}, { timeout: 9e4 });
    report.wideSettled = await settle("wide");
    await snap(page, "gpu-snapshot-wide-js.json");
    save();
    await page.locator("#grade").click();
    await page.waitForFunction(() => window.garmentState.grade && !window.garmentState.busy, {}, { timeout: 9e4 });
    check("three independently redrafted grading sizes", (await state()).grade.length === 3);
    await page.locator('[data-mode="fabric"]').click();
    const getDownload = async (id, name) => {
      const promise = page.waitForEvent("download");
      await page.locator("#" + id).click();
      const download = await promise;
      await download.saveAs(path.join(dir, name));
      return fs2.readFileSync(path.join(dir, name), "utf8");
    };
    const obj = await getDownload("obj", "browser-export-js.obj"), positions = await page.evaluate(() => window.garmentAPI.getPositions()), vertices = obj.split("\n").filter((s) => s.startsWith("v ")).flatMap((s) => s.split(" ").slice(1).map(Number));
    check("downloaded OBJ equals exact displayed frame", JSON.stringify(vertices) === JSON.stringify(positions));
    const svg = await getDownload("svg", "browser-pattern-js.svg");
    check("downloaded metric SVG has actual 100 mm calibration box", svg.includes('width="100" height="100"') && /width="[\d.]+mm"/.test(svg));
    await page.locator("#run").click();
    await page.waitForFunction(() => window.garmentState.running, {}, { timeout: 9e4 });
    check("pause remains enabled during integration", await page.locator("#run").isEnabled());
    await page.locator("#run").click();
    await page.waitForFunction(() => !window.garmentState.running && !window.garmentState.busy, {}, { timeout: 9e4 });
    check("pause stops integration", !(await state()).running);
    const next = (await state()).step + 1;
    await context.setOffline(true);
    await page.locator("#step").click();
    await page.waitForFunction((n) => window.garmentState.step === n && !window.garmentState.busy, next, { timeout: 9e4 });
    check("offline physical step really runs", (await state()).step === next);
    check("no remote runtime dependency requests", requests.every((u) => new URL(u).origin === new URL(url).origin), requests);
    await page.setViewportSize({ width: 390, height: 844 });
    check("mobile has no document horizontal overflow", await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
    await page.setViewportSize({ width: 1440, height: 1050 });
    report.final = await state();
    check("no uncaught browser exceptions", report.errors.length === 0, report.errors);
    await page.evaluate(async () => {
      window.garmentAPI.getSolver().step = async () => {
        throw new Error("controlled verification failure");
      };
      await window.garmentAPI.advance(1);
    });
    st = await state();
    check("controlled solver error invalidates old results", st.stale && !await page.locator("#obj").isEnabled() && (await page.locator("#diagnostics").innerText()).includes("STALE"));
    report.status = report.checks.every((c) => c.status === "PASS") ? "PASS" : "FAIL";
    report.acceleration = report.adapter.isFallbackAdapter ? "Real WebGPU API/WGSL via software adapter; hardware acceleration not asserted." : "Hardware adapter reported by browser; no performance guarantee.";
    save();
    await browser.close();
    return report;
  } catch (e) {
    report.status = "FAIL";
    report.exception = e.stack || String(e);
    save();
    if (browser) await browser.close();
    throw e;
  }
}

// tests/independent-geometry.js
import fs3 from "node:fs";
import path2 from "node:path";
import { createHash as createHash2 } from "node:crypto";
import assert from "node:assert/strict";
var sub = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
var dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
var cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
var vec = (p, i) => [p[i * 3], p[i * 3 + 1], p[i * 3 + 2]];
function stretchesQR(a, b) {
  const x = Math.hypot(...a);
  if (x === 0) return [Math.hypot(...b), 0];
  const q = dot(a, b) / x, r = Math.hypot(...cross(a, b)) / x, high = (Math.hypot(x + r, q) + Math.hypot(x - r, q)) / 2;
  return [high, high === 0 ? 0 : x * r / high];
}
function hit(a, b, t, ray = false) {
  const d = sub(b, a), u = sub(t[1], t[0]), v = sub(t[2], t[0]), h = cross(d, v), den = dot(u, h);
  if (Math.abs(den) < 1e-13) return null;
  const s = sub(a, t[0]), f = dot(s, h) / den, q = cross(s, u), g = dot(d, q) / den, k = dot(v, q) / den, e = 1e-9;
  if (f > e && g > e && f + g < 1 - e && k > e && (ray || k < 1 - e)) return k;
  return null;
}
function crosses(a, b) {
  for (let i = 0; i < 3; i++) if (hit(a[i], a[(i + 1) % 3], b) !== null || hit(b[i], b[(i + 1) % 3], a) !== null) return true;
  return false;
}
function faces(p, indices) {
  const out = [];
  for (let i = 0; i < indices.length; i += 3) {
    const ids = indices.slice(i, i + 3), xyz = ids.map((i2) => vec(p, i2)), lo = [0, 1, 2].map((k) => Math.min(...xyz.map((p2) => p2[k]))), hi = [0, 1, 2].map((k) => Math.max(...xyz.map((p2) => p2[k])));
    out.push({ ids, xyz, lo, hi });
  }
  return out;
}
function overlaps(a, b) {
  return a.lo[0] <= b.hi[0] + 1e-10 && a.hi[0] >= b.lo[0] - 1e-10 && a.lo[1] <= b.hi[1] + 1e-10 && a.hi[1] >= b.lo[1] - 1e-10 && a.lo[2] <= b.hi[2] + 1e-10 && a.hi[2] >= b.lo[2] - 1e-10;
}
function crossingPairs(a, b, roots = null) {
  let count = 0, candidates = 0;
  const examples = [];
  for (let i = 0; i < a.length; i++) for (let j = roots ? i + 1 : 0; j < b.length; j++) {
    if (!overlaps(a[i], b[j])) continue;
    if (roots && a[i].ids.some((x) => b[j].ids.some((y) => roots[x] === roots[y]))) continue;
    candidates++;
    if (crosses(a[i].xyz, b[j].xyz)) {
      count++;
      if (examples.length < 30) examples.push([i, j]);
    }
  }
  return { count, candidates, examples };
}
function insideCount(p, bodyFaces) {
  let inside = 0;
  const d = [1, 0.231764, 0.417398];
  for (let i = 0; i < p.length; i += 3) {
    const a = p.slice(i, i + 3), b = a.map((x, k) => x + d[k]), times = [];
    for (const f of bodyFaces) {
      const at = hit(a, b, f.xyz, true);
      if (at !== null) times.push(at);
    }
    times.sort((a2, b2) => a2 - b2);
    let count = 0, last = -Infinity;
    for (const t of times) if (t - last > 1e-8) {
      count++;
      last = t;
    }
    if (count % 2) inside++;
  }
  return inside;
}
function verifyGeometrySnapshot(snapshot, runtime, label = "case") {
  const d = snapshot.project.document, p = snapshot.positions, body = snapshot.project.body, tri = d.mesh.triangles, uv = d.mesh.restUV, errors = [], checks = [];
  const check = (name, value, detail = null) => {
    checks.push({ name, status: value ? "PASS" : "FAIL", detail });
    if (!value) errors.push(name);
  };
  const triangle = [[0, 0, 0], [1, 0, 0], [0, 1, 0]];
  assert.notEqual(hit([0.2, 0.2, -1], [0.2, 0.2, 1], triangle), null);
  assert.equal(hit([2, 2, -1], [2, 2, 1], triangle), null);
  assert.ok(Math.abs(stretchesQR([1, 0, 0], [0, 1e-9, 0])[1] - 1e-9) < 1e-20);
  const values = [];
  for (let f = 0; f < tri.length; f += 3) {
    const [i, j, k] = tri.slice(f, f + 3), x0 = (uv[j][0] - uv[i][0]) / 1e3, y0 = (uv[j][1] - uv[i][1]) / 1e3, x1 = (uv[k][0] - uv[i][0]) / 1e3, y1 = (uv[k][1] - uv[i][1]) / 1e3, det = x0 * y1 - x1 * y0, e1 = sub(vec(p, j), vec(p, i)), e2 = sub(vec(p, k), vec(p, i));
    assert.ok(Math.abs(det) > 1e-14);
    const a = e1.map((v, n) => (v * y1 - e2[n] * y0) / det), b = e1.map((v, n) => (e2[n] * x0 - v * x1) / det), s = stretchesQR(a, b);
    values.push(Math.max(Math.abs(s[0] - 1), Math.abs(s[1] - 1)));
  }
  values.sort((a, b) => a - b);
  const q = 0.95 * (values.length - 1), index = Math.floor(q), p95 = values[index] + (values[Math.min(index + 1, values.length - 1)] - values[index]) * (q - index), max = values.at(-1);
  check("finite coordinates", p.every(Number.isFinite));
  check("independent QR principal strain p95 <= 10%", p95 <= 0.1, p95);
  check("independent QR max principal strain <= 25%", max <= 0.25, max);
  check("WASM diagnostics agree with independent QR", Math.abs(p95 - runtime.metrics.strainP95) < 1e-8 && Math.abs(max - runtime.metrics.strainMax) < 1e-8);
  const parent = Int32Array.from({ length: p.length / 3 }, (_, i) => i), find = (i) => parent[i] === i ? i : parent[i] = find(parent[i]);
  let gap = 0;
  for (const seam of d.seams) for (const [a, b] of seam.pairs) {
    parent[find(b)] = find(a);
    gap = Math.max(gap, Math.hypot(...sub(vec(p, a), vec(p, b))) * 1e3);
  }
  check("independent seam gap <= 2 mm", gap <= 2, gap);
  const roots = Array.from(parent, (_, i) => find(i)), cloth = faces(p, tri), human = faces(body.positions, body.triangles);
  const bodyPairs = crossingPairs(cloth, human), selfPairs = crossingPairs(cloth, cloth, roots), inside = insideCount(p, human);
  check("independent closed-body ray parity: zero internal vertices", inside === 0, inside);
  check("independent complete body face crossing count = 0", bodyPairs.count === 0, bodyPairs);
  check("independent nonadjacent self crossing count = 0", selfPairs.count === 0, selfPairs);
  return { label, status: errors.length ? "FAIL" : "PASS", checks, principalStrain: { p95, max }, seamGapMm: gap, bodyFaceCrossings: bodyPairs.count, selfFaceCrossings: selfPairs.count, insideBodyVertices: inside, method: "Independent JavaScript QR-based singular values, closed-mesh ray parity, exhaustive AABB-filtered strict two-way triangle crossings.", limits: "Discrete saved frames only; coplanar overlap, CCD, material calibration and real-person fit are outside these automated assertions." };
}
function verifySavedGeometry(root) {
  const report = JSON.parse(fs3.readFileSync(path2.join(root, "evidence/browser-report-js.json"))), results = [];
  for (const [label, file, key] of [["baseline", "gpu-snapshot-js.json", "settled"], ["wide", "gpu-snapshot-wide-js.json", "wideSettled"]]) {
    const filePath = path2.join(root, "evidence", file), snapshot = JSON.parse(fs3.readFileSync(filePath));
    const r = verifyGeometrySnapshot(snapshot, report[key], label);
    r.snapshotSha256 = createHash2("sha256").update(fs3.readFileSync(filePath)).digest("hex");
    results.push(r);
  }
  const out = { status: results.every((r) => r.status === "PASS") ? "PASS" : "FAIL", results };
  fs3.writeFileSync(path2.join(root, "evidence/independent-report-js.json"), JSON.stringify(out, null, 2));
  return out;
}

// scripts/verify-artifact-entry.js
async function main() {
  const input = process.argv[2];
  if (!input) {
    console.error("Usage: node verify-garment.js /path/to/garment-gpu-studio.html");
    process.exitCode = 2;
    return;
  }
  const html = path3.resolve(input);
  if (!fs4.statSync(html).isFile()) throw new Error("HTML file required");
  const root = fs4.mkdtempSync(path3.join(os.tmpdir(), "garment-verification-"));
  fs4.mkdirSync(path3.join(root, "dist"));
  fs4.mkdirSync(path3.join(root, "evidence"));
  fs4.copyFileSync(html, path3.join(root, "dist/garment-gpu-studio.html"));
  const server = createServer((req, res) => {
    if (req.url !== "/garment-gpu-studio.html") {
      res.writeHead(404);
      res.end();
      return;
    }
    res.writeHead(200, { "content-type": "text/html; charset=utf-8", "cache-control": "no-store" });
    res.end(fs4.readFileSync(html));
  });
  await new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", resolve);
  });
  let browser;
  try {
    browser = await verifyBrowser(root, { url: `http://127.0.0.1:${server.address().port}/garment-gpu-studio.html` });
  } finally {
    await new Promise((resolve) => server.close(resolve));
  }
  const geometry = verifySavedGeometry(root), report = { status: browser.status === "PASS" && geometry.status === "PASS" ? "PASS" : "FAIL", htmlSha256: createHash3("sha256").update(fs4.readFileSync(html)).digest("hex"), browserChecks: browser.checks.length, independentCases: geometry.results.map((r) => ({ label: r.label, status: r.status, p95: r.principalStrain.p95, max: r.principalStrain.max, bodyCrossings: r.bodyFaceCrossings, selfCrossings: r.selfFaceCrossings, seamGapMm: r.seamGapMm })), adapter: browser.adapter, evidenceDirectory: path3.join(root, "evidence") };
  fs4.writeFileSync(path3.join(root, "verification-artifact.json"), JSON.stringify(report, null, 2));
  console.log(JSON.stringify(report, null, 2));
  if (report.status !== "PASS") process.exitCode = 1;
}
main().catch((e) => {
  console.error(e.stack || String(e));
  process.exitCode = 1;
});
