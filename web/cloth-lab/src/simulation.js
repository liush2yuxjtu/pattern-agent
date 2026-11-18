import { sector, patternSVG as sectorSVG } from "./pattern.js";
import avatarFit from "./avatar-fit.json";
import { requireRendererAvailable } from "./runtime-context.js";

/** Configure the cloth and advance its unchanged WASM solver. */
export function createSimulation(
  S,
  { captureFrame, updateReplayUI, setupClothSurface, applyMode, analyze, draw },
) {
  const { $, materials, N, M, K, NV, NT, idx, REFERENCE_STEPS } = S;
  function getParameters() {
    return {
      patternType: "anatomical-sector",
      bottomMm: +$("width").value,
      topMm: avatarFit.topsMm[0],
      topsMm: [...avatarFit.topsMm],
      lengthsMm: [
        +$("length").value,
        +$("length").value + ($("fault").value === "mismatch" ? 40 : 0),
      ],
      fault: $("fault").value,
      material: $("material").value,
      bodyOffsetMm: +$("body-shift").value,
      collision: $("collision").checked,
      wind: $("wind").checked,
    };
  }

  function material() {
    return materials[S.parameters.material];
  }

  function copyTo(ptr, bytes) {
    new Uint8Array(S.wasm.memory.buffer, ptr, bytes.length).set(bytes);
  }

  function floatView(ptr, n) {
    return new Float32Array(S.wasm.memory.buffer, ptr, n);
  }

  function intView(ptr, n) {
    return new Int32Array(S.wasm.memory.buffer, ptr, n);
  }

  function setRunning(value) {
    if (value) requireRendererAvailable(S);
    if (value) S.playing = false;
    S.running = value;
    $("run").textContent = S.running ? "暂停仿真" : "开始仿真";
    S.accumulator = 0;
    updateReplayUI();
  }

  function sideLength(p) {
    return S.parameters.lengthsMm[p];
  }

  function setupCloth(drape = true) {
    requireRendererAvailable(S);
    S.recording = false;
    S.playing = false;
    S.track = { frames: [], cursor: -1, atRecordedState: false };
    S.recordingNote = "重置或修改纸样／材料会清空旧录制。";
    S.parameters = getParameters();
    setRunning(false);
    S.history = [];
    S.droppedSeconds = 0;
    const mat = material();
    S.wasm.configure_material(
      mat.Eu,
      mat.Ev,
      mat.G,
      mat.nu,
      mat.thickness,
      mat.density,
    );
    S.positions = floatView(S.wasm.position_ptr(), NV * 3);
    S.previous = floatView(S.wasm.previous_ptr(), NV * 3);
    S.restUV = floatView(S.wasm.uv_ptr(), NV * 2);
    S.triangles = intView(S.wasm.face_ptr(), NT * 3);
    S.fields = floatView(S.wasm.field_ptr(), NT * 8);
    S.invMass = floatView(S.wasm.invmass_ptr(), NV);
    S.bodyDistances = floatView(S.wasm.body_distance_ptr(), NV);
    const rTop =
        (S.parameters.topsMm[0] + S.parameters.topsMm[1]) /
        1000 /
        (2 * Math.PI),
      rBottom = S.parameters.bottomMm / 1000 / Math.PI;
    let faceIndex = 0;
    for (let p = 0; p < 2; p++)
      for (let j = 0; j <= M; j++)
        for (let i = 0; i <= N; i++) {
          const k = idx(p, i, j),
            ratio = j / M,
            L = S.parameters.lengthsMm[p] / 1000,
            a = ((p * N + i) / (2 * N)) * 2 * Math.PI;
          const height = Math.sqrt(L * L - (rBottom - rTop) ** 2),
            flat = sector(
              S.parameters.topsMm[p],
              S.parameters.bottomMm,
              S.parameters.lengthsMm[p],
            ).at(i / N, ratio);
          const waist = avatarFit.waistPanelsM[p][i],
            hemY = avatarFit.waistHeightM - height;
          S.positions.set(
            [
              (1 - ratio) * waist[0] +
                ratio * (avatarFit.hemCenterM[0] + rBottom * Math.cos(a)),
              (1 - ratio) * waist[1] + ratio * hemY,
              (1 - ratio) * waist[2] +
                ratio * (avatarFit.hemCenterM[1] + rBottom * Math.sin(a)),
            ],
            3 * k,
          );
          S.restUV.set(
            flat.map((v) => v / 1000),
            2 * k,
          );
          if (i < N && j < M) {
            const a = k,
              b = k + 1,
              c = k + N + 1,
              d = c + 1;
            S.triangles.set([a, b, c, b, d, c], faceIndex);
            faceIndex += 6;
          }
        }
    S.wasm.configure_cloth(NV, NT);
    for (let p = 0; p < 2; p++)
      for (let i = 0; i <= N; i++) S.wasm.set_pin(idx(p, i, 0));
    S.seamMap = [];
    for (let j = 0; j <= M; j++) {
      S.seamMap.push({
        name: "S1",
        a: idx(0, N, j),
        b: idx(1, 0, j),
        active: true,
      });
      S.seamMap.push({
        name: "S2",
        a: idx(0, 0, j),
        b: idx(1, N, S.parameters.fault === "reverse" ? M - j : j),
        active: S.parameters.fault !== "open",
      });
    }
    for (const s of S.seamMap) S.wasm.add_seam(s.a, s.b, +s.active);
    S.wasm.finalize_seams();
    for (let p = 0; p < 2; p++)
      for (let j = 0; j <= M; j++)
        for (let i = 0; i <= N; i++) {
          const k = idx(p, i, j);
          for (const end of [
            i < N - 1 ? idx(p, i + 2, j) : -1,
            j < M - 1 ? idx(p, i, j + 2) : -1,
          ])
            if (end >= 0) {
              const d = Math.hypot(
                S.restUV[2 * k] - S.restUV[2 * end],
                S.restUV[2 * k + 1] - S.restUV[2 * end + 1],
              );
              S.wasm.add_bend(k, end, d);
            }
        }
    S.wasm.set_collision(+S.parameters.collision);
    S.wasm.set_body_offset(S.parameters.bodyOffsetMm / 1000);
    S.bodyMesh.position.x = S.parameters.bodyOffsetMm / 1000;
    setupClothSurface();
    $("width-value").value = S.parameters.bottomMm + " mm";
    $("length-value").value = S.parameters.lengthsMm[0] + " mm";
    $("shift-value").value = S.parameters.bodyOffsetMm + " mm";
    $("material-values").textContent =
      `E经 ${mat.Eu / 1000} kPa · E纬 ${mat.Ev / 1000} kPa · G ${mat.G / 1000} kPa · ν ${mat.nu}\n厚 ${mat.thickness * 1000} mm · ${mat.density * 1000} g/m²。合成参数，未经标定。`;
    $("patterns").innerHTML = patternSVG();
    $("waist-fit-info").textContent =
      `真实高腰截面 ${avatarFit.bodySectionGirthMm.toFixed(1)} mm · 裙腰 ${(S.parameters.topsMm[0] + S.parameters.topsMm[1]).toFixed(1)} mm\n前腰 ${S.parameters.topsMm[0].toFixed(1)} / 后腰 ${S.parameters.topsMm[1].toFixed(1)} mm · 7 mm 装配间隙`;
    if (drape) {
      if (S.parameters.collision && S.parameters.fault === "good") {
        const t = performance.now();
        S.wasm.step(REFERENCE_STEPS, S.parameters.wind ? 0.8 : 0);
        S.integratedSteps += REFERENCE_STEPS;
        S.stepMs = (performance.now() - t) / REFERENCE_STEPS;
      }
      $("activity").textContent =
        S.parameters.fault === "good"
          ? "已完成初始物理试衣；可单步、录制或运行。"
          : "故障对照：请查看缝合、覆盖与碰撞检查。";
      applyMode(S.mode);
      analyze();
      draw();
    }
  }

  function patternSVG() {
    return sectorSVG(S.parameters);
  }

  function takeSteps(n) {
    requireRendererAvailable(S);
    S.track.atRecordedState = false;
    if (S.recording) {
      let kernelMs = 0;
      for (let i = 0; i < n; i++) {
        S.track.atRecordedState = false;
        const t = performance.now();
        S.wasm.step(1, S.parameters.wind ? 0.8 : 0);
        S.integratedSteps++;
        S.stepMs = performance.now() - t;
        kernelMs += S.stepMs;
        captureFrame("step");
      }
      S.stepMs = kernelMs / n;
    } else {
      const t = performance.now();
      S.wasm.step(n, S.parameters.wind ? 0.8 : 0);
      S.integratedSteps += n;
      S.stepMs = (performance.now() - t) / Math.max(n, 1);
    }
  }

  async function advance(n) {
    requireRendererAvailable(S);
    if (S.busy) throw new Error("A simulation operation is already running");
    if (!Number.isInteger(n) || n < 0 || n > 12000)
      throw new Error("Invalid step count");
    S.playing = false;
    setRunning(false);
    S.busy = true;
    updateReplayUI();
    $("activity").textContent = "正在推进固定时间步…";
    try {
      for (let k = 0; k < n; k += 20) {
        takeSteps(Math.min(20, n - k));
        await new Promise(requestAnimationFrame);
      }
      analyze();
      draw();
      $("activity").textContent = `已完成 ${n} 步；检查结果见右侧。`;
      return { ...S.lastStats };
    } finally {
      S.busy = false;
      updateReplayUI();
    }
  }

  return {
    getParameters,
    material,
    copyTo,
    floatView,
    intView,
    setRunning,
    sideLength,
    setupCloth,
    patternSVG,
    takeSteps,
    advance,
  };
}
