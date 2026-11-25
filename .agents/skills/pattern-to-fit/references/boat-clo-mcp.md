# 在 Boat 用 CLO MCP 操作原生 CLO 3D

用户已指定虚拟机时，先核对该虚拟机和实际 CLO 版本。新任务从 `clo3d-2026-1-382-backup` 启动单台 worker。继续已有工程时，优先使用能读回该版工程和运行记录的指定 worker 或快照。该快照包含 Wine 下的 CLO 3D 2026.1.382。2026 年 11 月 25 日从该快照新建的虚拟机需要补装 CLO MCP。先检查本次实际环境。

## 启动并检查

```sh
boat --no-update --json new --from clo3d-2026-1-382-backup --type large --no-env --ttl 3600 --name clo-design
boat info "$BOX"
boat desktop "$BOX"
```

将 `BOX` 设为新返回的 worker ID，再运行后两条命令。用虚拟机桌面查看 CLO 版本、授权和当前工程。CLO 未启动时在虚拟机运行 `DISPLAY=:0 "$HOME/clo-wine/launch-clo"`。在 Wine 盘下创建本轮专用目录。Linux 路径 `~/clo-wine/prefix/drive_c/任务目录` 对应 CLO 中的 `C:/任务目录`。用 `boat scp` 双向传输。核对输入和交付物的 SHA-256。

## 安装和连接

1. 在虚拟机运行 `codex mcp list`。检查是否已有 CLO MCP，以及 Python 桥接是否启动。已有注册且桥接在线时跳到第 4 步。已有注册但桥接离线时从第 3 步继续。
2. 服务缺失时，将已获授权的 CLO MCP 源码放到虚拟机 `~/clo-mcp`。从当前授权的 CLO MCP 安装取得服务端源码。已验证的源版本为 `d1af0b1`。传输 `pyproject.toml`、`uv.lock`、`README.md`、`LICENSE`、`src` 和 `bridge`。在新目录安装。发现已有目录时，先核对版次和内容，再复用或另建目录。

   ```sh
   cd ~/clo-mcp
   uv sync --locked
   cp -r bridge ~/clo-wine/prefix/drive_c/codex-clo-bridge
   codex mcp add clo3d -- "$HOME/clo-mcp/.venv/bin/clo3d-mcp"
   codex mcp list
   ```

   对已验证的 CLO 2026.1.382、Qt 6 和桥接源码 `d1af0b1`，如果启动记录显示桥接加载 macOS Qt 库，编辑虚拟机内的 `C:/codex-clo-bridge/clo_bridge.py`。在 `_load_process_events()` 的 `global _process_events` 后加入以下分支。保留函数其余代码。

   ```python
   if os.name == "nt":
       core = ctypes.WinDLL("Qt6Core.dll")
       fn = getattr(core, "?processEvents@QCoreApplication@@SAXV?$QFlags@W4ProcessEventsFlag@QEventLoop@@@@H@Z")
       fn.argtypes = (ctypes.c_int, ctypes.c_int)
       fn.restype = None
       _process_events = lambda: fn(0, 5)
       return True
   ```
3. 在虚拟机的 CLO「编辑 → Python 脚本」中运行下面的命令。确认桥接监听虚拟机内的 `127.0.0.1:5077`。重启 CLO 后重新启动桥接。

   ```python
   import runpy
   runpy.run_path("C:/codex-clo-bridge/start_bridge.py", run_name="__main__")
   ```
4. 在同一虚拟机的新 Codex 会话调用 `clo_status`，确认 `bridge=up`。再调用 `scene_info`，核对工程路径、裁片、缝合及人台。服务经虚拟机回环地址连接 CLO 进程内的 Python。每次更换 worker、工程或重启 CLO 后重做检查。桥接离线时查 CLO 编辑器输出和监听端口。场景不匹配时先打开本轮工作副本，再复查。

## 求解并回读

按当前工具 schema 调用 `scene_open`、`pattern_list` 和 `seams_list` 核对副本。按需装配、赋布和求解。用 `scene_save` 保存新版本，再重开并读回同版工程。用 `scene_export`、`snapshot` 或已验证的原生界面采集需要的图、读数和网格。记录 worker、CLO 版本、工程版次、姿势、原生来源和导出路径。将证据传回并核对后，停止本轮专用 worker。四尺码十动作按该技能的批处理手册取证。

快照恢复后的历史烟测验证了 48 个工具可列出、`clo_status` 在线和空白场景读回。每轮保存回读和实际求解仍需从本轮工程取证。

[Boat 与 CLO 3D 服装设计操作指南](https://chatgpt.com/space/page_4ceb4ccf67b88191883cc003636b76cd)
