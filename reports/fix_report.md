# M1 审查问题修复报告

日期：2026-11-19（Asia/Shanghai）。依据：[review_triage.md](review_triage.md) 及用户明确授权。
修复分支：`fix/m1-review-20261119`。状态：已完成本轮已证实问题修复与验证，未提交或推送代码。

## 1. 修复结果

没有已确认P0问题。本轮按P1→P2处理，保留未证实数学争议。

| 审查编号 | 修改与原理 | 对应文件 | 验证 |
| --- | --- | --- | --- |
| #2，P1 | 区分预期求解拒收与意外程序异常；意外异常先保存完整traceback和当前失败行、flush，再重新抛出；运行状态改为failed并停止 | src/handeye/experiments.py | 3项阶段/异常类型测试及独立进程CLI测试，由失败变通过 |
| #6，P1测试 | 直接检查相同位姿、纯平移、单轴、小角度退化返回值、拒收消息，并确认未调用OpenCV | tests/test_review_fixes.py | 4项新增回归通过，无需修改原诊断算法 |
| #7，P1测试 | 注入OpenCV反射输出，确认适配器抛CalibrationError且指出det=+1约束 | tests/test_review_fixes.py | 新增测试通过，现有拒收功能保留 |
| #4，P2 | closure_max_abs改为本行实际N帧的理想观测前缀，仍保留生成器的完整序列几何验证；结果说明明确范围 | src/handeye/experiments.py | 检查诊断实际接收8帧，并从保存NPZ逐行复算，修复前失败、修复后通过 |
| #5，P2 | 绘图前检查必需列和三类实验是否齐全；缺失时给出ValueError；figure使用finally关闭，保存失败也不泄漏 | src/handeye/plotting.py | 缺类型/列、辅助查询、保存异常资源释放测试由失败变通过 |

生产代码只修改以上2个文件；新增1个测试文件。未改动 transforms、metrics、simulation、calibration 的数学实现、求解参数、阈值、原有测试或CLI代码。

## 2. Git与未提交成果保护

开始时分支为main，工作区已有README/requirements/.gitignore修改、多份历史代码删除以及大量未跟踪文件。未执行stash、reset、clean、restore、add、commit或push。

检查仓库状态并保存基线后，实际执行：

```powershell
git switch -c fix/m1-review-20261119
```

分支创建成功，HEAD仍为修复前同一提交。切换新分支不会隔离或清除已有未提交文件；本轮通过源码副本、完整哈希清单与差异文件保护它们。

- 修复前2755个文件的SHA-256清单及相关源码副本保存在 `reports/fix_evidence_20261119/`。
- 最终核对：**2753个已有文件未变**，仅experiments.py和plotting.py按计划修改。
- 原有已跟踪工作区差异与暂存区差异逐字节保留；没有将他人成果纳入提交。
- reviews、research_output、文献、申报书、旧实验目录和旧报告未修改。
- 当前src原先即为未跟踪目录，单靠git diff无法显示本轮源码差异，因此额外保存基于精确副本的unified diff。

证据：[保留核验](fix_evidence_20261119/preservation.json)、[修改前Git状态](fix_evidence_20261119/git_status_before.txt)、[修改后Git状态](fix_evidence_20261119/git_status_after.txt)、[修复差异](fix_evidence_20261119/changes.patch)。

## 3. 数学约定与PROJECT_SPEC状态

本轮开始时再次检查，`docs/PROJECT_SPEC.md` **不存在**，没有假称读过或遵守其中未提供的内容。沿用已有AGENTS、坐标文档和learning_guide的明确约定：

- T_A_B把B坐标映射到A；G等同旧E；内部米、弧度。
- G_i X Q_i=Y，Q_i=inv(G_i X)Y。
- OpenCV输入T_B_G与T_C_T，输出T_G_C。
- 无噪声验收阈值仍为1e-6 rad、1e-6 m；几何闭环检查阈值仍为1e-12。

上述数学实现和阈值均未改动。若后续补充PROJECT_SPEC，需将其与现有约定再次核对。

## 4. 关键实现说明

### 意外错误与预期求解失败分开

求解阶段的CalibrationError、ValueError作为既有数据/求解拒收契约，继续保留失败行并执行协议。
NameError、TypeError等非预期求解异常，以及误差评价阶段的异常（包括ValueError），先落盘再中止。误差评价阶段出现异常不应冒充某个求解器的正常失败率。

新行为：

```text
捕获意外异常
→ 保存traceback.txt
→ 写入当前CSV失败行及traceback_file路径并flush
→ 重新抛出原异常
→ 外层保存failed状态、recorded_trials、failure_stage和traceback_file
→ 非零退出，不继续后续实验/结论
```

这样避免了“直接raise导致当前失败行丢失”。预期求解失败仍可使实验正常完成，但失败数、失败消息和空误差列继续保留，未改成填零或丢弃。

`trials.csv`新增 `traceback_file` 列；成功及预期失败为空，意外错误指向日志。失败run_status新增错误阶段和traceback路径。按列位置读取CSV的外部代码需要注意这个增量；项目现有读取器使用字段名且已通过回归。

CLI未增加通用吞异常分支。独立进程测试确认NameError会以非零退出并保留stderr traceback；现有CLI对ValueError/TypeError等的简洁提示保持原样，此时完整traceback仍保存在实验目录内。

### 理想前缀闭环日志

生成器仍先检查完整长序列。实验行再用 `replace(data, t_b_g=g, t_c_t=ideal_q[:N])` 核查实际使用的理想前缀。closure_max_abs不是带噪观测残差，也不是空间位置误差。
旧CSV不追溯改写；新运行RESULTS.md明确该字段范围。不会改变求解观测或真值误差。

### 绘图验证与finally

进入绘图前一次性检查必需列和rotation_noise、translation_noise、sample_count，避免绘到一半才发现缺类型。独立rows_for查询也给出可解释ValueError。
绘制、标题和保存位于try内，finally关闭本次figure。保存错误仍向外传播，不被当成成功；未进行图形风格或统计方式重构。

## 5. 测试：先失败，再修复，再回归

| 阶段 | 实际结果 | 日志 |
| --- | --- | --- |
| 修复前原有完整测试 | 124通过，0失败 | [baseline.txt](fix_evidence_20261119/baseline.txt) |
| P1新增测试，生产代码未修复 | 4失败、7通过、8未选中 | [p1_red.txt](fix_evidence_20261119/p1_red.txt) |
| P1修复后对应测试 | 11通过、8未选中 | [p1_green.txt](fix_evidence_20261119/p1_green.txt) |
| P2新增测试，P2生产代码未修复 | 8失败、11未选中 | [p2_red.txt](fix_evidence_20261119/p2_red.txt) |
| P2修复后对应测试 | 8通过、11未选中 | [p2_green.txt](fix_evidence_20261119/p2_green.txt) |
| 最终完整pytest | **143通过，0失败、0跳过** | [full_after.txt](fix_evidence_20261119/full_after.txt) |

原始测试数量仍为124，新增19项。红灯阶段失败是新增期望行为暴露旧缺陷，不是修复导致原功能回归。没有删除测试或放宽阈值；#6/#7是已有正确行为的覆盖增强，因此修复前即能通过。
最终完整测试耗时8.60秒，退出码0。全部测试命令使用 `-W error`，临时目录在项目.venv内，禁用pytest缓存写入。各阶段JUnit XML和机器可读计数见 [test_results_summary.json](fix_evidence_20261119/test_results_summary.json)。

关键执行命令（项目根目录，省略日志重定向）：

```powershell
git rev-parse --show-toplevel
git branch --show-current
git status --short
git switch -c fix/m1-review-20261119
.\.venv\Scripts\python.exe -W error -m pytest -q -p no:cacheprovider --basetemp=.venv\fix-before-temp --junitxml=reports\fix_evidence_20261119\baseline.xml
.\.venv\Scripts\python.exe -W error -m pytest tests\test_review_fixes.py -q -p no:cacheprovider -k 'unexpected or expected_solver or degenerate or reflection' --basetemp=.venv\fix-p1-red-temp --junitxml=reports\fix_evidence_20261119\p1_red.xml
# P1修复后同样选择器，输出p1_green.xml并使用fix-p1-green-temp
.\.venv\Scripts\python.exe -W error -m pytest tests\test_review_fixes.py -q -p no:cacheprovider -k 'closure or plot or rows_for' --basetemp=.venv\fix-p2-red-temp --junitxml=reports\fix_evidence_20261119\p2_red.xml
# P2修复后同样选择器，输出p2_green.xml并使用fix-p2-green-temp
.\.venv\Scripts\python.exe -W error -m pytest -q -p no:cacheprovider --basetemp=.venv\fix-full-temp --junitxml=reports\fix_evidence_20261119\full_after.xml
```

没有发生修复后完整测试失败的情况。所有已观察失败都保存在红灯日志中，没有被后续日志覆盖。

## 6. 实际实验链路与旧数值对照

以新配置、新目录执行两方法、每条件2种子的小规模实验，保留N=8/12/20，旋转噪声0/0.1/0.3°、平移噪声0/0.1/0.5mm。实际执行：

```powershell
.\.venv\Scripts\python.exe -W error scripts\run_m1.py --config reports\fix_evidence_20261119\smoke_config.json --output experiments\M1_review_fix_smoke_20261119
```

结果：**40次求解，0失败，无噪声关卡通过**；CSV、估计矩阵、原始NPZ和三张PNG均保存，已查看sample_count.png确认输出可读。此小实验仅用于修复验证，不用于提出新的科研结论。

逐条对照原M1同条件/方法/重复编号的40行：旋转误差、平移误差、采样数及种子**完全一致**；每行closure均能从保存的理想前缀精确复算。该小配置的前两个seed恰好没有出现全集/前缀最大残差差异；前缀修复的故障暴露由专门测试（含seed=20261121与诊断长度断言）完成，不能声称小实验出现了未观察到的差异。

证据：[实验运行日志](fix_evidence_20261119/smoke_run.txt)、[逐次对照结果](fix_evidence_20261119/smoke_comparison.json)、[新实验结果说明](../experiments/M1_review_fix_smoke_20261119/RESULTS.md)。
本轮没有重跑或覆盖原840次正式实验，因为生成、求解与误差数值逻辑未变，针对性40次对照和完整回归已验证相关行为。

## 7. 改动与运行环境

改动文件：

1. [experiments.py](../src/handeye/experiments.py)：异常契约、落盘、失败状态、前缀closure与新结果说明。
2. [plotting.py](../src/handeye/plotting.py)：输入验证、明确错误及资源关闭。
3. [test_review_fixes.py](../tests/test_review_fixes.py)：新增19项回归，不改原测试。

其他新增文件仅为本报告、修复证据/差异和独立小实验输出。环境继续使用Python3.12.0、NumPy2.5.5、SciPy1.18.1、cv2 5.1.0、Matplotlib3.11.2、pytest9.2.0；未安装或升级依赖。pip check返回 `No broken requirements found.`。
Git空白检查通过，原有LF/CRLF提示未改变仓库设置。因为源码原本未跟踪，已另存精确差异用于审查。

## 8. 未解决与明确不做

- **#3相机运动诊断误拒**：仍未证实，保留既有双检查及阈值；不猜测数学结论或自行移除保护。
- **#1空reshape崩溃**：上一轮已否定，不作伪修复；直接退化测试已补足。
- **#8扩大CLI捕获**：未加通用捕获，保留意外异常诊断；如将来统一CLI错误体验，应保证完整日志和非零退出。
- PROJECT_SPEC.md缺失；没有擅自补写规范，若提供新规范需核对。
- 没有执行Claude Code二次审查，也没有把开发自测写成独立审查通过。

## 9. 建议Claude Code二次审查重点

1. 对照changes.patch，检查意外错误是否真的“当前行+traceback落盘→flush→抛出”，尤其是误差评价ValueError与求解阶段ValueError的分类边界。
2. 检查failed状态、recorded_trials、failure_stage与CSV最后一行的一致性；中止后没有继续运行后续条件或生成结论。
3. 检查新增traceback_file列对外部CSV消费者的兼容影响，以及CLI简洁提示与完整日志的配合。
4. 检查closure只用实际N帧**理想**观测，生成器完整序列检查仍在，且旧实验数据保持不变。
5. 检查绘图缺类型/列的预验证及保存失败时finally关闭资源，确保正常完整实验仍生成三张图。
6. 运行原124项与新增19项，检查测试是否验证实际行为而非放宽阈值；确认#3没有被未经证明地改动。

本轮修复已完成，后续审查可在当前分支继续。建议审查结果使用新的文件名，保留原独立审查与本轮证据。
