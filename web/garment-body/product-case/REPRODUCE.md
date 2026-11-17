# 实际商品案例：复核与重放

先 clone https://github.com/liush2yuxjtu/pattern-agent 并切到发布本包的提交。
从仓库根目录解压 reproduce.zip，然后运行 python REPRODUCE-RESTORE.py。
复核包按SHA256去重：恢复脚本将相同原始字节复制回其所有原有路径，并逐项校验。
包内 work/ 路径须原样保留，不能只移动 model/。
脚本使用仓库现有 web/human-studio/body-engine.js、vendor 与 human.json。
Python 依赖：numpy、scipy、opencv-python、Pillow；Node 使用仓库已有依赖。
读取 work/product-red-pointelle-20261117/model/README.md 的复核与重放命令。
renderer源文件同时解压到 work/anatomical-skill-evals-20261117/fixtures/render_mesh.py。
先核对 REPRODUCE-MANIFEST.json 的逐文件摘要，再在工作副本运行；重跑会覆盖输出。

generation-1 是袖长错误的冻结对照；model/generation-1 只用于历史只读审计，
其中脚本的相对层级是归档前层级，不在该子目录直接执行。当前可执行脚本位于 model/。
保留 generation-2 实际图像、冻结分割、相机、姿态、cm网格、带骨骼GLB、数值深度、
OpenCV图与指标。排除Python缓存、重复的早期iteration-1树、源站抓取base64缓存，
以及已被最终候选替代的M基线单图/原图诊断渲染和torso-only中间图；其状态/指标/搜索记录仍保留。
这是选定复核子集，不是整个执行工作目录：第一轮六张原生照片、审查、状态/网格/指标保留，
第一轮旧模型光栅预览/数值深度未打包（本地完整记录保留，必要时可从归档网格重渲染）。
原图专项旧候选保留状态/网格/指标及前后对比图，省略旧候选的重复光栅预览。
Image Gen是外部非确定性生成，不承诺字节级重新生成相同照片；原始返回字节已保留。
这不是布料/组织物理仿真。人体以中码先验初始化；包络约束下的条件调整值与网格参数，
均不是原模特真人测量。请以当前CSV的basis与模型报告区分先验和条件估计。
