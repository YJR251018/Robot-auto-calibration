# M1 V0.1 明日学习指南

## 1. 工程问题：相机看到的点，机器人该怎样理解

相机测量通常表达在相机自身坐标系中，而机器人执行动作需要基座或工具坐标。相机装在末端后，它随末端一起运动，但相机到末端的刚性安装关系不变。手眼标定的目标就是估计这个固定关系。
今晚实现位姿级仿真、OpenCV 求解和误差统计；当前观测是理想矩阵加可控噪声，不是图像检测得到的测量。没有真实机器人或相机，也没有验证实际精度。

## 2. 四个坐标系与方向

| 符号 | 坐标系 | 角色 |
| --- | --- | --- |
| B | 机器人基座 | 固定参考系 |
| G | 末端/夹持器 | 随机器人运动，本轮等同旧文档 E |
| C | 相机光学系 | 刚性固定在 G 上 |
| T | 标定板 | 在基座中保持固定 |

本项目定义 \(T_{A\_B}\) 将 B 系坐标转换为 A 系坐标。每个点使用列向量：

\[
p_A=R_{A\_B}p_B+t_{A\_B},\qquad
\begin{bmatrix}p_A\\1\end{bmatrix}
=T_{A\_B}\begin{bmatrix}p_B\\1\end{bmatrix}.
\]

内部用米、弧度；仅在输入配置和最终报告边界显式把 °→rad、mm→m，或反向换算。变换方向、相对运动方向与物体物理运动是不同概念，先看下标再乘矩阵。

## 3. 为什么使用齐次矩阵

旋转和平移原本是 \(Rp+t\)，用 4×4 矩阵能统一为矩阵乘法：

\[
T=\begin{bmatrix}R&t\\0&1\end{bmatrix},\quad
R^TR=I,\quad \det R=1,\quad
T^{-1}=\begin{bmatrix}R^T&-R^Tt\\0&1\end{bmatrix}.
\]

逆变换中的平移不是简单的 \(-t\)，因为还要把方向换到另一坐标系。
组合关系 \(T_{A\_C}=T_{A\_B}T_{B\_C}\)，右边先作用，中间坐标系必须匹配。
正交但行列式为 −1 的矩阵是反射，不能当作旋转。

## 4. 固定标定板怎样给出 AX=XB

令 \(G_i=T_{B\_G,i}\)、\(Q_i=T_{C\_T,i}\)、\(X=T_{G\_C}\)、\(Y=T_{B\_T}\)。从标定板沿相机、末端变到基座：

\[
G_iXQ_i=Y=G_jXQ_j.
\]

消去固定 Y：

\[
\underbrace{G_j^{-1}G_i}_{A_{ij}}X
=X\underbrace{Q_jQ_i^{-1}}_{B_{ij}}.
\]

这就是 AX=XB。两个 B 的含义不同：\(B_{ij}\) 是运动矩阵，单独字母 B 是基座坐标系。
同一方向旋转或纯平移会让部分未知量无法辨识。样本多并不自动代表激励充分，必须检查运动的多样性。

## 5. OpenCV 输入输出

`calibration.py` 直接调用本机 `cv2.calibrateHandEye()`：

| OpenCV 参数 | 本项目输入/输出 |
| --- | --- |
| R_gripper2base、t_gripper2base | 每帧 T_B_G 的旋转、平移，G→B |
| R_target2cam、t_target2cam | 每帧 T_C_T 的旋转、平移，T→C |
| R_cam2gripper、t_cam2gripper | 输出估计 T_G_C，C→G |

传入的是绝对位姿数组，不是自行算完的 A/B 相对运动数组。三维平移传给 OpenCV 时整理为 `(3,1)`。
函数签名只接受观测和方法名，不能接收真值。真值只在生成数据和事后计算误差时使用。
本轮比较 PARK 与 TSAI；未自己重写两种求解算法，也未对坏旋转矩阵静默投影修正。

## 6. 各模块职责与最小结构

| 文件 | 责任 |
| --- | --- |
| src/handeye/transforms.py | 原有旋转、齐次变换、组合、点变换；完整保留 |
| src/handeye/metrics.py | 稳定主旋转角、平移距离与单位换算 |
| src/handeye/simulation.py | 场景真值、G 采样、Q 几何生成、观测噪声 |
| src/handeye/calibration.py | 观测校验、运动激励诊断、OpenCV 适配与结果检查 |
| src/handeye/experiments.py | 固定配置、种子、关卡、逐次记录和统计 |
| src/handeye/plotting.py | 只读取实际 summary.csv 出图，使用 Agg 无界面后端 |
| scripts/run_m1.py | 项目内命令行入口，拒绝覆盖结果目录 |
| configs/m1_v0_1.json | 实际默认实验配置和预设验收阈值 |
| tests/test_m1.py | M1 数学、求解、失败机制、重复性和落盘链路测试 |

模块间没有真实机器人接口。`generate_dataset` 产生真值，`calibrate_hand_eye` 不导入或接收真值数据对象，`pose_error` 才做事后比较。

## 7. 仿真数据如何产生

真值 X 的旋转向量为 `[0.2,-0.15,0.3]` rad，平移为 `[0.05,0.02,0.10]` m；板在基座中平移 `[0.6,0,0.3]` m，旋转为 I。
每帧从标准正态向量归一化得到旋转轴，角度在 `[0.25,1.2]` rad 均匀采样；末端位置为 `[0.35,0,0.35]+U[-0.2,0.2]^3` m。不是均匀 SO(3) 采样，也不是实际机器人可达位姿采样。

然后构造：

\[
Q_i=(G_iX)^{-1}Y.
\]

生成后检查 `G_i X Q_i−Y` 最大绝对元素残差 <1e-12；这只是无噪声几何一致性检查，不是空间定位误差。
相对旋转轴奇异值比和堆叠 \((R_A-I)\) 的最小/最大奇异值比用于排除退化，阈值 1e-3 是本实现的数值防线，不是理论上的普遍精度界。

相机观测噪声：

\[
\delta\theta\sim\mathcal N(0,\sigma_r^2I),\quad
R'_{C\_T}=\operatorname{Exp}([\delta\theta]_\times)R_{C\_T},\quad
t'_{C\_T}=t_{C\_T}+\delta t,\quad
\delta t\sim\mathcal N(0,\sigma_t^2I).
\]

左乘表示误差轴表达在 C 系。这里旋转和平移独立注入，不是对整个 SE(3) 矩阵统一左乘一个噪声位姿。σ 是每分量标准差，不是总旋转角或平移范数的标准差。
机器人位姿保持无噪声；不同噪声水平共用相同标准正态样本缩放。样本数实验使用同一 20 帧序列的前 8/12/20 帧，具有配对关系。

## 8. 误差与统计怎么计算

\[
R_\Delta=\hat R_XR_X^T,\quad
e_R=\left\|\log(R_\Delta)^\vee\right\|\in[0,\pi],\quad
e_t=\|\hat t_X-t_X\|_2.
\]

实现使用 SciPy `Rotation.magnitude()`，避免接近零时直接 acos(trace) 的精度损失。
报告 \(e_R\cdot180/\pi\) 度和 \(1000e_t\) 毫米。无噪声门槛预先固定为 `e_R<1e-6 rad` 且 `e_t<1e-6 m`；任一基线不通过则停止后续实验。

每条件、每方法共 30 个种子；均值、样本标准差（ddof=1）、中位数、25/75 分位和最大值见 summary.csv。图上是均值±1个样本标准差，不是均值的置信区间，也不是最小/最大值。
失败次保留行，误差留空，统计只基于成功次，同时报告失败率。观察到所有次都成功，也不能保证其它噪声或场景必然成功。
无噪声和只加平移噪声时的约 1e-14° 旋转误差属于数值舍入层级，不应讨论这种量级的方法排名。

## 9. 明天如何复现

```powershell
Set-Location D:\Research\Robot-auto-calibration
.\.venv\Scripts\python.exe -m pytest -q --basetemp=.venv\M1-test-temp
.\.venv\Scripts\python.exe scripts\run_m1.py --config configs\m1_v0_1.json --output experiments\M1_my_reproduction
```

输出目录必须是项目内未存在的目录；重复运行请选择新名字，程序不会清空旧数据。环境已存在，不需要再次创建或安装。
测试临时文件限定在项目 .venv。若自行运行需指定 MPLCONFIGDIR，可在当前 PowerShell 设置 `$env:MPLCONFIGDIR = "$PWD\.venv\matplotlib-cache"`；CLI 已自动设置默认路径，不改系统配置。

本轮主结果在 `experiments/M1_v0_1/`：

- `config.json`、`environment.json`、`baseline_gate.json`、`run_status.json`：参数、版本与状态。
- `raw/*.npz`：每条件每重复的 G、理想/带噪 Q、真值和种子；不需要重新猜数据。
- `estimates/*.json`：OpenCV 的估计矩阵。
- `trials.csv`：每次求解状态、参数、种子、误差及数据路径。
- `summary.csv/json`：全量计数和统计。
- 三张 PNG、`RESULTS.md`、`artifact_hashes.json`：图、解释和完整性核对。

另一个独立进程的重跑放到 `experiments/M1_v0_1_reproduction/`，它只是复算验证，不能与主实验合并成 60 个独立种子。

## 10. 距真实应用还缺什么

视野、畸变、标定板可见性、像素噪声、PnP 与角点质量、时间同步、机器人位姿噪声和系统偏差均未建模。
没有正逆运动学、关节限制、可达性和碰撞检查；随机姿态可能看不到板，也可能无法由实际设备到达。
实际相机安装后还要核对法兰/TCP、单位、相机光学方向、图像/位姿编号配对、标定板尺寸、相机内参和独立验证真值。今晚的低误差来自几何一致的简化模型，不等于具备实机精度。

## 五道理解题

1. 若 \(T_{B\_G}\) 的平移是 `[0.1,0,0]` 米，它描述哪个原点在谁的坐标系下的位置？为什么不是 G→B 的物理移动距离？
2. 为什么 \(T^{-1}\) 的平移是 \(-R^Tt\)，而不是 \(-t\)？用绕 z 90°、平移 `[1,2,0]` 手算一次。
3. 从 \(G_iXQ_i=G_jXQ_j\) 推导 AX=XB，并解释只颠倒 Q 的乘法次序为什么错误。
4. 将所有机器人旋转改为 I，只改变位置，会影响哪些参数的可辨识性？为什么程序应拒绝这类数据？
5. 噪声图里误差棒缩小是否代表绝对真值误差一定下降？样本量配对实验的 8 帧和 20 帧是否是完全独立数据？

<details><summary>自查要点（先独立作答）</summary>

1. G 系原点在 B 系中的坐标；矩阵表示坐标映射，不是机器人动作指令。
2. 先减去 B 系平移再转入 G 系；例子逆平移为 `[-2,1,0]`。
3. A=inv(G_j)G_i，B=Q_j inv(Q_i)，两边相对运动次序必须一致。
4. 缺少旋转激励，平移方程无法约束手眼平移，部分旋转也欠约束。
5. 误差棒表达分散程度，不能代替均值与真值准确度；8 帧是20帧前缀，属于配对而非独立样本。

</details>
