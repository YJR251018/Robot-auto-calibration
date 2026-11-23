# Claude Code 独立审查请求：M1 V0.1

请独立检查实现和运行证据，不沿用开发者“已通过”的结论。不要修改或覆盖 DeepSeek 的文献产物、既有数据、M1 原始输出或本文件。请把审查结论写入新的 `reviews/M1_independent_review.md`；若该文件存在，改用新文件名。修复前先报告可定位的问题及影响。

## 审查入口

- 任务：项目根目录 CONTINUE WORK.md。
- 开发报告：reports/M1_development_report.md。
- 学习文档：docs/learning_guide.md。
- 源码：src/handeye/{metrics,simulation,calibration,experiments,plotting}.py。
- CLI：scripts/run_m1.py、scripts/verify_m1.py；配置：configs/m1_v0_1.json。
- 测试：tests/test_m1.py 及已有 tests；日志 reports/M1_tests.txt、reports/M1_pytest.xml。
- 主实验 experiments/M1_v0_1/；独立重跑 experiments/M1_v0_1_reproduction/。
- 复算报告 reports/M1_reproducibility.json；源文件哈希 reports/M1_source_hashes.json。

## 优先审查

1. **坐标/真值隔离**：T_A_B 为 B→A；Q=inv(GX)Y。OpenCV 输入 G→B、T→C，输出 C→G；求解器是否确实未接收或替换真值，测试是否足以排除方向颠倒和固定输出。
2. **退化和数值**：运动诊断中的全帧对旋转轴、设计矩阵奇异值和 1e-3 比值阈值是否合理；最低样本量、非法观测、非有限输出、角误差近零/近π处理是否可靠。
3. **噪声模型**：左乘 SO(3) 扰动与独立平移相加、每分量标准差、单位转换、同种子配对和 N 前缀，是否与文档严格一致。
4. **关卡与失败**：任何基线不达阈值必须停止后续实验；噪声求解失败不能丢行或填零；异常捕获是否过宽、能否暴露程序性错误；状态/统计是否误导。
5. **统计/绘图**：逐次 CSV→汇总→PNG 是否一致，样本 SD 的 ddof=1 是否正确；只统计成功样本时是否明确条件性；不能把共用种子、重复零噪声条件或重跑当作额外独立样本。
6. **实验简化**：理想矩阵观测不保证板可见或机器人可达，机器人测量无噪声、无系统偏差；结论是否越界。
7. **复现/保留**：CLI 拒绝覆盖、项目内输出约束、保存数据可否重放；原有 transforms、测试、文献和申报书是否保留。

## 建议实际运行

```powershell
.\.venv\Scripts\python.exe -W error -m pytest -q --basetemp=.venv\M1-review-temp
.\.venv\Scripts\python.exe scripts\run_m1.py --config configs\m1_v0_1.json --output experiments\M1_claude_review
```

复算若需要，可运行 verify_m1.py，报告使用新名字以免覆盖已有记录。已有默认试验量为 840 次求解，不含硬件；不得为通过而放宽测试阈值。

请按严重性排序给出文件/行号、触发条件、实际风险、建议验证或修复方法，并区分已确认缺陷、待查问题和非阻断建议。若没有发现问题，也要说明检查范围与未验证部分；本请求不要求形式化证明或方法创新审定。
