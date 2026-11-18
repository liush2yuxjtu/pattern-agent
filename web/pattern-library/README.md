# Pattern Agent 二维纸样图册

[打开二维图册](https://liush2yuxjtu.github.io/pattern-agent/pattern-library/) · [按来源和款式看反馈](https://liush2yuxjtu.github.io/pattern-agent/pattern-library/catalog/?view=feedback)

二维图册提供 26 张可放大的裁片预览。包括 6 张 SVG、1 张 Virtual Fashion Lab 卫衣 DXF 预览和 19 张浙江大学研究档案的二维 OBJ 轮廓。可按来源、服装类别和关键词查找，分享单张图卡链接。[预览和原始几何指纹](paper-gallery/manifest.json)

归档的 ET PRJ 和 CLO ZPRJ 等原件仍可在 CAD 索引查找。图册只收录已有二维几何的样本，预览尺寸经过适屏缩放。浙大预览取自作者档案中的平面 OBJ，裁片间距沿用原文件。[CAD 索引](catalog/) · [作者研究档案](https://github.com/Dancingmader/3D-High-quality-Garment-Dataset) · [Virtual Fashion Lab](https://www.virtualfashionlab.com/clo3dfreeassets)

## 三维渲染案例

三维对照页提供同款裁片、三维视角和可下载网格。[打开三维案例](https://liush2yuxjtu.github.io/pattern-agent/pattern-library/rendered.html)

| 样本 | 二维来源 | 三维来源 |
| --- | --- | --- |
| Sandy 基础款 | FreeSewing Sandy 4.10.2，裙长 560 mm，圆摆比例 38.75% | 四片裙身，以项目的合成棉质参数在参考人台上求解 120 步 |
| Sandy 加长增摆 | FreeSewing Sandy 4.10.2，裙长 650 mm，圆摆比例 60% | 四片裙身，以合成亚麻参数求解 120 步 |
| 贴身 T 恤袖口改版 | 项目原型的 M 码 DXF，袖口展开宽增加 10 U | 通过独立接缝检查的单层 GLB 静态外壳 |

每款的展示图由 Blender 从对应网格渲染。Sandy 的原始 FreeSewing SVG 包含腰头，三维只保留裙身。三维结果尚未经过实物试穿。T 恤的图形单位 U 尚未标定。

## 按改版意图生成和重放 YAML 补丁

下载并解压 [编辑器 ZIP](downloads/pattern-agent-editor.zip)，在其中的 `pattern-agent-editor` 目录运行以下命令，然后打开 `http://127.0.0.1:8765`。也可从仓库的 [editor](editor/) 目录直接运行。

```sh
python -m pip install -r requirements.txt
python -m pattern_tool serve
```

原始输入由二维纸样 YAML、一维规格 YAML 和同一版本的 DXF 组成。工具把可执行意图编译成补丁，核对原始文件 SHA-256，再生成修改后的 YAML、DXF、SVG 与量测报告。当前支持已建模的 M 码贴身长袖 T 恤，可试袖长、衣长、袖口展开宽和前领深。网页上的袖长样例实测增加 23 U，独立于三维袖口样例。

- [编辑器用法与命令行复跑](editor/README.md)
- [二维重建、一维规格、设计意图和补丁数据结构](editor/SCHEMA.md)
- [样例补丁](editor/example-output/edit.patch.yaml) · [改版 DXF](editor/example-output/edited.dxf) · [量测报告](editor/example-output/report.json)

## 纸样与需求样本

[完整资料库](catalog/)收录 62 份 CAD 原件及按原始来源和款式分组的评论，可在分组中筛选调整部位和关键词。24 份 ZPRJ 来自浙江大学服装皱褶研究档案。下方链接保留初版样本和回归输入。[扩充来源与复现说明](catalog/README.md)

- [纸样索引](data/pattern-assets.csv)记录 38 个去重原件及另列验证样本，含发布页、哈希和核验状态。请从索引中的发布方获取第三方原件。源项目的 [T 恤 DXF](editor/samples/input.dxf)、[衣身 DXF](downloads/bodice-v001.dxf)和 [DXF 回归样本](downloads/dxf-regression-samples.zip)可直接下载。
- [反馈索引](data/feedback-catalog.csv)收录 28 个公开页面的 36 条观察。[候选意图](data/feedback-derived-intents.yaml)按观察保存可调整部位、所需量法和要保留的部位。把用户意见转成生产指令前，需要确认尺码、量法和改动量。
- ET 的 PRJ 和 CLO 的工程文件保留原始来源。要进入通用编辑流程，仍需相应原生软件导出，并核对裁片、缝线、标记和尺码。现有工具的执行范围已写入架构说明。

## 重做二维预览

以 Python 3.11 或更新版运行，需安装 ezdxf 1.4.x、NumPy、Pillow 和 Inkscape。从浙大作者档案提取名称以 `2D.obj` 结尾的平面文件并保留相对路径，再从 Virtual Fashion Lab 取得 `SWEATSHIRT PATTERN.dxf`。生成脚本读取原二维三角网格的外露边及原 DXF 线条，索引记录源文件和预览的 SHA-256。

```sh
python web/pattern-library/source/build_paper_gallery.py --flattened work/corpus/zju-2d --vfl-dxf work/corpus/SWEATSHIRT-PATTERN.dxf
python scripts/build_pages.py
python web/pattern-library/source/verify_gallery.py --directory dist --output work/pattern-library/verify
```

## 重做三维渲染案例

在仓库根目录运行。需要 Python 3.11+、项目的 Playwright/Chromium、Pillow、PyYAML、NumPy、SciPy、Node.js，以及 Blender 4.3。命令中的 `work/` 是项目的临时目录。两个压缩求解快照可直接解压传入渲染器以复用已发布的精确网格。

```sh
npm ci --ignore-scripts --no-audit --no-fund --prefix experiments/freesewing_cloth_lab
PYTHONDONTWRITEBYTECODE=1 python web/pattern-library/source/capture_sandy.py --output work/pattern-library/capture
blender -b -t 4 --python-exit-code 2 -P web/pattern-library/source/render_garments.py -- --capture work/pattern-library/capture --output work/pattern-library/renders
PYTHONDONTWRITEBYTECODE=1 python web/pattern-library/source/assemble_gallery.py --capture work/pattern-library/capture --renders work/pattern-library/renders
python scripts/build_pages.py
PYTHONDONTWRITEBYTECODE=1 python web/pattern-library/source/verify_gallery.py --directory dist --output work/pattern-library/verify
```

- [Sandy 基础款来源与验证](gallery/sandy-standard/evidence.json) · [求解快照](gallery/sandy-standard/state.json.gz)
- [Sandy 加长增摆来源与验证](gallery/sandy-flared/evidence.json) · [求解快照](gallery/sandy-flared/state.json.gz)
- [T 恤袖口 3D 来源与验证](gallery/shirt-cuff/evidence.json)
- [FreeSewing Sandy 文档](https://freesewing.eu/designs/sandy/) · [FreeSewing MIT 许可证](source/FreeSewing-LICENSE.txt)
