import { pressureData } from "./contact-state.js";
import { wearDiagnostics } from "./wear.js";
import avatarFit from "./avatar-fit.json";

/** Analyze physical state, render verdicts, and collect performance evidence. */
export function createDiagnostics(
  S,
  { floatView, sideLength, replayInfo, performanceInfo },
) {
  const { $, payload, decode, N, M, K, NV, NT } = S;
  function topologyAudit() {
    let missing = false,
      orientationValid = true;
    for (const name of ["S1", "S2"]) {
      const pairs = S.seamMap.filter((s) => s.name === name),
        row = (k) => Math.floor((k % K) / (N + 1));
      missing ||= pairs.filter((s) => s.active).length !== M + 1;
      orientationValid &&= pairs
        .slice(1)
        .every(
          (s, i) =>
            (row(s.a) - row(pairs[i].a)) * (row(s.b) - row(pairs[i].b)) > 0,
        );
    }
    return {
      missingSeam: missing,
      orientationValid,
      lengthMismatchMm: Math.abs(sideLength(0) - sideLength(1)),
    };
  }

  function analyze() {
    S.wasm.analyze();
    const s = floatView(S.wasm.stats_ptr(), 16),
      topo = topologyAudit(),
      p = pressureData(S.wasm, NV, NT).summary,
      c = floatView(S.wasm.coverage_ptr(), 16);
    const coverage = {
      bodySamples: c[0],
      exposedSamples: c[1],
      maxDepthDeficitMm: c[2] * 1000,
      byView: { front: c[3], back: c[4], right: c[5], left: c[6] },
      covered: !!c[11],
    };
    S.lastStats = {
      wear: wearDiagnostics(
        S.positions,
        S.bodyDistances,
        S.parameters,
        avatarFit,
      ),
      frame: s[0],
      simulationSeconds: s[1],
      maxSeamGapMm: s[2] * 1000,
      maxBodyPenetrationMm: s[3] * 1000,
      minBodyClearanceMm: s[4] * 1000,
      maxPrincipalStrainPercent: s[5] * 100,
      maxPrincipalStressKPa: s[6] / 1000,
      contacts: s[7],
      finite: !!s[8] && S.positions.every(Number.isFinite),
      membraneEnergyJ: s[9],
      collisionEnabled: !!s[10],
      pressure: p,
      coverage,
      ...topo,
      stepMs: S.stepMs,
      bodyOffsetMm: S.parameters.bodyOffsetMm,
      droppedWallSeconds: S.droppedSeconds,
    };
    const fail =
      !S.lastStats.wear.fitted ||
      !S.lastStats.finite ||
      topo.missingSeam ||
      !topo.orientationValid ||
      topo.lengthMismatchMm > 1 ||
      S.lastStats.maxSeamGapMm > 2 ||
      S.lastStats.maxBodyPenetrationMm > 0.2 ||
      !coverage.covered ||
      (p.ready &&
        (!p.consistent ||
          !Number.isFinite(p.maxPressurePa) ||
          p.maxPressurePa < 0));
    const settled = s[0] >= 240;
    let text = fail
      ? "FAIL · 腰口、覆盖、缝合或碰撞未通过"
      : !S.parameters.collision
        ? "未验证 · 已关闭碰撞"
        : settled && p.ready
          ? "PASS · 腰口/缝合/覆盖/碰撞/压力"
          : "待验证 · 请推进试衣求解";
    const strainWarning =
      !fail && settled && S.lastStats.maxPrincipalStrainPercent > 20;
    if (strainWarning) text = "几何通过 · 局部应变偏大";
    if (S.renderBlocked) text = "BLOCKED · 图形后端不可用";
    else if (S.renderPending) text = "待验证 · 正在切换图形后端";
    $("verdict").textContent = text;
    $("verdict").className =
      S.renderBlocked || fail
        ? "fail"
        : S.renderPending ||
            !settled ||
            !S.parameters.collision ||
            strainWarning
          ? "pending"
          : "";
    const rows = [
      ["腰口最大离体间隙", S.lastStats.wear.maxWaistGapMm.toFixed(2) + " mm"],
      [
        "腰线定位偏差",
        S.lastStats.wear.maxWaistPlacementErrorMm.toFixed(3) + " mm",
      ],
      [
        "前/后腰纸样差",
        S.lastStats.wear.waistPatternMismatchMm.toFixed(3) + " mm",
      ],
      ["缝合长度差", topo.lengthMismatchMm.toFixed(2) + " mm"],
      [
        "方向 / 缺失",
        `${topo.orientationValid ? "同向" : "反向"} / ${topo.missingSeam ? "漏缝" : "完整"}`,
      ],
      ["最大接缝间隙", S.lastStats.maxSeamGapMm.toFixed(3) + " mm"],
      ["人体网格穿透", S.lastStats.maxBodyPenetrationMm.toFixed(3) + " mm"],
      ["最小人体距离", S.lastStats.minBodyClearanceMm.toFixed(2) + " mm"],
      ["最大主应变", S.lastStats.maxPrincipalStrainPercent.toFixed(2) + " %"],
      ["最大主柯西应力", S.lastStats.maxPrincipalStressKPa.toFixed(2) + " kPa"],
      ["接触点 / 总顶点", `${s[7]} / ${NV}`],
      ["臀部外露采样", `${coverage.exposedSamples} / ${coverage.bodySamples}`],
      [
        "峰值试衣压力",
        p.ready ? (p.maxPressurePa / 1000).toFixed(4) + " kPa" : "待求解",
      ],
      ["法向接触力", p.ready ? p.normalForceN.toFixed(4) + " N" : "待求解"],
    ];
    $("metrics").innerHTML = rows
      .map(([a, b]) => `<div><dt>${a}</dt><dd>${b}</dd></div>`)
      .join("");
    $("time").textContent = s[1].toFixed(2) + " s";
    $("solver-time").textContent = S.stepMs.toFixed(2) + " ms";
    if (S.history.at(-1)?.frame !== S.lastStats.frame) {
      S.history.push({ ...S.lastStats });
      if (S.history.length > 120) S.history.shift();
    }
    return { ...S.lastStats };
  }

  function performanceLog() {
    return {
      stats: { ...S.lastStats },
      frameTimesMs: [...S.frameTimes],
      history: [...S.history],
      ...performanceInfo(),
      wasmBytes: decode(payload.wasm).length,
      wasmMemoryBytes: S.wasm.memory.buffer.byteLength,
      fingerprint: payload.buildFingerprint,
      droppedWallSeconds: S.droppedSeconds,
      replay: replayInfo(),
    };
  }

  return { topologyAudit, analyze, performanceLog };
}
