# 独立物理实验 GitHub 与 Pages 交接核对

日期：2026年11月19日，北京时间。

本轮交付核对通过。物理项目已有独立代码目录、公开路由和完整证据；本轮新增两处 ChatGPT Pages 记录及仓库的返回入口。物理计算和网页运行代码没有改动，既有真人合身 NOT_RUN、三个 PROFILE_REQUIRED 与历史 FAIL 结论保留。

## 从这里打开

| 内容 | 入口 |
| --- | --- |
| 整个实验的统一目录 | [experiments/intent-edit-review/README.md](../../../experiments/intent-edit-review/README.md) |
| 独立物理项目及详细复现说明 | [physics/README.md](../../../experiments/intent-edit-review/physics/README.md) |
| 公开应用 | [GitHub Pages 物理实验台](https://liush2yuxjtu.github.io/pattern-agent/intent-edit-review/physics/) |
| 完整中文原型规格与二维原件 | [input-spec.yaml](../../../patterns/fitted-tshirt/input-spec.yaml) · [input.dxf](../../../patterns/fitted-tshirt/input.dxf) |
| ChatGPT Pages 项目总页 | [原型改版与物理实验独立交付](https://chatgpt.com/space/page_6afa77cb1b64819183bc62be09296842) |
| ChatGPT Pages 编辑验收记录 | [原型规格改版与独立物理实验交付](https://chatgpt.com/space/page_957e91c1b9388191ae2da7a7b649f626) |

## 候选与验证范围

本轮开始时工作树为 `79298c517656460f8f0837b9642f13111c4c8a82`，检查远端后以 `git merge --ff-only origin/main` 同步至 `3686e1994b63cb4fce95c464165754fadce0410d`。远端增加的是 CLO 试身线稿文档与技能，不涉及本实验网页或计算记录；没有覆盖其他工作的改动。

按根 `AGENTS.md` 与 `.agents/skills/verify/SKILL.md` 执行本地 `/verify`，读取 `references/intent-physics.md` 的范围约定。候选是上述基准加本次交付文档、两处 Page 保存后读回及公开字节收据。仓库改动只含 Markdown / JSON；运行时重复验收为 **SKIP（文档变更，无新增可执行行为）**。公开应用与原型文件的字节核对、外部 Page 的写入后读回分别有实际证据。

执行并记录的核对：

- `git fetch origin main`、`git rev-parse HEAD origin/main`、`git status --porcelain`，检查并同步远端；提交前再次检查远端。
- `gh api repos/liush2yuxjtu/pattern-agent/pages` 与 `gh api 'repos/liush2yuxjtu/pattern-agent/actions/workflows/pages.yml/runs?per_page=2'`，读取既有静态发布配置与实际发布回执。工作流只作发布，没有新增或依赖 CI 验收。
- 使用 `scripts/playwright_http.new_api_context` 的实际 HTTPS GET，保留 TLS 校验；对公开 HTML 和两份真实 GitHub 原件响应体计算 SHA-256，与候选磁盘字节比较。完整 URL、状态码、长度和摘要见 [public-route.json](public-route.json)。这不是新的浏览器交互或物理验收。
- 两次 `chatgpt_space_edit_page` 使用原有相邻块定位新增章节；随后分别 `chatgpt_space_read_page`，比较原有块的 ID、哈希、原文与标题，并检查全部新增块存在。收据和新增正文见 [pages-readback.json](pages-readback.json)。
- 提交前执行 `git diff --check`、检查上述 JSON 和仓库相对链接；确认应用 HTML、计算记录及旧网页字节无改动。

本轮 JSON 解析通过；最终两份相关 README 的36个仓库相对链接全部存在。三个实际公开响应均为200，摘要全部相同。两处 Pages 合计269个旧块保留、19个新块读回。`git diff --check` 无错误；本次交付文档变更没有修改 `web/` 或物理 `results/`。

## 本次重新发布与最终 Pages 回读

交接记录已在 [f5b875a](https://github.com/liush2yuxjtu/pattern-agent/commit/f5b875a52d7fa69cb57712d652191dbfa493c848)提交并推送。随后手动调用既有静态发布流程，[发布44450109647](https://github.com/liush2yuxjtu/pattern-agent/actions/runs/44450109647)成功。公开 `build.json` 的提交为该精确候选；发布前后2207项文件摘要全部相同，公开应用重新 GET 为200且字节相同，见 [republication.json](republication.json)。`build.json` 的发布元数据随版本更新。

部署后，两处 Pages 的本次交付段落又补充了上述精确提交与发布链接。项目总页最终为第29序列，编辑验收页为第17序列；逐段读回通过，见 [pages-publication-readback.json](pages-publication-readback.json)。最终回执以文档提交封存，网页运行字节仍对应已经公开核实的 f5b875a。

封存前再次读取远端，发现并以 fast-forward 保留了其他工作的 `34b7cc2ed404f3742d99082a8b4a8668438c18ce`（新增 Garment GPU Studio 独立目录）。该提交不改本实验目录或路由。最终封存候选为该远端版本加本轮三份交付文档与回执；再次按 `/verify` 检查 JSON、36个相对链接及文档差异，运行时重复验收为 SKIP。

## 实际结果与保留事项

公开 HTML 仍为46,107,845字节，SHA-256 为 `80ccaf68114ad1d650ccfec248c812cc77d31ab5c9383e56d4904f18f617c872`。原型 YAML 与 DXF 使用仓库中的真实原件地址，原始单位仍是未标定的 U。已有公开浏览器操作及六份真实下载的逐字节核对见 [上一轮完整公网证据](../intent-physics-20261118/svg-fallback-v2/live-public/README.md)。

首次额外试探的 `/patterns/fitted-tshirt/input-spec.yaml` 与 `/patterns/fitted-tshirt/input.dxf` 返回404；[原始失败收据](exploratory-unpublished-paths.json)保留。检查 `scripts/build_pages.py` 确认它只复制 `web/` 和直身裙附件，不会自动发布上述仓库目录。这两个猜测网址没有写进 Pages。交接文档使用实际 GitHub 原件链接，应用下载使用 HTML 内嵌原件；后者已有独立浏览器下载证据。

项目总页在第28序列新增14个原生块，原有103块逐字保留；编辑验收页在第16序列新增5块，原有166块逐字保留。两页均保留标题、全部旧块与原有指引。Pages 的保存内容已核对；本轮没有重新检查 Pages 的渲染布局。

原型与袖口加宽各61帧的既有离散验收 PASS 不等于材料实测、真人合身、连续时间无碰撞或生产批准。网页重放真实保存帧；实际物理求解在原生程序中完成。没有把其他三例改版的三维配置阻塞写成通过，也没有替换历史失败。
