# 接缝装配与三维形状项目技能

新增 [sew-pattern-to-3d](../../../.agents/skills/sew-pattern-to-3d/SKILL.md)，保存从
DXF 解析、走缝、二维剖分、三维形状映射到实际焊接与离线交付的执行流程。
新技能复用当前生成器和打包函数，没有另写一套算法或修改生产运行时。

## 现有技能与新增入口

检查仓库后，现有 `garmentcode-preview` 负责 GarmentCode JSON 网格及物理下垂，
`verify-seaming` 负责已有 DXF/GLB 的独立验收，`garment-body-six-view` 负责照片与
人体拟合。新增入口补充本款 DXF 静态装配，并从现有验收技能和根 README 链接。
Claude 的同名目录是指向 `.agents/skills/sew-pattern-to-3d` 的相对符号链接。

技能及实现参考明确说明：衣身用固定空间边界、调和平滑及展示鼓出，袖片映射到
弯曲轴管面，领条只构建外层；不能据此证明片内等距、面料性能或真实试穿。
仅支持本款配置，其他款式先建立来源与缝合合同。原纸样、修正记录和历史 FAIL 保留。

## 本次实际验证

按项目 `/verify` 的现有 `dxf-service`、`dxf-seams` 配方确定本次范围；
从新 SKILL.md 原样提取唯一 shell 代码块并实际执行，没有改写示例以绕过失败。
记录见 [documented-command.sh](documented-command.sh)、[generation.log](generation.log)
和 [generation-exit.json](generation-exit.json)。

| 检查 | 本次结果 |
| --- | --- |
| 新技能及更新后的 verify-seaming 格式 | 均通过现有格式校验器 |
| 本地 Markdown 引用及 Claude 共用路径 | 26 个引用可解析，符号链接正确 |
| 新生成离线包 | CRC 及 8 个包内文件与实际解压文件均一致 |
| 输入与输出身份 | 原 DXF 字节、原文件摘要及 GLB 摘要与报告一致 |
| 实际新 GLB 独立重开 | 15 对接缝通过，间隙 0 毫米，最大三维缝长误差 0.0737491202355045 毫米，穿插 0 |
| 现有消费者测试 | 3 项通过，覆盖重复生成、开口源轮廓拒绝、单位/大小/非有限坐标拒绝 |
| 运行时和浏览器重测 | 运行时代码未改，本轮浏览器重测 SKIP |
| 原生技能自动触发 | NOT_RUN，不把文件格式校验当作实际路由评估 |

模型为 25,758 顶点、51,150 三角面，保留四个正常开口，原纸样按当前合同仍为 FAIL。
当前本地模型摘要为 `dd4742ab120cb8e8abc2621ae42070657a3f07da885bd71d9ffc12fb65d15031`，
不能沿用冻结云端模型的文件摘要或把其检查视图直接绑定到新模型。

原始独立结果见 [independent.json](independent.json)，修正记录见
[pattern-revision.json](pattern-revision.json)，本次产物路径、逐文件大小和摘要见
[generated-artifacts.json](generated-artifacts.json)。实际模型和离线预览保留在该清单
记录的本地 work 目录；可用提交中的原样命令重新生成。没有将旧模型替代本次输出。

现有测试产生一条 Starlette TestClient 依赖弃用提示，测试本身通过；没有为此修改
项目依赖。消费者原始输出见 [consumer-controls.log](consumer-controls.log)。

## 范围与清理

本次完成项目技能保存、可执行说明的实际生成与独立验收、共用路径和入口维护。
候选来源及每条命令/退出码见 [receipt.json](receipt.json)。生产服务、Site、Pages、
付费资源与访问范围没有变更。没有新 CI、PR 或 Issue，也没有启动浏览器或服务器。
实物合身性、材料力学、人体碰撞及生产批准仍为 NOT_RUN；历史失败没有覆盖。
