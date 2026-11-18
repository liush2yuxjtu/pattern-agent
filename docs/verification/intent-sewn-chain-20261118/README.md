# 三技能顺序执行：本轮真实结果

用户要求 `sew-pattern-to-3d` → `verify-seaming` → `verify`。三个规范技能均已读取，
实际执行分别为新DXF到GLB构建、独立CLI重开实际模型，以及本地测试/真实预览/下载再重开。

**五项缝合总结果：BLOCKED。** 原型和袖口加宽修正版外壳几何PASS；袖长、衣长、前领
三项为PROFILE_REQUIRED。页面交付准确展示这些结果并通过浏览器验收，不把总结果改成PASS。

新页面：<https://liush2yuxjtu.github.io/pattern-agent/intent-edit-review/sewn/>。
源码与完整复跑说明见 [项目目录](../../../experiments/intent-edit-review/sewn/README.md)。
本次没有改动原有对照页、文档页、转换器、匹配阈值、缝合合同或独立几何检查器。

## 1. sew-pattern-to-3d

真实输入为 `patterns/fitted-tshirt/input.dxf` 和四个已提交的基准输出。新目录
`work/intent-edit-review/sewn-chain/run-01` 中调用既有 `convert_dxf` 与 `bundle`。
每次原字节、完整规格摘要、单位假定、来源代码及技能摘要都保留在
[generation-manifest.json](generation-manifest.json)。预先注册结果见
[registration-preflight.json](registration-preflight.json)。

```sh
python experiments/intent-edit-review/sewn/run_chain.py --output work/intent-edit-review/sewn-chain/run-01 --units-assumption mm
```

本轮明确沿用技能的毫米数值假定；原文件没有物理单位声明，中文规格仍为未标定U。
没有把软件默认值当作真实标定，也没有写回原始文件。CLI退出3对应下表三个配置阻塞，
不是运行器崩溃。没有生成或沿用这些受限输入的伪成功模型。

| 输入 | 实际决定 | 新模型 |
| --- | --- | --- |
| 原型 | 新生成并独立PASS | 25758顶点 / 51150面 |
| 袖长+20U | PROFILE_REQUIRED / BLOCKED | 无 |
| 衣身−15U | PROFILE_REQUIRED / BLOCKED | 无 |
| 袖口展开宽+10U | 新生成并独立PASS | 25958顶点 / 51546面 |
| 前领深+10U及领条 | PROFILE_REQUIRED / BLOCKED | 无 |

三项受限的规范依据为
[sew-pattern-to-3d](../../../.agents/skills/sew-pattern-to-3d/SKILL.md)：
“被拒绝时保留错误，不得退回旧模型或硬套本款裁片编号。”要解锁需新增并独立核对配置
与缝合合同；本轮没有把8毫米匹配界限放宽成接受这些轮廓。

## 2. verify-seaming

对每个已经写出的实际GLB另启独立CLI，以它自己的原始DXF重新验收，退出码均0。
这一步在所有生成决定之后开始，阶段时间顺序保存在执行清单中。

| 指标 | 原型 | 袖口加宽 |
| --- | --- | --- |
| 完整语义接缝 | 15 | 15 |
| 连通组件 / 正常开口 | 1 / 4 | 1 / 4 |
| 最大缝隙mm | 0 | 0 |
| 最大加工后平面残差mm | 0.000000604 | 0.000000604 |
| 最大三维缝长误差mm | 0.073749120 | 0.073831441 |
| 最大派生点移动mm | 4.407215288 | 4.407215288 |
| 严格穿插 | 0 | 0 |
| 原始缝线在当前合同下 | FAIL | FAIL |
| 修正外壳数字几何 | PASS | PASS |

独立检查实际float32、来源/UV、完整面域、正确两侧面来源、真正焊接、四开口、
欧拉特征−2、方向及全部三角面严格穿插，包括共用顶点/边的面。
报告见 [原型](baseline/independent.json)、[袖口改版](03_cuff_width/independent.json)。

实际GLB摘要：

- 原型：`dd4742ab120cb8e8abc2621ae42070657a3f07da885bd71d9ffc12fb65d15031`。
- 袖口：`ffb75cedd87eac81ef39250715e5ae1cf3d1c9230304c6ed01b60afa2bc42835`。

## 3. verify

页面与交付检查PASS。完整记录见 [browser/report.json](browser/report.json)，实际下载、
下载后独立报告和原始日志保留在两个案例子目录。

- 两个iframe显示本次实际GLB。分别解码实际预览内嵌字节，核对模型摘要；两个初始
  实际渲染像素不同，画面不是固定图片或只换标签。
- 实际鼠标拖动、滚轮、方向键、线框、复位均改变或恢复渲染像素；手机context用真实
  CDP触摸事件验证两模型旋转。375/320宽度均无页面横向溢出。
- 展开表格，逐项核对15条可见缝名、加工后残差、三维缝长误差和间隙，数值来自本次
  独立重开。受限案例无模型、无GLB链接，保留拒绝记录。
- 实际保存两个GLB和两个完整ZIP。下载字节与交付源相同；ZIP的CRC、模型、原DXF、
  完整中文规格和独立报告均核对。对实际下载的两个GLB再次运行独立CLI，均PASS。
- 精确单预览HTML在禁网context中运行、切换线框且有实际模型像素。无WebGL时显示
  明确的兼容查看器提示，父页面仍能实际下载同一模型；没有声称软件物理模拟。
- 使用view_image检查实际原型、袖口、目录、手机及禁网截图。模型是几何构型；
  没有用渲染照片或生成图片冒充验收。把两模型置于结果表前，便于直接查看。

现有服务测试重新运行：

```sh
SEWING_TEST_EVIDENCE=work/intent-edit-review/sewn-chain/tests PYTHONPATH=services/dxf-preview python -m unittest discover -s services/dxf-preview/tests -v
```

27项全部通过，无失败或跳过，包含23个解析几何对照及错误来源、漏缝、反向、3mm间隙、
面重叠/翻面、隐含变换等故障控制。原始日志为 [full-tests.log.gz](full-tests.log.gz)，
控制证据见 [tests/](tests/)。

另将本次原型GLB故意配给本次袖口DXF，独立CLI退出2并报告输入摘要和真实源边不符，
见 [cross-source-control.json](cross-source-control.json)。没有只靠元数据PASS文字判定。

静态站点用原有 `scripts/build_pages.py` 完整构建，新目录与源文件一致，旧页面保留。
候选清单见 [candidate-files.json](candidate-files.json)，本轮判定与命令见
[receipt.json](receipt.json)。所有自有浏览器/context和HTTP服务已退出，无新增CI。

## 范围与仍未解决的条件

这是对明确修正线的静态单层外壳证据。原始纸样FAIL、后身数量2与完整单片装配假定、
隐藏领条内层和缝份叠层均保留。材料力学、人体碰撞、真实试穿与生产批准仍NOT_RUN。
更早布料的7.6455毫米间隙/20穿插和v1的9组件/340穿插FAIL均未被覆盖或删除。

三项缺配置使五项总体仍BLOCKED。发布审阅页用于交付两项已通过数字外壳与三项明确
限制，不表示五项已全部生成或可以直接生产。后续线上读回记录另存 `live/`。
