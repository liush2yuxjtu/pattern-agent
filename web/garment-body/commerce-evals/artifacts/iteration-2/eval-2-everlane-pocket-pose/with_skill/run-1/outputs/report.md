# Everlane 原姿态人体拟合

本轮实际生成一张 ImageGen 点线引导，实际执行厘米校准、163 骨 FK/LBS、三候选优化与真实三角网格渲染。原图 2400×3000 原字节在 reference/original.jpg；native 引导 1121×1403 在 images/pose.png，receipt/input hashes 保留。本分支完整六图生成 NOT_RUN。

## 输入、尺寸和动作
原图来自 source.json 的 Everlane 官方 URL；官方模特身高和穿着码均未知。170cm、90/72/96cm胸腰臀为授权 generic M170 先验。所用成人女性 MakeHuman CC0 模板不意味着恢复了真人。宽松浅蓝长袖衬衫敞开、袖口卷/推起；白色内搭、黑裤和腰带是独立服饰。图像左侧（人体右）手臂下垂；图像右侧（人体左）手插前袋。隐藏左腕值在观测表为 null，拟合中只有权重0.12的粗范围假设。

## 实际拟合和引导
fit.py 从 generic neutral-state 独立启动。三候选分别使用正面/12°/-8°相机初始；第三候选条件性上臂/前臂表面尺为30/24cm。其余M先验不变。每候选联合优化相机与显式骨骼轴映射，完整保存参数块。数值过程30.13秒（实际 monotonic 本机计时，包括导出渲染；不是服务端遥测），不含生成等待。最终所有厘米/角度量化至0.1，再用同一状态重建所有几何。未复用其他run结果或案例解法。

ImageGen与数值流程异步；生成结果到达后执行SIFT/RANSAC原图配准，91内点，均误差2.15原图像素。引导用于动作语义复核，而未直接把生成点当数值检测真值。实际引导的右腕点仍落在袖口上方，予以拒绝，以原图可见手腕[888,1604]为约束。左腕/骨盆/膝保持推断。没有在生成到达后另起数值优化，故不能声称生成引导已定量改善拟合；也未把生成图作为新的轮廓参考。

## 网格和证据
final-state.json、neutral.obj、posed.obj 为真实人体，同状态 views/ 由 Runtime.save 保存。原相机 photo-render.png 为真实2400×3000光栅化，无PNG拉伸；camera.json含3×4 world_to_pixel_homogeneous及实际欧拉相机参数。原点Y向上、OBJ厘米，旋转采用YXZ。rawdepth.npy为相机旋转后的世界Z（越大越近，cm），背景-inf，depth-valid.png为有效标记；不是距相机的轴向距离。projected-joints.json保存完整实际FK关节世界与像素位置；inside_canvas不是遮挡可见性。

独立 inspect_human_state 使用匹配human.json重建neutral，最大目标误差0.00004045cm。artifact-checks.json保留实际顶点/拓扑/深度和同状态检查。bone-lengths.json是关节头到父关节头距离，和表面尺分开。measurements.json/CSV逐项保留prior/mesh_parameter/unavailable来源；不能将网格复量升级为真人实测。

## 观察和限制
OpenCV GrabCut在600×750执行，最近邻映射至原画幅。保存reference-mask及绿重合/粉参考独有/青模型独有叠加。相同最终相机下初始IoU0.5620，最终0.6907；Dice0.7196→0.8171，轮廓P95 370.93→217.17px。它们是穿衣包络对裸模的差异，不是身体测量准确率。initial own-camera另外保留以区分相机贡献。regional-observations为事后诊断，非事前冻结的独立验收协议，不声称所有关键区域通过。

真实正侧视已人工查看：右臂近直、左肘约29°弯曲；左腕在骨盆前侧，但手掌张开、位置过于向前，未恢复插袋接触和手指隐蔽形态。下肢站姿仍为neutral先验，真人裤下腿形未知。camera yaw到-30°边界，说明单张2D目标存在相机/姿态歧义，不能声称原相机已辨识。pocket-diagnostic只做公开启发式，NOT_ASSESSED；其链段倾斜警告包含rig根节点偏置，不是碰撞结论。未执行皮肤自交/手腹碰撞/服装仿真，故严重重叠覆盖 UNKNOWN。背视图片保留供复核，本次未单独目视验收。最弱证据为隐藏左腕/掌形、侧背、裤下腿形与躯干真实围度。

viewer.html通过同仓库真实Human Studio加载最终状态，可调厘米尺寸和完整姿态并导出。需HTTP服务；完整浏览器交互、保存重载和窄屏测试NOT_RUN，不冒充已验证。只有原始照片拟合；不存在独立真实侧背验证或生成六图一致性结论。功能产物齐全不代表动作或真人尺寸验收通过；本run不自评分。
