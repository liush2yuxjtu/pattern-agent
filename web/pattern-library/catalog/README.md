# Pattern Agent 纸样与版型反馈资料库

[浏览全部纸样](https://liush2yuxjtu.github.io/pattern-agent/pattern-library/catalog/) · [按部位筛选反馈](https://liush2yuxjtu.github.io/pattern-agent/pattern-library/catalog/?view=feedback)

## 纸样原件

62 份文件按 SHA-256 去重。原件类型包括 39 份 ZPRJ、17 份 PRJ、4 份 DXF 和 2 份 ZPAC。另列发布方提供的 31 个款式入口。网页逐条显示格式、来源、研究工程变体和文件核验状态。

- 初版 38 份原件来自 ET 官方学习版、Virtual Fashion Lab、Learn 3D Fashion 和 Pattern Agent。17 份 PRJ 含 16 份 ET 学习文件和 1 份项目原型。项目原型的创建软件待确认。[ET 官方下载页](https://www.etsystem.cn/News/detail.html?id=1039) · [初版原件索引](../data/pattern-assets.csv)
- 新增 24 份 ZPRJ 为浙江大学研究团队公布的 CLO 5.2 原档成员，含 17 份参考服装工程和 7 份同款变姿态工程。男式连帽衫、运动套装、休闲裤、旗袍、Polo 裙、礼服和衬衫等均有可查成员。已解包、核对原生标记和计算哈希。CLO 原生重开待验证。[作者档案](https://github.com/Dancingmader/3D-High-quality-Garment-Dataset) · [论文](https://doi.org/10.1016/j.cagd.2021.102020)
- 31 个 Open+Pattern 源入口列出了发布方标注的 DXF 或 CLO 项目格式，按发布方流程获取。收录范围为服装款式。[发布方的 CC BY 4.0 说明](https://openpattern.io/) · [纸样页面](https://openpattern.io/pattern-library/)

[下载原件索引 CSV](cad-origins.csv) · [下载发布方入口 CSV](cad-publisher-links.csv)

## 评论和变体请求

三套数据覆盖 298,820 条源记录，其中 291,248 条有正文。筛出 37,515 条含改版线索的评论，提取 40,438 条可筛选的部位或变体线索，另有 63 条附原网页的人工整理观察。

批量记录用原数据文件的零基索引回找评论，保留命中的英文片段、产品 ID、部位、候选改法、量法和要保护的部位。同一商品下重复的原文合并，每条评论可以涉及多个部位。中文的改法、量法和保护项是候选操作，目标数值留待确认。

- Women's E-Commerce Clothing Reviews 由 Nicapotato 发布，许可为 CC0。2,966 条评论命中，保留原文件行号。[数据源](https://www.kaggle.com/datasets/nicapotato/womens-ecommerce-clothing-reviews)
- Rent the Runway 有 27,752 条评论命中，ModCloth 有 6,797 条。Rishabh Misra、Mengting Wan 和 Julian McAuley 的研究发表于 RecSys 2018，所用版本由作者在 Kaggle 以 CC BY 4.0 发布。此处保留命中片段和派生标签，去除用户标识等字段。[数据源](https://www.kaggle.com/datasets/rmisra/clothing-fit-dataset-for-size-recommendation) · [论文](https://cseweb.ucsd.edu/~jmcauley/pdfs/recsys18e.pdf) · [许可](https://creativecommons.org/licenses/by/4.0/)
- 男装、童装和纸样试作者观察按条人工整理。每条保留原网页、定位短语和可用量法，可能包含同一条评论的多个问题。[人工整理 CSV](review-notes.csv) · [候选意图 YAML](review-design-intents.yaml)

[下载批量反馈 CSV](review-signals.csv) · [查看批量统计](summary.json)

规则筛选覆盖具体裁片位置、尺码一致性、面料、工艺和明确的变体表达。它适合找候选需求和抽取样例，应用前需看原评论并确认归因。同一套评论的数量无法代表整个市场。批量来源以女装为主，男装和童装的证据在人工整理条目中可查。

## 重建目录

以下命令从仓库根目录运行。原始输入从上面的作者入口获取。浙江大学的 `dataset.7z` 解出的 24 个工程保留各自在档案中的完整相对路径。Open+Pattern 列表来自发布方的公开商品接口。

```sh
python web/pattern-library/source/build_catalog_cad.py --baseline web/pattern-library/data/pattern-assets.csv --archive work/corpus/dataset.7z --extracted work/corpus/zju --publisher work/corpus/openpattern.json --output web/pattern-library/catalog
python web/pattern-library/source/build_catalog_feedback.py --source work/corpus/nicapotato.zip --fit-source work/corpus/fitdata.zip --output work/corpus/generated
cp work/corpus/generated/review-signals.csv web/pattern-library/catalog/
python web/pattern-library/source/build_catalog_notes.py --baseline web/pattern-library/data/feedback-catalog.csv --supplement web/pattern-library/source/curated-feedback.tsv --feedback work/corpus/generated/review-signals.json --output web/pattern-library/catalog
```

[Open+Pattern 商品接口](https://openpattern.io/wp-json/wc/store/v1/products?per_page=100) · [复现核验脚本](../source/verify_catalog.py)
