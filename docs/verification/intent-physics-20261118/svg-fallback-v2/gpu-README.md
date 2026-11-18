# WebGL 实际颜色缓冲独立复核

权威最终结论 **PASS**，证据为 `final/receipt.json`。已完成36项真实GL颜色VBO读回，最大RGB绝对误差 **1.4927182889756807e-7**（门槛2e-6），耗时49.60秒，page/console错误均为0。36份原始color.f32及12张frame60实际场截图均已保存并逐个重验SHA。

最终HTML为46,107,845字节，SHA256 `80ccaf68114ad1d650ccfec248c812cc77d31ab5c9383e56d4904f18f617c872`，运行前后相同。四个viewer实际源码SHA、两案例原始input/trajectory、HTML内全61帧全部数组以及所有YAML/DXF/diff/patch原字节均已绑定。receipt SHA256为 `eac78c7b2e42164cbff57c68a68e45317e72098b007af16000bd584f94075a10`。

完整复现命令见 `command.txt`，摘要见 `summary.json`。旧571…试跑仅保留历史诊断，不替代此次权威结果。

实际属性布局：color location=3、FLOAT vec3、stride=12、offset=0、divisor=0；baseline完整draw索引数21558、颜色float数13161，cuff分别21618和13197。每项均在独立的新draw sequence后读回，ARRAY_BUFFER恢复36/36。

已目视复核最终baseline应力图与cuff应变图：人体与服装真实可见，显示所选场、图例和frame60。此目视结论只覆盖显示是否可用，不代替数值缓冲比对。

## 读取路径

通过 Playwright 的 `page.add_init_script` 仅预加载观察器。在原生 WebGL2 `drawElements` 执行之后，按 `TRIANGLES`、完整 `nt*3` 索引数量和 `nv*3` 颜色数组长度识别实际布片 draw。查询当前 program 的 `color` attribute，验证 FLOAT vec3、stride=0或12、offset=0、非 normalized、非 integer、divisor=0，然后对其实际绑定 GL buffer 执行 `getBufferSubData`。临时 ARRAY_BUFFER 绑定始终恢复；不上传、覆盖或改写颜色、位置、索引或 shader。

颜色期望值只由原始 trajectory.json 的 fields/folds/contacts 经独立 NumPy 调色板插值和面到顶点平均计算。没有调用 `physicsReview.surface().colors`。每项均在 UI 切帧/切模式后 arm 新 token，等待更新 draw sequence，不把旧读回缓存当本项结果。

两案例 × 帧0/30/60 × cloth/strain/stress/fold/contacts/seams，共36项。RGB最大绝对误差门槛固定2e-6。

## 范围

上下文为 ANGLE / Vulkan / SwiftShader 软件渲染，不认证物理硬件GPU。读回的是实际 GL 颜色属性 VBO，并非最终光照/色彩空间变换后的片元输出色度测试。实际场截图另行保存。此报告不替代整衣物理、材料实测或真人合身验证。

## 已保存对照

- `pilot571/stride-verified/receipt.json`：旧571fd146…HTML的真实36项试跑PASS，最大RGB误差1.4927182889756807e-7，耗时127.4秒；不是新版权威结论。
- `pilot571/results/receipt.json` 和 `pilot571/run.log`：初次探针对stride=0的过窄假定被实际stride=12明确拒绝，保留原失败记录；修正为等价packed FLOAT3布局后通过。
- `wrong-html-hash-control/receipt.json`：全零期望SHA被实际拒绝，exit=1、0项draw核对；该FAIL是正确拒绝故障对照。

原始颜色读回保存为 `<case>-frame<frame>-<mode>.color.f32`，float32小端，Nv×3；每个frame60模式另有实际页面PNG。receipt逐项绑定其SHA、当前GL布局、draw sequence、program/buffer身份及软件渲染器信息。
