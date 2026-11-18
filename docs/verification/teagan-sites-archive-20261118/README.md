# Teagan Sites 第 14 版归档验证

**PASS — 完整源码可从新目录恢复，原有软件及折角检查和实际本地浏览器流程通过；三篇 Pages 已逐块读回。**

本次工作只归档，不重新部署原站点。[归档入口](../../../experiments/teagan_sites_studio/README.md) · [Pages 与 Markdown 副本](../../../experiments/teagan_sites_studio/pages/README.md)。

## 候选与方法

原始 Sites 第 14 版源提交为 `5fd4986222886d1e4aaa5944122eaaec397c9a2a`。pattern-agent 开始时 main 为 `e835ae7fbedd9426b159bfed17d6eae43a7cf23a`；先保留并 fast-forward 了独立 Supabase 提交 `fc78146952f7d48bd9212e7466aedef7bdf29f1b`。最终提交前再次检测到远端推进，旧 HEAD 的普通 push 被拒绝，没有修改远端；随后取回并 fast-forward 了另一 cloth-lab 证据提交 `324e18a`。两次并发更新均不触及本应用或所改的验证入口，已保留，无重写或覆盖。

候选以 `candidate.json` 的父提交、源清单哈希和逐文件 `candidate-files.json` 标识。运行 root `/verify` 及新增的最近目录 [verify 技能](../../../experiments/teagan_sites_studio/.agents/skills/verify/SKILL.md)，复用原有断言和独立验证器；在临时副本构建，冻结的 `app/` 文件保持原字节。

## 实际执行

```sh
cd experiments/teagan_sites_studio/app
npm ci --cache /tmp/teagan-archive-npm-cache --no-audit --no-fund
cd ../../..
python3 experiments/teagan_sites_studio/tools/verify-source.py
python3 experiments/teagan_sites_studio/tools/verify-archive.py --browser \
  --out /workspace/work/teagan-archive-check
```

本环境 Node v24.22.1、npm 11.9.0，已有 Python、NumPy、Pillow、Playwright 和 Chromium。首次未指定缓存的 `npm ci` 因默认 `/home/agent/.npm/_cacache` 不可写以 ENOENT 退出；改用授权的 `/tmp` 缓存后 25 个包安装成功，不修改 lockfile。`ego-browser skill` 返回 command not found，按仓库 Playwright 优先流程使用已有 Chromium，不安装新浏览器。

| 复核项 | 本次观测 |
| --- | --- |
| 源文件与冻结线上资产 | 93 文件逐项字节数和 SHA-256 匹配；两份线上记录的 12 个资产哈希逐项匹配 |
| 构建 | WAT→WASM 与三个 JS bundle 成功，构建后全部 93 个源文件哈希仍一致 |
| 原型与同源几何 | 原有三预设、+50 mm 衣长/+20 mm 袖侧、无关裁片保持、展开往返、导出尺寸检查通过 |
| 专家编辑与负例 | 62 项通过；见 `expert-report.json` |
| 生命周期模型 | 23 项通过，含 5,000 次确定性乱序转换 |
| 折角解析控制 | 37 项通过，含 0–180°、拼缝、2 mm 间隙和无效几何负例 |
| 独立折角复算 | NumPy 从原始邻接/配缝重建，用另一半角公式逐项复算；旧 FAIL 保留 |
| 实际本地状态机浏览器 | 44 项通过，80 次混合交互、故障注入、异步读取、重试及最后真实 Worker 求解 |
| 实际本地四视图浏览器 | 79 项通过，15 种非空组合、颜色与定位、独立相机、恢复、导出及 390 px 手机 |
| 控制台 | 两份浏览器报告均 0 未处理 JS 错误、0 WebGL 警告 |
| Pages | 三篇共 68 个正文块通过原生接口读回，与创建正文逐块完全一致；未做 Pages 排版截图验收 |

完整子命令、退出码、耗时在 `receipt.json`，逐项断言在同目录日志与浏览器 JSON。浏览器通过 HTTPS 测试源的 `route.fulfill` 读取临时副本的精确构建字节，真实运行 WebGL 与 Worker；这属于 **LOCAL**。本次未重新做生产站点网络/登录检查；归档中的旧 LIVE 50/85 项报告还各含 6 个生产资产哈希，所以计数不同。

## 可见结果与边界

已查看 `browser-views/four-views-final.png`：二维净样、普通穿着人体、形变热图、全衣折角热图均实际显示；折角呈多种连续颜色。已查看 `browser-state/mobile-state-pass.png`：390 px 手机纵向窗口中人体和折角图可见，无水平溢出。`failure-retry.png` 是受控错误注入，不是线上持续故障。

真实重算与基准缓存全顶点最大差为 `2.1510571102112408e-15 m`。独立修复后网格 27,227 条内部边与 720 个拼缝采样，角度最大差 `2.1316282072803006e-14°`，拼缝最大采样间隙 `0.33639170585211314 mm`；这不是完整穿着检查中另一个全配缝采样最大间隙的替代值。

旧尖棱的 161 条袖内超限边及 FAIL 被负例断言保留。全衣 90.19343° 最大角及袖底邻域 58.86470° 不隐藏；排除该邻域的历史袖内验收最大 31.90207°，无 >45° 内部边。角度随网格粗细和位置改变，不是一项普遍的服装好坏判据。

另一个历史 T-shirt 实验仍为 **FAIL：7.6455 mm 接缝间隙，20 个非相邻面相交**。物理合体 **NOT_RUN**；面料力学、压力及真人试样 **NOT_CALIBRATED / NOT_RUN**，本次 PASS 不扩大到这些范围。

## 清理与持久化

测试临时应用由上下文管理器自动清理，两个浏览器脚本均关闭自己创建的 Chromium；未启动新的 HTTP 服务。只把白名单源码、许可证、报告、截图和可编辑文档加入提交，不含 `.openai/hosting.json`、node_modules、凭据或 `.git`。

提交前检查差异、链接与候选清单，按仓库规则直接 commit main，检查最新远端后非 force push，再通过 GitHub 原生读取提交及关键文件核对。最终提交哈希由实际提交结果提供，避免把尚未生成的提交号写入自身造成循环依赖。
