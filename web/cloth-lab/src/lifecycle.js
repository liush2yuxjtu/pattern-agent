import { encodeTrajectory } from "./trajectory.js";
import { solvePressureCoupon } from "./pressure.js";
import { requireRendererAvailable } from "./runtime-context.js";

/** Initialize WASM and the renderer, publish the public API, and drive frames. */
export function createLifecycle(
  S,
  {
    copyTo,
    floatView,
    setupScene,
    firstRender,
    setupCloth,
    restore,
    wireUI,
    advance,
    takeSteps,
    analyze,
    draw,
    updateReplayUI,
    replayTick,
    sceneAudit,
    pointToPixel,
    rendererDiagnostics,
    surface,
    startRecording,
    stopRecording,
    seekFrame,
    playReplay,
    replayInfo,
    project,
    performanceLog,
    patternSVG,
    setRunning,
    applyMode,
    stateChanged,
  },
) {
  const { $, payload, decode } = S;

  function animate(now) {
    const elapsed = S.lastDraw ? (now - S.lastDraw) / 1000 : 0;
    S.lastDraw = now;
    const available = !S.renderBlocked && !S.renderPending;
    if (S.playing && !S.busy && available) replayTick(elapsed);
    else if (S.running && !S.busy && available) {
      S.frameTimes.push(elapsed * 1000);
      if (S.frameTimes.length > 600) S.frameTimes.shift();
      const use = Math.min(elapsed, 0.05);
      S.droppedSeconds += Math.max(0, elapsed - use);
      S.accumulator += use;
      let steps = Math.min(6, Math.floor(S.accumulator * 120));
      if (steps) {
        takeSteps(steps);
        S.accumulator -= steps / 120;
      }
      if (now - S.lastAnalyze > 150) {
        analyze();
        S.lastAnalyze = now;
        const samples = S.frameTimes.slice(-90);
        const avg = samples.reduce((a, b) => a + b, 0) / (samples.length || 1);
        $("fps").textContent =
          `${(1000 / avg).toFixed(1)} / ${avg.toFixed(0)} ms`;
      }
      draw();
      updateReplayUI();
    }
    requestAnimationFrame(animate);
  }

  function publicAPI() {
    return {
      ready: true,
      advance,
      sceneAudit,
      pointToPixel,
      rendererDiagnostics,
      pressureCoupon: (spec) => solvePressureCoupon(decode(payload.wasm), spec),
      replay: {
        start: startRecording,
        stop: stopRecording,
        seek: seekFrame,
        play: playReplay,
        info: replayInfo,
        export: () => encodeTrajectory(S.track, payload.buildFingerprint),
      },
      setCollisionCache: (enabled) => {
        requireRendererAvailable(S);
        return S.wasm.set_cache(+enabled);
      },
      stats: () => analyze(),
      project,
      restore,
      performanceLog,
      patternSVG,
      setRunning,
      setMode: (mode) => {
        requireRendererAvailable(S);
        return applyMode(mode);
      },
      reset: setupCloth,
      clearPerformance: () => {
        S.frameTimes = [];
        S.history = [];
        S.droppedSeconds = 0;
      },
      materialProbe: (u, v) => {
        S.wasm.material_probe(...u, ...v);
        return Array.from(floatView(S.wasm.probe_ptr(), 8));
      },
      collisionProbe: (p) => {
        S.wasm.collision_probe(...p);
        return Array.from(floatView(S.wasm.probe_ptr(), 7));
      },
      injectVertex: (index, point) => {
        requireRendererAvailable(S);
        S.wasm.inject_vertex(index, ...point);
        stateChanged("injection");
        analyze();
        draw();
        return { ...S.lastStats };
      },
      surface,
      source: {
        fingerprint: payload.buildFingerprint,
        wasmSha256: payload.wasmSha256,
        bodySourceSha256: payload.body.sourceSha256,
      },
      allocationBaseline: () => S.allocationBaseline,
    };
  }

  async function boot() {
    window.clothLab = { ready: false };
    const result = await WebAssembly.instantiate(decode(payload.wasm), {});
    S.wasm = result.instance.exports;
    for (const [key, method] of [
      ["positions", "body_ptr"],
      ["normals", "body_normal_ptr"],
      ["indices", "body_face_ptr"],
      ["order", "body_order_ptr"],
      ["nodes", "body_node_ptr"],
    ])
      copyTo(S.wasm[method](), decode(payload.body[key]));
    S.wasm.configure_body(
      payload.body.vertices,
      payload.body.triangles,
      payload.body.nodeCount,
    );
    await setupScene();
    const saved = JSON.parse($("initial-state").textContent);
    if (saved) restore(saved);
    else setupCloth();
    wireUI();
    document.querySelector(".chip")?.remove();
    const badge = document.createElement("span");
    badge.className = "chip";
    badge.textContent = "WASM 已加载 · 离线可运行";
    document.querySelector(".header-right").prepend(badge);

    // Publish readiness only after the selected backend has completed its first
    // render of the actual initial or restored cloth.
    await firstRender();
    const status = rendererDiagnostics();
    if (
      S.renderBlocked ||
      S.renderPending ||
      status.blocked ||
      !status.initialized ||
      !status.firstRenderComplete ||
      !["WebGPU", "WebGL2"].includes(status.api)
    )
      throw new Error("Renderer did not complete initialization");
    window.clothLab = publicAPI();
    S.allocationBaseline = performanceLog();
    requestAnimationFrame(animate);
  }

  function reportInitializationError(error) {
    S.renderBlocked = true;
    S.renderPending = false;
    S.renderError = String(error);
    S.running = false;
    S.playing = false;
    if (window.clothLab) window.clothLab.ready = false;
    updateReplayUI();
    window.clothLabError = String(error);
    $("verdict").textContent = "BLOCKED · 初始化失败";
    $("verdict").className = "fail";
    $("activity").textContent = String(error);
    const p = document.createElement("p");
    p.className = "fatal";
    p.textContent = String(error);
    $("viewport").appendChild(p);
    console.error(error);
  }

  return { boot, reportInitializationError };
}
