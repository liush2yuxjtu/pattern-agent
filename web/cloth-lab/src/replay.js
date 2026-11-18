import { MAX_FRAMES, STATE_FLOATS, MAX_TOTAL_RAW_BYTES } from "./trajectory.js";
import { capturePressure, restorePressure } from "./contact-state.js";
import { requireRendererAvailable } from "./runtime-context.js";

/** Capture and restore complete physical frames without integrating on replay. */
export function createReplay(S, { floatView, setRunning, analyze, draw }) {
  const { $, payload, NV, NT } = S;
  function updateReplayUI() {
    if (!$("replay-status")) return;
    const unavailable = S.renderBlocked || S.renderPending;
    const locked = S.busy || unavailable;
    const count = S.track.frames.length,
      f = S.track.frames[S.track.cursor],
      first = S.track.frames[0],
      last = S.track.frames.at(-1);
    const totalBytes = S.track.frames.reduce(
      (sum, f) => sum + f.state.byteLength + f.pressureState.samples.byteLength,
      0,
    );
    $("replay-status").textContent =
      `${S.renderBlocked ? "BLOCKED · 图形后端不可用" : S.renderPending ? "图形后端切换中" : S.recording ? "● 录制中" : S.playing ? "▶ 回放中" : S.track.atRecordedState ? "录制状态" : "实时状态"} · ${count} 帧 · ${(totalBytes / 1048576).toFixed(2)} MiB`;
    $("replay-time").value = f
      ? `${S.track.cursor + 1} / ${count} · ${(f.time - first.time).toFixed(3)} / ${(last.time - first.time).toFixed(3)} s · 物理步 ${f.frame}`
      : "0 / 0";
    $("replay-note").textContent = S.recordingNote;
    const slider = $("replay-timeline");
    slider.max = Math.max(0, count - 1);
    slider.value = Math.max(0, S.track.cursor);
    slider.disabled = !count || locked;
    $("record-start").textContent = count ? "重新录制" : "开始录制";
    $("record-start").disabled = locked || S.recording;
    $("record-stop").disabled = locked || !S.recording;
    $("replay-play").textContent = S.playing ? "暂停回放" : "播放回放";
    $("replay-play").disabled = locked || S.recording || count < 2;
    for (const id of [
      "replay-first",
      "replay-prev",
      "replay-next",
      "replay-last",
    ])
      $(id).disabled = locked || !count;
    $("export-replay").disabled = S.busy || !count;
    $("import-replay").disabled = locked || S.recording || S.playing;
    $("replay-speed").disabled = unavailable;
    $("run").textContent = S.running ? "暂停仿真" : "开始仿真";
    for (const id of [
      "width",
      "length",
      "material",
      "fault",
      "body-shift",
      "collision",
      "wind",
      "single-step",
      "settle",
      "reset",
      "run",
    ])
      $(id).disabled = locked || S.playing;
    for (const button of document.querySelectorAll("[data-mode],[data-camera]"))
      button.disabled = unavailable;
    $("pressure-calibrate").disabled = unavailable || S.pressureCalibrating;
  }

  function captureFrame(kind) {
    if (!S.recording) return;
    const start = performance.now(),
      state = new Float32Array(STATE_FLOATS);
    state.set(S.positions);
    state.set(S.previous, NV * 3);
    state.set(floatView(S.wasm.pin_ptr(), NV * 3), NV * 6);
    state.set(floatView(S.wasm.contacts_ptr(), NV), NV * 9);
    S.track.frames.push({
      state,
      frame: S.wasm.get_frame(),
      time: S.wasm.get_time(),
      parameters: { ...S.parameters, lengthsMm: [...S.parameters.lengthsMm] },
      stepMs: S.stepMs,
      kind,
      pressureState: capturePressure(S.wasm, NV, NT),
    });
    S.track.cursor = S.track.frames.length - 1;
    S.track.atRecordedState = true;
    S.captureTimes.push(performance.now() - start);
    if (S.captureTimes.length > MAX_FRAMES) S.captureTimes.shift();
    if (S.track.frames.length === MAX_FRAMES) {
      S.recording = false;
      S.recordingNote = "已达 1,201 帧上限，自动停止录制；已有轨迹完整保留。";
    }
  }

  function startRecording() {
    requireRendererAvailable(S);
    if (S.busy) throw new Error("Simulation busy");
    S.playing = false;
    setRunning(false);
    S.track = { frames: [], cursor: -1, atRecordedState: false };
    S.captureTimes = [];
    S.recording = true;
    S.recordingNote =
      "每个 1/120 s 物理步保存一次；人体移动、碰撞／风开关另存事件帧。接触压力随帧保存；最多 1,201 帧。";
    captureFrame("start");
    updateReplayUI();
  }

  function stopRecording() {
    S.recording = false;
    updateReplayUI();
  }

  function applyFrame(f) {
    requireRendererAvailable(S);
    S.parameters = { ...f.parameters, lengthsMm: [...f.parameters.lengthsMm] };
    $("body-shift").value = S.parameters.bodyOffsetMm;
    $("shift-value").value = S.parameters.bodyOffsetMm + " mm";
    $("collision").checked = S.parameters.collision;
    $("wind").checked = S.parameters.wind;
    S.wasm.set_body_offset(S.parameters.bodyOffsetMm / 1000);
    S.bodyMesh.position.x = S.parameters.bodyOffsetMm / 1000;
    S.wasm.set_collision(+S.parameters.collision);
    S.positions.set(f.state.subarray(0, NV * 3));
    S.previous.set(f.state.subarray(NV * 3, NV * 6));
    floatView(S.wasm.pin_ptr(), NV * 3).set(f.state.subarray(NV * 6, NV * 9));
    floatView(S.wasm.contacts_ptr(), NV).set(f.state.subarray(NV * 9));
    S.wasm.set_clock(f.frame, f.time);
    restorePressure(S.wasm, f.pressureState);
    floatView(S.wasm.contacts_ptr(), NV).set(f.state.subarray(NV * 9));
    S.stepMs = f.stepMs;
    analyze();
    draw();
  }

  function seekFrame(index, keepPlaying = false) {
    requireRendererAvailable(S);
    if (S.busy) throw new Error("Simulation busy");
    if (!Number.isInteger(index) || index < 0 || index >= S.track.frames.length)
      throw new Error("Invalid replay index");
    const start = performance.now();
    S.recording = false;
    if (!keepPlaying) S.playing = false;
    setRunning(false);
    applyFrame(S.track.frames[index]);
    S.track.cursor = index;
    S.track.atRecordedState = true;
    $("activity").textContent =
      `回放帧 ${index + 1} / ${S.track.frames.length} · ${S.lastStats.simulationSeconds.toFixed(3)} s；未进行物理积分。`;
    S.seekTimes.push(performance.now() - start);
    if (S.seekTimes.length > 600) S.seekTimes.shift();
    updateReplayUI();
    return { ...S.lastStats };
  }

  function playReplay() {
    requireRendererAvailable(S);
    if (S.busy || S.recording || S.track.frames.length < 2) return;
    if (S.playing) {
      S.playing = false;
      updateReplayUI();
      return;
    }
    if (
      !S.track.atRecordedState ||
      S.track.cursor === S.track.frames.length - 1
    )
      seekFrame(0);
    setRunning(false);
    S.playing = true;
    S.replayElapsed =
      S.track.frames[S.track.cursor].time - S.track.frames[0].time;
    updateReplayUI();
  }

  function replayTick(elapsed) {
    const start = performance.now(),
      frames = S.track.frames,
      origin = frames[0].time;
    S.replayElapsed += elapsed * Number($("replay-speed").value);
    let next = S.track.cursor;
    while (
      next + 1 < frames.length &&
      frames[next + 1].time - origin <= S.replayElapsed + 1e-7
    )
      next++;
    if (next !== S.track.cursor) seekFrame(next, true);
    if (next === frames.length - 1) {
      S.playing = false;
      updateReplayUI();
    }
    S.playbackTimes.push(performance.now() - start);
    if (S.playbackTimes.length > 600) S.playbackTimes.shift();
  }

  function replayInfo() {
    const pressureBytes = S.track.frames.reduce(
      (sum, f) => sum + f.pressureState.samples.byteLength,
      0,
    );
    return {
      pressureBytes,
      totalBytes: S.track.frames.length * STATE_FLOATS * 4 + pressureBytes,
      maxTotalRawBytes: MAX_TOTAL_RAW_BYTES,
      frames: S.track.frames.length,
      cursor: S.track.cursor,
      atRecordedState: S.track.atRecordedState,
      recording: S.recording,
      playing: S.playing,
      speed: Number($("replay-speed").value),
      maxFrames: MAX_FRAMES,
      bytes: S.track.frames.length * STATE_FLOATS * 4,
      integratedSteps: S.integratedSteps,
      captureTimesMs: [...S.captureTimes],
      seekTimesMs: [...S.seekTimes],
      playbackTimesMs: [...S.playbackTimes],
    };
  }

  function stateChanged(kind = "settings") {
    S.playing = false;
    S.track.atRecordedState = false;
    captureFrame(kind);
    updateReplayUI();
  }

  return {
    updateReplayUI,
    captureFrame,
    startRecording,
    stopRecording,
    applyFrame,
    seekFrame,
    playReplay,
    replayTick,
    replayInfo,
    stateChanged,
  };
}
