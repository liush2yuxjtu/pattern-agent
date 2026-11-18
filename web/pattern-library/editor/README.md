# Pattern Agent 纸样改版

工具从设计意图生成 YAML 补丁，并用同一版二维纸样重放补丁。随包提供 Pattern Agent 的 M 码贴身长袖 T 恤。四种操作可以输入新的改动量，并检查修改后的几何。

## 打开工作台

使用 Python 3.11 或更新版本，在解压后的目录创建环境并启动工作台。

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python -m pattern_tool serve
```

Windows PowerShell 的激活命令为 `.\.venv\Scripts\Activate.ps1`。打开 `http://127.0.0.1:8765` 后自动载入 M 码例子。选择「生成并应用」可编译和重放补丁，「仅生成补丁」可单独下载补丁，「重放已保存的补丁」可用选定的基线文件复跑。工作台通过本机连接读取上传文件。

## 命令行复跑

```sh
python -m pattern_tool compile --intent samples/intent.yaml --output run/patch
python -m pattern_tool apply --patch run/patch/edit.patch.yaml --output run/edited
python -m pattern_tool run --intent samples/intents/cuff.yaml --output run/cuff
```

通过 `--pattern`、`--spec` 和 `--dxf` 指定配套的二维 YAML、一维 YAML 及原始 DXF。继续改版时把对应的三个编辑输出同时作为下一次输入。可用 `python -m pattern_tool split --legacy-spec samples/input-spec.yaml --dxf samples/input.dxf --output run/split` 从旧版中文 YAML 拆出新版输入。

样例未标定实物比例，U 表示图形单位。经确认的比例须写入 `coordinates.mm_per_unit` 及旧版来源元数据。报告分别记录二维量测、生产批准和实物试穿。

## 设计意图样例

```yaml
schema: design-intent/v1
pattern_id: fitted-tshirt
size: M
id: shorter-sleeve
text: 缩短袖子，保留衣身和领条
operation:
  type: sleeve_length
  delta: -12.5
  unit: U
preserve_pieces: [front, back, neckband]
evidence_ids: [E01, E07]
```

省略 `operation` 时，工具可读「袖子加长 23 U」等简单的中英文指令。文字较宽泛时可同时提供已审核的结构化操作。目标不明、数值矛盾或实物单位尚未标定时，工具返回 `NEEDS_REVIEW`。一张补丁处理指定版本和尺码的一项操作。

| 操作 | 量法和几何约束 |
| --- | --- |
| `sleeve_length` | 改袖片中心线长度，保留袖山和腋下定位点，连带移动袖口。 |
| `body_length` | 同时改前后衣身中心线，保留腰线及以上区域，连带移动底边。 |
| `cuff_width` | 改袖口平铺展开总宽，两端各移动改动量的一半，保留上部袖型。 |
| `front_neck_depth` | 改前中领深，保留领宽、肩线和袖型。按当前候选领条长度比更新领条。 |

## 输出与来源

- `edit.patch.yaml` 保存修改前的值、三个输入的 SHA-256 和输出哈希。
- `edited-pattern.yaml`、`edited-spec.yaml` 和 `edited.dxf` 可用作下一版输入。
- `edited.svg` 展示新纸样，`before-after.svg` 叠加灰色原版虚线和蓝色改版。
- `report.json` 记录目标实测、接口变化、原有轮廓缝隙和待确认的生产条件。
- [数据结构](SCHEMA.md)说明当前执行范围、意图字段，以及工业 CAD 和其他服装所需的扩展字段。
- `python -m unittest discover -s tests -v` 运行测试。交付记录在 [verification.json](verification.json)。
- 可执行操作和独立审计源自仓库基准引擎 `3f69ad8213bf1a53ae995c04364cb1f4439f4638`。随包保留基准输入的原始字节。[Pattern Agent 基准引擎](https://github.com/liush2yuxjtu/pattern-agent/tree/3f69ad8213bf1a53ae995c04364cb1f4439f4638/experiments/intent-edit-benchmark)
