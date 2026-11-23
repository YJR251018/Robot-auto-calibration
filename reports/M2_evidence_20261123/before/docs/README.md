# 今晚成果阅读入口

建议先看 [验收报告](../reports/tonight_report.md)，再按以下顺序学习：

1. [申报书背景与当前范围](project_context.md)：区分申报目标、当前条件和实际成果。
2. [坐标系约定](eye_in_hand_frames.md)：每个矩阵到底把哪个坐标系变到哪个坐标系。
3. [基础知识](handeye_basics.md)：旋转、刚体变换与 AX=XB 的来源。
4. [基础代码使用](transforms_usage.md)：照着已知例子运行并读测试。
5. [技术路线](technical_roadmap.md)：从基础库走向仿真和主动采样。
6. [第一阶段仿真实验方案](simulation_plan.md)：待执行的实验协议，不是实验结果。
7. [文献初步调研](literature_review.md) 与 [检索记录](literature_search_log.md)。
8. [未来研究假设](research_questions.md)：创新性与收益均待验证。

本轮未实现手眼求解器、仿真数据生成器、自动位姿规划、相机采集或 GUI。

在项目根目录运行，无须激活虚拟环境或安装额外软件：

```powershell
.\.venv\Scripts\python.exe examples\basic_transforms.py
.\.venv\Scripts\python.exe -m pytest -q
```

`src/handeye/` 是可复用模块，`examples/` 是教学示例，`tests/` 是验证代码。
当前通过 pytest.ini 为测试设置 src 导入路径，示例只给自己的进程添加 src；尚未制作可安装发行包。
