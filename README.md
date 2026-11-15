# Pattern Agent · 参考 T 恤数字验证

**本轮结论：P1_NO_GO。完整数字流程已运行；纸样尺度、逻辑缝合结构和缓存完整性通过，Cloth 的实际缝隙与自交未通过。真实打印、样衣、真人试穿、用户任务成功和支付验证均为 NOT_RUN。**

本项目将一件用户报告尺寸的针织 T 恤转换为参数、可编辑纸样、Blender Cloth 场景和 1:1 PDF。每个输出都追溯到同一个 `output/pattern.json`。PDF 直接使用二维母版；模拟后的变形不会反写打印尺寸。完整判定见 `docs/validation-report.zh.md` 和原始 JSON 报告。

实际 Blender 4.3.2 已运行 120 帧。最终最大缝隙 7.6455 mm，超过本项目的 2 mm 门槛；非相邻三角面自交 20 对，门槛为 0。重新打开与异目录迁移均复现这些结果。纸样只能作为待验证试制版。

## 参考与边界

| 输入 | 用户报告数值 | 本轮采用的测量定义，待参考衣复核 |
| --- | ---: | --- |
| 胸宽 | 540 mm | 腋下成衣完整平铺宽度；不是人体胸围 |
| 衣长 | 650 mm | 肩颈高点至成品下摆 |
| 肩宽 | 500 mm | 两外肩缝点的水平距离 |
| 袖长 | 250 mm | 肩点至成品袖口，沿袖中方向 |

数值由用户报告；上表的具体测量定义沿用先前制版解释，尚未对参考衣确认。没有参考照片、独立复测、身体尺寸或面料试验值。袖窿深、领口形状、肩斜、袖山高和领条缩率列在 `specs/reference-tshirt.json` 的 `assumptions` 中。四个数不能唯一确定原衣纸样。这个输出是受约束的试制版，不是精确复刻认证。

**没有真人试穿，不能证明合身。** 数字尺度、缝边匹配、拓扑闭合、布料求解和实际穿着分别记录。真实打印、裁布、缝制、试穿、面料标定及照片比对均未执行。

## 先打开这些文件

- `output/pdf/tshirt-a4-1to1.pdf`：21 页。第 1 页为校准说明，第 2 页为组装图，后面 19 页为纸样。
- `output/pdf/tshirt-1to1-master.pdf`：5 页。1 页校准说明和 4 页自定义尺寸的整张纸样。
- `docs/print-and-sew.zh.md`：打印、拼页、裁剪和试样缝制步骤。
- `output/svg/`：以毫米为物理单位的可编辑轮廓。完整裁剪标记以 PDF 为准。
- `output/pattern.json`：完整裁片、缝线、缺口、缝份和缝合关系。
- `output/simulation/`：实际 Blender 场景、缓存、数值检查及渲染；以该目录报告中的状态为准。
- `research/pattern-agent-demand-research.zh.md`：6 条公开需求证据、7 个替代产品、用户测试方案与研究限制。
- `docs/user-test-record.csv`：5 个待执行用户测试记录，当前均为 `NOT_RUN`。

前、后片的数字母版是完整衣片。打印版取右半片并标记沿布折线裁剪，展开后与母版一致。前、后片各裁 1 片；袖片裁一对镜像；领条为未标定的试制件。普通缝份 10 mm、下摆折边 25 mm、袖口折边 20 mm 已包含。领条和缝份不纳入主衣壳的 Cloth 网格。

## 重跑

本轮在 Linux、Python 3.12 和 Blender 4.3.2 上执行。Blender 为独立免费程序，需先安装，并确保命令 `blender` 在 PATH 中。Python 依赖见 `requirements.txt`。Blender 脚本使用其自带的 Python 和 `mathutils`。

在项目根目录执行：

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 run_pipeline.py --out rerun
```

`rerun` 必须为空或尚不存在。当前基准会返回非零退出码，并写入 `DIGITAL_PIPELINE_VALIDATION_FAILED`；这是已复现的 Cloth 质量失败。`execution_complete=true` 表示流程已实际执行，不表示通过验收。脚本保留失败输出，不覆盖已有验收。修改尺寸时，先复制并编辑规格文件，再运行：

```bash
python3 run_pipeline.py --spec specs/my-tshirt.json --out rerun-my-tshirt
```

若数值是设计修改，使用 `DESIGN_TARGET`，保留原参考值并写明原因。例如将衣长从 650 mm 改为 680 mm：

```json
{"value":680,"status":"DESIGN_TARGET","reference_value_mm":650,"design_reason":"Increase finished length by 30 mm","definition":"Vertical distance from shoulder-neck high point to finished lower hem.","definition_status":"ADOPTED_DRAFTING_CONVENTION_NOT_INDEPENDENTLY_CONFIRMED"}
```

不要把设计目标标成新实测值。已另行验证衣长 680 mm、袖长 230 mm 的派生纸样和打印输出；该变体未运行 Cloth，未实际打印或试穿。

如果只要纸样，可显式跳过模拟：

```bash
python3 run_pipeline.py --out rerun-paper --geometry-only
```

此模式只标记 `GEOMETRY_EXPORT_ONLY`，不会生成 Cloth 通过结论。

## 单独复核

```bash
python3 -m unittest discover -s tests -v
python3 -m pattern_agent.verify_artifacts --output output --report verification-local.json
```

生成器先验证输入、闭合裁片和缝边。独立检查器不调用生成器的验证函数。它重新读取纸样、PDF 的实际矢量和 SVG 的物理单位，检查尺寸、缝份、四个预期开口、折线镜像、1:1 比例和全部拼页覆盖。它不会把 PDF 数字通过算成打印机通过，也不会把主衣壳的缝合拓扑算成穿着合身。

模拟另有真实缓存、源顶点映射、逐帧位置与独立重载结果。任何数值门槛失败都保留为失败，不由渲染图片替代。

`output/simulation/reference_tshirt_cloth.blend` 已内嵌 120 帧缓存。已验证在原文件不可访问时，从新目录打开并直接跳到终帧；6 个检查点的顶点坐标误差均为 0。该验证只证明结果可携带，不会把质量 FAIL 改成 PASS。

## 产品判断

本轮完成公开需求访查和官方产品资料核查，没有发起真人访谈或验证支付意愿。先验证一个窄任务：有基本缝纫能力的用户，以自己喜欢的普通针织 T 恤为参考，确认结构尺寸后制作试样；首轮只改衣长或袖长，再比较成品与参考衣。

后续物理证据应记录真实参考衣、面料、100 mm 校准方框的实测、试样和真人活动情况。没有这些记录，产品状态不能升级为“合身已验证”。

## 证据目录

`evidence/` 保留独立数值检查、重现结果、PDF 视觉检查和模拟失败记录。`decisions.tsv` 是追加式决策记录。`WORK_PLAN.md` 记录本轮范围和完成条件。归档中的清单给出交付文件的 SHA-256；历史失败结果不应当作最终场景打开。