# GitHub Pages 线上验证：PASS

实际页面：<https://liush2yuxjtu.github.io/pattern-agent/cloth-lab/>。
部署版本：`b90b22582072912df8ab4041bbf3d4113bab49d8`。
HTML SHA-256：`2581406c2493386262fc3d0bb0af0b479eb55119021ae299ac1cafcd26dc0a1f`。

[真实发布记录](deployment.json)对应 [Pages 发布任务](https://github.com/liush2yuxjtu/pattern-agent/actions/runs/44080589244)，
但线上 PASS 取自实际公开 URL 的浏览器行为、下载及独立重开，不取自发布任务状态。

## 实际线上结果

- [原始 Playwright 收据](receipt.json)：**15 项检查全部通过**，没有页面异常、
  控制台错误或 HTTP 错误；真实线上 HTML 与本地测试字节及部署 commit 一致。
- 默认/移动人体/恢复穿透的导出网格经独立 NumPy/trimesh 重新读取：缝隙 0 mm，
  4,770 个采样点无人体内点，衣片边→人体面、人体边→衣片面两种相交均为 0。
- 全部三角形应力应变、静止/刚体旋转/10% 经纬拉伸/剪切试片与独立公式吻合；
  实际颜色属性由这些场驱动。故障场景和被篡改的数据均被拒绝。
- 真正下载 SVG、场景 OBJ、工程 JSON、诊断和带状态 HTML。断网后坐标、上一帧
  及下一步精确一致；重新打开后再次保存仍保留新状态；移动人体后的固定点续算一致。
- 软件 ANGLE/SwiftShader、像素比 0.8，线上 120 帧样本中位帧时间 **33.4 ms**，
  p95 **66.605 ms**。受控 20 步对照：缓存约 **4.0 ms/步**，完整查询约
  **61.275 ms/步**，位置数组逐位一致。不是硬件 GPU 的帧率保证。
- [既有站点线上回归](existing-pages.json)也通过：四个真实下载匹配部署哈希，
  手机弹窗、工作台编辑/导入/导出、拒绝不支持格式及不存在文件 404 均保持正常。

## 截图与实际文件

- [正常织物](step-300-fabric.png) · [应变](strain.png) · [应力](stress.png)
- [人体移动](body-moved.png) · [错误缝合](fault-reverse.png)
- [手机布局](mobile.png) · [断网重开](offline-restored.png)
- [实际下载文件包](actual-downloads.zip)及[各文件 SHA-256](actual-download-hashes.json)
- [环境版本](versions.json) · [浏览器原始日志](browser.log)

已视觉复核实际线上应力图和人体移动后的图像；没有用生成图片替换仿真。
材料仍是合成参数，默认局部主应变约 **23.92%**、主柯西应力约 **53.88 kPa**，
页面保留高应变警告。材料标定、布料自碰撞、连续碰撞检测、完整成衣与实体适体
仍是 **NOT_RUN**，线上 PASS 不覆盖这些边界或历史 T 恤 FAIL。

## 测试工具的网络修复

首次线上测试在辅助 APIRequestContext 读取时遇到直接 IPv6 连接不可达，
保留在 [首次 BLOCKED 原始日志](first-api-blocked/cloth-api.log.gz)。Chromium 当时已能
加载真实页面，但不能据此宣告完整 PASS。

依据 [Playwright APIRequest 文档](https://playwright.dev/python/docs/api/class-apirequest)
加入 `scripts/playwright_http.py`：辅助 HTTP 客户端显式继承现有 HTTP(S) 代理和
NO_PROXY，保持 TLS 验证。没有改网络策略、代理环境、DNS、响应头或返回内容，
也没有改物理程序与验收阈值。修复后线上完整测试及本地主页测试均通过。

本证据/测试工具后续提交不改变 `web/`，不会触发新 Pages 发布。以上部署身份始终
指向实际测过的 `b90b225`，而不是误称后续纯证据提交为新部署。
