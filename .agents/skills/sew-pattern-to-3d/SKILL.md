---
name: sew-pattern-to-3d
description: "从二维服装 DXF 纸样识别接缝、装配裁片并构建可旋转的三维形状；用于纸样缝合、seaming and building 3D shape、DXF 到 GLB、静态缝合预览，以及解释或复现本项目的生成流程。生成后调用 verify-seaming 独立验收。GarmentCode JSON 或物理下垂转 garmentcode-preview；已有模型仅检查接缝时使用 verify-seaming。"
compatibility: "Pattern Agent 完整仓库；Python 3.12 和 services/dxf-preview/requirements.txt；预览使用支持 WebGL 的浏览器。当前自动构建只支持 fitted-tshirt-v1 纸样配置，不需要 Blender 或外部模型服务。"
---

# 接缝装配与三维形状构建

工作目录为 Pattern Agent 根目录。先读 `AGENTS.md`，复用
[现有转换服务](../../../services/dxf-preview/README.md)和独立检查器；
Claude 通过 `.claude/skills/sew-pattern-to-3d` 读取同一目录。
显式请求名为 `$sew-pattern-to-3d`，文件安装不证明客户端自动触发已验证。

## 选择入口

| 输入与目标 | 执行路径 |
| --- | --- |
| 本款 DXF，构建带接缝的静态外壳 | 本技能，调用既有 `convert_dxf` 和离线打包函数 |
| 已有 DXF 和 GLB，只核验连接 | [verify-seaming](../verify-seaming/SKILL.md) |
| GarmentCode 纸样 JSON，网格或物理下垂 | [garmentcode-preview](../garmentcode-preview/SKILL.md) |
| 商品照片，人体体形与姿态拟合 | [garment-body-six-view](../garment-body-six-view/SKILL.md) |

原理说明先读 [装配实现与形状假定](references/assembly.md)。要求生成时实际运行并
交付新产物；命令示例、旧模型或 PASS 标签不能替代本次生成。

## 确认来源与支持范围

保存实际输入路径、原字节摘要、单位和当前源码版本。原 DXF 没有单位声明，
本项目样例明确采用毫米；不把尺寸表或参考照片当作文件单位声明。
仅演示且未给文件时使用 `services/dxf-preview/public/sample.dxf`，标明是已保存样例。

当前配置 `fitted-tshirt-v1` 对应 126 条 POLYLINE，限制 6,000 顶点、512 KiB 输入，
接受已支持的重排、反向、平移及 0.7～1.3 倍整体等比缩放。
任意款式、旋转排料、镜像或不同导出结构需要新的配置；被拒绝时保留错误，
不得退回旧模型或硬套本款裁片编号。PRJ 与 EMF 不是此函数输入。
整体缩放不等于号型放码，原后身数量 2 仍需版师核对。

## 装配裁片并构建形状

1. `parse_dxf` 和 `register` 读取并匹配真实线段，识别前身、后身、左右袖和领条。
2. `patterns` 对肩、侧、袖山、袖底生成有界修正线，原线另存；按局部归拢、
   拔开和吃势定义配对后的长度与方向，不能假设原始两边天然等长。
3. `triangulate` 在二维域内剖分，保留真实边界；保存二维点和面到来源的映射。
4. 根据声明的空间边界摆放肩、领、袖窿与侧缝；衣身作调和平滑及展示用鼓出，
   袖子沿弯曲轴映射成管状，围度参考袖片宽度；领条只构建显示的外层。
5. 对缝边统一采样参数并合并对应顶点，统一面方向，得到一个实际焊接网格；
   保留领口、下摆与两袖口四个正常开口。
6. 导出米制、Y 轴向上的 float32 GLB。转换器必须在最终文件上重新执行独立
   验收；失败就拒绝输出，不能只检查生成器内存中的高精度数组。

衣身前后深度、A 字袖姿和显示材质是展示假定。此映射没有证明片内等距保留，
没有校准面料的拉伸、剪切、弯曲、重力或人体碰撞。焊接后的零间隙证明数字
连接，不能直接证明真实缝制后的褶皱、压力与合身性。

## 在 Linux 上生成完整离线结果

复用已有 Python 3.12 环境。缺依赖时按服务 requirements 建独立环境，
不修改其他工具环境。以下代码直接调用已有生成与打包函数，不启动服务器，
结果写入新的命名目录，保留每次产物。使用用户文件时修改 `source_path` 和单位。

```sh
PYTHONPATH=services/dxf-preview python - <<'PY'
import io, json, subprocess, sys, tempfile, zipfile
from pathlib import Path
from converter.core import convert_dxf
from app import bundle

source_path = Path('services/dxf-preview/public/sample.dxf').resolve()
units = 'mm'
source = source_path.read_bytes()
result = convert_dxf(source, units=units, profile='fitted-tshirt-v1')
archive = bundle(result, source)
Path('work').mkdir(exist_ok=True)
out = Path(tempfile.mkdtemp(prefix='sewn-preview-', dir='work')).resolve()
(out / 'preview.zip').write_bytes(archive)
with zipfile.ZipFile(io.BytesIO(archive)) as z:
    if z.testzip() is not None:
        raise RuntimeError('离线包完整性检查失败')
    z.extractall(out / 'files')
subprocess.run([
    sys.executable, 'services/dxf-preview/verify_connections.py',
    '--dxf', str(source_path), '--glb', str(out / 'files/model.glb'),
    '--units', units, '--out', str(out / 'independent.json'),
], check=True)
print(json.dumps({
    'output': str(out), 'preview': str(out / 'files/preview.html'),
    'model': str(out / 'files/model.glb'),
    'source_sha256': result.report['input_sha256'],
    'model_sha256': result.report['output_sha256'],
    'mode': result.report['mode'], 'physical_fit': 'NOT_RUN',
}, ensure_ascii=False))
PY
```

返回目录中保存 `preview.zip`、独立重开报告，以及包内的 `model.glb`、`preview.html`、
`viewer.js`、`report.json`、`original-input.dxf`、`connection-verification.json`、
`pattern-revision.json` 与 `corrected-seam-lines.svg`。重开原文件与报告，核对输入/
输出摘要、单位、修正记录和本次几何结论。启动或依赖异常为 BLOCKED，
真实几何拒绝为 FAIL；不要用任何非零退出一概解释为纸样失败。

## 预览与交付

展示本次生成的 HTML 或 GLB，浏览器通过实际位置、面索引、法线与灯光渲染。
按 [dxf-service](../verify/references/dxf-service.md) 检查模型像素、真实拖动、
缩放、线框、下载、手机、离线和无 WebGL 回退。浏览器禁止直接文件导航时，
沿用配方中的允许路径，不能改变浏览器策略；未运行浏览器时单独标明预览交互未验收。
需要在线调用时沿用服务 README 的本地 FastAPI 或既有生产接口；凭证不进入模型和证据。

生成后执行 [verify-seaming](../verify-seaming/SKILL.md)：独立核对来源、处理后缝长、
UV 覆盖、正确相邻来源面、开口和严格穿插。需要逐缝交互页时再走其视图来源绑定
检查，不能把冻结查看器绑定到另一次新生成的模型而沿用旧结论。

最终交付实际模型、离线预览、原始输入、修正对照、独立报告和本次文件摘要，
区分生成、几何验收、预览交互、发布与真实试穿结果。保留原纸样及全部历史 FAIL。
提交前执行项目 `/verify`，记录候选和原始命令，直接提交 main，再以非强制方式推送。
