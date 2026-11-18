import {
  STATE_FLOATS,
  validateParameters,
  encodeTrajectory,
  decodeTrajectory,
  encodePressure,
  decodePressure,
} from "./trajectory.js";
import { pressureData } from "./contact-state.js";
import { requireRendererAvailable } from "./runtime-context.js";

/** Validate and restore projects, and export state, geometry and offline HTML. */
export function createPersistence(
  S,
  {
    floatView,
    intView,
    material,
    analyze,
    setupCloth,
    applyFrame,
    applyMode,
    updateReplayUI,
    setRunning,
  },
) {
  const { $, payload, originalHTML, N, M, NV, NT, REFERENCE_STEPS } = S;
  function download(name, text, type = "application/json") {
    const url = URL.createObjectURL(new Blob([text], { type })),
      a = document.createElement("a");
    a.href = url;
    a.download = name;
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  function project(includeReplay = true) {
    analyze();
    const pressure = pressureData(S.wasm, NV, NT);
    return {
      schema: "pattern-agent.cloth-lab.v3",
      fingerprint: payload.buildFingerprint,
      units: { pattern: "mm", geometry: "m", stress: "Pa", pressure: "Pa" },
      parameters: { ...S.parameters },
      material: { ...material(), calibration: "synthetic-not-measured" },
      grid: [N, M],
      positions: Array.from(S.positions),
      previous: Array.from(S.previous),
      pinPositions: Array.from(floatView(S.wasm.pin_ptr(), NV * 3)),
      contactFlags: Array.from(floatView(S.wasm.contacts_ptr(), NV)),
      pressureState: encodePressure(pressure.packet),
      fitPressure: pressure.fields,
      pressureContacts: pressure.contacts,
      replay:
        includeReplay && S.track.frames.length
          ? encodeTrajectory(S.track, payload.buildFingerprint)
          : undefined,
      restUV: Array.from(S.restUV),
      triangles: Array.from(S.triangles),
      seams: S.seamMap,
      triangleFields: Array.from(S.fields),
      fieldOrder: [
        "principalEngineeringStrain",
        "warpEngineeringStrain",
        "weftEngineeringStrain",
        "maxPrincipalCauchyPa",
        "vonMisesPa",
        "GreenE11",
        "GreenE22",
        "GreenE12",
      ],
      body: {
        positions: Array.from(
          floatView(S.wasm.body_ptr(), payload.body.vertices * 3),
        ),
        triangles: Array.from(
          intView(S.wasm.body_face_ptr(), payload.body.triangles * 3),
        ),
        offsetX: S.parameters.bodyOffsetMm / 1000,
        sourceSha256: payload.body.sourceSha256,
        license: "CC0-1.0",
      },
      mode: S.mode,
      diagnostics: { ...S.lastStats },
      initialReferenceSteps: REFERENCE_STEPS,
      limitations: [
        "synthetic material and normal interface",
        "rigid body",
        "no cloth self collision",
        "no CCD",
        "approximate distance bending",
        "not manufacturing approval",
      ],
    };
  }

  function restore(data) {
    requireRendererAvailable(S);
    if (S.busy) throw new Error("Simulation busy");
    if (
      data.schema !== "pattern-agent.cloth-lab.v3" ||
      data.fingerprint !== payload.buildFingerprint
    )
      throw new Error("Incompatible project or source fingerprint");
    const p = validateParameters(data.parameters),
      savedPressure = decodePressure(data.pressureState);
    for (const key of ["positions", "previous", "pinPositions"])
      if (
        data[key]?.length !== NV * 3 ||
        !data[key].every((v) => Number.isFinite(v) && Math.abs(v) < 10)
      )
        throw new Error("Invalid saved vertex array");
    if (
      data.contactFlags &&
      (data.contactFlags.length !== NV ||
        !data.contactFlags.every((v) => v === 0 || v === 1))
    )
      throw new Error("Invalid saved contact array");
    if (
      !Number.isInteger(data.diagnostics?.frame) ||
      data.diagnostics.frame < 0 ||
      data.diagnostics.frame > 1e7 ||
      !Number.isFinite(data.diagnostics.simulationSeconds) ||
      data.diagnostics.simulationSeconds < 0 ||
      data.diagnostics.simulationSeconds > 1e6
    )
      throw new Error("Invalid saved clock");
    if (
      data.mode &&
      !["fabric", "strain", "stress", "contact", "pressure"].includes(data.mode)
    )
      throw new Error("Invalid saved view");
    const decoded = data.replay
      ? decodeTrajectory(data.replay, payload.buildFingerprint, p)
      : { frames: [], cursor: -1, atRecordedState: false };
    if (decoded.atRecordedState) {
      const f = decoded.frames[decoded.cursor];
      if (
        !f ||
        f.pressureState.valid !== savedPressure.valid ||
        f.pressureState.samples.length !== savedPressure.samples.length ||
        !f.pressureState.samples.every(
          (v, i) => v === savedPressure.samples[i],
        ) ||
        f.frame !== data.diagnostics.frame ||
        f.time !== data.diagnostics.simulationSeconds ||
        JSON.stringify(f.parameters) !== JSON.stringify(p) ||
        !f.state.subarray(0, NV * 3).every((v, i) => v === data.positions[i]) ||
        !f.state
          .subarray(NV * 3, NV * 6)
          .every((v, i) => v === data.previous[i]) ||
        !f.state
          .subarray(NV * 6, NV * 9)
          .every((v, i) => v === data.pinPositions[i]) ||
        !f.state
          .subarray(NV * 9)
          .every((v, i) => v === (data.contactFlags?.[i] || 0))
      )
        throw new Error("Selected replay frame differs from saved state");
    }
    $("width").value = p.bottomMm;
    $("length").value = p.lengthsMm[0];
    $("fault").value = p.fault;
    $("material").value = p.material;
    $("collision").checked = p.collision;
    $("wind").checked = p.wind;
    $("body-shift").value = p.bodyOffsetMm;
    setupCloth(false);
    const state = new Float32Array(STATE_FLOATS);
    state.set(data.positions);
    state.set(data.previous, NV * 3);
    state.set(data.pinPositions, NV * 6);
    if (data.contactFlags) state.set(data.contactFlags, NV * 9);
    applyFrame({
      state,
      parameters: p,
      frame: data.diagnostics.frame,
      time: data.diagnostics.simulationSeconds,
      pressureState: savedPressure,
      stepMs: Math.max(0, data.diagnostics.stepMs || 0),
    });
    S.track = decoded;
    S.recordingNote = S.track.frames.length
      ? "已恢复完整录制；拖动时间轴可离线检查各帧。"
      : "已恢复单帧状态。";
    applyMode(data.mode || "fabric");
    updateReplayUI();
  }

  function sceneOBJ() {
    const lines = [
      "# Pattern Agent scene snapshot; units metres. Surface meshes, not 3D-print solids.",
      "o cloth",
    ];
    for (let i = 0; i < NV; i++)
      lines.push(
        `v ${S.positions[3 * i]} ${S.positions[3 * i + 1]} ${S.positions[3 * i + 2]}`,
      );
    for (let t = 0; t < NT; t++)
      lines.push(
        "f " + [0, 1, 2].map((j) => S.triangles[t * 3 + j] + 1).join(" "),
      );
    lines.push("o MakeHuman_CC0");
    const bv = floatView(S.wasm.body_ptr(), payload.body.vertices * 3),
      bf = intView(S.wasm.body_face_ptr(), payload.body.triangles * 3);
    for (let i = 0; i < payload.body.vertices; i++)
      lines.push(
        `v ${bv[3 * i] + S.parameters.bodyOffsetMm / 1000} ${bv[3 * i + 1]} ${bv[3 * i + 2]}`,
      );
    for (let t = 0; t < payload.body.triangles; t++)
      lines.push("f " + [0, 1, 2].map((j) => bf[3 * t + j] + NV + 1).join(" "));
    return lines.join("\n");
  }
  async function importReplay(e) {
    requireRendererAvailable(S);
    const file = e.target.files[0];
    if (!file || S.busy || S.recording || S.playing) return;
    setRunning(false);
    S.busy = true;
    updateReplayUI();
    $("activity").textContent = "正在读取录制文件；仿真已暂停。";
    try {
      if (file.size > 160 * 1048576)
        throw new Error("Recording file exceeds 160 MiB");
      const saved = JSON.parse(await file.text());
      // No event can interleave validation/restore in this synchronous section.
      S.busy = false;
      restore(saved);
      $("activity").textContent =
        `已导入 ${S.track.frames.length} 帧录制；仿真保持暂停。`;
    } catch (error) {
      S.recordingNote = "导入失败：" + error.message;
      $("activity").textContent = "导入失败；原工程已保留，仿真保持暂停。";
    } finally {
      S.busy = false;
      e.target.value = "";
      updateReplayUI();
    }
  }

  function saveHTML() {
    const html = originalHTML.replace(
      /<script id="initial-state" type="application\/json">[\s\S]*?<\/script>/,
      () =>
        `<script id="initial-state" type="application/json">${JSON.stringify(project()).replaceAll("<", "\\u003c")}</script>`,
    );
    download("cloth-lab-snapshot.html", html, "text/html");
  }
  return { download, project, restore, sceneOBJ, importReplay, saveHTML };
}
