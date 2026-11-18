# Everlane 单原图条件人体与六张生成图

已实际完成 1 次原图姿态引导和 6 次独立 ImageGen；全部原生 PNG 与调用参数、返回输出路径、尺寸及输入 SHA256 保存在 `images/` 和 `receipts/`。未裁拼图、未放大。正/侧/背/特写原生 1122×1402；pose/depth 原生 1024×1536。原图为未修改的 2400×3000 JPEG，来源与官方细节保存在 `reference/source.json`。

模式 `prior_avatar`。身高170、胸90、腰72、臀96cm等来自授权 generic M170 neutral prior，不是照片真人测量。照片只提供穿衣外观、腕部可见位置、粗肢体方向、裁切；没有可靠真人尺度、背面或下腿证据。单张穿衣图不足以识别围度，因而保留12项先验尺寸，实际校准morph并拟合姿态/相机，不缩小围度躲进衣服。模型 MakeHuman CC0，13,380表面顶点、26,756三角形、163骨；OBJ为Y-up厘米。没有SMPL、布料、组织或碰撞仿真。

## 执行与可重建文件

从共享neutral独立运行 `fit.py`，没有读旧拟合、其他run或私有评分。两块候选分别从yaw0°和10°初始化，SciPy bounded least_squares实际优化明确映射的肩/肘/颈/头角度及相机；脊柱保持初始值。日志见 `parameter-block-history.json`。生成前角度和cm状态按0.1规范化后重新导出；`generation-inputs/`保留生成时最终状态、相机和真正输入PNG。生成后没有修改人体。

`final-state.json` 保存完整163骨姿态、厘米目标、measuredNeutral、morphWeights和资源指纹；`neutral.obj`、`posed.obj` 可复算。独立neutral重建结果见 `evidence/neutral-check.json`，重建测量差约2.84e-14cm，目标残差约4.04e-5cm。这只是模型校准精度，不是真人误差。`views/`由Runtime.save同状态导出正/侧/背/pose/depth和各mask、完整joints/state/camera及哈希。独立OBJ和投影复核见 `evidence/replay-check.json`。

`camera.json`记录原生2400×3000、3×4世界到像素矩阵和实际oblique orthographic六参数；未拉伸PNG。`photo-render.png`为实际网格原相机投影。`source-depth.npy`是旋转相机坐标Z厘米值，越大越近；无效背景 -inf，与`source-depth-valid.png`分开。`views/rawdepth.npy`是canonical front同相机几何Z-buffer，非生成图。`source-joints.json`和`views/pose-joints.json`是FK实际投影，in-canvas不代表未遮挡。

## 原图动作和残差

原图双腕均可见，标注位于皮肤/手掌连接而非袖口；肩肘和骨盆为衣下粗关节先验，含不确定性。先实际ImageGen保留动作的引导，再SIFT/RANSAC配准回原图，保存原坐标、矩阵、内点误差和语义审查。引导点仍是示意；原图腕连接有优先级。腿脚与三维隐藏深度没有被发明为观测。

最终粗关节点RMS约47.74px。相机yaw约20°、pitch约10°触及边界，揭示相机/骨架/人工标注歧义；不能据此宣称姿态精确恢复。侧背实际渲染显示站立、手臂下垂、轻度屈肘，没有把手放臀后；腕掌朝向与原图仍可能不同。pose-audit产生一项累积脊柱段倾斜警告（root到spine05为模型结构连接）；已保留，未通过改字段消除。工具acceptance为NOT_ASSESSED。没有执行完整皮肤自交检测，不能声称无穿身或动作通过。

GrabCut在600×750执行，再最近邻映回原分辨率；原图右侧头发附近存在背景误收，参考mask有已知局限。它是衣物/头发人物包络，不是裸体真值。参考及区域在优化前冻结，优化本身使用关节点，不使用该mask追逐分割误差。相同最终相机和2400×3000比较初始/最终：IoU 0.6160→0.8339，Dice 0.7624→0.9094，对称轮廓均值171.23→64.38px，P95 511.64→250.25px。指标改善不表示所有局部匹配，更不表示真人尺寸准确。初始mask是初始neutral在最终相机下的公平比较；initial-camera.json另存初始化相机，不能混作该mask相机。局部包络、中心扫描线见`evidence/regional-diagnostics.json`，没有私有评分/自评分。

## 商品与生成图限制

直接查看原图并核对source中的官方说明：白色轻薄棉府绸、宽船领、暗门襟、腰省、长袖挽至前臂带袖口、黑裤，无新增饰品。六图逐张目视检查保留这些主要特点。背面收省/缝线、侧面隐藏结构、完整裤腿鞋均为推断。原图腿脚被裁切，生成补全不构成真人验证。pose图有额外胸点且非检测拓扑；depth只是艺术相对深度风格，不作数值深度。生成器把部分站姿、腕掌和手指细节规整，六图没有天然逐像素或精确3D姿态一致性保证；最弱证据是隐藏侧背和手部。没有把生成质量冒称几何测量准确。

`viewer.html`配套`viewer-server.py`为可继续编辑入口：在此目录运行`python viewer-server.py`，打开127.0.0.1:8877/viewer.html。12项cm参数和163骨XYZ角度驱动实际Runtime重建，支持前侧背、状态保存/导入，无浏览器缓存。真实参数/姿态改变顶点、非法类型/越界/0.1步长的程序检查见`evidence/viewer-check.json`。浏览器UI点击、手机布局、完整GLB导出和生成按钮后端均NOT_RUN/未连接；未虚称完整UI验收。当前改动后的照片指标不再有效。真人准确性需要同人可靠身高和原始多视角，物理试衣仍未运行。

未知token/耗时保持null。没有提交或推送。
