# 补充领子与袖子规格验收

候选为基准提交 `91a83c4ca1a1fbf8628fd3e03163760594c4249a` 之上的 `patterns/fitted-tshirt/components/20261118/`；本次提交只交付该目录与本记录，不把进行中的物理试算当作通过。最初验证基于 `0278a4f`，已快进合并最新 main，并重跑同一重建检查。遵循根 `AGENTS.md` 和 `.agents/skills/verify/SKILL.md`。

## 声明与结果

**PASS：两份中文 YAML 独立重建各自上传 DXF 的二维几何实体。** 完整图形列出所有多段线、直线、文字及位置；源文件名只用于追溯。没有调用原型几何、照片或旧 DXF 来补足重建数据。

| 边界 | 实际证据 | 结果 |
| --- | --- | --- |
| 原始上传归档 | `manifest.json` 中9份输入的字节数与 SHA-256；6份新增文件保留，3份重复文件引用原件 | PASS |
| 中文规格可重画 | 读取 YAML，新建 R12 DXF，用 ezdxf 恢复器重开，逐个比较实体类型、图层、颜色、点位、闭合、文字、位置、字高与旋转 | PASS |
| 非空图形 | 领子25 POLYLINE / 19 LINE / 8 TEXT；袖子19 / 15 / 5 | PASS |
| 中文文字 | 前中、后中、右肩、面料A在实际重建文件中保持正确编码 | PASS |
| 人可读性 | 简体中文说明与部件要点在前；单位、版次、工艺未确认项明确；原始坐标表在后 | PASS |
| 语义接缝、物理参数、生产与试穿 | 没有因图形重建而获得批准 | NOT_RUN |

机器读入 YAML 不构成可读性证明；本轮还人工检查了规格开头的叙述顺序、部件数量来源、单位待定、两份尺码表冲突和末尾二维实体表。坐标与 CAD 类型属于制版人员核对图形所需信息。

## 实际命令

工作目录为仓库根，Python 3.12、PyYAML、ezdxf。设置任务缓存目录仅解决当前环境只读的用户缓存，不修改 HOME。

```sh
XDG_CACHE_HOME="$PWD/work/intent-physics/cache" \
  work/intent-physics/venv/bin/python \
  patterns/fitted-tshirt/components/20261118/build_references.py
git diff --check
```

最终结果见 [geometry-roundtrip.json](../../../patterns/fitted-tshirt/components/20261118/geometry-roundtrip.json)。它绑定两份原始 DXF 与两份实际 YAML 的摘要。

最初直接读取只有 ENTITIES 的原流时，原生读取器返回了空模型；已改用显式容器与 GBK 声明，并添加非空实体断言。第二次重开发现重建文件的中文编码声明不符；已同时设置文档编码和 `$DWGCODEPAGE`，重跑逐实体核对通过。没有把上述启动或读取错误写成服装验收通过。

补充尺码表是成衣参考，源 DXF 没有 INSUNITS；本记录不将其自动转换成人体测量或毫米标定。PRJ 与 EMF 原始字节归档，不宣称 PRJ 已能解码或往返。
