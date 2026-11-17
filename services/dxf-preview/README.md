# 纸样转三维预览函数

将本项目女士紧身长袖上衣的文本 DXF 转成可旋转的 GLB 外观模型。每次根据上传几何重新计算，可在 Linux 或 Vercel Python Functions 运行，不依赖 Blender、桌面软件、外部模型服务或任务数据库。

[复用已有纸样并生成预览](https://pattern-agent-convert.vercel.app/?reuse=fitted-tshirt-v1#convert) · [打开在线转换网站](https://pattern-agent-convert.vercel.app/) · [交互接口文档](https://pattern-agent-convert.vercel.app/docs) · [线上验收证据](../../docs/verification/dxf-service-20261117/)

版本2将实际纸样三角化为五个来源明确的裁片面域，按15条声明的缝合关系焊接为一个静态外壳，并重新读取最终GLB进行独立检查。原始缝线存在差异，当前模型采用另存的修正缝合线；原始DXF字节保持不变。人体厚度、姿态和材质仍为展示假定，未进行校准布料求解，不保证所有片内尺寸等距保留。PRJ与EMF不作为此接口输入。

## 支持范围

- 模板 `fitted-tshirt-v1`：原始导出的 126 条 `POLYLINE`，最多 6,000 个顶点。
- 必须显式传入 `units=mm`、`cm` 或 `inch`；原文件未声明单位，此原型使用毫米假定。
- 允许线段重排、反向、整体平移；允许原模板 0.7 至 1.3 倍的整体等比缩放。
- 使用全局匹配及 32 点线形采样，归一化后的最大采样偏差不超过 8 毫米；这不是严格连续曲线距离或缝合容差。
- 布局旋转、镜像、重新排料、不同款式、不同实体类型或不同导出拓扑需要新的配置，当前会拒绝。
- 输入最多512 KiB；GLB最多4,000,000字节。单位与模板匹配后，还必须通过源轮廓闭合、修正幅度、逐缝和导出网格检查；否则接口拒绝输出。
- 整体缩放属于几何变换，归拔量随基准一起变换，不是真实号型放码。原后身数量标注为2仍需版师核对；当前装配采用一片完整后身。

修正版的静态裁片连接与自交检查为 **PASS**，物理试穿、校准面料力学和生产裁剪批准仍为 **NOT_RUN**。本次证书只覆盖显示的单层外壳；领条隐藏内层和缝份叠层不在此几何模型中。历史实验的7.6455毫米接缝间距及20处自交FAIL保留；另对已发布的v1预览独立复测，得到9个组件和340对穿插，均保留在[本次证据](../../docs/verification/dxf-seams-20261117/)中。

## Linux 运行

使用 Python 3.12。在本目录执行：

```sh
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m uvicorn app:app --host 127.0.0.1 --port 8765
```

打开 `http://127.0.0.1:8765/`，点击“复用已有纸样”，即可载入之前保存的中码原始文件并生成预览；也可上传相同导出结构的纸样。交互文档位于 `/docs`；状态位于 `/api/health`；模板范围位于 `/api/profiles`。

复用直达链接：`/?reuse=fitted-tshirt-v1#convert`。它自动载入已发布的原始纸样，并填入文件与毫米单位；随后可直接再次点击“生成三维预览”。当前复用列表仅有本款上衣，不保存后来上传的文件。

## 接口

请求体为文件的原始字节，不使用表单，也不接受远程文件 URL：

```sh
curl --fail-with-body -X POST \
  'http://127.0.0.1:8765/api/preview?units=mm&profile=fitted-tshirt-v1&format=glb' \
  -H 'Content-Type: application/dxf' \
  --data-binary '@女紧身款T恤.dxf' \
  --output preview.glb
```

`POST /api/analyze?units=mm` 仅检查实体、单位及模板匹配。`POST /api/preview` 的 `format` 可取：

| 格式 | 返回内容 |
| --- | --- |
| `glb` | 可直接打开的二进制三维模型 |
| `json` | 转换报告及 `glb_base64`，供网页或其他函数接入 |
| `bundle` | 模型、报告、自包含离线预览、原始DXF、修正缝合线SVG/JSON及逐缝验收报告ZIP |

成功响应携带 `X-Conversion-Id` 和 `X-Output-Sha256`，前端核对模型 SHA-256 后显示。同一输入、单位、模板及引擎版本返回同一模型字节。转换编号用于核对版本，**不是持久任务编号**。接口没有查询任务、异步队列或长期下载地址；调用者应保存返回文件。

错误返回 `{"status":"rejected","error":{"code":"…","message":"…"}}`。损坏文件／缺少单位为 400，过大文件为 413，不适用的模板／单位尺寸组合为 422。无法可靠闭合或未通过连接验收时为422 `SEWING_ASSEMBLY_REJECTED`／`SEWING_VERIFICATION_FAILED`；单实例正在转换时为503 `BUSY`，调用方可退避重试；这不是跨实例流量限制。未承诺并发容量或服务可用性等级。

## Vercel 运行方式

将本目录作为项目根目录，使用原生 FastAPI 检测，入口 `app.py`。Python 3.12 由 `pyproject.toml` 固定，函数最长 60 秒，静态文件与模板通过 `includeFiles` 打包。没有 Blender 可执行文件、外部 worker、付费存储或工作流资源；这是同步、无状态的普通函数。

健康接口返回应用代码、模板、Python 项目声明和公开资源的逐文件摘要。Vercel 构建会改写 `vercel.json`，它的原始上传摘要保存在部署证据中，不纳入运行时应用源摘要。

应用不持久写入上传文件，不把文件内容写入应用日志；平台仍按账户设置记录访问与运行日志。浏览器仅在当前页面持有模型和下载对象。高保真 Blender 渲染与物理布料仿真应另设受控计算任务，此版本只输出实时外观预览。

## 独立裁片连接验收

原始中码在当前缝合约定下存在约2.39毫米肩缝差、计入归拔后的约2.51毫米侧缝差、约2.49毫米袖底差，以及袖山前后吃势分配差。修正版最大点位移动约4.41毫米；保留原文件和所有改动，袖山吃势按项目规则分为前40%／后60%，衣身袖窿保持不变。

每次生成必须在实际导出GLB上通过：15条缝共用顶点、逐缝长度与局部吃势配对、二维面域完整覆盖、一个连通组件、四个预期开口、无非流形／翻面／退化面，以及严格自交检查。检查器独立于生成器，可重跑下载文件：

```sh
python services/dxf-preview/verify_connections.py \
  --dxf 女紧身款T恤.dxf --glb preview.glb --units mm \
  --out independent-result.json
```

上例从仓库根目录执行。阈值为：接缝间隙不大于2毫米，处理后的二维缝长残差不大于0.05毫米，三维缝长差不大于2毫米；穿插为0，数值容差为1微米。当前原始中码修正版实测：间隙0、缝长差约0.074毫米、51,150个三角面、穿插0。四个开口分别是领口、下摆和两袖口，不要求服装封闭成实体。

校验代码位于`verification/`，来源为仓库经过23个解析对照验证的独立严格几何检查器；它不因共享顶点而跳过相交面。27项测试包含故意破坏的模型。操作路径见[连接验收配方](../../.agents/skills/verify/references/dxf-seams.md)。

## 本地验证

从仓库根目录：

```sh
PYTHONPATH=services/dxf-preview python -m unittest discover -s services/dxf-preview/tests -v
python scripts/verify_dxf_service.py \
  --base-url http://127.0.0.1:8765 \
  --output work/verify-dxf-service
```

测试需要测试环境中的 `httpx`、Playwright、Pillow 及 `/usr/bin/chromium`；这些不打包进函数。验证器还支持 `--browser` 指定现有浏览器，以及 `--expected-source` 核对部署的实际源摘要。操作路径见[项目验证配方](../../.agents/skills/verify/references/dxf-service.md)。

## 第一版发布历史

2026 年 11 月 17 日，线上匿名浏览器的 15 组验收与本地 10 项测试通过，包含旧纸样复用、表单回填、再次生成及复用直达链接。验收时首轮 HTTP 转换约 1.0 秒，原文件输出 1,314,124 字节；两次在线调用模型逐字节一致，线上下载模型、报告及离线包与本地版本摘要相同。这是实测样本，不是容量或可用性承诺。

项目 `pattern-agent-convert`；此前v1生产部署 `dpl_B9bvShHiB9s84XHJF8ZiUdhWoPr2`；运行源码提交 `0f9edae21e6fc28183bcaedd7c47d03ea29ef5b2`；应用源摘要 `e77db4e7cd6ea82d4ff8a55a47a2de0a4ecaff18274f3aa21cf77ecfa5c24049`。后续文档提交不表示已重新部署函数。

| 部署 | 固定地址 | 记录 |
| --- | --- | --- |
| 首次发布 | [7phar6sp7](https://pattern-agent-convert-7phar6sp7-nyn5255-8475s-projects.vercel.app/) | 转换通过；聚合源摘要有差异，未完成全部线上验收 |
| 逐文件诊断 | [hkah8e9z4](https://pattern-agent-convert-hkah8e9z4-nyn5255-8475s-projects.vercel.app/) | 定位构建改写 vercel.json；应用文件一致 |
| 摘要修正 | [c7hobhy9l](https://pattern-agent-convert-c7hobhy9l-nyn5255-8475s-projects.vercel.app/) | 实际源码同其更正发布版本；提交标记录入错误，由下条更正 |
| 首版验收通过 | [fuegobiac](https://pattern-agent-convert-fuegobiac-nyn5255-8475s-projects.vercel.app/) | 源文件、提交标记与线上浏览器验收通过 |
| 旧纸样一键复用 | [g9sdxn3c7](https://pattern-agent-convert-g9sdxn3c7-nyn5255-8475s-projects.vercel.app/) | v1软件验收通过；本次严格几何复测FAIL，记录保留 |

固定部署地址保留 Vercel 原有登录保护；生产别名可匿名访问。没有为验收关闭保护或改变其他项目。
