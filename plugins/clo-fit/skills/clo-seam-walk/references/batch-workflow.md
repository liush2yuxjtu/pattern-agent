# 批处理参考

组织方式参考 Anthropic 的 [webapp-testing](https://github.com/anthropics/skills/tree/main/skills/webapp-testing) 技能。先摸清实际环境和对象，优先用能直接运行的辅助脚本，再按回执和实际画面更新脚本。如需另验 HTML 报告，优先按该技能写一份 Python Playwright 测试脚本，在一次运行里检查页面、图片和日志。CLO 缝合本身走原生 Python 和 CLO MCP。

## 先试一个离线示例

从技能目录运行：

```sh
python3 scripts/seam_batch.py --help
python3 scripts/seam_batch.py --catalog references/example-catalog.json \
  --plan references/example-plan.json --report /tmp/clo-seam-report.json
```

示例把 60 mm 和 40 mm 的两段接到一条 100 mm 的边，应该看到 `plan_passed`、2 个计划组、空的 `coverage_gaps`。把示例路线中下摆结束段的 `end` 改成 0.8，保留独立覆盖清单的完整目标，预检应报出 8 mm 的缺口。

## 从 CLO 取边并运行

目录格式是以唯一裁片名为键，值为 `GetPatternLineInfo(i)` 的 `lines` 数组。参考脚本的 `live_catalog` 会读取原生 `lineIndex` 和 `length`，数组顺序可不同。对照原纸样与 2D 缝线核实线号和起终点。源文件自己的线号和方向先映射到本工程的原生数据。

每个段写为 `[裁片名, 原生线号, 起点比例, 终点比例]`。比例按原生线的起点到终点、以弧长分数表示。交换起点和终点会反向。路线中的段按缝合顺序写入。脚本按累计弧长等比例分割两侧，保留声明的路线端点。需要在刀口、后中或肩点等位置对齐时，围绕每对关键点拆成独立路线。允许的吃势和最大长度差由计划决定，建议在计划的 `note` 记录理由。

在 CLO MCP 的一次 `clo_run_python` 中运行。用实际绝对路径替换示例，先把工程副本打开。改动前的缝合组数写进计划的 `expected_groups_before`。

```python
from pathlib import Path

script = Path("/absolute/path/to/clo-seam-walk/scripts/seam_batch.py")
ns = {"__name__": "clo_seam_walk"}
exec(compile(script.read_text(encoding="utf-8"), str(script), "exec"), ns)
report = ns["run_clo"](
    "/absolute/path/to/plan.json",
    "/absolute/path/to/seam-report.json",
    pattern_api,
    utility_api,
    apply=True,
    steps=120,
)
if report["status"] == "native_groups_verified":
    export_api.ExportZPrj("/absolute/path/to/working-sewn.zprj", False)
result = {k: report[k] for k in ("status", "groups_added", "simulation_steps")}
```

`apply=False` 在实际工程中只跑预检，可用在当前场景。修改旧缝时，项目脚本负责先建立正确的缝合前状态。不要对状态不明的工程重复添加整个计划。模拟步数根据工程决定，`Simulate` 返回成功表示完成请求的步数。

## 怎样判断通过

| 证据 | 能确认的事项 |
| --- | --- |
| `plan_passed`、`coverage_gaps` 为空 | 两段长度差在你声明的范围内，计划覆盖指定边段。 |
| `native_groups_verified` | 已确认预期新增组出现在两片的缝合列表，记录请求的模拟步数。 |
| CLO 2D 或原生缝线视图 | 缝线方向、刀口配对和端点是否正确。 |
| 同姿势 3D 截图或网格 | 接缝两端对齐，衣片没有明显扭转、张口或穿模。 |
| 回导 DXF，若需要 | 与原切线逐片比较，单独记录外轮廓和内部线的变化。 |

误差或覆盖缺口会挡住整个批次的应用。返回 `error` 且进入过应用时，先检查 `groups_after` 和 CLO 场景再处理。原生修改没有自动回滚。原生组列表只能证明组归属，关键对位点和布面效果需要另外检查。

## Carlton 例子

当时由 CLO MCP 的 `clo_run_python` 执行整份脚本。脚本读取每条原生边，再循环调用 `AddSeamlinePairGroupPartial`。例如，领座下缘分两段接后领口和前领口。早期侧缝为了接近等长，在前片底部漏掉约 78 mm，原生组数仍然正确。改版把前后下摆端点配齐，把差量分摊到侧缝并重跑模拟，最后比较端点和 DXF，而后确认纸样外轮廓保持一致。
