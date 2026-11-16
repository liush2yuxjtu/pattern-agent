# 评估与优化

维护时按 Anthropic skill-creator 的旧版快照 → 真实任务 → 断言评分 → 报告 →
修订 → 复测流程。旧版快照作为功能基线；不要把旧历史报告当成本次执行结果。

触发集为 20 条中英真实请求，10 正例和 10 相近负例。固定 seed=42，按类别分层
划分 12 训练、8 留出；每版三个独立路由评审。优化先看训练错误，最终冻结后再
报告留出结果。它们是独立模型的描述适用性代理评估，不是原生调用频率。

原生触发需要 Claude CLI。在它可用且已登录的环境，从 Anthropic skill-creator
源码根目录运行以下命令；将路径替换为本仓库位置，model 使用实际评估模型：

```bash
python -m scripts.run_loop \
  --eval-set /repo/.agents/skills/garmentcode-preview/evals/trigger-evals.json \
  --skill-path /repo/.agents/skills/garmentcode-preview \
  --model YOUR_ACTUAL_MODEL_ID --max-iterations 5 --verbose
```

本次环境没有 Claude CLI，Codex CLI 的模型连接也遭代理拒绝。原生触发应记为
BLOCKED，不把代理路由的通过率称为真实客户端激活率。人工反馈是否完成、功能
执行次数、时长和 token 是否可得，都在每次的 docs/verification 记录中单列。

在 pattern-agent 内优先复用 tools/skill_evals/run.py 的 strict adapter：
prepare/doctor 可先检查格式与运行时；optimize 的 --skill 指向本技能，--eval-set
指向上述触发集。它保留外层留出集，运行时失败维持 BLOCKED，不把失败计为正确负例。
原生输入只保留 query 与 should_trigger 两字段，内部案例 ID 另存评估记录。

功能用例与断言在 evals/evals.json。用旧版和候选版分别运行真实输入，保留命令、
输出和失败；独立读取 GLB 实际字节、比较单位和拓扑，验证显式状态及缺失输入。
CPU 仿真要实际完成并记录源版本、帧数和相交计数；不因输出文件存在就算成功。

用 skill-creator 自带 aggregate_benchmark 与 eval-viewer/generate_review.py
生成可人工检查的报告；机器评分不替代人对网页和预览质量的判断。没有用户反馈时
标为未评阅，不伪造 feedback.json。样本量小，不能据此宣称普遍能力或速度优势。

报告包含预览 HTML 时，用仓库 scripts/build_garmentcode_eval_review.py 调用
固定官方生成器并只转义其嵌入 JSON 的小于号，避免预览中的 script 结束标签截断
外层报告。包装器验证转义前后 JSON 相同，官方生成器源码保持不变。
