---
name: design-cloth
description: 用 FreeSewing、Style3D、CLO 3D、CLO_RUST 或 Boat 设计、试穿与验收服装。适用于起版与 DXF、选布、量体、缝合、配饰和扣件检查、线稿或效果图对照、原生模拟、修复、复测与验收报告。
---

# 服装设计与试穿

按用户指定的范围、尺码、姿势、工程和运行环境执行。默认用中文交付，遵循用户指定的语言。原始证据保留软件名、标识和单位。

## 流程图

```mermaid
flowchart TD
    Idea(["开始 · 设计需求或已有工程"]) --> Skill["$design-cloth"]
    Skill --> Prepare["按需选布、量体、起版或模拟"]
    Skill -->|已有有效证据| Review
    Prepare --> Review["数字验收 · 模型自主选路"]
    Review -.-> Quick["四类快查<br/>人台与纸样 · 面料赋值 · 缝合与闭合 · 姿势与摆位"]
    Review -.-> Methods["五项验证 · 按需选择<br/>• 上身与线稿对照<br/>• 应变图与伸长率<br/>• 应力图与读数<br/>• 接触压力图与读数<br/>• 褶皱图与折角"]
    Review --> Gate["汇总验收结果<br/>正式报告每尺码四姿势 × 五类验证"]
    Gate --> Report["报告与下一步分诊<br/>按优先级写明部位、证据、执行方或工具、复测条件"]
    Report -->|确认缺陷| Repair["修复缺陷"]
    Report -->|证据不足| Collect["补采证据"]
    Report -->|局部验收交付或整衣待补证| Scoped["交当轮复核报告<br/>注明结论、范围和复测条件"]
    Report -->|整衣四姿势五类通过| Publish["发布正式报告<br/>Markdown 与独立证据图"]
    Publish --> Deliver["打样定稿<br/>同版纸样 · 3D 渲染 · 定稿报告"]
    Repair --> Return["复查受影响项"]
    Collect -->|取得证据| Return
    Collect -->|需要人提供证据或决定| Human["HITL · AskUserQuestion<br/>请用户补证或作出决定"]
    Human -->|反馈后| Return
    Return --> Review
    Deliver --> Sample["制作实物样衣"]
    Sample --> Fit{"HITL · 实物验收"}
    Fit -->|工艺问题| Sample
    Fit -->|版型或用料问题| Review
    Fit -->|通过| Done(["结束 · 交付最终成衣"])

    classDef terminal fill:#dcfce7,stroke:#15803d,color:#14532d,stroke-width:2px;
    classDef hitl fill:#fef3c7,stroke:#b45309,color:#451a03,stroke-width:2px;
    classDef verification fill:#dbeafe,stroke:#2563eb,color:#172554,stroke-width:2px;
    classDef reportNode fill:#f3e8ff,stroke:#7e22ce,color:#3b0764,stroke-width:2px;
    class Idea,Done terminal;
    class Human,Fit hitl;
    class Methods verification;
    class Report,Scoped,Publish reportNode;
```

## 服装开发

从最能推进当前任务的环节接手。需要准备输入时，按[工作流程](references/workflows.md)选布、量体、起版或接续已有工程。需要新模拟或取证时，按[运行环境对照](references/runtime-support.md)选择 Style3D、原生 CLO、CLO_RUST 或 Boat。保留原工程，在副本上修订。

## 数字验收与定稿

按症状、最近改动和证据缺口，自主选用[四类常见问题快查](references/workflows.md#四类常见问题)和[五种验证方法](references/workflows.md#五种验证方法)。可从已有证据开始，也可在试穿前后切换。复用与当前版次、尺码和姿势匹配的证据。按[验证方法索引](references/verification/index.md)查各软件的逐项操作手册。

用[整衣验收](references/finish-verification.md)判断当前候选，按[三条处理路径](references/workflows.md#数字验收的三条路径)推进。

- **有缺陷。** 自动修复范围内已确认的问题，重查受影响项，回到同一验收关口。
- **证据不足。** 自主补采或做受控对比。仍需用户输入或决定时，按[疑难交接](references/workflows.md#定稿与疑难交接)用 `AskUserQuestion` 提问，并给出证据和建议下一步。收到反馈后继续当前验收。
- **整衣验收通过。** 交付同版定稿纸样、3D 渲染和[定稿报告](references/试穿报告模板.md)。需要实物验证时，由实际样衣和试穿证据判定。

**当轮验收报告。** 每次向用户交付验收结果时，按[报告模板](references/试穿报告模板.md)交付有独立证据图的 Markdown。效果图对照、局部验收和证据不足的交接也有当轮报告。发送最终答复前，打开报告并检查证据链接。在答复开头用明确的报告名链接文件，作为第一条交付链接，旁边写明本轮状态与范围。答复中的本地报告链接用实际绝对路径，报告内的证据图用相对路径。用户只要求对话简报时，直接在答复中呈现同等结论和关键证据。

**用户交接触发条件。** 写完当轮「结论与复测标准」后，若首个尚未解决的步骤明确交由用户或其版师补证、选择方案或决定是否改版，在发送最终答复前实际调用 `AskUserQuestion` 或当前环境的结构化提问工具（例如 `request_user_input_async`）。报告中的复测清单、写给版师的建议和最终答复里的文字都不能代替这次调用。工具不可用时才在对话中提问。可自主完成的步骤继续执行。

试穿、复验和定稿报告面向版师、服装设计师及没有服装背景的工程师。正文先用日常语言说明服装部位、改动和结果。每轮验收后在[结论与复测标准](references/试穿报告模板.md#七结论与复测标准)按优先级给出下一步、对应证据、执行方或工具、复测姿势及可观察或可量化的通过条件。正式报告和打样定稿须先通过[四姿势五类验收](references/workflows.md#四姿势五类验收)，再用[导出脚本](scripts/bake-report.mjs)校验发布清单并生成默认 Markdown。正文用大图和短图注，采用多级标题，所有表格集中放在结论前。

## Style3D MCP / 原生 API Playbook

指定 Style3D 时先读 [Style3D 操作约定](references/verification/style3d.md)，再从[验证方法索引](references/verification/index.md)选对应的 Style3D 手册。只核对工具能力时使用目录和 schema。原生工程读写、导出与模拟按本轮授权和当前版本能力执行。指定 CLO 3D 时读 [CLO 3D MCP 操作约定](references/verification/clo3d.md)及对应手册。
