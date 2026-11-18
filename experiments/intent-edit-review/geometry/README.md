# 真实DXF绑定的静态三维装配示意

五个JSON分别读取基准及四个改版的真实DXF和对应YAML。未读取旧GLB，也没有对旧模型作整体缩放。图形单位仍为未标定的U。

```sh
python experiments/intent-edit-review/geometry/build_meshes.py
python experiments/intent-edit-review/geometry/verify_meshes.py --output work/intent-edit-review/geometry/verification.json
```

依赖已有的 NumPy、SciPy、PyYAML。构造仅复用现有服务的 `parse_dxf`、`triangulate` 和纯几何 `harmonic`。不调用强制物理单位、修改原始肩侧袖边、分配40/60吃势的 `register`、`patterns` 或 `sewn.build`。

## 模型格式

每个 `*.mesh.json` 包含源DXF/YAML路径与SHA-256、共用姿态、U单位、未标定状态和五个展示面片：前片、后片、袖片展示实例A/B、领条。袖实例不等于批准裁数或已确认穿着者左右。

每片含 `positions`、`triangles`、`normals`、`uv`。`uv`是片内U坐标，加上 `binding.dxf_layout_origin_U` 回到DXF总图。前 `boundary_vertex_count` 个点通过 `boundary_sources` 精确对应实际DXF的多段线序号和顶点序号；后续点是实际轮廓域内新三角网格的内部点。

展示采用声明内圈，但不将其认定为已批准净样。原始轮廓中小于0.05U的重复或近重复连接点在 `binding.joins` 记录，保留前一个真实源顶点，跳过后一个近重复端点；没有悄悄修订源DXF。内圈轮廓、UV及三角剖分均来自各自DXF。

`manifest.json` 保存每个JSON的字节数、模型SHA、源DXF/YAML SHA及构造脚本来源校验。浏览器应从这些原始JSON字节解析并校验，使用同一相机中心与比例，不能分别自动缩放每个改版以抵消真实尺寸变化。

## 可复算的展示映射

- 衣身：实际边界按固定基准姿态映射为前后半壳，边界值保存在 `construction.boundary_targets_U`。内部点按三角网格邻接的均匀Laplacian调和插值，再按实际UV到边界的距离添加 `48 × (1 − exp(−distance / 35)) U` 的前后鼓起；边界保持精确目标。
- 袖片：实际边界映射到纵向距离u和环角θ，内部这两个参数作同样的调和插值。静态管截面由实际左右袖底线间宽度除以2π取得半径，纵向长度来自真实腋下到袖口的纵向跨度；两侧弧长另作记录。根部椭圆在45U内平顺过渡到圆截面，姿态方向由基准一次确定。袖口变宽改变实际三维截面但不无故缩短展示轴，袖长变更使实际三维轴长恰好增加20U。
- 领条：实际前后领口经同一衣身边界映射组成当前领圈路径；领条横向沿此路径摆放，纵向采用明确的展示折叠（高度为平幅一半、径向错开为平幅5%）。新领口改变领圈路径，领条也改变。这个映射不是材料拉伸仿真或批准的领条工艺。

五例共用一次确定的姿态；未改裁片的顶点、UV、三角形和法向数据精确相同。数值自检会检查实际源绑定、非退化面、单位法向、四种几何响应、未改片保持及错误DXF/YAML配对拒绝。独立审计和真实WebGL/离线HTML验收由交付流程另行完成。

## 验收范围

这是便于理解二维改版的可旋转静态装配示意。`physical_fit`、`cloth_simulation`、`sewing_validation` 均为 `NOT_RUN`。净裁角色、毫米换算、材料、装袖前后、实际缝合、相交、穿着合身与生产批准不由可见模型代替。
