# M1 V0.1 第二轮独立审查报告

审查日期：2026-11-19  
审查依据：第一轮审查报告 `reviews/M1_independent_review.md`、Codex 修复报告 `reports/fix_report.md`、修复分诊 `reports/review_triage.md`。  
审查方法：实际修改源码逐行审查 + 143 项全量测试执行 + 独立边界验证 + 数学一致性复核。  

---

## 一、已解决

### 1. #2 异常捕获过宽 → 已解决

**修改文件**：`src/handeye/experiments.py`  
**验证**：

- 求解阶段引入 `phase` 变量区分 `"solve"` 与 `"evaluate"`。
- 预期数据/求解异常（`CalibrationError`、`ValueError` 在 solve 阶段）保留失败行，实验继续执行协议。
- 意外程序异常（`NameError`、`TypeError`、`ValueError` 在 evaluate 阶段）通过 `persist_unexpected()` 先保存当前失败行及完整 traceback 到 `traceback.txt`，flush CSV，再重新抛出；外层标记 `status: failed` 并停止，不继续后续实验。

**测试证据**：
- `test_unexpected_error_persisted_then_reraised`：6 个参数化场景（NameError/TypeError+evaluate, ValueError+evaluate）全部验证异常重新抛出、当前行落盘、traceback 文件完整、run_status 为 failed、不生成 summary/PNG。
- `test_expected_solver_failure_still_continues_and_keeps_rows`：CalibrationError/ValueError 在 solve 阶段仍使实验 complete，失败行保留，不生成 traceback.txt。
- `test_cli_unexpected_error_is_nonzero_with_traceback`：独立进程 CLI 验证 NameError 非零退出且 stderr 保留 traceback。

**独立验证**：pytest 143 项全部通过；手动注入 NameError/ValueError 验证行为与修复报告一致。

### 2. #4 closure 使用完整序列而非实际 N 帧 → 已解决

**修改文件**：`src/handeye/experiments.py`  
**验证**：

- 由 `closure_error(data)` 改为 `closure_error(replace(data, t_b_g=g, t_c_t=data.t_c_t[:n_samples]))`，使用 dataclass `replace` 构造仅含实际 N 帧理想观测的副本。
- `RESULTS.md` 新增明确说明：`closure_max_abs` 是当前 `n_samples` 帧理想观测的闭环最大元素残差。

**测试证据**：
- `test_logged_closure_uses_actual_ideal_prefix`：monkeypatch `closure_error` 观察传入数据长度，确认 sample_count 实验传入长度为 8；从保存的 NPZ 独立复算 N 帧闭环残差，与 CSV 记录逐行精确相等。

**独立验证**：读取修复后实验 CSV，sample_count 行的 closure_max_abs 与 NPZ 前缀复算一致。

### 3. #5 绘图缺类型/列未处理 → 已解决

**修改文件**：`src/handeye/plotting.py`  
**验证**：

- 进入绘图前一次性检查必需列（`required` 集合）和三类实验类型是否齐全，缺失时抛出明确的 `ValueError`。
- `rows_for` 改为显式循环，缺失实验类型时抛出 `ValueError` 而非未处理的 `StopIteration`。
- figure 创建后置于 `try...finally`，保存失败或异常时确保 `plt.close(fig)` 执行，不泄漏资源。

**测试证据**：
- `test_plot_missing_experiment_is_explicit_and_creates_no_figures`：4 种缺失场景（rotation_noise/translation_noise/sample_count/all）均抛出 ValueError 且不创建 PNG、不残留 figure。
- `test_plot_missing_column_is_explicit_before_drawing`：缺失列时在绘制前抛出 ValueError。
- `test_plot_closes_figure_on_save_failure`：模拟磁盘错误时抛出 OSError 但 figure 被关闭。
- `test_rows_for_missing_type_has_domain_error`：空列表查询返回可解释 ValueError。

**独立验证**：正常完整实验仍生成三张 PNG；人为构造缺失实验类型的 CSV 调用 `plot_results` 时确实提前抛出 ValueError。

### 4. #6 退化返回值测试不足 → 已解决

**新增文件**：`tests/test_review_fixes.py`（其中 4 项）  
**验证**：

- `test_degenerate_diagnostic_and_adapter_do_not_call_opencv` 覆盖 identical/pure_translation/single_axis/tiny_angle 四种退化场景。
- 直接断言 `motion_diagnostics` 返回 `nondegenerate=False` 和 `axis_second_first_ratio=0.0`。
- 断言退化输入不会调用 OpenCV（通过 monkeypatch 计数验证），且 `calibrate_hand_eye` 抛出可解释的 `ValueError`。

**独立验证**：在当前 NumPy 2.5.5 环境中，`motion_diagnostics` 对完全相同位姿、纯平移、单轴、小角度序列均正常返回 `nondegenerate=False`，不会崩溃。

### 5. #7 反射矩阵测试缺口 → 已解决

**新增文件**：`tests/test_review_fixes.py`（其中 1 项）  
**验证**：

- `test_opencv_reflection_output_is_rejected`：monkeypatch `cv2.calibrateHandEye` 返回 `diag(1, 1, -1)` 和零平移。
- 验证 `calibrate_hand_eye` 抛出 `CalibrationError` 且消息包含 `det=+1`。

**独立验证**：适配器确实通过 `make_transform` 的 `is_rotation_matrix` 检查拒绝反射矩阵，功能已存在，测试补足了覆盖。

---

## 二、部分解决 / 争议澄清

### 6. #1 空 reshape 崩溃 → 未修复，但验证为当前环境误报

**第一轮审查结论**：`np.asarray([]).reshape(-1, 3)` 会抛出 ValueError。  
**Codex 核验结论**：在当前 NumPy 2.5.5 下返回 `shape=(0, 3)`，`motion_diagnostics` 正常返回 `nondegenerate=False`。  
**第二轮独立验证**：

```python
np.asarray([]).reshape(-1, 3).shape  # 实测 (0, 3)
motion_diagnostics(np.repeat(np.eye(4)[None], 15, axis=0))  # 正常返回 nondegenerate=False
```

**判断**：第一轮审查对 NumPy 版本行为的判断有误。当前环境下 `motion_diagnostics` 在空旋转向量时通过 `len(vectors) else np.zeros((3, 3))` 分支正常返回退化标志，不会崩溃。由于 #6 已补充直接退化测试，无需额外代码修复。

**风险**：若未来迁移到对此行为更严格的 NumPy 版本（如有），`reshape(-1, 3)` 仍可能崩溃。建议作为防御性编程，在 `reshape` 前保留空列表检查（一行即可），但当前非阻断。

### 7. #3 target 退化诊断冗余 → 保留现状，未解决

**Codex 分析**：在理想几何下，target 相对运动 `Q_j^{-1} Q_i = Y^{-1} G_j G_i^{-1} Y` 与 gripper 相对运动 `G_j^{-1} G_i` 为相似变换（通过 `Y` 共轭），不改变旋转奇异值结构；因此理想数据下 target 检查是冗余的。有限搜索（2000 个近单轴候选）未找到 "G 通过、Q 不通过" 的反例。

**判断**：这是一个正确的数学观察，但"冗余"不等于"有害"。target 检查作为安全网，在带噪数据或极端几何下仍可能捕获 gripper 检查遗漏的问题。没有可运行反例前，保留双检查是合理的技术决策。未引入新 Bug，也未改变任何行为。

### 8. #8 CLI 异常捕获范围 → 未采纳，与 #2 设计一致

**Codex 决定**：不扩大 `run_m1.py` 的 `except` 范围。未预期异常保留 traceback 与非零退出，与 #2 的"暴露程序性错误"目标一致。

**判断**：合理的设计取舍。`test_cli_unexpected_error_is_nonzero_with_traceback` 已验证 CLI 在意外错误时的行为符合预期。

---

## 三、未解决（原报告中的低优先级项）

### 9. 测试未覆盖 OpenCV 返回非正交矩阵（接近退化）的情况

`test_nonfinite_solver_outputs_rejected` 和新增的反射测试覆盖了非法旋转矩阵的拒绝，但未覆盖 OpenCV 返回**非正交但仍为旋转**的矩阵（如条件数极差的近似旋转矩阵）。当前 `make_transform` 的 `is_rotation_matrix` 使用固定容差 `atol=1e-9`，未测试边界附近的输入。

**风险**：极低。OpenCV 的 PARK/TSAI 方法在正常数据下不会返回此类结果，且当前已有 NaN/inf/反射测试。

---

## 四、新发现

### 10. `traceback.txt` 可能被覆盖，丢失内层 traceback 细节

**位置**：`src/handeye/experiments.py`  
**细节**：`persist_unexpected()` 先写入 `traceback.txt`，然后 `raise`；外层 `run_experiment` 的 `except Exception` 再次写入同一文件，最终保留的是从 `run_experiment` 开始的完整 traceback，而 `persist_unexpected` 中捕获的更精确位置信息被覆盖。

**实际风险**：极低。当前流程在第一个意外错误后即停止，不存在多个并发 traceback 的竞争；外层的 traceback 实际上更完整（包含调用链）。但若未来需要保留多层错误上下文，可能需要使用唯一文件名（如 `traceback_{timestamp}.txt`）。

**建议**：非阻断。当前实现可接受。

### 11. `persist_unexpected` 与主循环的 `records.append(row)` 存在潜在重复风险

**位置**：`src/handeye/experiments.py:146` 和 `:210`  
**细节**：`persist_unexpected()` 内部执行 `records.append(row)` 和 `writer.writerow(row)`，然后 `raise`。主循环 `:210` 在异常抛出后不会执行，因此当前无重复。

**但若未来重构时**，在 `persist_unexpected` 和 `raise` 之间插入代码，或意外移除 `raise`，将导致同一行被追加两次。

**建议**：非阻断。可通过将 `records.append(row)` 和 `writer.writerow(row)` 从主循环移至 `else/finally` 块，或让 `persist_unexpected` 设置标志避免重复，来增强维护安全性。当前代码正确但脆弱。

### 12. `experiments.py` 中 `except (CalibrationError, ValueError)` 的 `ValueError` 在 evaluate 阶段被硬编码为意外错误

**位置**：`src/handeye/experiments.py:190–193`  
**细节**：

```python
except (CalibrationError, ValueError) as exc:
    if phase != "solve":
        persist_unexpected(row, exc, phase)
        raise
```

这里 `ValueError` 在 evaluate 阶段被无条件归类为意外错误。虽然当前 `pose_error` 正常流程不会抛出 `ValueError`，但如果未来 `pose_error` 被扩展为在某些合法但边缘的场景下抛出 `ValueError`（例如添加对误差量级合理性的检查），这些将被错误地归类为程序性错误并中止实验。

**实际风险**：低。当前代码正确，但这是未来扩展时的潜在陷阱。

**建议**：在代码注释中明确说明：`evaluate` 阶段的 `ValueError` 被视为程序性错误；若未来 `pose_error` 需要抛出预期的数据错误，应定义专用异常类型（如 `EvaluationError`）而非复用 `ValueError`。

---

## 五、数学定义与坐标变换方向一致性复核

**结论：修复未改变任何数学实现，所有定义保持一致。**

| 审查项 | 修复前 | 修复后 | 变化 |
|--------|--------|--------|------|
| T_A_B = B→A | ✓ | ✓ | 无变化 |
| Q = inv(GX)Y | ✓ | ✓ | 无变化 |
| OpenCV 输入映射 | ✓ | ✓ | 无变化 |
| 误差定义与单位 | ✓ | ✓ | 无变化 |
| 无噪声阈值 1e-6 | ✓ | ✓ | 无变化 |
| 噪声模型（左乘 SO(3) + 独立平移） | ✓ | ✓ | 无变化 |
| 随机种子配对与 N 前缀 | ✓ | ✓ | 无变化 |
| 统计量 ddof=1 | ✓ | ✓ | 无变化 |

修复仅涉及：错误分类与持久化、CSV 字段新增 `traceback_file`、closure 诊断范围、绘图输入校验与资源释放、新增回归测试。**所有求解、生成、误差数值逻辑均未改动。**

---

## 六、测试执行结果

| 测试集 | 数量 | 结果 | 耗时 |
|--------|------|------|------|
| 原有回归测试 | 124 | 全部通过 | — |
| 新增审查回归测试 | 19 | 全部通过 | — |
| **合计** | **143** | **全部通过** | **37.16s** |

新增测试覆盖：意外错误持久化（6 项）、预期失败继续（2 项）、退化诊断直接返回值（4 项）、反射拒收（1 项）、closure 前缀（1 项）、绘图健壮性（4 项）、rows_for（1 项）、CLI 意外错误（1 项）。

---

## 七、总结

Codex 的修复**有效且保守**：只修改了必要的文件（`experiments.py`、`plotting.py`），新增了充分的回归测试（`test_review_fixes.py`），**未改动任何数学、求解或误差计算逻辑**。

| 原审查编号 | 状态 | 说明 |
|------------|------|------|
| #1 空 reshape 崩溃 | 不修复，验证为误报 | 当前 NumPy 版本下正常返回退化标志；#6 测试已补足 |
| #2 异常捕获过宽 | **已解决** | 预期/意外异常分离，先落盘后停止，traceback 保留 |
| #3 target 检查冗余 | 保留现状 | 数学上冗余但无害，无反例前不改 |
| #4 closure 语义 | **已解决** | 改为实际 N 帧理想前缀，文档已更新 |
| #5 绘图健壮性 | **已解决** | 输入预校验、显式错误、finally 关闭资源 |
| #6 退化测试不足 | **已解决** | 4 种退化场景直接断言 |
| #7 反射测试缺口 | **已解决** | 新增 monkeypatch 回归测试 |
| #8 CLI 捕获范围 | 不采纳 | 与 #2 设计一致，保留 traceback |

**新发现问题**（3 项）均为非阻断性代码维护/扩展风险，不影响当前功能正确性：
- `traceback.txt` 被覆盖（风险极低，当前更完整的 traceback 是合理结果）
- `records.append` 的潜在重复风险（当前代码路径安全，但重构时需注意）
- `evaluate` 阶段 `ValueError` 被硬编码为意外错误（未来扩展时的设计约束）

**建议**：当前修复已达到可验收状态。若需进一步加固，可考虑为 #1 添加防御性空列表检查（单行），以及在 `experiments.py` 中为异常分类逻辑添加更详细的注释。
