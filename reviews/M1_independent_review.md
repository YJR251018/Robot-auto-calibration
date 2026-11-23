# M1 V0.1 独立审查报告

审查日期：2026-11-19  
审查范围：坐标/真值隔离、退化诊断、噪声模型、关卡/失败机制、统计一致性、复现链路、代码鲁棒性。  
审查方法：源码逐模块审查 + pytest 124 项测试执行 + 快速独立实验（60 次求解）验证 + 已有复算报告核对。  

---

## 一、已确认缺陷（按严重性排序）

### 1. `motion_diagnostics` 空旋转向量时崩溃，而非返回退化标志

- **位置**：`src/handeye/calibration.py:42–43`
- **触发条件**：所有帧对的相对旋转角 ≤ 1e-8（如完全相同的位姿序列，或测试中的 `np.repeat(np.eye(4)[None], 15, axis=0)`）。
- **实际风险**：代码意图通过 `nondegenerate=False` 优雅拒绝退化输入，但 `np.asarray([]).reshape(-1, 3)` 会直接抛出 NumPy 内部 `ValueError: cannot reshape array of size 0 into shape (0,newaxis)`。错误消息是 NumPy 实现细节，而非用户友好的退化提示。当前测试 `test_solver_input_checks_and_degenerate_motions` 意外依赖此崩溃行为来拒绝退化输入，而非验证预期的退化诊断路径；若未来 NumPy 版本改变空数组 reshape 行为，该测试可能意外失效。
- **建议修复**：在 `reshape` 前检查空列表，或提前返回退化结果。最小修复示例：

```python
trans_s = np.linalg.svd(np.vstack(translation_blocks), compute_uv=False)
trans_ratio = float(trans_s[-1] / trans_s[0]) if trans_s[0] > 0 else 0.0

if not rotation_vectors:
    return {
        "pair_count": len(translation_blocks),
        "rotation_axis_singular_values": [0.0, 0.0, 0.0],
        "translation_design_singular_values": trans_s.tolist(),
        "axis_second_first_ratio": 0.0,
        "translation_min_max_ratio": trans_ratio,
        "nondegenerate": False,
    }

vectors = np.asarray(rotation_vectors).reshape(-1, 3)
axes = vectors / np.linalg.norm(vectors, axis=1, keepdims=True)
...
```

### 2. `experiments.py` 异常捕获范围过宽，可能掩盖程序性错误

- **位置**：`src/handeye/experiments.py:177`
- **触发条件**：求解或误差评估阶段出现未预期的程序性错误（如 `NameError`、`AttributeError`、`IndexError`）。
- **实际风险**：`except Exception as exc:` 将所有异常统一记录为 `"solve_or_evaluate"` 失败并继续执行。虽然满足"不丢行、不填零"的要求，但 traceback 完全丢失，程序性错误被归类为求解失败，显著增加调试难度。审查请求明确要求检查"异常捕获是否过宽、能否暴露程序性错误"。
- **建议修复**：区分预期异常（`CalibrationError`、`ValueError`）与未预期异常。对后者记录后重新抛出，或至少附加 traceback：

```python
from handeye.calibration import CalibrationError

try:
    estimate = calibrate_hand_eye(g, q, method=method)
    error = pose_error(estimate, data.t_g_c_true)
except (CalibrationError, ValueError) as exc:
    row.update(failure_stage="solve_or_evaluate", message=f"{type(exc).__name__}: {exc}")
except Exception as exc:
    row.update(failure_stage="unexpected", message=f"{type(exc).__name__}: {exc}")
    raise
```

---

## 二、待查问题

### 3. `motion_diagnostics` 对 target 做冗余且可能过度严格的退化检查

- **位置**：`src/handeye/calibration.py:72–73`
- **触发条件**：Eye-in-Hand 配置中，相机观测（`T_C_T`）的相对运动在数值上表现为"退化"。
- **实际风险**：在 Eye-in-Hand 配置中，`T_C_T` 的运动完全由 `T_B_G` 和固定的 `T_G_C` 决定。若 gripper 运动非退化，target 运动理论上也非退化（除非 `T_G_C` 存在特殊的退化映射）。对 target 再做一次 `motion_diagnostics` 是冗余的安全网，但在某些边缘场景下可能不必要地拒绝有效输入。当前实验中未触发。
- **建议验证**：构造一个 `T_G_C` 使 target 运动的奇异值比刚好低于 1e-3、但 gripper 运动高于阈值的手动场景，检查是否会被错误拒绝。

### 4. `experiments.py` 的 closure 基于 `max_samples` 而非实际 `n_samples` 计算

- **位置**：`src/handeye/experiments.py:153`
- **触发条件**：样本数实验（`N=8/12`）时。
- **实际风险**：`closure_error(data)` 使用完整 20 帧数据计算闭环残差，而非实际使用的 `N` 帧。虽然理想几何的前缀子集闭环残差与完整序列在数值上相同，但 CSV 中 `closure_max_abs` 的语义与实际使用数据不完全一致。极低风险，不影响统计结论。
- **建议**：对截断数据单独计算 `closure_error` 以保持记录语义一致性，或在 `RESULTS.md` 中明确说明 `closure` 值对应完整序列。

### 5. `plotting.py` 的 `rows_for` 未处理缺失实验类型

- **位置**：`src/handeye/plotting.py:52–53`
- **触发条件**：`summary.csv` 缺少某个实验类型（如基线失败导致噪声图未生成，但代码仍尝试读取不完整的 CSV）。
- **实际风险**：`next()` 会抛出未处理的 `StopIteration`，用户体验差。正常流程下不会发生。
- **建议**：添加默认值处理或显式错误提示，例如：

```python
def rows_for(rows, experiment, key):
    for r in rows:
        if r["experiment"] == experiment:
            return r[key]
    raise ValueError(f"实验类型 '{experiment}' 在 summary.csv 中不存在")
```

---

## 三、非阻断建议

### 6. 测试未直接覆盖 `motion_diagnostics` 的预期退化返回路径

- **位置**：`tests/test_m1.py`
- **说明**：`test_solver_input_checks_and_degenerate_motions` 验证了退化输入被拒绝，但当前依赖的是缺陷 #1 中的崩溃行为（抛出 `ValueError`），而非预期的 `"nondegenerate": False` 返回路径。修复缺陷 #1 后，该测试可能需要调整断言方式。
- **建议**：增加专门针对 `motion_diagnostics` 返回值的显式测试，例如：

```python
def test_motion_diagnostics_returns_false_on_pure_translation():
    poses = np.stack([make_transform(rotation_matrix("z", 0), [t, 0, 0]) for t in np.linspace(0, 1, 15)])
    diag = motion_diagnostics(poses)
    assert not diag["nondegenerate"]
    assert diag["axis_second_first_ratio"] == 0.0
```

### 7. 未测试 OpenCV 返回反射矩阵（det = −1）的情况

- **位置**：`tests/test_m1.py`
- **说明**：`test_nonfinite_solver_outputs_rejected` 仅覆盖 NaN/inf 情况，未覆盖 OpenCV 返回行列式为 −1 的反射矩阵场景。`make_transform` 会拒绝此类输入，但缺少自动化测试覆盖。
- **建议**：增加对反射矩阵的 monkeypatch 测试，验证 `calibrate_hand_eye` 拒绝 det = −1 的结果。

### 8. `run_m1.py` 的异常捕获范围可扩展

- **位置**：`scripts/run_m1.py:27–28`
- **说明**：当前仅捕获 `ValueError`、`TypeError`、`OSError`。`run_experiment` 重新抛出的 `RuntimeError` 等会以 traceback 形式暴露，虽不影响正确性，但友好的错误消息可覆盖更多异常类型。
- **建议**：扩展为 `except (ValueError, TypeError, OSError, RuntimeError) as exc`，或添加通用的 `except Exception as exc` 兜底分支并打印友好消息。

---

## 四、已验证正确的关键事项

| 审查项 | 结论 | 依据 |
|--------|------|------|
| **坐标方向与真值隔离** | ✓ 正确 | `T_A_B` 严格为 B→A；`Q = inv(GX)Y` 与文档一致；OpenCV 参数映射 `R_gripper2base = T_B_G`、`R_target2cam = T_C_T`、`R_cam2gripper = T_G_C` 完全正确；`calibrate_hand_eye` 不接收真值，真值仅用于生成和事后 `pose_error` |
| **退化与数值** | ✓ 基本正确，见缺陷 #1/#3 | 1e-3 阈值已在文档中明确为"数值防线"；`Rotation.magnitude()` 避免近零/近 π 的精度损失；测试覆盖已知角度和边界值 |
| **噪声模型** | ✓ 正确 | 左乘 `Exp(δθ)R` 和独立平移相加，σ 为每分量标准差；同 `noise_seed` 共用标准正态样本再缩放；`N` 前缀（截断前缀）实现正确，测试已验证 |
| **关卡与失败** | ✓ 正确 | 基线任何一次失败即停止后续实验；求解失败保留行、误差留空、不按 0 处理；测试通过故障注入验证 |
| **统计/绘图** | ✓ 正确 | 样本标准差 `ddof=1`；统计仅针对成功样本；未将共用种子、重复零噪声或重跑当作额外独立样本；图表由实际 CSV 生成 |
| **实验简化声明** | ✓ 充分 | 文档和报告中多次明确：理想位姿观测 ≠ 真实图像测量；未模拟视野、检测、遮挡、运动约束或系统误差 |
| **复现/保留** | ✓ 正确 | CLI 拒绝覆盖（`exist_ok=False`）；输出目录限制在项目内；两次独立运行逐字节一致；840 次重放验证通过；未覆盖旧文献或申报书 |
| **测试执行** | ✓ 通过 | 本次审查实际执行 124 项测试，全部通过；快速独立实验 60 次求解通过 |

---

## 五、未验证部分

- **跨版本数值一致性**：未在多个 OpenCV/BLAS 版本下验证逐位一致性（开发报告已声明未承诺此项）。
- **极端噪声稳定性**：未验证噪声水平远超当前配置（如 >5° 或 >10 mm）时的求解失败率和数值行为。
- **多真值泛化**：未在多个 `T_G_C` 真值下进行完整实验，仅在单元测试中覆盖。
- **形式化证明**：本次审查不涉及可辨识性证明、全局精度界或方法创新审定（审查请求本身不要求）。

---

## 六、总结

M1 V0.1 的核心数学、坐标映射、真值隔离、噪声模型和实验流程是**正确且可复现的**。 pytest 124 项全部通过，独立快速实验成功，复算报告完整。

发现的 **2 个已确认缺陷** 均属于**代码鲁棒性和错误处理细节**，而非数学或算法层面的根本性错误：

1. `motion_diagnostics` 在极端退化场景下通过 NumPy 内部错误崩溃，而非返回预期的退化标志。
2. `experiments.py` 的异常捕获过宽，可能将程序性错误（如 `NameError`）归类为求解失败。

建议优先修复缺陷 #1（涉及测试稳定性），再修复缺陷 #2（涉及调试体验）。其余待查问题和非阻断建议在后续迭代中按需处理即可。
