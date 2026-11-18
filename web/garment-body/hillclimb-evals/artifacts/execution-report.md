本轮冻结技能已真实运行至六张独立ImageGen。

模型从case旧失败初始化开始，经包装器配准、三阶段体形/姿态/相机优化、手部拟合、实际中性网格复量。TRACE.json与model-fit/execution.json记录命令、输入与源码SHA及实际阶段日志。独立模型门槛由hc_protocol_grader检查后，root明确授权六图生成。

images/包含exactly six主PNG：front、side、back、closeup、pose、depth，各自一次独立真实image_gen.imagegen，原生1024×1536、2:3，无裁切、拼图或放大；原生路径未删除。generation-manifest.json和逐图receipt保存完整prompt/工具返回路径/实际引用图SHA/像素/输出SHA。每图使用本轮final对应真实guide与原商品图；pose/depth另以本轮front保持画幅。

12项主要尺寸在model-fit/measurements.model.json与CSV，来源为neutral.obj真实顶点，不是目标或缓存。可调状态为model-fit/final/final-state.json；neutral/posed与每相机/真实骨架/rawZbuffer全部保存。编辑器新状态导入与交互验证由独立执行者写editor-probe，未被此执行覆盖。

限制：原图单视图且腿脚裁切，背面/腿脚为先验；模型测量不是真人测量；ImageGen姿态/深度是illustrative，不能用于厘米或检测真值；骨骼蒙皮不是物理布料试衣。商品观察与推断见product-audit.json及generation-observation.json。六图几何与页面最终独立评分尚待完成，不预填全PASS。

迭代记录：初批front/side经独立grader实际核验失败，全部保留未改。attempt2重新实际生成front/side，front2通过可见锚点/方向/包络后，root明确授权基于其不可变原图生成pose2/depth2；side2因可见袖肘弯86px误差被拒。attempt3side以同state同camera语义着色armguide+灰side+原商品图实际重新生成，待独立评分。共11次真实原生ImageGen调用。最终选择请读取generation-selection.json，逐图永久真实路径/工具引用见generation-receipts.json，不能用旧canonical路径冒充新图。

新增同camera比较：case原始失败state实际Runtime重建initial posed OBJ，与本轮final saved OBJ在固定final photo camera原生1000×1276重投影。OpenCV initial IoU0.755633/P95109px，final IoU0.846981/P9575px；不是历史neutral初始化指标。comparison保留实际网格/camera/输入hash/metrics与12%薄叠加。整体轮廓差异含头发和衣物，不能当真人尺寸准确度。

更新：side3已由独立grader报告通过observable锚点/臂方向/包络；back1由独立grader报告8可见锚点通过。原closeup1经独立grader发现相机/腕/眼漂移被拒，root授权真实生成closeup2（本轮actualcloseupguide+原商品，无front链），保存images/attempt-2/closeup.png及actualreceipt。累计12次真实原生ImageGen，最终closeup2待独立验收；其它已通过选择保持未改。

最新：closeup2独立P95.02513H超过冻结.02H，被拒绝；closeup3使用实际新semantic-guide+灰guide+原商品实际调用ImageGen，但output阶段moderation_blocked sexual（request76529cb7-6a9b-414d-b85b-23e1ef9f0d27），未生成任何图。失败receipt和全部prompt/refs已保存。累计13次实际调用、12个原生输出；当前closeup尚未通过，不能宣称六图全部验收通过。

配准语义复审更正：原图再次实际view，image-left blue marker映回raw约(184,773)位于更远端手背，不能称可靠腕关节；可见腕/袖口皮肤过渡约(145,760)。执行后审查保存为hand-back/cuff-proxy/uncertain，未改冻结case/markers且use_for_fit:false不变。约44px错node偏差不能称模型腕关节残差；实际模型wrist-skinband为另一个表面比较。

最终候选更新：16次真实ImageGen调用，共15个原生输出、1次工具output-moderation拒绝。closeup4安全着装输入版经独立几何通过但下摆动作失败，closeup5局部衣摆修复仍有垂落长片，均保留。closeup6只用acceptedfront2经固定相机转换的着装参考+原着装商品+真实二值closeup轮廓，新独立native1024×1536输出，目视原提衣下摆恢复，等待最终独立验收。输入camera参考是明确标注的OpenCV分析图，不是最终生成；其源SHA/固定2.5 affine矩阵已单独保留。后续没有再次提交被拒的anatomical近景图片。

当前selected真实路径：front2、side3、back1、closeup6、pose2、depth2；generation-selection.json记录全部attempt状态/真实失败原因，generation-receipts.json每selected图片有完整实际tool/refs/原生path/SHA/像素。所有早期原图和reference路径保持不可变。模型真人尺寸/隐藏3D/物理试衣仍未验证。

最终冻结：closeup6已收到独立geometry/knowncamera8visibleanchors/heldlowerhem action通过消息，详见STATUS.md。selected6均独立preflight通过，正式13语义评分外置同级../grading.json。本执行者全部产物现冻结，不自填allPASS。
