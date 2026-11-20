# 人体碰撞与穿模 · Style3D MCP / API

停模拟和录制，保持姿势和场景不变。用 `Avatar.GetAllIds` → `Mesh.GetAvatarSnapshot`，再按主裁片取 `Mesh.GetClothPieceSnapshot`。检查各快照的 `valid`，用 `Mesh.ValidateSnapshot` 检查输入，再逐片调用 `Mesh.QueryCrossings`。保存相交面所在裁片和人体部位、局部图及 `truncated`；必要时提高结果上限以补齐。

交叉查询覆盖非共面三角面穿插。共面接触、碰撞厚度、完全包入和人体附件需用相应视图或另有明确能力的工具复核。近邻查询的 `normalOffset` 只表示法向投影。零交叉和模拟已停止均不足以确认无穿模。出现夹布或层间翻转时，可用同方法检查裁片间交叉，结合姿势、层次和初始摆位定位。
