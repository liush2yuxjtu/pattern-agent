# 03_cuff_width：来源绑定物理记录

整衣结论 **PASS**；准备状态 **PASS**。记录角色：`candidate`。
机制对照或查看器通过不能覆盖该结论。真人合身及面料实测仍为 NOT_RUN。

- [完整文件摘要](artifact-manifest.json)
- [实际条件（中文 YAML）](experiment-conditions.yaml)
- [设计意图](intent.txt)
- [逐帧独立报告](audit.json)
- [准备状态检查](preparation-gate.json)
- [新进程继续检查](resume-independent.json)
- [完整输入 JSON（无损压缩）](input.json.gz)
- [全部61帧真实记录（无损压缩）](trajectory.json.gz)

原始规格、DXF与该案例实际差异文件均在本目录，文件名和内容保持原样。
`source-reference.glb`只是从二维来源复核的静态壳，不是物理轨迹。
`solver.wasm`及`solver-capacity.c`是实际执行文件与生成源码；`frozen-source/`记录运行时源码字节。

将两份 `.json.gz` 解压为同名 JSON 后，按[上级物理实验说明](../../README.md)从仓库根复验。
所有文件均有压缩字节及原始字节SHA-256，解压不作量化或坐标取整。
