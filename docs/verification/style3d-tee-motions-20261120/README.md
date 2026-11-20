# Style3D M 码针织长袖十项动作发布验收

本地网页验收为 PASS。基线提交为 `7eae27520d0704f2cb588e61c823277cd8fb9837`，添加验收记录前的候选 Git tree 为 `2286dd6618304e3d2562cccf3cdd76a7e5f4f503`。服装的判定范围为已录制轨的 113 个抽查帧。实体试穿与浏览器内模拟为 NOT_RUN。

- `python3 scripts/build_pages.py` 构建成功。
- `python3 -m unittest discover -s scripts -p test_verify_artifacts.py -v` 的 6 个既有用例通过。
- `python3 scripts/verify_pages.py --browser <Chrome>` 通过首页、4 个下载、既有 T 恤工作台和 375 px 移动端回归检查。
- `python3 scripts/verify_style3d_tee_motions.py --browser <Chrome>` 从首页进入复验，播放 5 段 MP4，跳到 59.75 秒，打开 4 份报告，核对 4 个下载的 SHA-256，并检查缺失视频返回 404。原通用本地服务器未实现字节范围，首次跳播复验超时。使用带字节范围响应的本地预览重测通过。
- `git diff --cached --check` 通过。

[浏览器验收记录](receipt.json) · [桌面预览](desktop.png) · [移动端预览](mobile.png)
