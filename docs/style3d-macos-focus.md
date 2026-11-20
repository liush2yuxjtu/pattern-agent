# Style3D 在 Mac 上保留键盘焦点

在 macOS 上通过 MCP 自动操作 Style3D 时，以 `QT_MAC_SET_RAISE_PROCESS=0` 启动 Studio。2026 年 11 月 20 日，在 Style3D Studio 10.1.258 上用同一个动作工程复测，打开、保存和导出期间，键盘焦点始终留在 Codex。

## 启动方法

保存当前工程并正常退出 Style3D，然后在终端运行：

```sh
/usr/bin/open -g --env QT_MAC_SET_RAISE_PROCESS=0 /Applications/Style3D.app
```

变量由新启动的 Style3D 进程读取。下次需要后台执行 MCP 任务时，继续用这条命令启动。实测启动时 Style3D 和 CrashServer 曾短暂切到前台，适合在批处理开始前提前启动。

## 复测结果

- `Project.Open` 成功 2 次，包括最后恢复原先打开的工程。未观察到焦点切换。
- `Snapshot.ExportImage3D` 成功 3 次，导出 3 帧各 3 个视角，共 9 张 PNG。渲染对话框照常打开，未观察到焦点切换。
- `Project.Save` 成功保存 1 份工程副本，归档完整性检查通过。未观察到焦点切换。

通过 macOS 应用激活通知、前台应用轮询和系统日志交叉核对。结论适用于这次测过的调用和版本。

## 触发机制与 Boat 行为

Style3D 导出时会打开渲染进度框并调用 Qt 的 `raise()`。Qt 6.3.2 的 Cocoa 实现默认请求 AppKit 激活整个应用。这个环境变量关闭该分支。 [Qt 6.3.2 Cocoa 源码](https://github.com/qt/qtbase/blob/v6.3.2/src/plugins/platforms/cocoa/qcocoawindow.mm#L901-L923) · [Style3D 第三方组件声明](https://www.style3d.com/oss)

在 Boat 的 `style3d-studio-10-1-wine` 快照上，同一个工程的打开、保存和 3 次导出都把焦点切到了虚拟机内的 Style3D。Mac 没有观察到切到本机 Style3D。
