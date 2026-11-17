# Style3D 接入验证记录

本轮交付的是只读 MCP 客户端、可复用验证步骤和既有安装证据。**真实 Style3D V10.1 接入判定为 BLOCKED**：账户注册未提交、目标版本未安装，因此未执行真实工具调用、DXF 往返或三维试衣。

## 本地验证

从仓库根目录运行：

```bash
python3 -m unittest discover -s tools/style3d/tests -v
python3 tools/style3d/probe_mcp.py --help
git diff --cached --check
```

9 项测试通过，原始输出见 [tests.log](tests.log)。测试启动真实的本地 HTTP 监听器并驱动公开 CLI，覆盖 JSON/SSE、202 通知、会话/协议头、只读方法序列、分页、失败回执、地址拒绝与重定向限制；监听器是协议测试服务，不是 Style3D。命令帮助和差分检查分别见 [cli-help.log](cli-help.log) 与 [diff-check.log](diff-check.log)。

候选代码由 [receipt.json](receipt.json) 中的基线提交及源文件 SHA-256 清单标识。测试临时服务和目录已清理，没有新增 CI 或付费计算资源。

## 已有实际安装证据

以下为本次会话中实际使用 Boat 电脑操作接口取得的原始截图，捕获发生在客户端代码提交之前：

- [8.0.513 安装完成](evidence/installation-success.png)：安装器显示 Installation successful。
- [重新启动后的登录页](evidence/login-after-restart.png)：已安装程序显示 V8.0.513 PROD 登录界面，未填写登录凭据。

截图只支持安装及基本启动结论。此前日志的 llvmpipe 软件渲染不代表拥有独立显卡；官方 Simulate CPU 模式可作为后续测试路径，但 Wine 模拟性能尚未测得。

## 继续位置

完成账户注册、安装并登录官方 V10.1，核实 DXF 权限，再按 [Style3D recipe](../../../.agents/skills/verify/references/style3d.md)执行真实 MCP 与工程操作。使用固定人台、面料、单位和缝合关系；保存重开并对照测量。实际合身继续保持 NOT_RUN，既有 T 恤几何 FAIL 不因本轮代码测试改变。

[集成说明与官方来源](../../style3d-integration.md)
