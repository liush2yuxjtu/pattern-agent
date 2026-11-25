# Design Cloth 功能复测

## 试穿与复验报告

评测直接读取交付文件。Markdown 和 HTML 都须以唯一、可见的「分诊与下一步复测」章节收尾，正文包括具体待办或有依据的结案。评测会拒绝附录在后、标题藏在引用或隐藏块内、只有占位符或链接等情形。用例 39、40 再核查固定编号、修复与补证顺序、复测门槛、放行依赖，以及已结案的验收范围。

在技能目录使用 Python 3.10+，在当前 Python 环境安装 `markdown-it-py==4.0.0`。报告导出测试另需 Node 和 `sharp`，可以把 `DESIGN_CLOTH_SHARP` 指向已有的 `node_modules/sharp`。配对实跑需要已登录的 Codex CLI，`--baseline` 指向含 `SKILL.md` 和 `references/` 的旧版技能目录。

```sh
python3 evals/check-report-follow-up.py /path/to/review.md /path/to/review.html
python3 evals/test-report-follow-up.py -v
python3 evals/run-report-evals.py /path/to/new-eval-run --baseline /path/to/old-skill
```

脚本逐文件返回通过或失败，配对运行保存原始报告、逐项评分和模型事件。用例的读数来自文字夹具。脚本核对尾节结构和用例指定要素，交付前另核对每项证据、实际执行人、通过条件与真实验收状态。HTML 可见性检查覆盖常见隐藏标记、内联隐藏样式和折叠内容。预览时再确认实际样式及图片加载。

## 用户交接

使用已登录的 Codex CLI，在技能目录运行。输出目录由脚本新建。

```sh
python3 evals/run-handoff-evals.py /path/to/handoff-run --baseline /path/to/previous-skill
```

用 `--ids 20 21` 运行指定用例。每题启动临时会话。需要选择的用例检查原生 `item/tool/requestUserInput` 或带 `delivery: async` 和问题字段的桌面消息，使用预设答复继续会话。无需询问的用例核对事件为零。纯文字用例模拟无法显示结构化问题的客户端，并同时检查没有问题事件及答复中确有具体提问。每题保留协议事件与逐项判定。

### Boat 候选版分诊与跟进

运行 `python3 evals/run-handoff-evals.py /path/to/boat-followup --baseline /path/to/previous-skill --ids 37 38`。两题源自已交付报告但没有执行后续的 V03 案例。评测器在临时 app-server 会话注入隔离的 Boat 工具，返回预设读数。用例 37 核对先做袖口与腋下单变量对比，再发一次原生尺码提问，收到答复后沿用对比副本核对人台。用例 38 核对半拉链保持打开并实际调用胸围松量对比，本轮局部诊断无需询问正式用料和尺码。两题检查参数与事件顺序，模拟读数只作为夹具，原服装工程和 Boat VM 不参与运行。

## 验收失败后的诊断与修复

`evals.json` 中的 26–32 是无工具功能用例。按同一题面与模型分别运行旧版和候选版，载入每题 `references` 指定的技能参考，按 `assertions` 逐条评分。用例检查排查顺序、藏在面布里的里布摆位、优先使用求解实例、原生压力截图的范围、人台量体来源、复测验收，以及有证据支持时的纸样修正。

用例中的读数和工程状态是题设。比较的是判断和先执行哪一步，模型给出的动作与结论都须有题面依据。

## 从零起版的实调评测与基准

用例 33、34 分别要求从简报生成微 A 字松紧裙和围裙，再单独改裙长或前胸宽。四个独立 Codex 进程使用同一模型、同一材料和工具版本。新版与旧版各做两题。没有可供复制的母版，初版及修订版各交参数源、毫米 DXF、整幅和 A4 拼接文件。工具轨迹保留命令、退出状态、时长和用量。

准备 Node 和含 `@freesewing/core@4.10.2` 的依赖目录，以及装有 `ezdxf==1.4.3`、`PyMuPDF==1.26.5`、`reportlab==4.4.4`、`shapely==2.1.2` 的隔离 Python。先保留旧版技能快照，再从技能根目录运行。使用新评测目录。

```sh
"$EVAL_PYTHON" evals/run-zero-draft.py /path/to/iteration-1 \
  --baseline /path/to/skill-snapshot --node-modules /path/to/node_modules \
  --python "$EVAL_PYTHON"
"$EVAL_PYTHON" evals/grade-zero-draft.py /path/to/iteration-1
"$EVAL_PYTHON" evals/check-zero-draft-controls.py /path/to/iteration-1
```

评分从文件量净尺寸、轮廓、配缝、缝份、修订差值、整幅比例、分幅页码及行列覆盖。每个运行从空目录重建三次，比较几何量测和打印结构，并单列重建时长。缺页、单位错置、打印缩到九成六分别作负对照，在隔离目录通过重建恢复，再重跑同一读取检查。检查的范围是数字文件。没有实体打印、原生 CAD 回导、试穿和真人合身证据时，继续保留对应的未验状态。

### 最终验收关口

```sh
"$EVAL_PYTHON" evals/test-zero-draft-gates.py -v
"$EVAL_PYTHON" evals/run-zero-draft-gates.py /path/to/iteration-1 /path/to/gates.json
```

最后一条命令重新执行真实工具和独立读取。每份候选至少五个不同的数字关口通过，实际纳入的关口必须全部通过。对首轮归档的四种导出规范，可附 `--audit-recorded-exports` 加跑第八关，用原生裁切框将每页净线、裁剪线及对位标记拼回去，与 DXF 比对。新导出规范需用对应版式审计。

随后等待真人亲自审版并完成同版足尺试印。人工回执可通过 `--approvals /path/to/decision.json` 输入。字典以 `33/with_skill` 之类的用例及配置键索引，包含报告中当前 `subject.fingerprint`、`reviewer`、`review_date`（年-月-日）和 `decision`（`approve` 或 `reject`）。批准还须提供 `actual_size_printed`、`scale_x_mm`、`scale_y_mm`、`design_matches_brief`、`cut_markings_readable` 和 `all_tile_joins_aligned`。两边试印量测各允许一毫米偏差。将真人实际给出的量测与明确决定原样记录，评测器和智能体不可代签。版次摘要覆盖修订输入、DXF、整幅及分幅打印文件。

新版全部用例放行退出零；数字失败、退回或回执无效退出一；数字通过但待人工签核退出二。程序控制用的合成记录只用于判定回归测试，不能提交到真实验收。

## 时装设计师与版师的 Markdown 报告

历史试穿原图使用单独的取证目录。这些文件由用例方提供。设置环境变量指向包含 `appearance`、`boat-style3d-v02` 和 `s07-report` 的目录。

```sh
python3 -m pip install markdown-it-py Pillow
export DESIGN_CLOTH_REPORT_FIXTURES=/path/to/private/fixtures
python3 evals/run-report-eval.py /path/to/run-19 --case 19 --without-skill
python3 evals/run-report-eval.py /path/to/run-35 --case 35 --without-skill
python3 evals/run-report-eval.py /path/to/run-43 --case 43 --without-skill
python3 evals/grade-report-readability.py /path/to/run-43/current --case 43
```

用例 19 核对牛仔裤外观、裤脚覆盖、磨白和前袋。保留五张原图。用例 35 核对针织短袖侧举脱袖、右肩意外露肤和左露肩设计。按题面保留二十七张原图。用例 43 核对 S 码长袖放臂后的回位。保留三张原图。三个用例复用存档证据。原生仿真执行未纳入此评测。

运行器保存原始报告和交付答复。发布器内嵌证据图。评分器检查首段定稿意见、服装决策、仿真职责、折叠内容、开发者工件和交付。结果写入 `grading.json`。有技能组须通过全部关口。无技能组使用相同题面和证据，作为对照。

在评测页逐份展示报告。打开折叠区。检查实际图片加载。Markdown 解析与浏览器渲染分别验证。
