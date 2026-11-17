# 独立视觉审查 v2

结论：**作为生成服装参考有条件通过；不是商品构造级精确复刻，也不是真实人体多视测量。最终v2拟合复核已完成：仅支持条件诊断，不支持真实人体或严格共享姿势准确性。**

逐张打开原始分辨率front/side/back/closeup/pose/depth，检查领口、袖口、玫瑰、针织孔眼，并对照原图和官网截图；未仅看contact sheet。v1长袖FAIL保留。

## source — CONFIRMED_SOURCE

官网截图中的hero与原图在脸、发型、提衣手势、领口和裤腰细节上视觉一致；来源文件报告0.993相关。页面/摘录确证boatneck、three-quarter sleeves、slim fit、100% cotton及171cm模特穿S。这个身高/尺码不提供胸腰臀真实测量。

对应文件/视图：`reference/asos-page.png`, `reference/original-product.jpg`, `reference/source-verification.json`, `reference/asos-product-excerpt.md`。

## sleeves — PASS_ILLUSTRATIVE

四张彩色图均已变成肘以下、腕以上袖口，明显露出前臂；v1错误长袖已修正。front/back袖口位于前臂中段，side弯臂袖口略靠肘，closeup弯肘露前臂，均属七分袖合理视觉范围。不能由不同弯肘图反推精确衣长或袖纸样。

对应文件/视图：`front`, `side`, `back`, `closeup`。

## neckline — PASS_WITH_DETAIL_WARNING

浅而宽的船领、窄平滑红包边得以保留，v1明显picot/锯齿花边已消失。原图肩头有可见叠片/信封式边缘，v2 front和closeup弱化成普通肩缝；若要求原商品构造级复刻，这两图需重做肩头细节。

对应文件/视图：`front`, `side`, `closeup`。

## rosette — PASS_WITH_DETAIL_WARNING

领口中央小红绿装饰保留；closeup的玫瑰依然较原图更大、更规则、叶片更对称。现在不再压过整体设计，但不能当真实针织附件尺寸依据。优先小幅缩小closeup玫瑰而不是全组六图重生。

对应文件/视图：`front`, `closeup`。

## knit — PARTIAL

红色细针织、纵列纹理与小眼孔已保留。高清closeup显示规则花形/菱形孔眼；原图纵列较细、更低对比、局部更不规则。属于可信的pointelle视觉族类，不足以认证针法、孔距/重复单元和实际色值完全相同。

对应文件/视图：`front`, `side`, `back`, `closeup`。

## pants — INFERRED

红裤、松紧褶皱腰口和中央小红绿装饰保留。原图只展示腰与上腿，官网截图侧栏全身缩略图分辨率有限；直筒裤脚、完整后片和裸脚不是从原图可靠恢复。closeup提衣露腹与原图一致；front/back平放衣摆不能据原图验证实际上衣长度。

对应文件/视图：`front`, `side`, `back`, `closeup`。

## cross-view — PARTIAL

front/pose的脸与发型、躯干、红套装总体连贯；side鼻/下颌为相容的侧面想象，不能确认真实身份。back无脸且发型遮背，缺乏身份核验依据。front/back近似外展双臂；side弯肘前伸、远侧手/腿遮挡；closeup双手提衣，属于另一个姿势。不能把六图作为同一3D姿势的严格多视投影。各图主体高度/领口到衣摆比例略有不同。

对应文件/视图：`front`, `side`, `back`, `closeup`, `pose`, `depth`。

## pose — ILLUSTRATIVE_ONLY

彩色线节点比v1更简洁可读，腕/肘/踝大致落在合理可见位置。但骨盆是腰带处单中央点、肩线为绘制示意，不能当标准姿态检测器输出、真实关节定位或三维骨骼量测。pose照片局部比例也与front有轻微变化。

对应文件/视图：`pose`。

## depth — ILLUSTRATIVE_ONLY

v2去除了多数针织孔眼，形成较平滑灰度体积效果，视觉上比v1更像深度示意。但仍有发丝、面部明暗和表面照明感；无标定/距离单位/相机投影保证，不能作为测得或计算的metric depth。应始终标注生成深度示意，与actual mesh Z-buffer分列。

对应文件/视图：`depth`。

## 具体修正与接受边界

- front,closeup：恢复原图肩头叠片/信封式边缘；保持平滑窄船领。（If construction-level faithful reproduction is required）
- closeup：将领口玫瑰缩小到更接近原图的tiny bud，避免对称放大绿叶。（Minor fidelity refinement）
- side：重生为与front/back相同骨骼姿势的侧投影；明确保留远侧遮挡的不确定性。（If synchronized multiview pose is required）
- pose,depth：只能标注illustrative，真实投影骨架与Z-buffer另行展示。（Required labeling）

不建议仅因微小纹理差异把当前六图全部重生。若目标是可信的示意输入，可以在披露这些偏差后使用；若声称完全复刻原商品或严格同姿势多视，以上肩部/侧面修正必须完成。

## 最终实际拟合复核（已完成）

已检查actual `final-renders/{front,side,back,pose,depth}.png`、三视`fit/*-final-photo-overlay.png`、`shape-fit/side-before-after.png`、`view-specific/{side,back}/before-after.png`与`original-reference/before-after.png`。图中现在确为v2七分袖；此前过渡阶段的PENDING不再适用。v1长袖FAIL与其历史审查原样保留。

选中尺寸为170/90/69/96/37cm，thigh50；waist由72降为69、thigh由54降为50，其余M先验保留。它是冻结相机、生成衣物包络下的条件估计，不是官网171cm/S模特的测量。独立比较`original-reference/state.json`、`shape-source-state.json`、`selected-neutral-state.json`及两个view-specific state，asset/version/dimensions/morphWeights与final-state全部一致；state/OBJ/camera、生成引用图和所有final-render文件hash与render-provenance吻合。

`shape-fit/optimization.json`记录训练front/side包络外像素936→797、3578→2850，整体loss .02397→.01398；侧面图可见腹腰/大腿略收窄。但全clothed IoU在三个视图均下降：

| 视图 | fixed M | 条件shape |
|---|---:|---:|
| front | .81420 | .80564 |
| side | .68676 | .68376 |
| back | .74962 | .74437 |

因此“人体更能包含在衣物里”与“轮廓全面更吻合”不是同一结论；这里前者有训练证据，后者失败。侧面头脸前突、臀/腿和手脚残差仍明显。实际裸人体Z-buffer和骨骼投影与生成illustrative pose/depth应分列。

共享pose严格多视一致性：**FAIL**。front四个腕踝误差3.46/.18/3.09/2.89px、side两点5.40/3.45px；back双腕仍23.15/30.76px，双踝3.36/9.99px。`fit/back-final-photo-overlay.png`中cyan腕与magenta点肉眼分离，不能说十点全部小误差。back全包络IoU .74437也不意味着腕姿势已正确。

同一body/camera的分view pose诊断：**被优化腕点改善有证据；不能当heldout准确性。** `view-specific/back/before-after.png`右图双腕对上，误差降为.224/.081px；side腕降为.182px。back IoU .74437→.79957、side .68376→.68493。它们直接使用各自view的人工手腕标签优化，已不属于heldout；肩臂外沿、手指与脚轮廓残差仍在，side头/胸腹残差也没消失。

原图手部专项最终结论：**POSE_FAIL / UNRESOLVED / DEPTH_AMBIGUOUS；无accepted matched candidate。** 已直接与geometry多轮检查真实正面和侧面mesh，保留全部失败历史。原图当前顶层是`iteration-5-forward-IK`的最新失败诊断镜像，不是选定恢复成功样本。主final人体与生成视图验证不变。

第2轮（`iteration-2/`）：头yaw/roll改善，腕.388/.463px、肘.425/.612px，crop IoU .74135；但实际一手竖腕扭折、另一手/前臂藏入躯干，失败。

第3轮（`iteration-3-depth-dominant/`）：手横向会合改善，但掌指穿叠，侧面上臂抬胸、肘前突如抱球，肘移位约57/142px，失败。第4轮（`iteration-4-elbow-dominant/`）：肘移位降至27.5/45.6px，但手再次入腹/腕补偿，失败。

第5轮forward-IK：正面手腕/掌连续且双手横向看似更自然，肘1.78/4.77px、腕1.26/3.92px；眼6.31/13.75px、鼻12.79px，肩仍26.60/24.98px，neck roll22度上界保留，crop IoU .73973。`renders/side.png`却显示双臂向前悬伸，手离腹前表面最小21.16/25.30cm，根本没有原图在腹前近身捏衣摆的动作。手表面100%在躯干前不是自然动作或接触通过。侧面inspection camera只做居中以免伸远双手被裁，原crop camera和2D评分未改。

重新核查最新state的asset/version/dimensions/morphWeights与主final一致，原crop camera与iteration-1逐字节一致；`geometry-check.json`仅数值导出PASS且明确pose_verdict=POSE_FAIL。不能拿数值导出或2D低误差覆写姿态失败。JSON新增`reviewed_model_artifact_sha256`绑定最新state/metrics/正侧图/OBJ/GLB/状态/深度证据；字节变化须重审。

停止边界：在这个固定body、实际bone-head臂长、近似正交相机和人工隐藏肩肘点假设下，靠后的深度解让手藏入腹，前解让手远离腹部，多轮折中也未产生可信近身提衣动作。它是未解决的条件性诊断，不是普遍IK不可能，也不是声称真人无法做该动作。单图衣物下的肩肘人工标点非解剖真值；可见手掌/指/衣摆形态与三维动作合理性优先于subpixel点分数。原图人体shape准确、真实三维手姿、握衣接触与物理fit均不能宣称通过。

## 逐项证据判定与评估边界

按`tools/skill_evals/upstream/agents/grader.md`核对输出内容而非仅有文件：JSON的`expectations`逐项列出PASS/FAIL及证据。四项服装基本特征通过、资源版本一致性通过、分view被优化腕点与原图第二轮被优化头/肘/腕点改善通过；“条件shape提高全部IoU”“共享pose严格匹配三视”“原图证明人体准确恢复”均FAIL。不得把不同范围的断言合并成一个误导性的总体成功率。

可用范围：展示单商品图→六张生成参考→真实可调人体/骨骼/导出资源及OpenCV匹配的可审计工作流；展示共享pose失败和同body分view调节效果；作为披露prior/estimate后的人工调整起点。两轮是同case修正历史，不是skill因果benchmark。

不能宣称：精确复刻全部针织/肩部/不可见结构；真实同步多视或严格共享姿势；恢复官网模特实测尺寸；生成pose/depth为真值；包含性或分view腕点改善等于heldout/真实人体准确；原图拟合PASS；布料、松量、碰撞支撑或物理穿着验证。

## 限制

- 生成图不是实拍多视角；保留同一人物外观不等于验证身份。
- 100% cotton为官网文案，不能由图像验证材料。
- 171cm/S不等于恢复胸腰臀或授权精确人体测量声明。
- 没有物理服装拟合、接触、布料模拟或真实人体误差验证。

JSON保存此次图像与来源文件hash。后续替换不能自动继承本审查。
