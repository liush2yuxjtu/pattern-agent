# 原生 CLO 3D · 四尺码十动作

在独立 Boat Wine fork 中使用有授权的 CLO 3D 编辑器。先确认每台的并发授权及当前编辑器版本，依次打开 **Animation → Animation Editor** 和 **Edit → Python Script**。每个 worker 专用，脚本会替换其当前工程和 Python Editor 内容。准备好本轮的 S、M、L、XL 原生 `.zprj`、FreeSewing 量体与裁片记录、线稿及动作包。示例里的项目位置、阈值和机器列表由执行者按本轮实际内容填写。

```sh
python3 scripts/clo-motion-batch.py --config /path/to/batch.json --out /path/to/evidence --jobs auto
```

配置模板为 [clo-motion.example.json](../../scripts/clo-motion.example.json)。路径相对配置文件。并行上限是待运行组合、专用 worker 和验证可同时使用的 CLO 席位三者的最小值。配置并发机器前，先从独立 fork 验证登录与录制。检查 Boat 的当前并发、创建配额和计划用量，以可用容量启动 worker。

Boat worker 需要 `xdotool`、`xclip` 和经试跑的 CLO Wine 2026.1.382 桌面。安装 `wmctrl` 时可以移动 Python Editor。默认使用 `scp`。SSH 连接不可用时，可把 `boat.transfer` 设为 `"exec"`，通过 Boat 已认证命令通道分块传输并校验 SHA-256。同一 worker 会按 SHA-256 复用已传入的工程和动作。Python 3.9+ 需要 Pillow。折角复用同仓库 `clo-fit-export` 的 NumPy 和 Matplotlib 脚本。视频汇总需要 FFmpeg 或 `imageio-ffmpeg`。若修改了工程、动作、阈值或抽查帧，程序按新输入指纹生成独立证据。使用相同输出目录可续跑。加 `--review-only` 可从已下载的原生记录离线生成审查包。

## 动作包

在安装 Blender 的环境，按 01–10 顺序传入已有动作和对应的 V4 `.savt`。资产与模型数据保留在本地工作区。

```sh
blender --background --factory-startup --python-exit-code 3 \
  --python scripts/clo-motion-assets.py -- --avatar /path/to/Female.savt \
  --out /path/to/motions /path/to/ordered-motion-files/*.sanim
```

转换以同一动作变换和皮肤绑定为输入。检查 Style3D 每帧读回与源一致、Blender 导入的 FBX 关节位置和网格，并从 `motions.json` 查看帧数、帧率及误差。CLO 中导入 FBX、读取实际时间轴和关节位置，再核对姿态峰值、行进轨迹和回位。已独立验证的 `.mtn` 在动作配置填写，保留工程内的尺码人台。直接使用 FBX 人台时，先核对同一尺码及着装对齐，再在该尺码的 `checks` 中设置 `use_fbx_avatar: true`，读取工程时只载入服装。FBX 离线读回与原生 CLO 导入是两项独立验证。

逐尺码的动作文件填在 `motions.<动作>.fbx_by_size`。`sizes.<尺码>.checks.fbx_scale` 以 CLO 导入后回读的人台网格为准，工程缝组数可填 `seam_group_count`。包含人台修正形变动画时设置 `fbx_blend_shapes: true`。`motions.<动作>.checks.warmup_frames` 对应原生录制开头的预热段，动作帧号与导出视频从预热结束后开始计数。

同一动作的某个尺码需要更多预热或更细的求解时，在 `motions.<动作>.checks_by_size.<尺码>` 覆盖 `warmup_frames`、`native_simulation_quality`、`native_simulation_substeps`、`native_self_collision_iterations` 或 `native_particle_distance_mm`。设置粒子间距后，录制前逐片回读，单位为毫米。原动作帧数、抽查帧、帧率和验收阈值继续由共同配置确定。有效设置随该组合的输入指纹保存。 [CLO Python API](https://developer.clo3d.com/list.html)

`pieces_mm2` 取经独立核对的已保存 `.zprj` 的裁片面积。CLO 的曲线保存和重载会导致原始绘制面积出现微小差异。请分别保留纸样轮廓和已保存工程的回读记录。

检查动态人台表面时，使用原生服装录制对应的 Avatar Cache Animation（Alembic）。2026.1.382 的 FBX 人台 OBJ 导出在试跑中重复输出结束帧的身体。用两个动作幅度明显不同的原生帧确认缓存确实随帧变化，再用同帧的数字网格核算穿插。

## 审查

1. 打开 `stats.csv` 读 40 项统计判定。退出码 2 表示存在失败或缺证。修复后再次执行同一命令。
2. 打开 `index.html`，逐动作看关键帧卡片。可从 `frames.csv` 跳转到原生视频时间，检查异常前后。当原生读数不可导出时保留缺证。折角来自同一帧的原生衣片网格。
3. 在输出目录的 `visual-review.json` 以 CSV「指纹」为键写入 `{"status":"PASS","notes":"实际观察"}` 或 `FAIL`，再用 `--review-only` 汇总。每项检查外观与设计稿、袖口或裤脚及领口的包覆、局部压迫和靠近缝线的拉扯。批处理完成与服装合身各自判定。

有同帧点测截图时，可在该图层记录 `point_image` 相对路径，审查卡把原生点测截图排在统计值旁。色图保留采集时的光标。应变截图显示 CLO 原始百分比，统计显示相对 100% 的应变增量。

原生采集尝试读取 CLO 的动画时间轴、录制和保存工程、逐帧导出网格及外观图。需要同时核对 CLO 实际支持的拟合图采集和数值导出能力。数据缺失或只取得截图时，定量判定保留为待补证。
