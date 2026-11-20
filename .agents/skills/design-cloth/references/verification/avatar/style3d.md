# 人台、尺码与姿势 · Style3D MCP / API

用 `Avatar.GetAllIds` → `Avatar.GetMeasurements` 读取已加载人台可见量体（mm）。用 `Avatar.GetCurrentPose` 查骨架姿势 ID，必要时查 `Grade.GetCurrentGradeId` 确认成衣尺码，并保存当前姿势图。比较已约定的量体定义、目标和实测，记录缺失项和差值；松量另用净成衣尺寸核对。

按 [人台与量体](../../avatar-setup.md) 核实人体来源。姿势 ID 或尺码名相同的结果仍需检查手臂、躯干及穿着状态。
