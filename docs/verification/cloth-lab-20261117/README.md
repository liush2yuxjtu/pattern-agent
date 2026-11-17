# 单文件 WASM 布料实验：本地验证

候选基线：`eb1ea230e81298bd0dd036e0d454a209d88bf700`。
实际交付字节、WASM、人体源与组合指纹见 [receipt.json](receipt.json)。
使用仓库 `/verify`：[操作配方](../../../.agents/skills/verify/references/cloth-lab.md)。
本地结论 **PASS**，范围仅为声明的求解器、合成材料公式、缝合与离散人体碰撞；
**真实面料标定、布料自碰撞、连续碰撞检测、完整成衣和实体试穿均未验证**。
历史 T 恤 FAIL 保持不变。

## 实际结果

- 3 个消费者测试执行 HTML 中真正的 WASM：16 MiB 固定内存、无约束重力与独立
  递推式一致、初始拉伸三角形在弹性时间步后降低膜能量。
- Playwright 15 项实际交互/数值检查通过，详见 [原始收据](local/receipt.json)。
  逐步推进 0 → 1 → 60 → 300 步，保存实际页面截图；不是用静态图代替仿真。
- 默认导出：850 个布料顶点 / 1,536 个三角形；实际 MakeHuman 人体为
  13,380 顶点 / 26,756 三角形，独立重开时须匹配源文件哈希、位置和拓扑。
- 独立 NumPy/trimesh：默认两条侧缝均约 610.921 mm，接缝最大间隙 0 mm；
  4,770 个顶点/边中点/面重心无人体内点；两个方向的边—面相交均为 0。
  默认最小独立采样距离约 5.678 mm。移动人体及恢复真实注入穿透后也通过。
- 默认局部最大主应变约 **23.92%**，主柯西应力约 **53.88 kPa**。
  页面保留高应变警告，不把几何通过当作服装适体批准。
- NumPy 重算全部三角形材料坐标张量；静止、刚体旋转、10% 经/纬拉伸、剪切试片
  与运行时吻合。真实 GPU 颜色数组按对应物理标量生成；切换视图不改动几何。
- 六类反例被拒绝：长度不一致、漏缝、反向缝合、关闭碰撞后的真实穿透、
  伪造应力和替换人体。零接缝间隙不能遮蔽反向缝合错误。
- 实际下载 SVG/OBJ/JSON/HTML；SVG 的 mm 尺度和 100 mm 标尺有效，OBJ 包含
  身体和衣片。下载 HTML 在断网上下文恢复坐标及上一帧，下一步逐位一致；
  二次保存也恢复新的状态，人体移动后的固定点续算同样一致。
- 十次重置保持几何体、纹理和 WASM 内存数量；390 px 无横向溢出；
  无页面异常、控制台错误、HTTP 错误或离线外部请求。
- 软件渲染 ANGLE/SwiftShader、像素比 0.8；五秒样本中位帧时间 **33.4 ms**，
  p95 **66.7 ms**，不是硬件 GPU 的 60 FPS 声明。
- 最终同状态 20 步 A/B：碰撞距离缓存约 **4.080 ms/步**，完整查询约
  **69.835 ms/步**；全部位置数组逐位相同。缓存使用距离的 1-Lipschitz 下界，
  不是用球体、径向代理或跳过真实接触来换取性能。

## 视觉证据

已人工视觉复核人体/裙装真实网格、应变与应力的不同分布、反向缝合畸变与 FAIL、
以及手机布局。布局和图像支持这些有限结论，不建立面料、生产或人体适体批准。

| 阶段/场景 | 截图 |
|---|---|
| 初始排列，尚有穿透 | [第 0 步](local/step-000.png) |
| 单步/半秒/稳定后 | [第 1 步](local/step-001.png) · [第 60 步](local/step-060.png) · [第 300 步](local/step-300-fabric.png) |
| 工程主应变 | [应变图](local/strain.png) |
| 最大主柯西应力 | [应力图](local/stress.png) |
| 实际人体距离 | [碰撞距离图](local/contact.png) |
| 错误缝合 | [反向缝合](local/fault-reverse.png) |
| 碰撞负对照与恢复 | [关闭碰撞并注入穿透](local/collision-disabled.png) · [恢复](local/collision-recovered.png) |
| 人体真实横移 | [移动后](local/body-moved.png) |
| 手机 | [390 px](local/mobile.png) |

原始项目以 gzip 保存，解压后可独立复查（不是仅查看 runtime 汇总）：

```sh
gzip -dc docs/verification/cloth-lab-20261117/local/cloth-project.json.gz > work/cloth-lab/reopened.json
python tools/cloth_lab/oracle.py work/cloth-lab/reopened.json
```

恢复穿透和移动人体的项目也保存在 `local/`。可访问性快照、真实 SVG、构建、
内核、浏览器及原有纸样/下载回归的命令和退出码保存在该目录及 `logs/`。
`manifest.json` 记录所保存证据的 SHA-256。

## 迭代与限制

`initial-observed.json/png` 保留第一轮观测：约 40.3% 局部应变、32.62 ms/步。
它是较早候选，不是最终源的受控对照。后续修正了缝合自由度、迭代和丝缕轴映射；
最终受控性能结论只取 `local/receipt.json` 的 cacheAB，不跨候选推导因果。
早期测试环境未生成 dist 导致原有 artifact 测试无法启动；按现有配方构建后全部
通过。未删除反例或修改历史 FAIL。应力比较使用明确的 float32/float64 容差，
不得把浮点误差或颜色饱和解释成材料实测。

GitHub Pages 部署和公开 URL 是后续独立边界；初始本地 PASS 不代替线上验证。

并发新增的 `web/cloth-lab.html` 是另一路单文件实验，本次保留不覆盖；本实验入口为 `web/cloth-lab/`。
