模型阶段已实际执行，未自行判定PASS。

从case旧失败初始化开始，冻结wrapper运行配准、三阶段躯干/相机拟合、真实手部拟合和neutral.obj独立复量。命令、输入/源码SHA和各阶段真实returncode见TRACE.json及model-fit/execution.json。已实际查看原图与最终photo/front/side/back/closeup。

配准156/188内点，均值1.279px、P95 2.694px。8示意markers保持语义/visibility，全部use_for_fit:false，不能当关节检测。模型12尺寸由neutral.obj复量；这些数值不是照片真人实测。

摆姿为同一真实解剖模型，正侧背仅相机不同；腿脚/后背为先验。骨骼蒙皮不是布料/组织物理仿真。独立验收与编辑器实测尚待其他执行者；六张原生ImageGen尚未调用。
