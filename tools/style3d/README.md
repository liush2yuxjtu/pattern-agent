# Style3D 代理连接检查

此目录提供一个仅依赖 Python 3 标准库的只读 MCP 检查脚本。它检查连接并读取实际工具名称与输入格式，不会修改纸样、运行仿真或接受许可。

当前已验证：Boat Ubuntu + Wine 中安装的 Studio 8.0.513 可以启动到登录页。账户注册尚未提交；三维试衣尚未完成。V10.1 官网公开说明 MCP 支持纸样制作、修改和处理，因此后续应安装 V10.1，不能用旧版登录窗口代替 MCP 功能验证。

## 运行

1. 在运行 Studio 的同一台机器上登录 V10.1，点击右上角 MCP，开启服务并确认服务地址。保持本地连接模式。
2. 使用本机的 Python 3 运行：

   ```bash
   python3 tools/style3d/probe_mcp.py --url http://127.0.0.1:57281/mcp --output work/style3d-mcp-discovery.json
   ```

3. `status=connected` 只表示 MCP 初始化与工具列表成功。随后必须依据返回的真实工具格式执行服装测试，不能仅根据工具名称判断功能已通过。

脚本不读取密码或邮件、不输出 MCP 会话标识，不需要在网络上公开 MCP 端口。无需安装额外 Python 包。可修改本地端口以匹配软件设置。

退出码 `0` 表示初始化和完整工具枚举成功；退出码 `2` 表示连接或协议检查受阻，或命令行参数无效。连接或协议错误写入 JSON 报告；参数错误在网络访问之前拒绝。脚本仅接受本机 HTTP 地址，拒绝 URL 中的凭据、查询参数、片段及 HTTP 重定向，分页最多 100 页。

在仓库根目录运行协议与命令行测试：

```bash
python3 -m unittest discover -s tools/style3d/tests -v
```

测试会启动并关闭临时本地 HTTP 服务，覆盖 JSON/SSE、分页、会话标识不泄露、失败回执、禁止重定向和非法地址。它们验证客户端行为，不能代替真实 Style3D 接入。当前状态、截图与后续验收见 [Style3D 接入记录](../../docs/style3d-integration.md)；可复用的 `/verify` 流程见 [Style3D 验证步骤](../../.agents/skills/verify/references/style3d.md)。

## 登录后的实际验证顺序

1. 导入已知尺寸的服装 DXF，核对单位、版片数量、封闭轮廓和一条已知长度。
2. 保存 `.sproj`，修改一个明确的二维尺寸，重新读取确认修改，再恢复原值。
3. 建立并核对缝合关系，使用固定人体与面料物性运行模拟。
4. 保存正面、侧面、背面结果；读取软件实际提供的拉伸、穿模、尺寸或合身分析结果。没有提供的指标应注明，不应从图片猜造数值。
5. 保存项目，检查授权允许的导出格式，并验证导出文件重新打开后的单位和尺寸。

Boat 日志显示使用 llvmpipe 软件渲染，DXVK 的模拟显卡名称不代表硬件 GPU。官方提供 **Simulate CPU** 模式，因此后续优先尝试 CPU 模拟；其在 Wine 中的兼容性和性能尚待实测。

官网 Free 套餐列有 MCP 和布料模拟，但不含 DXF 导入。验证 ETCAD 交换流程前须核实账户试用或其他适用授权，不能把接口连接成功视为已取得业务功能权限。

## 官方资料

- V10.1 与 MCP： https://help.style3d.com/studio/en/1f8f/120a2
- MCP 连接说明： https://help.style3d.com/studio/en/1f8f/6ef76
- 官方注册页： https://studio.style3d.com/en/auth/singup
- CPU 模拟： https://help.style3d.com/studio/en/c4905/c74f/0716/2996
- 套餐表： https://studio.style3d.com/

新账户密码需要账户本人在安全界面创建。此目录不保存账户密码、验证码或令牌。
