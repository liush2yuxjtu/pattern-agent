# Teagan Sites 工作室：第 14 版完整归档

[打开原站点](https://pattern-atelier-three-wasm.liushiyuxjtu.chatgpt.site) · [中文交接页面](pages/README.md) · [归档验证](../../docs/verification/teagan-sites-archive-20261118/README.md)

这里保存本次 ChatGPT Sites 纸样工作室的完整源码、运行资产、许可证和验证证据。站点源码提交为 `5fd4986222886d1e4aaa5944122eaaec397c9a2a`，对应 Sites 第 14 版。`SOURCE-MANIFEST.json` 逐文件记录原始字节数与 SHA-256；93 个受控文件原样保存，总计 14,216,626 字节。

`app/` 是独立工作副本。原站点的部署绑定 `.openai/hosting.json` 不进入归档；安装后的 `node_modules/` 与 Git 内部文件也不提交。此目录不会接管原站点。原有开源许可逐文件保留，不用仓库的一份总许可替代第三方许可。

## 当前可以做什么

FreeSewing Teagan 4.10.2 的真实命名点和贝塞尔边驱动纸样。设计意图先变为规格差量或有序编辑操作，再重新生成同源二维纸样和三维网格。基础、宽松和短身是同一个原型的参数变体。Three.js 负责显示，WASM 实际执行部分几何与形变计算。

支持二维纸样、普通三维、三维形变热图、三维折角热图四个独立开关，共 15 种非空组合；每次打开默认二维加普通三维。三维窗口有独立相机。人体为 MakeHuman hm08 CC0 参考模型。编辑包括点与控制柄、曲线与弧长、缝份、剪口、布纹、走缝、配缝优化、撤销重做、版本与工程导入导出，以及 SVG / DXF / A4 / OBJ。

袖山在固定端点、袖口和袖底缝长度的前提下修顺；三维增加内部及跨缝弯曲约束。折角直接测量真实三角面的转向角：0° 为平，90° 为直角，180° 为折回。全衣统计包括前后片、双袖及拼缝双向采样，使用固定连续 0–180° 色标；袖底邻域另列，开口边不冒充 0°。

第 14 版把尺寸草稿、纸样修订、求解任务、显示窗口和资源恢复分开管理。任务属于特定修订并独占 Worker；迟到结果不能覆盖新修改。保存和导出先提交待应用尺寸；失败及求解中撤销旧读数。`READY` 表示计算结果有效，其几何报告仍可能为 `FAIL`。

## 如何运行

需要 Node.js（本次 v24.22.1）、npm 和支持 WebGL2 的浏览器。

```sh
cd experiments/teagan_sites_studio/app
npm ci --cache /tmp/teagan-studio-npm-cache --no-audit --no-fund
npm run build
python3 -m http.server 8080 --directory dist
```

打开 `http://localhost:8080/`。`/sleeve-debugger.html` 是保留旧尖棱与修复后网格的对照检查器。停止自己启动的 HTTP 服务即可清理。默认 npm 缓存在当前受限环境不可写，因此命令明确使用 `/tmp`；不需要更改系统 HOME。

## 如何复核归档

在仓库根目录运行。完整检查需要 Python 3、NumPy、Pillow、Playwright 和 `/usr/bin/chromium`；本次使用环境中已有依赖，不自动安装浏览器。

```sh
python3 experiments/teagan_sites_studio/tools/verify-source.py
python3 experiments/teagan_sites_studio/tools/verify-archive.py --browser \
  --out /tmp/teagan-archive-verification
```

验证在临时副本中构建与运行原有测试，避免覆盖冻结的线上报告。浏览器仍执行原始测试脚本，只将证据输出目录改为 `--out`，业务断言不变。测试通过精确本地字节路由驱动真实 Chromium、WebGL 和 Worker；它验证本地恢复能力。`evidence/` 内的线上报告是此前实际请求生产站点的证据，不能把本地复跑称为本次重新上线。

## 证据与结论的范围

| 记录 | 已保留的观测 | 能说明什么 |
| --- | --- | --- |
| `evidence/state-machine/live-verification.json` | 第 14 版 50 项线上检查、80 次混合交互、实际 Worker 重算 | 状态归属、异步及失败恢复；0 JS 错误与 WebGL 警告 |
| `evidence/fold/live-verification.json` | 第 14 版 85 项线上检查、15 种视图组合 | 视图、颜色、独立相机、恢复、导出与手机交互 |
| `evidence/fold/independent-verification.json` | 独立 NumPy 重建邻接、拼缝匹配和另一角度公式 | 全量数值逐项一致；不是仅凭截图判断 |
| `app/dist/diagnostics/` | 修复前后原始网格、人体和来源清单 | 可重新测量的历史正负例 |
| `evidence/screenshots/` | 文件名明确 v13 / v14 | v13 是折角全衣截图；v14 状态机改动不改变几何。`injected-error` 为受控故障测试 |

基础款归档网格有 27,227 条内部边和 720 个拼缝采样。全衣最大转向角 90.19343°；袖底 15 mm 邻域最大 58.86470°；排除该邻域的袖片内部最大 31.90207°，超过项目 45° 观察门槛的内部边为 0。全衣超过 45° 的 16 项包含拼缝双向采样，不能当作 16 个独立缺陷。详细定义和旧新同材质位置对照见中文页面。

几何与软件通过不等于专业版师签核、真实面料力学、压力或个人合体通过。这里只是静态约束组装和当前参考人体的几何检查。面料标定、连续动态、自碰撞完整性及真人试样未验证。历史另一 T-shirt 实验的最大接缝间隙 **7.6455 mm** 和 **20 个非相邻面相交**仍是 **FAIL**；其物理合体仍是 **NOT_RUN**，本归档不覆盖该结果。

`app/README.md` 与部分旧报告是逐轮开发记录，其中早期关于三视图、人体不参与接触等描述属于历史状态；本文件和三篇交接页描述第 14 版。保留原文件字节是为了可追溯，不能混用不同版本的结论。
