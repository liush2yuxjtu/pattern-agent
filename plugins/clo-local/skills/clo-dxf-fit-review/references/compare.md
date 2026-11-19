# 用同一网格核对多姿势结果

先按 clo-fit-export 的 SKILL.md 逐个姿势运行，例如：

```sh
python /path/to/clo-fit-export/scripts/export_fit.py relaxed/cloth.glb --out-dir relaxed/fit --project relaxed/shirt.zprj --stress-front relaxed/stress_front.png --stress-back relaxed/stress_back.png
```

仅在核对 GLB 裁片顺序后才加 `--piece-ids`。若原始坐标单位不是毫米，传入实际转换参数。用 CLO 裁片包围尺寸和二维面积验证平面 UV 的尺度。统一各姿势的面积过滤、伸长阈值、折角阈值及图例。压力截图单独采集，export_fit.py 不计算压力。

把以下结构写入工作目录的 poses.json。路径相对于该 JSON 文件，也可用绝对路径。

```json
{"poses":[
  {"name":"自然垂臂","glb":"relaxed/cloth.glb","statistics":"relaxed/fit/fit_statistics.json"},
  {"name":"侧平举","glb":"level/cloth.glb","statistics":"level/fit/fit_statistics.json"}
]}
```

在已能运行 clo-fit-export 的 Python 环境中执行：

```sh
python /path/to/clo-dxf-fit-review/scripts/compare_poses.py poses.json --out comparison.csv
```

脚本默认在本技能的同级目录寻找 clo-fit-export，可用 `--fit-skill /path/to/clo-fit-export` 指定。它核对网格文件摘要、原始平面坐标、三角形编号、裁片 ID、单位和阈值，再按姿势与裁片输出数据。输出使用新文件名。它不推断裁片名称、不做人体区域标注，也不从颜色估算压力。若重划网格或更改纸样，保留各自独立报告；需要直接对比时重新从相同基准导出。新的 CSV 用于同版不同姿势的比较，不用于比较已改动的版型。

CSV 中 strain_p50_pct 与 strain_p95_pct 是按原始布料面积加权的伸长百分位，area_above_threshold_pct 是超过设定伸长阈值的面积占比，fold_p95_deg 是按可测内部边统计的折角第 95 百分位。numeric_stress 说明是否存在已记录的 CLO 应力样本。
