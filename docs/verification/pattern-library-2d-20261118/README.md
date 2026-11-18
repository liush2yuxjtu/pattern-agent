# 二维纸样与来源款式反馈验收 · 2026-11-18

本地验收通过。浏览器在 Pages 的项目路径下打开 26 张图卡，检查组合筛选、空结果、键盘放大与焦点恢复、手机链接和原图入口。二维入口链接到独立的三维对照页，九个渲染视角、旧分享链接、三个改版状态和下载校验均通过。比对 19 个实际平面 OBJ 和 4 个原始 DXF 的 SHA-256。用网页下载的编辑器 ZIP 重新生成补丁，补丁、DXF、SVG 和量测报告与包内样例字节一致。[候选版本与浏览器验收](candidate.json)

反馈按发布方和款式分组。浏览器核对原始评论、批量评论展开和翻页、按部位检索、款式链接和原网页跳转。对照源压缩档验证 40,438 个片段与其源评论和商品 ID。隔离 PostgreSQL 与托管 Supabase 回读均得到 5,451 个来源和款式分组。两个数据集共享的一个匿名商品 ID 分别归组。Zappos 的 Dickies Eisenhower 男式夹克有三条观察。公开浏览角色无专用 schema 和新视图的读取权限。[本地与托管数据库回读](feedback-source-styles.json)

从仓库根目录运行本地验收。浏览器使用 Playwright 驱动的 Chromium，截图和原始下载保存在被 Git 忽略的 work 目录。

    export PYTHONDONTWRITEBYTECODE=1
    (cd web/pattern-library/editor && python -m unittest discover -s tests -v)
    python scripts/build_pages.py
    python web/pattern-library/source/verify_gallery.py --directory dist --output work/pattern-visual/verify/local-gallery
    python web/pattern-library/source/verify_catalog.py --directory dist --output work/pattern-visual/verify/local-catalog \
      --source work/corpus-expansion/sources/nicapotato.zip --fit-source work/corpus-expansion/sources/fitdata.zip
    python scripts/verify_pages.py --output work/pattern-visual/verify/local-pages

[二维图册](https://liush2yuxjtu.github.io/pattern-agent/pattern-library/) · [按来源和款式看反馈](https://liush2yuxjtu.github.io/pattern-agent/pattern-library/catalog/?view=feedback) · [本地验收说明](../../../.agents/skills/verify/references/pattern-library.md)
