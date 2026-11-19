# 零基础纸样教程验收

候选以远端 `main` 的 `e17b78ed74078ecbb70c1add42152aa706c1418d` 为基线。教程的发布入口是 `web/pattern-drafting/`，候选网页哈希见 [网页校验值](sha256.txt)。

## 本地验收

`node scripts/verify_pattern_drafting.mjs` 使用本地 HTTP、Playwright 和系统 Chrome。通过首页导航进教程，实点八款的 296 个落笔目标，逐步检查笔画数量，再检查撤回和清空。打开修身衬衣的二维纸样，切换步骤后刷新确认恢复；在 320 像素重新检查 A 字裙转省和上衣第一笔，无横向溢出或页面脚本异常。

本地交互判定为 **PASS**。样衣试穿与纸样的实物验证未运行。
