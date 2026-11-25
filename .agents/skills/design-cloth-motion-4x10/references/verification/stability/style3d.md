# 模拟状态与稳定性 · Style3D MCP / API

用 `Simulation.GetDiagnostics` 读项目在场、运行、录制、状态和模式。该回执没有穿透深度、碰撞计数或求解帧 ID。复核现有结果时沿用匹配的姿势和图。仅在任务允许新模拟时，考虑 `Simulation.ToConverge`，按当前 schema 检查前置条件和超时。它会改变衣片状态。留实际选定模式和调度结果，分别记录 Converged 或 Timeout，再看衣片稳定、翻转、牵拉以及 [人体碰撞](../collision/style3d.md)。
