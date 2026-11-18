# Everlane 原动作人体拟合

本次实际执行 Image Gen 原图姿态引导 1 次、真实 MakeHuman 解剖网格厘米校准、163 骨 FK/LBS、相机/姿态优化和原分辨率光栅化。完整六张服装生成分支：**NOT_RUN**，本 prompt 明确不要求。未调用私有评分器，无案例总分或断言自评。

`original.jpg` 是未改变的 2400×3000 官方商品响应字节，SHA-256 与 source.json 一致。官方身高和模特尺码均未知。170 cm / M 是获准的通用假设，全部胸腰臀、肩宽和肢体尺寸仍为先验，并非真人测量。松衬衫、白色内搭和宽裤属于衣物包络；不能将包络围度当裸身围度。模型使用实际 CC0 MakeHuman 成人女性模板，资源指纹见 final-state.json。

`images/pose.png` 是 Image Gen 原生 1121×1403 示意引导，原生返回路径、请求和输入哈希保留于 pose-receipt.json。生成有轻微重绘：实际 SIFT / RANSAC 单应性配准 120 对匹配、89 内点、平均内点残差约 1.95 个原图像素，见 guide-registration.json。该残差只表示纹理配准，不是关节准确率。guide 的肩点外置，腰带点不等于髋关节；人工向解剖肩/髋位置纠正并降低不可观测点权重，见 guidance-points.json。image-right wrist.L 在袋内，只有低权重条件位置，不是可见腕真值。膝和髋被裤遮盖。

从 fixtures/neutral-state.json 独立开始，先相机，再姿态，再联合相机/姿态，均从真实骨骼计算。第一候选颈/脊柱不合理，保留 rejected-unconstrained-state/history；第二候选加入颈脊 ±7°、膝和髋范围约束并重跑同一三块流程，最终角度规范化到 0.1°。两个候选优化部分计时合计约 4.28 秒；这不包含渲染、生成、等待、代码编写或总任务时间。总时间及 tokens 未知为 null。全部12项 M170 中性尺寸保持先验，没有依据单张宽松穿衣照片改小围度。参数块的全部初终值与实际目标函数变化保留在历史 JSON。

`final-state.json` 保存厘米 dimensions、morphWeights 与完整 163 骨 poseDegrees。`neutral.obj`、`posed.obj` 是真实皮肤表面，Y向上、cm。`camera.json` 包含实际 2400×3000 的 3×4 world_to_pixel_homogeneous；不拉伸图片。final 内中心是世界原点的像素位置，轴顺序和旋转矩阵明确记录。`photo-render.png`、`final-mask.png`、`depth.png`、rawdepth.npy 和 depth-valid.png 同一相机、网格。raw depth 为相机旋转后 Z cm，越大越靠近观察者，背景 -inf，非射线长度、非真人单目深度。

`views/` 由 Runtime.save 实际生成正侧背：尺寸和完整骨骼姿态与主状态相同，仅相机改变，OBJ 逐字节一致。pose-joints.json 保存真实世界和原图像素坐标；in_frame 不等于可见性检测。侧面目视显示插袋一侧手在髋后侧附近，原照无法确定深度、腕旋转及手指。手指保持默认，不声称正确复原插袋接触。未运行完整表面自碰撞或组织/衣物模拟；严重穿身是否存在需独立几何检查，不能由二维覆盖推断通过。

OpenCV GrabCut 在600×750实际执行，最近邻还原原分辨率，reference-mask.png 可检查；它不是精密真人分割。initial/final 使用同一最终相机重新渲染，另存 initial-unfitted-mask / initial-camera 以分离相机贡献。metrics.json 记录衣物包络 IoU 约 0.517→0.738、轮廓P95约305→201像素；它们只描述裸模投影与穿衣图之间差异，不能证明裸身尺寸或动作通过。头发、长裤和鞋差异明显。区域诊断与中心扫描在完成拟合后建立，未用作优化条件，也未声称预冻结验收协议；见 regional-observations.json。没有独立真实侧背证据，生成图不能补足真实隐藏解剖。

独立 inspect_human_state.py 从匹配 human.json 和保存系数重建中性顶点，最大重建尺寸差约2.84e-14 cm；最大目标残差约4.04e-5 cm。这仅检查厘米模型合同，不是本评测自评分。artifact-checks.json 验证163骨、维度一致、同状态OBJ和非空有限有效深度。不可观测的下胸围、胸点距、裆弧、腰节长、肩斜保留 null。

可调入口 `adjust.py`：在本目录执行 `python adjust.py --out adjustments/example --dimensions '{"height":172}' --pose '{"lowerarm01.R":[-30,0,5]}'`，通过真实 Runtime 重新校准形变及完整FK/LBS后另存新状态、网格和正侧背。调整后原叠加指标失效。`fit.py` 是本次可复算求解代码。没有提交或修改输出目录外的项目文件。
