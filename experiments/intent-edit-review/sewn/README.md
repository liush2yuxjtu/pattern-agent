# 按三个技能生成并验收真实缝合外壳

[返回整个实验的中心README](../README.md) · [在线实验总览](https://liush2yuxjtu.github.io/pattern-agent/intent-edit-review/experiment/)。本页是缝合子流程说明，原型、改版案例、其他页面和完整证据从中心README统一进入。

本目录实际执行用户指定顺序：
[sew-pattern-to-3d](../../../.agents/skills/sew-pattern-to-3d/SKILL.md) →
[verify-seaming](../../../.agents/skills/verify-seaming/SKILL.md) →
[verify](../../../.agents/skills/verify/SKILL.md)。

独立结果页：<https://liush2yuxjtu.github.io/pattern-agent/intent-edit-review/sewn/>。
单文件对照页、在线文档与本页通过中心README串联。本结果页引用本次生成的真实预览，每个预览HTML
内嵌其自己的GLB和脚本，不使用旧模型或图片替代。

只调整本目录页导航时，先运行 `verify_preview.py` 得到与新HTML匹配的真实浏览器报告，
再用 `publish_review.py --refresh-existing web/intent-edit-review/sewn --verification <报告路径>`
刷新交付证明。该模式逐项核对原清单，拒绝模型、源文件或交付包变化，保留原整体结论。

## 本轮真实结论

五项整体为 **BLOCKED：2项修正版外壳几何PASS，3项受当前配置限制**。

| 输入 | 本次状态 | 事实 |
| --- | --- | --- |
| 原型 | PASS | 25758顶点、51150面、15条缝、1连通组件、4正常开口、间隙0、严格穿插0 |
| 袖长+20U | BLOCKED | PROFILE_REQUIRED；新轮廓超出当前模板识别范围，没有输出旧模型冒充新结果 |
| 前后衣身−15U | BLOCKED | PROFILE_REQUIRED；需要新的明确配置与缝合合同 |
| 袖口展开宽+10U | PASS | 25958顶点、51546面、15条缝、1连通组件、4正常开口、间隙0、严格穿插0 |
| 前领深+10U及领条 | BLOCKED | PROFILE_REQUIRED；需要新的明确配置与缝合合同 |

原型与袖口案例最大三维缝长误差分别约0.073749、0.073831毫米，最大点位修正均约
4.407215毫米。数字只适用于本次文件和明确的毫米假定，不是量产、材料或合身认证。

## 单位与派生纸样

原始DXF没有物理单位声明，完整中文规格仍为未标定U。本次通过显式
`--units-assumption mm` 沿用技能的同款毫米约定进行数字几何测试；没有回写规格或
宣称已经测得真实比例。

原始缝线在当前合同下仍为FAIL。转换器另存有界修正线，处理肩、侧、袖山和袖底，
按明确归拔和吃势规则配对，然后三角化、摆放并真正焊接。修正版不能混同为原纸样，
也不能当作已批准的生产净样。原始DXF/YAML与修正SVG/JSON均交付。

后身原标注数量2和单片完整后身装配假定未解决；领条隐藏内层与缝份叠层未包含。
物理试穿、材料力学、人体碰撞和生产批准均为NOT_RUN。历史7.6455毫米间隙/20穿插
以及v1的9组件/340穿插FAIL保留，本次不覆盖它们。

## 实际可复跑的顺序

从仓库根目录，使用当前服务的既有Python/NumPy/SciPy/FastAPI环境；浏览器检查
另用已安装的Playwright、Pillow及 `/usr/bin/chromium`，无需Blender或外部模型服务。

```sh
python experiments/intent-edit-review/sewn/run_chain.py --output work/my-sewn-run --units-assumption mm
```

输出目录必须全新或为空。第一阶段直接调用现有 `convert_dxf` 和 `bundle`，每个接受的
模型均由实际DXF重新生成。第二阶段再启动独立CLI，重开已经写出的float32 GLB和原始
DXF。每个拒绝项保存决定，没有模型，也不会把另一案例的成功复制过来。

CLI退出0代表五项全部PASS，2代表存在真实失败，3代表存在阻塞。本轮预期退出3，
对应三项不受当前配置支持；不是执行器崩溃，也不是五项全部通过。

```sh
python experiments/intent-edit-review/sewn/publish_review.py --run work/my-sewn-run --output work/my-sewn-review
python experiments/intent-edit-review/sewn/verify_preview.py --directory work/my-sewn-review --output work/my-sewn-browser
python experiments/intent-edit-review/sewn/publish_review.py --run work/my-sewn-run --verification work/my-sewn-browser/report.json --output work/my-sewn-final
```

最终发布目录可用 `--output web/intent-edit-review/sewn`，同样需要全新目录，不能覆盖
上次产物掩盖失败。已有发布物应先另写新目录、核对，再替换明确归本项目生成的文件。

第三步真实检查两模型像素、拖动/缩放/键盘/线框/复位、真实触摸、375/320窄屏、
完整下载、15条可见测量、禁网的单文件预览及无WebGL时的明确提示和可下载模型。
实际下载的GLB还会再次独立重开。页面交付验证PASS不把五项缝合总结果BLOCKED改成PASS。

## 文件与证据

- `manifest.json`：输入摘要、单位假定、来源代码摘要、阶段顺序、五项真实状态。
- 每个案例的 `source-input.dxf`、`source-spec.yaml`、`decision.json`：实际原文件与决定。
- 接受项的 `files/model.glb`、`files/preview.html`：本次实际模型和自包含预览。
- `files/pattern-revision.json`、`files/corrected-seam-lines.svg`：原始与派生修正线对照。
- `independent.json`：独立15缝、UV、拓扑、四开口及严格穿插报告。
- `delivery.zip`：上述实际文件、完整规格、独立报告和决定，不包含伪成功模型。
- `preview-verification.json`：第三步预览、下载和再重开的真实报告。
- `files-manifest.json`：逐文件大小与SHA-256。

本次原始日志、独立报告、实际下载和截图保存在仓库新的
`docs/verification/intent-sewn-chain-20261118/`。发布只新增该子路由，沿用main的既有Pages
流程，不新增CI，也不改变原页面、转换器、匹配阈值、缝合合同或独立检查器。

## 三项受限结果如何继续

技能明确规定：“被拒绝时保留错误，不得退回旧模型或硬套本款裁片编号。”新配置需要
重新核对裁片语义、方向、配对、局部加工区间、开口及空间摆放，并补齐独立来源和故障
控制。不能只放宽8毫米匹配阈值、改文件名或把已通过模型贴上新的来源摘要来解锁。
