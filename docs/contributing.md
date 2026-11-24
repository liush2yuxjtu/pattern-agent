# 贡献与复核

[返回 README](../README.md) · [仓库执行规则](../AGENTS.md) · [真实贡献提交](https://github.com/liush2yuxjtu/pattern-agent/commits/main/)

欢迎改进可复现样例、输入契约、独立检查和解释文档。贡献身份与历史以 Git 提交记录为准，这里不额外宣称社区规模或活跃度。

## 给维护者的最小交接

1. 指明输入文件、来源、单位、版本与要改变的判断；不要提交账户凭据、私有照片或未经许可素材。
2. 提供复现命令、期望与实际结果。几何、软件交互、原生模拟和实物试穿分别记录；保留失败和负例。
3. 文档或图表注明来源与含义。不要将示意图标作界面、将渲染标作真人试穿，或把检测日志写成求解日志。
4. 依 [verify 技能](../.agents/skills/verify/SKILL.md)运行适用的本地验证；记录候选版本、命令、证据和 PASS / FAIL / BLOCKED / SKIP。失败或阻塞不提交。
5. 有 main 写权限的维护者遵守 AGENTS.md：先检查远端与并发改动，再普通 commit/push 到 main；不强推，不创建 PR/Issue，不新增或运行 CI。没有写权限时，先准备可审阅补丁与证据，交由维护者确认，不能绕过权限。

[已有问题与反馈入口](https://github.com/liush2yuxjtu/pattern-agent/issues)可先查重；这不是要求创建 Issue，也不是已建立的响应时效承诺。引用问题时附公开的最小复现，不暴露私有工程。

## 历史结论不能清零

历史 T-shirt 的最大缝隙 7.6455 mm 与 20 处非相邻面相交仍 FAIL，实物试穿 NOT_RUN。任何新案例只能改变自己的验收结论。[旧 README 全索引](readme-history.md)与[验证档案](verification/)保留来源。
