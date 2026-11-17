# 接缝验证检查面与复现记录

本次将已经执行的接缝检查固化到Pattern Agent的`/verify`技能，并新增可独立运行的视图来源绑定检查。技能登记及本地检查验收通过；线上登录交互和服务端归档内容读回仍有明确的受阻记录。

| 检查面 | 范围与本次结果 |
| --- | --- |
| `dxf-seams` | 独立重读原始DXF及实际GLB，修正版静态外壳PASS：15组接缝、间隙0毫米、最大缝长误差约0.07375毫米、穿插0、正常开口4 |
| `seam-inspector` | 新增；HTML中的每个三维位置、面索引、二维原／修正曲线、接缝标签、全局顶点和测量报告均与实际模型及独立重算一致；18项正反例及12组真实本地浏览器操作PASS |
| `seam-sites` | 新增；已保存版本2的源码提交及生产入口读回成功，仍为仅所有者可访问；发布元数据已确认，登录后的生产交互BLOCKED |
| `seam-pages` | 新增；原介绍页第12次保存的两个目标块、准确文件引用、HTML类型及1,054,889字节元数据读回PASS；未声称普通文件链接是可执行嵌入 |

保留的GLB摘要为`f67f74dfbbff9859e394a3b8e8b1c0f349edbfda2a22ed65d1d5b979b09f9a86`。其25,758个顶点及51,150个三角面以实际导出值核对。二维图示仅为显示而舍入至0.01毫米；报告与三维比较使用未舍入数据。独立检查器仍验证源纸样配对、归拔区间、共用缝边的相邻面、二维完整覆盖、方向和严格穿插，不能从图片或共用顶点这一项单独推断合格。

原始纸样未改动，其在当前缝合约定下的FAIL仍保留。旧版预览9组件／340对穿插，与更早布料实验7.6455毫米间隙／20处自交，是不同历史证据，均未改写。此PASS只适用于修正版单层静态外壳，领条隐藏内层、缝份叠层、实物面料和试穿仍未验证。

## 仓库内复现

工作目录为仓库根目录。使用服务声明的Python3.12、NumPy／SciPy，及已有Playwright、Chromium：

```sh
SEAM_INSPECTOR_CONTROL_EVIDENCE=work/seam-inspector-controls.json python -m unittest discover -s scripts -p test_seam_inspector_binding.py -v
python scripts/verify_seam_inspector.py --html experiments/fitted_tshirt/seam_inspector/inspector.html --glb experiments/fitted_tshirt/seam_inspector/accepted-model.glb --dxf services/dxf-preview/public/sample.dxf --units mm --output work/seam-inspector
```

不需要原机器的临时Site目录或登录凭证。固定工件仅含此前已提交纸样的派生几何、HTML和报告，未复制Site身份配置或用户会话。工件原字节摘要见[清单](../../../experiments/fitted_tshirt/seam_inspector/manifest.json)，Git属性保留HTML及GLB原字节，避免改变内嵌脚本摘要。

18项对照包含一个真实正例及模型／原纸样摘要、三维顶点、面翻转、来源标签、配对、漏缝、全局ID、二维坐标、原线、测量值、原版FAIL、开口、原始报告、材料批准和重复数据块等反例。全部按预期拒绝，见`local/controls.json`与原始日志。

12组浏览器检查覆盖全部接缝按钮及**可见**测量值，真实点击二维边／三维缝线、鼠标与触摸旋转、键盘和正背视角、原线开关、刷新恢复、原字节下载、503失败与重试、窄屏、禁网运行下载的HTML与其报告下载、无WebGL回退。静态请求由真实工件文件提供，不是假造接缝测量，也不属于生产HTTP或登录验证。

独立HTML与实际Site构建文件分别执行了相同12组检查，证据分别位于`local/`和`site-artifact-local/`。合并远端新增工作后，检查脚本与固定输入的摘要保持不变；三个新配方的注册、链接及Claude共用技能路径也已重新核对。

首次把Site检查程序迁入仓库时有两处旧目录变量未替换，驱动报`ROOT`未定义；原始失败保存在`earlier-driver-failure/`，修复后重跑通过。此失败是检查驱动错误，没有把它混为裁片几何失败或删除证据。

## 发布与文件保存的独立边界

`site-native-readback.json`保存原Site当前所有者访问范围、版本2、源码`4f9aef474d7d3e76ab3da0f0f3f329479d70c365`与对应部署的独立读回。原始发布回执保留在`prior-publish-receipt.json`，不把原字段`NOT_RUN`改写成线上交互PASS；新的必需线上交互检查面使用BLOCKED。

提交的tar为2,140,160字节，摘要`de1c1f542cee704d1d5f470e75806a48f10d043124effc6b583c97605a3ad7f2`。服务端元数据中的tar为2,129,920字节，摘要`e5b103c5ada6b15356de697e3dd38bc42810bfa14ebc5911b59096e31cefef8b`。容器摘要差异不直接证明内容改变或归档重写成功；需要逐文件读回比较。尝试通过返回的Sediment标识下载时，工具报“file could not be authorized or resolved”，因此服务端归档内容一致性仍为BLOCKED，未换身份或绕过访问限制。

`page-native-readback.json`核对实际存在的HTML文件引用与两个目标块，并保留原上传回执中的文件摘要。当前原生文件检查只提供元数据，未声称重新下载了Page中的完整文件或验证了交互嵌入。没有改变Site或Page的分享范围。

## 验证配方

- [独立裁片几何](../../../.agents/skills/verify/references/dxf-seams.md)
- [交互视图与模型来源绑定](../../../.agents/skills/verify/references/seam-inspector.md)
- [生产Site与登录交互](../../../.agents/skills/verify/references/seam-sites.md)
- [Space文件与页面内容读回](../../../.agents/skills/verify/references/seam-pages.md)

本次未修改生产函数或Site，没有新部署、CI、权限变更或付费资源。浏览器由检查程序关闭，未启动预览服务器。
