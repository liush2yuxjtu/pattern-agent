# 补充领子与袖子资料

本批9份上传已经归档。整件 DXF、EMF、PRJ 与已有文件逐字节相同，因此通过 [manifest.json](manifest.json) 引用原文件；新增6份领子、袖子文件按原字节保存。

| 部件 | 原始 CAD | 独立中文规格 | 几何预览 | 原始辅助资料 |
| --- | --- | --- | --- | --- |
| 领子 | [领子.dxf](领子.dxf) | [collar-spec.yaml](collar-spec.yaml) | [collar.svg](collar.svg) | [EMF](女紧身款T恤领子.emf) · [PRJ](女紧身款T恤领子.prj) |
| 袖子 | [袖子.dxf](袖子.dxf) | [sleeve-spec.yaml](sleeve-spec.yaml) | [sleeve.svg](sleeve.svg) | [EMF](女紧身款T恤袖子.emf) · [PRJ](女紧身款T恤袖子.prj) |

两份 YAML 各自保存全部二维坐标、直线、多段线、闭合状态、图层、文字、文字位置和旋转角，不需要再读取原 DXF 才能重画。领子有25条多段线、19条直线、8条文字；袖子有19条多段线、15条直线、5条文字。仅用 YAML 重建 DXF 后，已用 ezdxf 重新打开并逐实体核对，见 [几何重建结果](geometry-roundtrip.json)。

制版、缝制要点与未确认项放在规格开头，坐标表放在后面。这里的“可重建”指保留上传 CAD 的二维实体；全部线条的裁剪／缝制语义及生产工艺仍待复核。源文件中的文字按资料读取，不作为运行指令。

独立部件与整件纸样的实体分段和部分几何存在差异，不能仅凭同名自动替换总原型。原型的 [input.dxf](../../input.dxf) 和 [input-spec.yaml](../../input-spec.yaml) 均保留。接下来可以明确指定以整件原型或哪个部件候选为编辑基准，再生成规格差异与 DXF 补丁。

新旧两份尺码表的 M 码不同，见 [尺码参考记录](size-chart-references.yaml)。这些是成衣表，不能代替人体尺寸；截图中的“平量／围量”及异常项也不自动推断。DXF 没有实际单位声明，新增文件没有提供面料拉伸、剪切或弯曲测试，因此原型的“未标定”状态继续保留。

## 复现

在仓库根目录运行，使用已有 Python、PyYAML 与 ezdxf：

```sh
python patterns/fitted-tshirt/components/20261118/build_references.py
```

原始 DXF 是仅含 ENTITIES 段的 R12 文本。原文件始终保留；读取时给原生恢复器补充容器与 GBK 编码声明。重建文件正确声明中文编码，防止“前中／后中／面料A”乱码。PRJ 仅归档，尚未声明可解码或可往返。
