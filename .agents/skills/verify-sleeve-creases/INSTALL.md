# 使用方法

在本仓库的 Codex 会话中显式请求 `$verify-sleeve-creases`，或把
`verify-sleeve-creases.skill` 解压到本仓库的 `.agents/skills/`，保留整个技能文件夹。
这是项目级技能，完整工作流依赖本仓库的 AGENTS 与 verify；单独解压仍可运行随包的离线 CLI 与测试。
Claude 项目路径通过 `.claude/skills/verify-sleeve-creases` 链接到同一 canonical 源。
文件存在和打包成功不证明客户端已加载或原生自动触发；本次未做 native routing 评测。

只需 Python 3.9+ 的标准库即可重测冻结样例；没有新增依赖、付费算力或 CI。

```sh
python -m unittest discover \
  -s .agents/skills/verify-sleeve-creases/scripts -p test_inspect.py -v
```

实际工作室的“袖子尖折诊断”可以导出包含 `geometry` 的 JSON，直接传给
`scripts/inspect.py --input ... --out ... --trace ...`。CLI 输入格式和结论范围见 SKILL.md。
作者原有私有 Site 的访问范围保持不变；离线 CLI 和随包控制文件不依赖该 Site。
