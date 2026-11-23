# 源代码入口

当前可复用包位于 handeye/，方向与数据契约见 ../docs/PROJECT_SPEC.md。

| 模块 | 职责 |
| --- | --- |
| transforms、metrics | 刚体变换及旋转/平移误差 |
| simulation、calibration | 理想数据、噪声、退化检查与OpenCV适配 |
| experiments、plotting | M1实验与图表 |
| evaluation、sampling | 独立留出评价与三种离线选择策略 |
| m2_experiments、m2_plotting、m2_verification | M2协议、落盘、统计和重放 |
| camera | 针孔投影、可见性和训练估计接口 |
| projection_experiment、projection_verification | W2几何实验及核验 |

运行入口在 ../scripts/，测试在 ../tests/。目前没有PnP、真实角点检测或机器人控制。
