# 安装与使用

技能名称：garment-body-six-view。

## Claude Code

解压后，将整个 garment-body-six-view 文件夹放在当前项目的
`.claude/skills/garment-body-six-view/` 下，确保该文件夹直接包含 SKILL.md。
此包没有自动安装程序，也不会自动修改个人配置或调用付费生成服务。

## Claude 的自定义 Skills 界面

若当前账号/界面提供上传自定义 Skills 的功能，使用 ZIP 包导入；
`.skill` 也是 ZIP 格式，可按支持的格式使用或解压。
不同客户端的上传入口可能不同，不保证所有客户端均提供相同界面。

## 示例调用

“使用 garment-body-six-view，基于这张模特穿着商品的原图，生成六张独立高清图；
建立可调节裸模，用 OpenCV 和真实三维快照验证，输出带证据来源的人体体形参数。”

“继续改进已有裸模的侧面匹配，不重新生成参考图。同步滑块和网格，展示优化前后叠加。”

## 依赖与能力

SKILL.md 是 agent 的操作指令。图像生成、模型权重、3D 模型资源和网页浏览能力由运行环境提供。
包内提供两个可执行核验辅助脚本，不声称提供完整的一键人体重建引擎。
需要辅助脚本时，在隔离 Python 环境安装 requirements.txt；使用方法见 references/tools-and-evidence.md。

## 验证范围

已通过 Anthropic 官方 quick_validate.py 的技能格式检查，以及当前 16 项 Python 辅助脚本测试。
另完成 3 个方案场景的独立 agent 有/无技能对照；这不是 Claude 平台的端到端图像生成评测。
此包没有包含本次对话的商品图片、原图、人体网格或任何密钥。

## Pattern Agent 集成

规范源码：`.agents/skills/garment-body-six-view/`。`.claude/skills/garment-body-six-view` 的相对链接指向同一份源码，供 Claude 发现；实际自动加载尚未实测。
触发评测准备、原生运行依赖和严格错误处理见仓库 `tools/skill_evals/README.md`。
本环境没有 Claude CLI，原生触发率、描述 hill climbing 及 Claude 端到端任务评测仍为 BLOCKED，不能从文件存在推断自动加载成功。
