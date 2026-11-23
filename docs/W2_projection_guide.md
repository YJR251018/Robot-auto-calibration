# W2 学习指南：板上的点怎样落到画面里

W2 已实现零畸变针孔投影和可见性判定。它把板上63个已知三维点变成合成像素坐标；没有渲染照片或检测真实角点。

## 1. 公式与单位

板点先用 Q=T_C_T 变到相机系：p_C=R_C_T p_T+t_C_T。相机系 x 向右、y 向下、z 向前。只有 Z_C>1e-6m 才投影：

```text
u = fx * X_C / Z_C + cx
v = fy * Y_C / Z_C + cy
```

三维坐标用米；焦距fx/fy和主点cx/cy用pixel。默认1280×960图像、fx=fy=900、cx=640、cy=480、零畸变。这些是实验设定，不是设备测量值。例如相机点(0.1,0.2,1)m投到(730,660)pixel。

板点以中心为原点，x为-0.10…0.10m、y为-0.075…0.075m，步长0.025m，共9×7点。检查整个网格也包含其矩形四角；该矩形不代表未知实物边框。

## 2. 什么叫可见

按顺序返回一个首要原因：

1. `depth`：任一点深度≤1e-6m，不做除法。
2. `outside_image`：点超出像素中心范围[0,1279]×[0,959]。
3. `margin`：点虽在画面内，却进入默认16pixel边缘余量。
4. `visible`：所有规定点通过上述检查。

边界包含端点；例如余量内有效区域为[16,1263]×[16,943]。函数不会静默把负深度点投到图像中。模型不检查遮挡、正反面纹理、模糊、检测置信度、机器人可达性和碰撞。

## 3. 测量端与规划端有什么不同

`measure_visibility(Q, camera)` 在仿真测量端用真实观测Q判定当前几何。`predict_visibility(G, X_hat, Y_hat, camera)` 在规划端只用候选机器人位姿和已有估计，按 Q_hat=inverse(G X_hat)Y_hat 预测；接口不接收真实Q或真值对象。

X_hat由共同训练G/Q实际调用OpenCV求得，Y_hat由训练中的G X_hat Q估计。旋转使用训练闭环旋转矩阵均值的极分解，平移取算术均值；病态或不唯一的旋转均值拒绝。没有将固定板真值直接传给预测器。

正式验收用每个种子的前20个可见候选训练，剩余100个候选评价预测。这个训练集合由仿真测量端筛选，是几何验证协议，不能称为未知可见性下的自主采样实验。

## 4. 实际结果和解释边界

30个固定种子各120候选：1941可见，1542画面外，117进入边缘余量；每种子最少55个可见。60次PARK/TSAI无噪声恢复全部通过，3000个剩余候选预测无错判。全部候选保存，不以重抽种子筛出成功场景。

零错判发生在理想训练观测下，X_hat/Y_hat几乎等于真实关系。它主要验证坐标方向、预测接口与边界实现，不能证明有像素噪声或较大初值偏差时仍准确。

官方投影说明见 [OpenCV文档](https://docs.opencv.org/4.13.0/d9/d0c/group__calib3d.html)。网页4.13.0与本机cv2 5.1.0版本不同，本轮同时保存了本机projectPoints文档，并实际对照数值；最大差约4.55e-13pixel。

## 5. 使用和文件入口

| 文件 | 用途 |
| --- | --- |
| src/handeye/camera.py | 相机参数、板点、投影、测量/预测可见性、训练估计固定板位姿 |
| src/handeye/projection_experiment.py | 固定种子候选生成、训练恢复、预测评价、逐种子落盘和示意图 |
| src/handeye/projection_verification.py | 哈希、再生成、原始数据重放、CSV/计数/统计复算 |
| scripts/run_projection.py、verify_projection.py | 真实命令行入口 |
| configs/w2_projection_v0_1.json | 正式30种子配置；候选分布写于预设协议及生成器 |
| experiments/W2_projection_20261123/ | 已完成的正式数据、图、结果和哈希 |

PowerShell项目根目录：

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PYTHONIOENCODING='utf8'
$env:MPLCONFIGDIR="$PWD\.venv\matplotlib-cache"
.\.venv\Scripts\python.exe scripts\run_projection.py --config configs\w2_projection_v0_1.json --output experiments\W2_my_run
.\.venv\Scripts\python.exe scripts\verify_projection.py --run experiments\W2_my_run --report reports\W2_my_verification.json
```

目录和报告须为新名字。实验失败会保存原始候选、当前seed、阶段与traceback；保留失败目录并换新目录重跑，不清空旧数据。完整测试命令与最终日志见验收报告。

## 6. 理解题

1. **米改成毫米后，能否只改板点？** 不能，所有相关平移和点坐标须统一；否则投影与闭环都会错误。
2. **点投到画面内就代表真实检测成功吗？** 只代表这个几何模型通过；遮挡、纹理、畸变和检测质量尚未建模。
3. **为什么规划端不能读取实际Q？** 它对应尚未采集的观测；提前读取会使选位策略获得未来信息。
4. **为什么零错判不能直接推广到实机？** 训练没有像素噪声或系统误差，估计几乎精确；真实环境需要W3和后续不确定性实验。
5. **怎样验证T_C_T没有用反？** 用手算点对照投影，检查G X Q=Y，并验证OpenCV无噪声恢复；单看矩阵是否正交不足以识别方向。
