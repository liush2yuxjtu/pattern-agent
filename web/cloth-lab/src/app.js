import { createRuntimeContext } from "./runtime-context.js";
import { createRendering } from "./rendering.js";
import { createSimulation } from "./simulation.js";
import { createDiagnostics } from "./diagnostics.js";
import { createReplay } from "./replay.js";
import { createPersistence } from "./persistence.js";
import { createControls } from "./controls.js";
import { createLifecycle } from "./lifecycle.js";

const S = createRuntimeContext();

// Factories capture callbacks without running them. Controllers can therefore
// call one another without circular module imports.
const rendering = createRendering(S, {
  floatView: (...args) => simulation.floatView(...args),
  onAvailabilityChange: () => replay.updateReplayUI(),
});
const simulation = createSimulation(S, {
  captureFrame: (...args) => replay.captureFrame(...args),
  updateReplayUI: () => replay.updateReplayUI(),
  setupClothSurface: rendering.setupClothSurface,
  applyMode: rendering.applyMode,
  analyze: () => diagnostics.analyze(),
  draw: rendering.draw,
});
const replay = createReplay(S, {
  floatView: simulation.floatView,
  setRunning: simulation.setRunning,
  analyze: () => diagnostics.analyze(),
  draw: rendering.draw,
});
const diagnostics = createDiagnostics(S, {
  floatView: simulation.floatView,
  sideLength: simulation.sideLength,
  replayInfo: replay.replayInfo,
  performanceInfo: rendering.performanceInfo,
});
const persistence = createPersistence(S, {
  floatView: simulation.floatView,
  intView: simulation.intView,
  material: simulation.material,
  analyze: diagnostics.analyze,
  setupCloth: simulation.setupCloth,
  applyFrame: replay.applyFrame,
  applyMode: rendering.applyMode,
  updateReplayUI: replay.updateReplayUI,
  setRunning: simulation.setRunning,
});
const controls = createControls(S, {
  ...simulation,
  ...replay,
  ...diagnostics,
  ...persistence,
  ...rendering,
});
const lifecycle = createLifecycle(S, {
  ...simulation,
  ...replay,
  ...diagnostics,
  ...persistence,
  ...rendering,
  ...controls,
});

lifecycle.boot().catch(lifecycle.reportInitializationError);
