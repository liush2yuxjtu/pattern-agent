# Style3D Studio 接入与三维验证

目标是在同一工程中导入和修改二维纸样、建立缝合关系、运行三维试衣，再让代理根据真实尺寸与模拟结果迭代。当前已完成 **Studio 8.0.513 在 Boat Ubuntu + Wine 中安装并启动至登录页**；账户注册尚未提交，V10.1、真实 MCP、DXF 往返和三维模拟仍待验证。

资料与操作记录日期为 2026 年 11 月 17 日。本文不改变仓库既有服装几何 FAIL 或实体合身 NOT_RUN 的结论。

## 已完成的检查

| 检查 | 结果 | 证据及边界 |
| --- | --- | --- |
| 官方历史版安装 | PASS | 安装器显示 Installation successful；[截图](verification/style3d-20261117/evidence/installation-success.png) |
| 安装后重新启动 | PASS | 已安装的 EXE 再次显示 V8.0.513 PROD 登录页；[截图](verification/style3d-20261117/evidence/login-after-restart.png) |
| 图形运行路径 | 软件渲染 | Wine 11.22 Staging 与 DXVK 使用 llvmpipe；模拟的 AMD 显卡名称不代表存在实体 GPU |
| 账户 | BLOCKED | 官方注册表单已准备，注册尚未提交；未完成新凭据设置 |
| MCP 检查客户端 | 见本地验证回执 | 已保存只读工具枚举脚本与 CLI 协议测试；测试服务不是 Style3D |
| V10.1 真实 MCP 及服装操作 | BLOCKED | 尚未安装并登录目标版本，不能读取实际工具清单 |
| DXF 编辑回读与 CPU 试衣 | NOT_RUN | 需要对应版本、账户权限及基线工程 |
| 实体合身 | NOT_RUN | 数字模拟也不能代替标定面料和实物试穿 |

已安装程序位于 Wine 的 `C:\Program Files\Style3D\Style3D.exe`。其 SHA-256 为 `661f0c4aba88ebf340bc35c71edf250bff080355d9b3069a20fb752dd798e51e`，文件大小 66,804,672 字节。官方历史版安装包 SHA-256 为 `887605ceae3b7f92bdc3fc819a3b2ca13ddfff0664a1f2d86dd7391faf17b98e`。本仓库不重新分发厂商安装包；Boat 工作环境已归档且保留可恢复快照。

## 版本和授权选择

[V10.1 官方说明](https://help.style3d.com/studio/en/1f8f/120a2)列出 MCP 对制版、改版及版片处理的扩展，默认本机服务地址为 `http://127.0.0.1:57281/mcp`。实际工具名和参数必须从运行实例读取，不在此猜测。

[官网套餐表](https://studio.style3d.com/)将 MCP 与布料模拟列入 Free，但不含 DXF 导入；ETCAD DXF 的试验须先核实 30 天试用或其他授权的实际权限。尚未购买付费方案，也未证明任何商业用途许可。

[官方模拟说明](https://help.style3d.com/studio/en/c4905/c74f/0716/2996)提供 Simulate CPU；[CPU 与 GPU 选择说明](https://help.style3d.com/studio/en/4152/faa4/2a78/29e4)明确无独立显卡时使用 CPU 模拟。后续在 Boat 优先测 CPU 模式，不从登录窗口或软件渲染日志推断仿真已经可用。

原生工程使用 `.sproj`；服装 CAD DXF 是交换输入，尺寸、放码、刀口、内部线和缝份必须逐项回读核对。参考 [DXF 官方说明](https://help.style3d.com/studio/en/c4905/c2c8/6cc0/60d0/a589)。

## 只读 MCP 检查

在运行目标 Studio 的同一台机器上启用本机 MCP 服务，然后从仓库根目录运行：

```bash
python3 tools/style3d/probe_mcp.py \
  --url http://127.0.0.1:57281/mcp \
  --output work/style3d-mcp-discovery.json
```

检查客户端只发送 `initialize`、`notifications/initialized` 和 `tools/list`，输出完整工具清单和输入格式，不发送 `tools/call`。`connected` 仅代表发现服务成功；`garment_simulation_verified` 始终为 false。报告不输出 MCP 会话标识。

本地 CLI 测试与真实软件接入必须分别登记。可复用步骤见 [Style3D 验证 recipe](../.agents/skills/verify/references/style3d.md)，本轮结果见 [验证回执](verification/style3d-20261117/README.md)。

## 继续验证的顺序

1. 完成账户注册和登录，取得官方 V10.1 安装包，并确认试用与 DXF 权限。新凭据须由账户本人输入、确认和提交；[注册页](https://studio.style3d.com/en/auth/singup)和[登录页](https://studio.style3d.com/en/auth/login)只显示常规邮箱密码流程，未发现可用的 Google 或免密码登录。
2. 启用本机 MCP，保存实际工具清单，并把一次读取结果与 GUI 工程核对。
3. 导入有权使用的 DXF，记录单位、版片数量和已知长度，保存 `.sproj` 基线。
4. 在副本中只改一个明确的二维尺寸，读取修改前后数值；保存、重开，再确认并恢复基线。
5. 核对缝合对象、方向、人台和面料物性，运行 CPU 模拟，保存前侧后视图与软件实际返回的拉伸、穿模或合身指标。软件没有提供的量不得从截图编造。
6. 重新打开工程与获授权的导出文件，对比关键尺寸、版片和尺码。记录模拟耗时与失败，实体合身继续保留独立验收。

账户邮箱、密码、验证码、API Key、私有沙箱地址和登录会话不进入仓库或公开记录。
