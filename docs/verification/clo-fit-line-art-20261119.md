# CLO Fit 0.1.1 线稿对照验收

候选基线为 `79298c517656460f8f0837b9642f13111c4c8a82`，已测试的插件树为 `90b88fb9376b1f03025a89c552142ee6e89f7aec`。本地 `/verify` 对插件安装、线稿对照和离线试穿数据复核的判定为 **PASS**。使用 [CLO 导出与插件验收流程](../../.agents/skills/verify/references/clo-fit-export.md)。

| 操作 | 观察 |
| --- | --- |
| 在独立 Codex 配置执行 `codex plugin marketplace add <checkout> --json` 和 `codex plugin add clo-fit@pattern-agent --json` | 安装 0.1.1。逐文件比对安装缓存和插件树一致。`codex app-server --stdio` 的 `skills/list` 返回两个已启用的 `clo-fit:` 技能，试穿技能显示线稿对照说明。 |
| `python -B -m unittest discover -s .agents/skills/clo-fit-export/scripts -p test_fold_preview.py -v` | 两项折角测试通过，原 T 恤示例的 11 张图和主 DXF 可读，DXF 摘要与原记录一致。 |
| 运行安装缓存里的 `export_fit.py` 与 `compare_poses.py` | 从 Carlton Joost 的保存资料重新导出垂臂、斜展、平举。每姿势 28 片和 84,750 个有效三角面，84 条汇总记录与独立参考逐字段一致。CSV SHA-256 为 `2eecef67acab3de56935781a035bb422911c7ab905b5aadd440798968c5cf5f5`。应力点数值保持缺失。重新打开导出图，核对了原生应力和工程应变色标。 |
| 对照可追溯的线稿与快照 | FreeSewing Carlton 正面线稿与 Joost 垂臂基准普通材质正面照均可打开。报告保留原图链接，注明截图可见的叠合、开口和翻领状态。工程扣合与领部支撑待核实。线稿加入后，本地报告的四类图及原链接仍可读。 |
| 给导出器传一个裁片名，给汇总器传与统计摘要不符的斜展网格 | 两次均报错退出，未生成错误输出。 |

本次使用 [Carlton 案例](../cases/carlton-joost/README.md) 的已保存资料。验收后关闭临时 app-server，核对记录保存在本地。新的 CLO 动态仿真及实物试穿为 NOT_RUN。
