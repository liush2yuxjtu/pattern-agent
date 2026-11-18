import { solvePressureCoupon } from "./pressure.js";

/** Bind DOM controls to the simulation, replay, rendering and file operations. */
export function createControls(
  S,
  {
    setRunning,
    startRecording,
    stopRecording,
    seekFrame,
    playReplay,
    download,
    project,
    importReplay,
    setupCloth,
    takeSteps,
    stateChanged,
    analyze,
    draw,
    advance,
    applyMode,
    updateCamera,
    patternSVG,
    sceneOBJ,
    performanceLog,
    saveHTML,
    updateReplayUI,
  },
) {
  const { $, payload, decode, REFERENCE_STEPS } = S;
  const whenAvailable =
    (handler) =>
    (...args) => {
      if (S.renderBlocked || S.renderPending) return;
      return handler(...args);
    };
  function wireUI() {
    $("pressure-calibrate").onclick = async () => {
      const b = $("pressure-calibrate");
      S.pressureCalibrating = true;
      b.disabled = true;
      try {
        setRunning(false);
        const q = await solvePressureCoupon(decode(payload.wasm), {
            loadPa: 1000,
          }),
          free = await solvePressureCoupon(decode(payload.wasm), {
            loadPa: 0.22 * 9.81,
            detached: true,
            steps: 4,
          });
        const mean =
          q.totalNormalForceN / q.nodalAreaM2.reduce((a, b) => a + b, 0);
        if (
          Math.abs(mean - 1000) > 1 ||
          Math.abs(q.totalNormalForceN - 40) > 0.04 ||
          free.totalNormalForceN !== 0
        )
          throw new Error("Known-load pressure check failed");
        $("pressure-coupon").textContent =
          `载荷校验通过：${(mean / 1000).toFixed(3)} kPa · ${q.totalNormalForceN.toFixed(3)} N；悬空 ${free.totalNormalForceN.toFixed(3)} N`;
      } catch (e) {
        $("pressure-coupon").textContent = "FAIL · " + e.message;
      } finally {
        S.pressureCalibrating = false;
        b.disabled = S.renderBlocked || S.renderPending;
      }
    };
    $("record-start").onclick = startRecording;
    $("record-stop").onclick = stopRecording;
    $("replay-timeline").oninput = (e) => seekFrame(+e.target.value);
    $("replay-first").onclick = () => seekFrame(0);
    $("replay-last").onclick = () => seekFrame(S.track.frames.length - 1);
    $("replay-prev").onclick = () => seekFrame(Math.max(0, S.track.cursor - 1));
    $("replay-next").onclick = () =>
      seekFrame(Math.min(S.track.frames.length - 1, S.track.cursor + 1));
    $("replay-play").onclick = playReplay;
    $("export-replay").onclick = () =>
      download("cloth-replay.json", JSON.stringify(project()));
    $("import-replay").onchange = importReplay;
    updateReplayUI();
    for (const id of ["width", "length", "material", "fault"])
      $(id).addEventListener("input", () => {
        if (!S.busy && !S.renderBlocked && !S.renderPending) setupCloth();
      });
    $("body-shift").addEventListener("input", () => {
      if (S.renderBlocked || S.renderPending) return;
      S.parameters.bodyOffsetMm = +$("body-shift").value;
      $("shift-value").value = S.parameters.bodyOffsetMm + " mm";
      S.wasm.set_body_offset(S.parameters.bodyOffsetMm / 1000);
      S.bodyMesh.position.x = S.parameters.bodyOffsetMm / 1000;
      if (S.parameters.collision && S.parameters.fault === "good") {
        setRunning(false);
        takeSteps(REFERENCE_STEPS);
        $("activity").textContent = "人体移动后已重新完成物理试衣。";
      } else stateChanged();
      analyze();
      draw();
    });
    $("collision").onchange = () => {
      S.parameters.collision = $("collision").checked;
      S.wasm.set_collision(+S.parameters.collision);
      stateChanged();
      analyze();
      draw();
    };
    $("wind").onchange = () => {
      S.parameters.wind = $("wind").checked;
      S.wasm.pressure_restore(0);
      stateChanged();
      analyze();
      draw();
    };
    $("run").onclick = () => {
      if (!S.busy) setRunning(!S.running);
    };
    $("single-step").onclick = () => advance(1);
    $("settle").onclick = () => advance(240);
    $("reset").onclick = () => {
      if (!S.busy) setupCloth();
    };
    for (const b of document.querySelectorAll("[data-mode]"))
      b.onclick = () => applyMode(b.dataset.mode);
    for (const b of document.querySelectorAll("[data-camera]"))
      b.onclick = () => {
        S.cameraAngle = { front: 0, side: Math.PI / 2, back: Math.PI }[
          b.dataset.camera
        ];
        updateCamera();
        draw();
      };
    $("export-svg").onclick = () =>
      download("cloth-patterns.svg", patternSVG(), "image/svg+xml");
    $("export-obj").onclick = () =>
      download("cloth-body-scene.obj", sceneOBJ(), "text/plain");
    $("export-json").onclick = () =>
      download("cloth-project.json", JSON.stringify(project()));
    $("export-log").onclick = () =>
      download(
        "cloth-diagnostics.json",
        JSON.stringify(performanceLog(), null, 2),
      );
    $("save-html")?.remove();
    const button = document.createElement("button");
    button.id = "save-html";
    button.textContent = "当前状态单文件 HTML ↓";
    button.style.gridColumn = "1 / -1";
    button.onclick = saveHTML;
    document.querySelector(".export-grid").appendChild(button);

    // Disabled DOM controls cannot be clicked normally; this also protects the
    // handler boundary from synthetic events while graphics are unavailable.
    for (const id of [
      "pressure-calibrate",
      "record-start",
      "record-stop",
      "replay-timeline",
      "replay-first",
      "replay-prev",
      "replay-next",
      "replay-last",
      "replay-play",
      "import-replay",
      "collision",
      "wind",
      "run",
      "single-step",
      "settle",
      "reset",
    ]) {
      const element = $(id);
      for (const event of ["onclick", "oninput", "onchange"])
        if (element[event]) element[event] = whenAvailable(element[event]);
    }
    for (const button of document.querySelectorAll("[data-mode],[data-camera]"))
      button.onclick = whenAvailable(button.onclick);
  }
  return { wireUI };
}
