# 纸样与反馈资料库验收 · 2026-11-18

本地候选 PASS。[浏览器回执](browser-report.json) · [桌面纸样目录](cad.png) · [手机反馈定位](mobile.png)

- 核对已有 38 份原件和浙江大学研究档案新增的 24 份 CLO 工程。每个研究成员已解包并比对原生文件头、长度和 SHA-256。新档案包含 17 份参考工程及 7 份同款变姿态工程。Google Drive 服务器复制回读得到 1,208,878,562 字节。原生 CLO 重开待验证。
- 访问 93 条有出处的纸样记录，其中 62 份原件具唯一的文件哈希，31 条是 Open+Pattern 发布方入口。用浏览器分别筛选 17 份 PRJ、16 份 ET PRJ 和 24 份浙大 ZPRJ。对空结果和「男式连帽衫」的 3 项结果做了检查。
- 遍历 298,820 条源记录，291,248 条有正文。37,515 条评论包含可复核线索，40,438 条批量结果全部与源文件索引、产品 ID 和规范化证据片段匹配。另有 63 条人工整理观察。合身与量测目标待确认。
- 本地浏览器从图册进入目录，实际下载两类纸样表及两类反馈表，比对四个 SHA-256，检查了分页、口袋筛选和手机直达单条记录。初次 360 px 验收发现来源下拉框溢出，已约束下拉框宽度，复测通过。
- 原图册既有裁片、9 个视角、改版图和工作台文件下载通过回归。老首页、原直裙和旧 T 恤工作台的浏览器使用流程通过回归。

```sh
node --check web/pattern-library/catalog/catalog.js
python scripts/build_pages.py
python web/pattern-library/source/verify_catalog.py --output work/corpus-expansion/check --source work/corpus-expansion/sources/nicapotato.zip --fit-source work/corpus-expansion/sources/fitdata.zip
python web/pattern-library/source/verify_gallery.py --output work/corpus-expansion/regression-gallery
python scripts/verify_pages.py --output work/corpus-expansion/regression-home
git diff --cached --check
```

[复现与来源](../../../web/pattern-library/catalog/README.md) · [项目验证流程](../../../.agents/skills/verify/references/pattern-library.md)

## 公开验收

GitHub Pages 发布提交 `cfb9efdae96d0ccc24e45ef769ad49f75ec75061`。无登录浏览器在公开站完成目录筛选、分页、手机直达、四项实际下载和图册回归，下载哈希与本地候选相同。 [公开资料库](https://liush2yuxjtu.github.io/pattern-agent/pattern-library/catalog/) · [发布运行](https://github.com/liush2yuxjtu/pattern-agent/actions/runs/44256818976)

[发布回执](live/publication.json) · [目录验收](live/catalog-browser.json) · [图册回归](live/gallery-browser.json)
