# 原型与改版：单文件对照页

直接打开新的[在线页面](https://liush2yuxjtu.github.io/pattern-agent/intent-edit-review/)。发布文件只有 `web/intent-edit-review/index.html`，所有数据、样式、脚本与五套模型内嵌，不加载外部资源。

1. 左侧：完整输入 YAML、原始 DXF、真实二维图和可旋转的三维几何示意。
2. 右侧：选择一个已经运行的设计意图，查看对应的新 YAML、规格差异、DXF 坐标补丁、新 DXF、二维图和三维示意。

四项案例为袖长增加20U、前后衣身缩短15U、袖口展开宽增加10U、前领加深10U并联动领条。页面用于查看已运行结果；选择器不会调用模型，不代表任意自然语言生成服务。生成代码与原始产物在 `../intent-edit-benchmark/`。

两个三维视图共用相机和尺寸参照，可拖动、滚轮缩放、方向键旋转，也可用正面、背面和复位按钮。二维图点击放大；完整 YAML 可阅读和下载；差异弹窗可看尺寸变化及两个完整补丁。下载保留源文件原始字节。

## 重建与验证

实际使用的环境：Python 3.12、PyYAML 6.0.3、ezdxf 1.4.4、NumPy 2.3.5、SciPy 1.17.0、Pillow 13.0.0、Playwright 1.62.0、`/usr/bin/chromium`。页面运行本身不依赖这些 Python 包。

```sh
python experiments/intent-edit-review/build.py
python -m unittest discover -s experiments/intent-edit-review/verification -p 'test_*.py' -v
python experiments/intent-edit-review/verification/audit_embedded_review.py --html web/intent-edit-review/index.html --output work/intent-edit-review/data-audit.json --adversarial
python experiments/intent-edit-review/verify_browser.py --output work/intent-edit-review/browser
```

三维构造与独立来源核对见 [geometry/README.md](geometry/README.md)。验证器除检查摘要，还会读取实际 SVG、DXF 顶点、三维边界UV、构造公式和内部点，拒绝只改来源标签的旧图或旧模型。浏览器验证实际点击、渲染像素、18次文件保存、完整中文文档、窄屏和 WebGL 不可用时的真实软件绘制。

本机受管 Chromium 禁止 `file://` 导航，保留此项 BLOCKED，不修改浏览器策略。独立单文件测试采用：复制唯一 HTML 到隔离目录，从本机 HTTP 读取这一个文档后停止服务器、禁用浏览器网络，再操作案例、三维视图、完整 YAML 和 DXF 下载。只观察到一次文档请求；不能将此证据写成已验证双击本地文件。

## 三维与生产范围

三维来自每一版各自的 DXF，而非旧 GLB 的缩放或图片替代；显示姿态、深度、镜像和领条折叠属于明确的示意假设。U 未标定，静态装配不是布料仿真、批准缝合或试穿结果。物理试穿和布料模拟均为 NOT_RUN，生产批准仍待确认。

本次仅新增独立页面，未修改原有 GitHub Pages 的内容或导航。完整验收记录在 `docs/verification/intent-edit-review-20261118/`。
