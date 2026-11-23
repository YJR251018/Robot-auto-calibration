# 项目数学与数据规范

版本 M2-0.1；整理日期 2026-11-23。本文整理 AGENTS、eye_in_hand_frames、learning_guide 及用户 M1/M2 任务书中已经明确的约定，不改变既有数学实现。

## 坐标与单位

T_A_B 将 B 系坐标变到 A 系：p_A=R_A_B p_B+t_A_B。右手系、列向量；点数组按行存储不改变数学方向。内部米和弧度，报告边界显式换为 mm、°。G 与早期 E 均指末端，C 为相机光学系（x右、y下、z前），B 为基座，T 为固定板。

```text
G_i=T_B_G,i; X=T_G_C; Q_i=T_C_T,i; Y=T_B_T
G_i X Q_i=Y; Q_i=inverse(G_i X) Y
A_ij=inverse(G_j) G_i; B_ij=Q_j inverse(Q_i)
A_ij X=X B_ij
```

OpenCV calibrateHandEye 的 gripper2base 对应 G、target2cam 对应 Q，cam2gripper 输出 X；传入绝对位姿，不是相对运动。真实 X/Y 只出现在生成和事后评价；选择器与求解器不得接收真值容器。原无噪声门槛 e_R<1e-6 rad、e_t<1e-6 m；理想闭环最大元素残差<1e-12。

通用 motion_diagnostics 对输入序列计算 inverse(P_j)P_i；将 Q 输入它不等于直接使用 AX=XB 中的 B_ij。未经证明不得假定两侧全部数值诊断完全相同，现有双检查和阈值保持。

## M2 数据与实验单位

- 每次独立重复有候选池与独立种子的留出集；共用同一场景 X/Y，默认留出为理想观测。
- candidate_ids 是候选数组行的唯一整数标签；initial_ids 为共同初始标签，计入 N；selection.ids 为完整有序采样序列，各 N 取其前缀。
- 同一候选 ID 在所有策略下使用相同观测和噪声；先生成全候选标准正态表，再按 ID 索引。留出数据不得用于选择或调参。
- 候选/留出/相机噪声/选择随机流各自固定并记录。正式默认种子分别 310000+i、320000+i、330000+i、340000+i，i=0…29；开发使用分离的 410000 系列。
- 一个重复编号是统计单位；共享估计的帧、板点、帧对和 N 前缀不算独立重复。重放也不增加样本数。
- 三策略仅比较计划姿态的选择；不包含视野、可达性、碰撞或运动时间保证。rotation_farthest 是启发式，不是信息最优算法。

## 噪声与评价

相机 R'=Exp(δθ)R、t'=t+δt，噪声表达在 C 系，旋转和平移独立，每分量标准差为 sigma；不是对整个 SE(3) 左乘同一误差变换。机器人噪声扩展在真实 G 生成 Q 之后独立施加到测量 G，噪声表达在 B 系，不用带噪 G 重生成 Q。

手眼误差使用 R_hat R_true^T 的主角度和 ||t_hat-t_true||。独立留出点误差比较 G_h X_hat Q_h p_T 与 Y p_T，对全部帧/点平方距离平均后开方。闭环旋转和平移残差分别报告，不能混合单位相加。

## M2 输出协议

每个运行使用新目录：config/environment/code_hashes/trial_plan/run_status JSON；raw/repeat_*.npz 保存候选、理想 Q、标准噪声、理想留出、点、真值；selections.json 保存选择顺序和分数；estimates/ 保存估计与逐帧评价；trials.csv 保存逐次结果；summary/paired JSON 与 CSV、PNG/PDF 及哈希清单供核验。

CSV 的 trial_id 唯一且对应冻结计划；repeat 是独立重复编号；condition 是噪声条件；strategy/method/N 指明比较组；*_seed 为随机种子；rotation_sigma_deg、translation_sigma_mm 是相机分量 sigma；robot_* 为独立机器人 sigma；error_deg、error_mm、point_*_mm、closure_* 指标注明物理单位；closure_max_abs 是本次所选理想 G/Q 的矩阵元素最大残差，仅用于生成核查。selection_seconds 和 solve_seconds 是本机运行时间，不是机器人采集耗时。

成功 status=ok，预期数据/求解拒收 status=error 且数值误差留空；意外程序异常保存当前行、traceback，运行 failed 并停止。完整运行可包含预期失败，但必须同时报告失败数。无噪声任一失败停止后续比较。中断只保留 partial/running 证据，不冒充完整；续跑需配置/代码指纹和 trial 唯一性核验，否则建立新运行。

统计报告成功条件下分布及总数/失败率。配对比较披露共同成功的重复数；bootstrap 按重复编号重采样，不按点重采样。既有 M1 产物和数据格式不追溯更改。

## W2 零畸变投影补充（2026-11-23）

相机点由T_C_T得到，u=fx X/Z+cx、v=fy Y/Z+cy。长度米，像素坐标pixel；默认图像1280×960、fx=fy=900、cx=640、cy=480。板9×7点、间距0.025m、中心原点，边界覆盖x±0.10m/y±0.075m。当前零畸变，无厚度双面几何模型，无真实图像检测。

可见性先检查所有规定点Z>1e-6m，再检查像素中心画面[0,width-1]×[0,height-1]及16pixel余量；端点包含。首要拒收原因依次为depth、outside_image、margin。不得将非法深度直接除法投影。

测量端使用实际Q；预测端仅使用候选G、训练得到的X_hat/Y_hat，计算Q_hat=inverse(G X_hat)Y_hat。Y_hat取训练闭环旋转的极分解均值及平移均值；病态/不唯一旋转均值拒绝。训练筛可见协议属于几何验收，不能当作有限预算自主采样收益证据。
