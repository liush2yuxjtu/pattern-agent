# 布料自交组件负例

原33轮准备末态：人体样本与双向交叉为0，但严格布料自交为6，所以整衣准备结论FAIL。这里保留完整输入、实际float32末态及当时WASM，给 `test_self_step_guard.mjs` 的真实7186面控制使用。它不是通过的穿着状态，也没有正式物理轨迹。

从仓库根运行：

```sh
SELF_GUARD_REAL_FIXTURE=experiments/intent-edit-review/physics/fixtures/self-contact-negative \
  node experiments/intent-edit-review/physics/test_self_step_guard.mjs
```

保护模块把“初始到第24轮末态”作为一次线性候选时，可以返回自交0，却重新产生人体穿插。该跨多轮探针不是物理步；独立人体检查仍FAIL，证明自交保护不能替代人体验收。最终逐步耦合结果另见results。
