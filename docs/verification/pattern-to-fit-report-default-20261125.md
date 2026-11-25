# Pattern to fit 报告默认版式复验

基线提交为 cb39d50caf11ae7c2b3803e31b3c4c536e2f4fb3。已验候选的 pattern-to-fit 技能树为 5196d775491aa8c33b73336f9966e1d6fd342480。按仓库 /verify 执行本地检查。

1. 用 Codex quick_validate.py 检查 pattern-to-fit。技能入口通过。
2. 从可复制模板生成潮线 A 码复验报告。用 scripts/publish_report.py 生成单文件 Markdown。9 张内嵌图与源图逐字节一致。
3. 用 evals/grade-fit.py 对照证据清单。报告格式通过。服装证据维持 PENDING。退出码为 2。
4. 用同一评分入口重放 22 个既有用例。图表证据判定、报告判定和退出码与基线逐项一致。
5. 用 Markdown-it 将仅含交付 Markdown 的目录渲染为预览。Chrome 在 1024 和 390 像素宽度离线打开。TLDR、两张关键对照图和分诊末节无需展开即可见。五视角、代理实施和技术证据三个区默认收起。展开后可见 9 张图和两张验收表。三个区均可重新收起。

版式验收为 PASS。此复验复用已有试穿证据。它未重新求解，也未实测 Codex 侧栏。
