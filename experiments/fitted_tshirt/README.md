# 女士紧身长袖上衣原型

原始中码纸样的文件调查、三维外观重建及静态展示。使用 Linux、Python 和 Blender 4.3.2；没有调用付费建模服务。

## 资料与结果

- `source/`：用户提供的原始工程、裁剪交换文件及矢量图，原字节保留。
- `analysis/原型资料.md`：款式、七张参考图的用途、面料差异、八个尺码和待确认问题。
- `data/`：原始多段线、文字调查结果及重建网格。
- `scripts/`：可重复执行的提取、参数化重建和 Blender 渲染脚本。
- `../../web/fitted-tshirt/assets/`：三张最终渲染、两张二维预览、可编辑场景及通用三维模型。
- `analysis/decode*.py`：未成功的工程文件解码探索，不是可用读取器。

## 重现

从此目录运行，Python 环境安装 `requirements.txt` 中的依赖；Blender 使用其自带的 Python。

```sh
python scripts/extract_patterns.py
MPLCONFIGDIR=../../work/mpl python scripts/prepare_mesh.py
blender -b -t 4 --python scripts/render.py -- --mesh data/tshirt_mesh.json --output output
```

在仓库根目录运行 `python scripts/build_pages.py`，再用 `python -m http.server --directory dist 8000` 可查看本地网站。

`output/` 为本地结果，不要提交临时备份。重新生成完整下载包：在仓库根目录运行 `python scripts/build_fitted_tshirt_bundle.py`，再运行现有静态构建脚本。

## 建模范围

前后身使用原二维内侧轮廓生成网格并映射至假定人体曲面；袖窿取自原轮廓，袖身围度参考原袖片展开宽度。侧缝及肩部以连接面补齐，领条沿领口曲线近似构造。人体厚度、袖子姿态、面料物性、车缝与细微褶皱采用展示假定。

这是参数化外观重建，不是经校准的布料物理仿真。材料未定版，原始工程未完整解码，二维文件单位未声明，后身数量标注存在疑问。物理合身性、严格接缝间隙、布料压力及自交发布门槛均 **NOT_RUN**。网站可用性通过不等于服装生产批准。

历史实验已记录的几何失败不由此展示替代或覆盖。先前提供的模特及色卡照片没有独立可下载源文件，因此保存了其解释与参数，未重造这些照片。
