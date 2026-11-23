# M1 手眼标定基础仿真系统 V0.1 开发验收报告

日期：2026-11-18（Asia/Shanghai）。项目：`D:\Research\Robot-auto-calibration`。
任务来源：用户要求读取并继续 `CONTINUE WORK.md`。执行计划在 `reports/M1_execution_plan.md`，无噪声阈值在正式实验前固定。

## 1. 实际完成情况

| 阶段 | 实际交付 | 状态 |
| --- | --- | --- |
| A 数学 | 保留原旋转/刚体/点变换，新增稳定旋转误差、平移误差和报告单位转换 | 完成 |
| B 仿真 | 固定板、固定手眼真值、20帧多轴运动、Q=inv(GX)Y、闭环核验、种子与观测落盘 | 完成 |
| C 求解 | 真实调用本机 OpenCV PARK、TSAI；方向映射和非法结果验证 | 完成 |
| D 实验 | 无噪声关卡、独立旋转/平移噪声、8/12/20帧、每条件30个配对种子 | 完成 |
| E 可视化 | 实际 CSV 生成3张英文 PNG；逐次/汇总表、配置、结果说明 | 完成 |
| F 测试 | 既有回归与新增数学、真值恢复、非法输入、失败保留、关卡停止、复现和落盘测试 | 124项通过 |
| G 学习材料 | docs/learning_guide.md：工程背景、LaTeX公式、模块说明、复现和5道题 | 完成 |
| H 验收/审查 | 本报告及 reviews/review_request.md | 完成；独立审查待Claude执行 |

没有重复文献调研、硬件或 GUI 工作。没有使用子代理、付费 API、系统安装、额外权限或远程仓库操作。

## 2. 现有内容与保留措施

开始前已检查 README、AGENTS、现有源码/测试和仿真方案；`docs/PROJECT_SPEC.md` 不存在。项目已初始化，因此复用 .venv、requirements 和已有模块，不重建环境。
新任务采用末端符号 G；旧文档 E 与本轮 G 指同一末端参考系，已在新文档明确映射，没有反转变换方向。

在 `reports/M1_baseline/` 保存本轮49个已有文件的 SHA-256，并备份 README、AGENTS 和包入口。原有源码、测试、依赖、文献和申报书保留；README/AGENTS 仅追加当前 M1 入口。最终保留核对见 `reports/M1_preservation.json`。
DeepSeek 的 `research_output/literature_report.md` 未编辑；旧 `reports/tonight_report.md` 及此前日志不改写。Git 原有旧代码删除状态不恢复、不清理、不提交。

## 3. 文件清单

新增源码：

- `src/handeye/metrics.py`：误差定义、近零/近π角误差、度/毫米报告属性。
- `src/handeye/simulation.py`：场景、理想观测、噪声、闭环检查。
- `src/handeye/calibration.py`：观测验证、退化诊断和 OpenCV 适配器。
- `src/handeye/experiments.py`：配置、关卡、失败保留、配对实验、CSV统计。
- `src/handeye/plotting.py`：Agg 后端从真实汇总 CSV 出图。
- `scripts/run_m1.py`：项目内新目录执行入口；`scripts/verify_m1.py`：两次运行完整性、数据与重放核验。
- `configs/m1_v0_1.json`：完整默认实验配置；`tests/test_m1.py`：新增49项用例，原有75项完整保留。

新增材料与记录：

- `docs/learning_guide.md`、本报告、`reviews/review_request.md`。
- `reports/M1_execution_plan.md`、`M1_p0_probe.json`、`M1_tests.txt`、`M1_pytest.xml`。
- `reports/M1_experiment_run.txt`、`M1_reproduction_run.txt`、`M1_reproducibility.json`、`M1_reproducibility_log.txt`。
- `reports/M1_source_hashes.json`、`M1_preservation.json`、`M1_final_checks.json`、`M1_file_inventory.json`。
- `experiments/M1_v0_1/` 为主结果；`experiments/M1_v0_1_reproduction/` 为同配置独立进程复算。

README、AGENTS 追加内容；没有修改原有公共函数或覆盖其他 Agent 成果。文件清单的最终哈希以 M1_file_inventory.json 为准，其自身不做自引用哈希。

## 4. 环境与实际命令

| 环境 | 实测 |
| --- | --- |
| Python | 3.12.0，项目 .venv\Scripts\python.exe |
| Git | 2.54.0.windows.1 |
| NumPy / SciPy | 2.5.5 / 1.18.1 |
| opencv-python | 包5.1.0.95，cv2版本5.1.0 |
| Matplotlib / pytest | 3.11.2 / 9.2.0 |

主要命令（均在项目根目录）：

```powershell
Get-Content -LiteralPath 'CONTINUE WORK.md'
Get-Content README.md,AGENTS.md
git -c core.quotepath=false status --short
.\.venv\Scripts\python.exe -W error -m pytest -q --basetemp=.venv\M1-test-temp --junitxml=reports\M1_pytest.xml
.\.venv\Scripts\python.exe scripts\run_m1.py --config configs\m1_v0_1.json --output experiments\M1_v0_1
.\.venv\Scripts\python.exe scripts\run_m1.py --config configs\m1_v0_1.json --output experiments\M1_v0_1_reproduction
.\.venv\Scripts\python.exe scripts\verify_m1.py --first experiments\M1_v0_1 --second experiments\M1_v0_1_reproduction --report reports\M1_reproducibility.json
```

还通过项目 Python 执行20帧 P0 探针、哈希基线核验、CSV统计核对、版本和本机 OpenCV docstring 检查，使用 view_image 查看3张实际 PNG。最终依赖、旧示例、文档链接和 Git 空白检查另记 M1_final_checks.json。
测试的临时文件及 Matplotlib 缓存限定在 .venv；命令的 UTF-8 / PYTHONPATH / MPLCONFIGDIR 只影响当前进程，不修改系统设置。

## 5. 几何与求解正确性

定义 G_i=T_B_G,i、X=T_G_C、Q_i=T_C_T,i、Y=T_B_T，生成关系严格为 Q_i=inv(G_i X)Y。
默认真实 X 的旋转向量 `[0.2,-0.15,0.3]` rad、平移 `[0.05,0.02,0.10]` m；Y 的 R=I、t=`[0.6,0,0.3]` m。20帧末端姿态按明确分布和种子生成，并检查运动激励，数据不是独立乱造的两组位姿。

求解器输入仅为 T_B_G、T_C_T 和方法名。测试用伪造 OpenCV 输出确认适配器确实返回 OpenCV 结果而不是替换成真值；实际测试还使用多个手眼真值，避免固定答案通过。真值仅用于生成及事后误差评价。

预设门槛：旋转误差 <1e-6 rad、平移误差 <1e-6 m，且理想几何闭环残差 <1e-12。60次无噪声基线（30种子×2方法）全部通过；最大旋转误差约 **9.93e-14°**，最大平移误差约 **2.96e-13 mm**，属于数值舍入层级。未因结果调整阈值。

## 6. 实验规模与实际结果

主运行：**840条求解记录、0条失败**，保存420份原始观测 NPZ、840份估计矩阵 JSON、28行方法/条件汇总。构成如下：

| 实验 | 条件 | 求解数 |
| --- | --- | --- |
| 无噪声关卡 | N=20，30种子，2方法 | 60 |
| 旋转噪声 | 0/0.1/0.3/0.6/1°每分量；平移噪声0 | 300 |
| 平移噪声 | 0/0.1/0.5/1/2mm每分量；旋转噪声0 | 300 |
| 样本数 | N=8/12/20；噪声0.3°、0.5mm每分量 | 180 |

几何种子20261118—20261147，噪声种子20271118—20271147。各条件复用对应seed的几何与标准正态噪声，两方法共享观测，N使用前缀。因此840不是840组独立随机场景；零噪声曲线端点重复同一基线，独立重跑也不扩充统计样本。

PARK 的部分实测结果（每条件30次；均值±样本SD）：

| 条件 | 旋转误差 ° | 平移误差 mm |
| --- | --- | --- |
| 旋转噪声0.1°、N20 | 0.06518±0.02619 | 0.25222±0.12534 |
| 旋转噪声1°、N20 | 0.65210±0.26153 | 2.52717±1.25344 |
| 平移噪声0.5mm、N20 | 约1.20e-14（数值层级） | 0.30184±0.08991 |
| 混合噪声、N8 | 0.34251±0.10926 | 1.45297±0.74126 |
| 混合噪声、N12 | 0.28711±0.10269 | 1.27813±0.57122 |
| 混合噪声、N20 | 0.19556±0.07853 | 0.83546±0.40716 |

TSAI 的完整结果保存在 summary.csv，不只保留最佳方法。混合噪声N20时，TSAI均值约0.19754°、0.84497mm；两方法在本实验相近，未做显著性检验，不宣称 PARK 普遍更优。

可支持的有限观察：在当前场景与配对种子中，增加观测噪声提高误差；8→20帧的平均误差降低。纯平移噪声未改变这两种分离式方法的旋转求解，旋转误差停留在数值层级；不能推广到所有联合求解器。单次误差不保证随 N 单调降低。

## 7. 数据、图表与复算

主结果目录 `experiments/M1_v0_1/`：

- `trials.csv`：条件、方法、重复编号、N、两种seed、噪声、状态、原因、误差、原始数据/估计路径。
- `summary.csv/json`：成功/失败数、失败率、均值、样本SD(ddof=1)、中位数、四分位和最大值。
- `config.json`、`environment.json`、`baseline_gate.json`、`run_status.json`、`RESULTS.md`。
- `raw/*.npz`：G、理想Q、带噪Q、真值与seed；`estimates/*.json`：估计X。
- `rotation_noise.png`、`translation_noise.png`、`sample_count.png`：均值±1样本SD，英文标注。
- `artifact_hashes.json`：实验产物完整性清单。

已实际查看三张PNG，文字和图例无截断。纯平移噪声图的旋转轴显示1e-14数量级，只是数值舍入，不能拿该图微小差异讨论精度排名。

第二个独立进程重新生成全套实验；trials.csv、summary.csv/json、config.json、baseline_gate.json逐字节一致，420份NPZ各字段数组一致。再从保存观测重放全部840次成功求解，误差与CSV一致，并核对28行均值/标准差。详见 M1_reproducibility.json。
同一机器同一环境下的复现已验证，未承诺跨 OpenCV/BLAS 版本逐位一致。

## 8. 测试与失败机制

实际命令返回：**124 passed in 8.68s**，退出码0；0失败、0跳过，使用 `-W error`。
包含原有75项及新增49项。覆盖已知角度/距离、近零/近π、独立通用逆参照、多个手眼真值、配对数量不足、重复/单轴退化、非法矩阵、非有限OpenCV输出、可重复噪声和种子，以及完整小规模落盘/重放测试。

专门故障注入验证：

- 用错误输出触发无噪声门槛失败，程序只保留基线行，不运行噪声组、不绘噪声图。
- 在基线之后注入求解失败，全部失败行保留、消息保存、误差为空，汇总失败数正确。
- 复用同一输出目录抛出 FileExistsError，防止覆盖旧数据。

实际主运行没有失败记录，是本轮测试条件下的事实，不代表失败机制未覆盖或未来不会失败。失败注入是自动测试，不混入科研结果CSV。

## 9. 问题、限制和未完成内容

- 本轮未遇到阻断性环境错误，所有P0/P1/P2任务均完成。未安装依赖或提权。
- 未找到 PROJECT_SPEC.md，因此以用户任务、CONTINUE WORK.md 和现有约定为依据，没有虚构该文件的要求。
- 理想位姿观测未模拟成像、视野、板检测、遮挡、畸变、PnP、不确定性相关性或机器人测量误差。
- 随机末端变换没有机器人正逆运动学、关节限制、碰撞或可达性保证，也可能让板位于相机背后；它验证代数闭环，不是可执行采集轨迹。
- 只研究一组默认安装真值、30个配对seed、两种求解器；测试中的额外真值不算正式实验场景。没有做多真值泛化、离群点、机器人噪声或实机实验。
- 运动奇异值阈值是数值诊断规则，不是全局可辨识性或精度证明；后续应研究近退化和条件数变化。
- 图上SD不是置信区间；统计是对成功求解的条件统计，实际失败率同时保存。没有创新声明，也不将这些误差称为已达到真实2mm定位目标。
- 独立代码审查尚未执行。Claude Code 后续审查结果应写新文件，不能称为本轮已审查通过。

## 10. 建议 Claude Code 重点审查

详细任务见 `reviews/review_request.md`。优先核对输入/输出方向和真值隔离、全帧对运动诊断、近零角误差、噪声左乘约定、样本前缀配对、关卡/失败状态和CSV统计一致性；再检查CLI输出约束与原有文件保留。

## 11. 下一阶段建议与明天验收

先运行测试并读 learning_guide，手动抽一份 raw NPZ 核对 G X Q=Y 和求解输出。确定是否接受现有无噪声阈值和 G/E 命名映射。
下一阶段优先增加纯平移/近单轴退化实验、机器人位姿噪声、多安装真值及留出点空间误差；随后才增加标定板投影和可见性。主动采样需要公平候选池、相同尝试预算和失败计数，不能从本轮结果直接宣称采样策略创新。
暂不进入GUI、设备控制或深度学习框架。全部材料保存在项目内，未上传私人资料。
