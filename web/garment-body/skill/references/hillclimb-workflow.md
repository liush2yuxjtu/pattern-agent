# 同姿态生成与接触动作的迭代

本流程用于保持原商品照片动作的完整执行。它把“真正运行过”与“结果满足动作”分开，避免
点位看似对齐而手掌翻转、骨盆漂移或生成侧背另换姿势。案例坐标、关节可见性、物体表面点
和验收阈值放在本次 case JSON，不写进通用技能或求解器。

## 先拟合和验收模型，再条件生成

1. 冻结原图、来源、像素和商品细节；从原图或已配准的 Image Gen 示意图建立目标。
2. 每个目标标记是 `joint`、`surface`、`garment` 还是 `contact`。领口、腰带和衣摆不是颈/髋
   关节；它们应绑定相应表面或接触区域。遮挡的三维量用明确先验，不编造观察值。
3. 联合或分块优化厘米形体/可辨识骨长、骨架姿态及相机。先修躯干与骨盆，再重新求腕手，
   因为改变躯干/相机后，沿用旧腕部角度通常不能保留相同投影和深度。
4. 对提衣/捏合动作同时检查腕/MCP/指尖投影、手背/掌平面法向、拇指食指捏距、双手间
   深度与局部躯干表面的前后间距。骨段tail或joint helper可能不属于bodyVertexIds，
   不能称为真实指腹；从实际连通body皮肤表面选取/追踪拇指与食指接触区域，分别检查
   同手两指、双手、手与躯干的表面间距及穿透。仅helper端点接近不是指腹接触证据。
   只对齐手腕或只做到不穿身，不能判捏衣成功。
5. 关节快速FK与最终LBS皮肤必须共用单位、坐标轴、站立floor平移和相机变换；改变站姿后
   floor可能变化，仅比较关节坐标会漏掉真实表面偏移。用实际OBJ独立重投影核查，而非把同一
   快速FK的自报点位当最终皮肤证据。图像内的点只表示 `in_frame`；`occluded`、`visible` 与
   `NOT_OBSERVED` 分列，遮挡未验证时不能把在画幅内当可见检测真值。
6. 用真实侧视和未 warp 的原图叠加检查肩臂、躯干、腰臀及手。仅将裸模缩进衣物、拉远手
   或降低总体均值不能通过；超出可辨识范围的尺寸维持先验并报告，不用不合理形变追逐轮廓。
7. 冻结通过本次模型门槛的同一 `state`、中性/摆姿网格、完整骨角及每个相机，从该状态
   生成各视角真实 RGB/骨架/相对深度引导。Image Gen 每个视图都接收原商品图、该视角
   的真实引导和源指纹，不能仅用新 front 链式推断 side/back 后宣称共享精确三维姿势。
8. 实际生成六张独立原生图，记录原生像素、工具返回路径、提示及每张实际引用图指纹。
   与本轮同状态投影独立对照；改变姿态/体形或生成位置时另开候选，不沿用旧分数。

Image Gen 姿态/深度风格仍是示意。若要求可信骨点和深度，另交真实骨架投影与 Z-buffer；
不能因风格图使用相同输入就把点线升级为检测真值，也不能由生成背面证明真人尺寸。
不同视图允许已冻结的有限评价误差，不承诺从单张照片证实精确隐藏三维结构。

## 可复算模型入口

在安装了本项目真实 Human Studio 资源与 Python 依赖的工作区使用
`scripts/run_model_fit.py --case CASE.json --repo-root REPO --out NEW_DIR`。
它运行本次 case 配置的通用躯干/手部求解入口，再从最终 `neutral.obj` 复量尺寸；
实际工具调用、文件与源码指纹落到输出目录。它不调用或模拟 Image Gen；六图仍须由
执行者通过实际生成工具完成并保存 receipt。缺少求解器/资源时明确失败，不回退到先验表。

case 的文件引用相对 case 所在目录解析。示例结构（路径指向实际输入，不是案例坐标模板）：

```json
{
  "schema": "garment-body-fit-case-v1",
  "input_state": "initial-state.json",
  "input_camera": "camera.json",
  "pose_guide": "raw-pose-guide.png",
  "pose_markers": "manually-reviewed-markers.json",
  "source_photo": "original.jpg",
  "source_mask": "mask.png",
  "region_protocol": "acceptance.json",
  "grip_case": "grip-targets.json",
  "asset_json": "human.json",
  "body": {"stages": [
    {"steps": 70, "camera_fit": false, "standing_prior": false},
    {"steps": 100, "camera_fit": true, "standing_prior": false},
    {"steps": 100, "camera_fit": true, "standing_prior": true}
  ]}
}
```

`body.stages` 逐阶段把实际输出传入下一步；每步参数和结果单独保留。这里的70/100只是本例预算示范，其他案例应按其协议选择。

手部求解预算写在 `grip_case` 的 `restarts` 与 `max_nfev`，由实际 `--case` 传入；没有会被静默忽略的 `grip.steps`。`standing_prior` 是可解释的站姿先验，只在本例输入支持时采用，不能用于实际坐姿/屈膝目标。

求解器输入协议仍需与其实际 CLI/schema 匹配。运行前检查 `--help` 和源版本，若入口不支持
某参数，修正通用适配而不是把未执行部分写成完成。`NEW_DIR` 不能覆盖历史或已评分目录。

## 功能评测与技能改进

开发期间可以搜索候选，但开发产物通过后应冻结包含可运行入口的 `skill-candidate`，
让新执行者仅凭技能与 case 输入实际重跑求解/渲染/测量和 Image Gen，不能把开发目录
复制后改名当独立技能执行。相同输入的重新执行旧技能才是新的配对基线；历史结果明确
标为 `REUSED_HISTORY`，放官方 Previous Output，不用于因果提升或耗时/token 差值。

独立评分者实际检查输出并检验反例：移动骨盆、翻转掌面、手前后分离、按视角换状态、
伪造指标或缓存、换掉生成引用。已冻结门槛不因候选失败而放宽；新门槛另记本轮前置协议。
只在全套必需断言与实际目视/三维检查都满足时报告本案例验收通过。通过一个已调案例不代表
新商品、未知姿态、真人围度或原生技能触发准确率已验证。用官方查看器展示新输出、原始
Previous Output、Formal Grades、Benchmark 和反馈；所有图库只放在原生 Output 内。

运行时固定入口为项目内 `tools/human_fit/pose_guided/{refine_body_envelope.py,fit_grip.py,runtime.py,render_mesh.py,calibrate-worker.mjs}`，配合 `web/human-studio/body-engine.js` 和同目录资源 `assets/human.json`。包装器要求提供 `--repo-root`，并核对 case 资源与运行时资源 SHA 相同；它不是离线自包含模型权重包。输出 `execution.json` 记录实际源码 SHA，防止只以 Git HEAD 代替本次未提交源码版本。

可选 `pose_guide`/`pose_markers` 由包装器实际调用 `register_pose_guide.py`：SIFT与similarity RANSAC将示意图注册到未改动原图，保存变换、内点误差、原生坐标/映射坐标、语义和可见性。配准误差不等于关节误差，`use_for_fit:false` 的示意点不能自动覆盖原图独立标注。

## 执行反馈后新增：重叠肢体的语义控制图

当同色裸模侧视使生成器混淆近/远两条手臂时，可在**同一**已冻结的真实网格与相机下，
把实际蒙皮权重归属绘成近/远臂色块，并保存可见表面锚点。骨 helper 投影可能位于皮肤后，
不能把它当可见肘/腕或指腹；控制图只显示 Z-buffer 真正可见的皮肤三角。

在匹配的项目运行时使用：

```sh
python tools/human_fit/pose_guided/render_semantic_view.py \
  --asset web/human-studio/assets/human.json \
  --mesh MODEL/final/posed.obj --camera MODEL/final/views/camera.json \
  --view side --out NEW_GUIDES/side-semantic.png
```

输出 PNG 及同名 `.json`、`.mask.png`、`.labels.png`，记录实际 asset/mesh/camera/script/image
指纹、轴、矩阵与深度语义。颜色是权重区域控制，不是精确解剖分区；本 CLI 不修改网格，
不是碰撞测试或独立评分 oracle。先验证相机矩阵、可见标签与实际表面锚点投影，不能仅
因图看起来相似就宣称与原先渲染器等价。工具按输入 view 定义读取 axis/px_per_cm/center_cm，
不硬编码图片尺寸、中心或侧面符号；传入实际 front/side/back 或自定义 view 名。

来源应分开：本次执行中提供的早期 `native_side_semantic.png` 由当时的 VTK 审查脚本实际
生成，其不可变图像/源码/receipt 仍按原来源保存。之后新增的通用 CPU CLI 经真实相机矩阵、
表面锚点和掩膜验证，是后续可复用入口；不能倒填成它早已包含在原 `skill-executed` 或
`runtime-executed` 快照，更不能改写已调用 Image Gen 的输入图来源。反馈后新增工具、
额外诊断与真实重试记录为辅助执行，不称 blind 无辅助一次成功。

## 执行反馈后补充：服务无图与安全服装重试

实际服务拒绝或无图返回要保存原始 receipt、状态和原因，`path:null` 明确不计入原生图数量。
不重复提交原受阻的解剖参考。对于本来合法的普通服装任务，可改用已着装商品参考和真实
二值掩膜/固定相机的分析性轮廓参考，清楚区分输入提示图与最终交付；最终图仍须是实际
Image Gen 原生输出，不能把掩膜、参考裁切或模拟渲染包装成新生成照片。

服务调用成功只代表生成出图，不代表任务通过。改变衣长、把提起下摆改为捏住衣服中段、
改变腕手或相机，都应由原动作/款式门槛否决并保留失败图。安全参考重试不降低这些门槛，
也不把反馈后的多次重试称为 blind 一次成功。本节是执行反馈后的文档补充；原
`skill-executed`/`runtime-executed` 快照及每次生成的真实输入来源保持不变。
