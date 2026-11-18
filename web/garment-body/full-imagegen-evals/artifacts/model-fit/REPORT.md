# 本轮模型实际执行报告

最终选择 `final/`（候选neutral-waistband-semantic），不是warm-start或hand-refine。完整真实模型state/neutral/posed/相机/多视图和模型实测JSON/CSV均已保存。整体原图姿态/视觉匹配 **FAIL**，绝不以文件齐全、低腕点残差或22项编辑器测试当成完美提衣姿态。

## 实际执行

原图1000×1276；新ImageGen raw pose guide1110×1417，复制到reference/imagegen-pose.png后冻结。实际SIFT+Lowe0.72+similarity RANSAC：153匹配、120内点，均值1.476333px、P953.342754px。标记是手动种子定位的示意衣物表面点，非detector/真人关节真值。原始照片未warp。全分辨率GrabCut3次迭代重新生成参考掩膜，历史同源mask仅作初始化；577538前景像素，较seed改变2003像素。

本轮5候选实际执行并保留：new-guide-round-1（历史warm start，初始不称neutral）、neutral-new-guide（零大骨架角+M170尺寸）、neutral-upright-refine（修正累积脊柱前倾）、neutral-hand-refine（局部手臂/腕对照，未选）、neutral-waistband-semantic（低腰衣物表面代理从Y105改Y95，最终选择）。每个候选独立目录，不覆盖失败轮次。调用源和日志在fit-*.py/fit*.log。真实肩宽控制37→36.4cm，其余胸腰臀保持先验；肩/臂长度坐标搜索实际重建形变，无法改善的候选不会伪造参数变化。关节角按0.1°保存，163骨骼完整pose。

最终源照片投影重新从真实OBJ计算，固定最终camera比较初始/最终：IoU0.685816→0.821961，Dice0.813631→0.902281，裸体在衣物外像素比例12.5944%→3.7157%。这些只是衣物/头发包络指标，不是尺寸准确率。7区域中肩/双臂/躯干的包络启发式通过，腰臀左P9532px、右36px且外溢10.38%，仍否决整体二维吻合。原图单视角不足以恢复隐藏腿/背/真实围度。

最终侧视仍是杯状/离体手姿，真实skin ray检查L仅455/1424覆盖、R1424/1424，已覆盖0inside，但L最小前间距18.44cm，绝不代表服装捏合。完整手势/服装接触未通过，物理布料NOT_RUN。对应同一个final state/pose/mesh导出front/side/back/pose/depth，只有观察相机变化。

Human Studio真正导入final state，浏览器实际改腰围+2cm保持全pose，再改左上臂+7°只改变posed顶点、中性测量不变；实际下载state/neutral/JSON/CSV、重导入恢复、错误单位拒绝，22checks PASS（editor-probe/report.json与截图）。编辑副本独立，不覆盖最终state。

主要尺寸重新从最终保存neutral.obj测得，带源哈希、带尺路径/标志点定义、残差和CSV；不是dimensions/cached measuredNeutral抄写。170cm等只表示假设avatar几何，不是真人实测。旧export_evidence生成的cache字段已命名measurements.engine-diagnostics.json，仅诊断，不作为主要尺寸。

ImageGen六图已经由root实际生成，但先于此final拟合；真实输入状态见上层run.json，各视图可能存在生成几何不一致，交给独立grader判定，不能把此final-state反写成生成输入。执行代码/输出全部保留。原生Claude触发仍未测；本轮是独立子代理按技能的真实功能执行。

## 复跑

从项目根执行，workspace不改名可直接运行：

```sh
python [model-fit]/prepare-pose-targets.py
python [model-fit]/fit-neutral.py --resume [model-fit]/neutral-start --frontal --label replay-neutral --steps 65
python [model-fit]/fit-upright.py --resume [model-fit]/iterations/replay-neutral --frontal --label replay-upright --steps 65
python [model-fit]/fit-waistband.py --resume [model-fit]/iterations/replay-upright --frontal --label replay-waistband --steps 65
python tools/human_fit/pose_guided/export_evidence.py --candidate [model-fit]/final
python .agents/skills/garment-body-six-view/scripts/export_body_measurements.py --state [model-fit]/final/final-state.json --asset-json web/human-studio/assets/human.json --neutral-mesh [model-fit]/final/neutral.obj --posed-mesh [model-fit]/final/posed.obj --out [model-fit]/measurements.model.json --csv [model-fit]/measurements.model.csv
node tools/human_fit/verify_measurement_export.cjs --state [model-fit]/final/final-state.json --out [model-fit]/editor-probe-replay
```

`[model-fit]`为本文件所在目录。新label避免覆写已评分文件。Python依赖numpy/scipy/opencv，Node校准使用真实Human Studio body-engine.js/human.json。
