# 在 Boat 运行一个批次

在本机确认已经登录 Boat CLI，且有权使用指定的运行中 sandbox。在
Boat 的 Python 环境按需安装 `scripts/requirements.txt`。只做
`seam-walk` 可直接使用 Python 标准库和 Rust 程序。

需要从已有快照新建机器时，先确认有权使用该快照和计算额度：

```sh
boat new --personal --no-env --from clo-rust --type small --name clo-rust-review
```

在 Boat 上已有插件目录时，可用独立的 Python 环境安装绘图依赖：

```sh
python3 -m venv .clo-rust-venv
.clo-rust-venv/bin/python -m pip install -r scripts/requirements.txt
```

使用下一节的 `--python` 指向这个环境。保存结果后，可用
`boat stop <sandbox-id>` 停止自己为这批任务创建的实例。

## 输入与执行

对服装网格先确认公制 UV、原始位置为毫米、Y 向上、+Z 向前。只传入
需要分析的服装网格。脚本检查所有姿势的 UV 和三角面拓扑：

```sh
python3 scripts/prepare_meshes.py review-input --mesh-source "项目和姿势出处" \
  --pose "垂臂" relaxed.glb --pose "斜展" angled.glb --pose "平举" raised.glb
```

按需要在输入目录补上以下文件：

```text
review-input/
  manifest.json
  pose-01.glb
  pose-02.glb
  pose-03.glb
  line-art.png
  maps/pose-01/{fit-front,fit-back,stress-front,stress-back}.png
  maps/pose-02/{fit-front,fit-back,stress-front,stress-back}.png
  maps/pose-03/{fit-front,fit-back,stress-front,stress-back}.png
  seams/{edges,edge-map,seams,connectivity}.json
```

- `review` 需要姿势网格。可选图或缝合定义齐备时一并处理。
- `fit-export` 还需要每个姿势的四张原生正背 PNG。
- `seam-walk` 只需要四个缝合 JSON。Rust 将缝合区间写成工程，重开审计并输出约束及连通性。

```sh
python3 scripts/run_boat.py <sandbox-id> review review-input review-result
# 如 Boat 依赖装在 venv，传 --python /path/to/venv/bin/python。
# GitHub 版可传 --remote-native /path/on/boat/to/pattern-native。
```

如果已经在 Boat 内，将 CLI 切到已安装技能目录：

```sh
python3 scripts/boat_batch.py fit-export review-input review-result
# GitHub 版可传 --native /path/on/boat/to/pattern-native。
```

批次会在 Boat 使用独立工作目录，并打印相对路径供排查。核对本机
收到的 `run.json`，其中包含实际架构、模式和运行的二进制摘要。
查看 `map-status.json` 中每一姿势的四类图和各自来源。HTML 应离线
显示；JSON、CSV 和 VTK 的裁片及三角面统计应一致。原生 PNG 应与
输入原图一致。服装实时模拟、压力和原生 CLO 工程写入走原生 CLO 工作流。

保留的 Carlton 出样示例可在已设置的 Rust 工程上运行旧入口
`run_review.py <CLO_RUST> <input> <output> --carlton`。将本技能
`vendor/` 中的三个文件放入工程 vendor 目录，使用
`npm ci --prefix <CLO_RUST>/vendor --ignore-scripts` 安装固定版本。
