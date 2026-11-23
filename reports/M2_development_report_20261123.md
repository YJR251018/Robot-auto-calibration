# M2 离线采样与留出评价开发报告

日期：2026-11-23，Asia/Shanghai。**A—G 必做项已经验收；H 扩展另行记录，不与主实验合并。** 分支 `feat/m2-sampling-20261123`，未提交或推送。

## 1. 实际完成与文件用途

- `docs/PROJECT_SPEC.md`：整理既有 T_A_B、AX=XB、米/弧度、真值边界、噪声与数据契约。
- `src/handeye/evaluation.py`：20 帧独立理想留出、五个板点的空间 RMSE、最大误差、逐帧误差及分别量化的闭环残差。
- `src/handeye/sampling.py`：ordered、random、rotation_farthest；共同初始 ID、稳定并列和 N 前缀；选择器不接收 Q 或真值。
- `src/handeye/m2_experiments.py`：配置验证、候选/留出/噪声随机流、冻结试次、无噪声关卡、失败落盘、统计与配对 bootstrap。
- `src/handeye/m2_plotting.py`：从保存统计生成三类 PNG/PDF。
- `src/handeye/m2_verification.py`：产物哈希、选择序列、试次计数、统计复算及实际求解重放。
- `scripts/run_m2.py`、`scripts/verify_m2.py`：项目内真实 CLI；新目录/报告拒绝覆盖。
- `configs/m2_sampling_v0_1.json`、`configs/m2_smoke.json`：正式和开发协议分开。
- `tests/test_m2_math.py`、`tests/test_m2_experiments.py`：新增45项数学、故障、计数、配对与CLI验证。
- `docs/M2_sampling_guide.md`：中文原理、命令、局限与5道带答案理解题。
- `reports/M2_review_followup_20261123.md`：独立核验第二轮意见，未改原审查报告。

没有修改原有 M1 数学、求解、异常或绘图源码；原测试全部保留。README、AGENTS 增加当前入口，plans/progress.json 记录实际进度。精确新增清单、差异和保护核验在 M2_evidence_20261123 中。

## 2. 实际测试与遇到的问题

| 阶段 | 实际结果 | 证据 |
| --- | --- | --- |
| 开始前完整基线 | 143通过，22.93秒 | M2_evidence_20261123/baseline.txt、xml |
| 新数学测试首次运行 | 1个收集错误：新模块尚未创建 | math_red.txt、xml；属于新功能缺失，不宣称发现旧Bug |
| 数学模块完成 | 27通过 | math_green.txt、xml |
| 首轮M2集成 | 44通过、1失败 | integration.txt、xml |
| 编码修复后 | 45通过 | integration_green.txt、xml |
| A—G完整回归 | **188通过，0失败/错误/跳过，13.37秒** | full_core.txt、xml |

集成失败来自 Windows 子进程编码：子进程输出 UTF-8，测试父进程按 GBK 解码。修复仅在新增测试中显式设置 PYTHONIOENCODING 与 subprocess encoding='utf-8'，保留原始失败日志，未改系统设置，未关闭警告、删除测试或降低阈值。

故障注入验证了预期求解失败继续且误差留空；意外 NameError/评价 ValueError 当前行落盘后终止；无噪声失败不运行后续噪声；重复输出/项目外路径被 CLI 拒绝。

## 3. 正式协议与实测结果

协议在正式运行前冻结于 `M2_evidence_20261123/protocol_freeze.json`，保存正式配置与代码哈希。三策略、N=8/12/20、四噪声条件、30重复、PARK/TSAI，共 **2160次成功，0失败，0未运行**；其中540次无噪声全部通过。最大无噪声旋转误差约3.714e-13°，平移约1.681e-12mm，远低于原定1e-6rad/1e-6m门槛。

正式产物：`experiments/M2_sampling_20261123/`，包含30份候选/独立留出原始NPZ、2160份估计与逐帧评价、选择序列、CSV/JSON、三类PNG/PDF、完整性清单。

预设主比较为 PARK、混合相机噪声0.3°/0.5mm、N20下的留出点RMSE：

| 策略 | 均值±样本SD（mm），30重复 |
| --- | --- |
| ordered | 1.302740 ± 0.548577 |
| random | 1.176113 ± 0.431949 |
| rotation_farthest | 0.999925 ± 0.314928 |

farthest-random 的30个有效配对均值差为 **-0.176187mm**，固定2000次按repeat重采样的95% bootstrap区间为 **[-0.313610,-0.031088]mm**。当前配置下平均误差较低，但不是每个重复都更好；图中保留了正差值。不能据此宣称全场景优势、最优性、创新性或实机毫米级精度。

## 4. 再现与独立数值复核

- 两次开发CLI运行各144次，均成功；开发种子与正式分离。两个独立进程的原始数组、选择序列、试次数值字段完全一致；两组共288次成功全部重放通过。
- 正式2160次成功全部从保存的观测再次调用OpenCV求解，估计与指标符合核验容差；试次唯一性、前缀、计数、原始哈希、统计、配对bootstrap均通过。
- 另用独立齐次点矩阵乘法复算2160个留出RMSE，并独立按CSV分组算均值/SD；最大RMSE差仅1.33e-15mm。证据 `independent_numeric_audit.json`。
- 主实验三类PNG已逐张查看，图例、单位、零失败计数与误差棒含义可读；图由保存统计绘制。没有进行期刊版式认证。

证据：`smoke_verification.json`、`formal_verification.json`。重跑与重放不增加独立实验样本数，也不代表其他Agent已经独立审查。

## 5. 实际关键命令

```powershell
git switch -c feat/m2-sampling-20261123
.\.venv\Scripts\python.exe -W error -m pytest -q -p no:cacheprovider --basetemp=.venv\M2-baseline-temp --junitxml=reports\M2_evidence_20261123\baseline.xml
.\.venv\Scripts\python.exe -W error -m pytest tests/test_m2_math.py tests/test_m2_experiments.py -q -p no:cacheprovider --basetemp=.venv\M2-integration-green-temp --junitxml=reports\M2_evidence_20261123\integration_green.xml
.\.venv\Scripts\python.exe -W error scripts/run_m2.py --config configs/m2_smoke.json --output experiments/M2_smoke_20261123_a
.\.venv\Scripts\python.exe -W error scripts/run_m2.py --config configs/m2_smoke.json --output experiments/M2_smoke_20261123_b
.\.venv\Scripts\python.exe -W error scripts/verify_m2.py --run experiments/M2_smoke_20261123_a --compare experiments/M2_smoke_20261123_b --report reports/M2_evidence_20261123/smoke_verification.json
.\.venv\Scripts\python.exe -W error scripts/run_m2.py --config configs/m2_sampling_v0_1.json --output experiments/M2_sampling_20261123
.\.venv\Scripts\python.exe -W error scripts/verify_m2.py --run experiments/M2_sampling_20261123 --report reports/M2_evidence_20261123/formal_verification.json
.\.venv\Scripts\python.exe -W error -m pytest -q -p no:cacheprovider --basetemp=.venv\M2-full-core-temp --junitxml=reports\M2_evidence_20261123\full_core.xml
```

命令在项目根目录执行，当前进程设置 PYTHONDONTWRITEBYTECODE=1、PYTHONIOENCODING=utf8、MPLCONFIGDIR 为项目.venv缓存。环境版本见 review_probe.json 与每个实验 environment.json，未安装或升级依赖。

## 6. 限制与待验证事项

- M2是位姿级观测仿真，简化相机视野、图像测量、可达性与碰撞。留出是理想观测，不是部署噪声误差。
- 选择只用旋转分散代理，不保证信息最优；不同安装、噪声和候选分布须分开检验。
- 双退化诊断的数学等价性未证明，保持旧实现。没有新的已证实P0。
- 不支持直接原地续跑部分目录；中断保存状态与已落盘行，新运行另建目录，不能混合不同代码指纹。
- 哈希用于一致性而非数字签名；本机测试和复算不替代独立代码审查。
- H扩展与W2在必做项验收后继续，实际完成范围以后续报告及progress为准。
