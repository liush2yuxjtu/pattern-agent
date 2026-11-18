# FreeSewing 四片裙的项目入口更新

本次只更新公开 README、首页导航与说明，并保存可复跑的 Playwright 点击检查。
首页从“FreeSewing 四片裙”导航进入说明，再实际点击进入已验证的单文件。
原布料 HTML SHA-256 保持 de26a1069750fbabc7abeedac7d7040de3aff96e6f40bcec51267a017dc0316a。
页面明确保留 189.5% 局部伸长、材料／压力未标定和真实合体性未通过的边界。

遵循根 /verify 与 github-pages 配方：6 项原导出回归、首页完整浏览器流程、
实际新入口的源文件哈希绑定与后臀启动检查，以及桌面／手机截图均 PASS。
见 local-verification.json 的候选、命令和源文件哈希；local/ 内是原始收据和截图。
当前检查不重新批准材料物理标定，也不改变历史 T 恤失败。

其他项目 Pages 通过已授权的 Pages connector 定点更新并回读；个人／空间
页面原文和标识保留在私有工作记录中，不复制进公开仓库。保存的 Markdown
已经核对，Pages 本身的渲染版式没有进行浏览器目视复核。

新入口检查：python scripts/verify_cloth_entry.py --out work/cloth-entry-local
公网检查：同一命令增加 --url https://liush2yuxjtu.github.io/pattern-agent/
现有发布 workflow 仅用于发布；通过与否来自本地驱动实际页面的检查。

公网新入口专项检查已通过。完整公网回归在最后的缺失文件断言收到 GitHub
Unicorn 503，原始响应和失败保存在 missing-file-recovery/；未放宽预期404。
随后新增 web/404.html，局部页面、真实返回首页操作及完整本地回归通过。
这只建立本地候选证据，公网缺失路由是否恢复必须以发布后的实际HTTP结果为准。

## 公网恢复与最终核验

入口提交7b9bd79、错误页提交82484b1已发布。新入口的6项浏览器检查、
完整首页11项公网回归、真实缺失PDF的404响应与手机返回首页点击均PASS。
缺失路由响应与新404.html源码SHA完全一致；未放宽原HTTP404断言。
此前GitHub Unicorn 503失败仍保留，服务端具体触发原因不作推断。
见live/verification.json的实际部署提交、源码绑定、命令和所有检查。
本证据提交只更新文档/收据，运行时SKIP，不宣称证据提交本身是部署版本。
