/**
 * Share mutable state across controllers, including replaced typed-array views
 * and replay tracks. Capture the original HTML before any UI initialization.
 */
export function createRuntimeContext() {
  const $ = (id) => document.getElementById(id);
  const payload = JSON.parse($("payload").textContent);
  const originalHTML = "<!doctype html>\n" + document.documentElement.outerHTML;
  const decode = (b64) => Uint8Array.from(atob(b64), (c) => c.charCodeAt(0));
  const N = 16,
    M = 24,
    K = (N + 1) * (M + 1),
    NV = 2 * K,
    NT = 4 * N * M;

  return {
    $,
    payload,
    originalHTML,
    decode,
    N,
    M,
    K,
    NV,
    NT,
    idx: (p, i, j) => p * K + j * (N + 1) + i,
    materials: {
      woven: {
        Eu: 200000,
        Ev: 120000,
        G: 30000,
        nu: 0.2,
        thickness: 0.0005,
        density: 0.22,
      },
      soft: {
        Eu: 45000,
        Ev: 25000,
        G: 6000,
        nu: 0.2,
        thickness: 0.0005,
        density: 0.18,
      },
    },
    REFERENCE_STEPS: 240,
    wasm: undefined,
    positions: undefined,
    previous: undefined,
    restUV: undefined,
    triangles: undefined,
    fields: undefined,
    invMass: undefined,
    bodyDistances: undefined,
    scene: undefined,
    camera: undefined,
    renderer: undefined,
    cloth: undefined,
    clothGeometry: undefined,
    bodyMesh: undefined,
    seamLines: undefined,
    texture: undefined,
    cameraAngle: 0.36,
    cameraElevation: 0.1,
    cameraDistance: 2.8,
    drag: null,
    seamMap: [],
    parameters: undefined,
    mode: "fabric",
    renderBlocked: false,
    renderPending: false,
    renderError: "",
    pressureCalibrating: false,
    running: false,
    busy: false,
    stepMs: 0,
    frameTimes: [],
    history: [],
    lastStats: {},
    lastDraw: 0,
    droppedSeconds: 0,
    accumulator: 0,
    lastAnalyze: 0,
    gpuString: "",
    rendererClass: "unknown",
    allocationBaseline: undefined,
    track: { frames: [], cursor: -1, atRecordedState: false },
    recording: false,
    playing: false,
    replayElapsed: 0,
    integratedSteps: 0,
    captureTimes: [],
    seekTimes: [],
    playbackTimes: [],
    recordingNote: "尚未录制。",
  };
}

/** Keep graphical failure and backend switching separate from file-import busy. */
export function requireRendererAvailable(S) {
  if (S.renderBlocked)
    throw new Error("Renderer is blocked: " + (S.renderError || "unavailable"));
  if (S.renderPending) throw new Error("Renderer backend is switching");
}
