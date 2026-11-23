# 手眼标定文献初步调研（6 篇）

检索日期：2026-11-18。性质：面向项目起步的定向调研，不是系统性综述，也不宣称覆盖全部研究。
已联网阅读下列论文的原始摘要或指定全文章节，并检查部分作者代码仓库。没有运行外部代码，没有复现论文数值结果。细节见 [检索与核验记录](literature_search_log.md)。作者方法的效果不能记为本项目成果。

## 1. Tsai–Lenz：经典分离式手眼标定

Tsai, R. Y., & Lenz, R. K. (1989). *A new technique for fully autonomous and efficient 3D robotics hand/eye calibration*. IEEE Transactions on Robotics and Automation, 5(3), 345–358.

- 来源：[论文全文（高校托管）](https://kmlee.gatech.edu/me6406/handeye.pdf)；[DOI: 10.1109/70.34770](https://doi.org/10.1109/70.34770)。
- 问题与方法：由相对运动约束估计末端相机外参，采用先旋转、后平移的求解思路。
- 条件：论文报告仿真与 IBM 机器人上的相机实验。本次读到摘要、建模及实验设置段落，未全面核对结果表。
- 项目价值：学习 AX=XB、运动激励和基础闭环，作为后续 OpenCV 基线的原理来源。
- 代码状态：没有核实该年代原作者代码；OpenCV 的同名方法是后来的实现，不能称为原作者发布代码。

## 2. Daniilidis：双四元数联合求解

Daniilidis, K. (1999). *Hand-eye calibration using dual quaternions*. The International Journal of Robotics Research, 18(3).

- 来源：[出版社页面与摘要](https://journals.sagepub.com/doi/10.1177/02783649922066213)；DOI：10.1177/02783649922066213。
- 问题与方法：统一处理旋转和平移，用双四元数表示螺旋运动，并用 SVD 构造联合解。
- 条件：摘要描述合成实验、立体重建和相机定位验证；具体样本数与设备参数未核对。
- 项目价值：作为分离式方法的比较对象，提醒两类噪声可能耦合；不推断其在本项目必然更好。
- 阅读/代码状态：只核对出版社摘要与元数据；作者高校 PDF 请求超时。未核实原作者代码，未付费获取正文。

## 3. Enebuse 等：算法精度评价与噪声条件

Enebuse, I., Ibrahim, B. K. S. M. K., Foo, M., Matharu, R. S., & Ahmed, H. (2022). *Accuracy evaluation of hand-eye calibration techniques for vision-guided robots*. PLOS ONE, 17(10), e0273261.

- 来源：[开放全文](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0273261)；[DOI](https://doi.org/10.1371/journal.pone.0273261)。
- 问题与方法：比较六种方法在噪声和运动范围变化时的表现。
- 条件：仿真及 UR5e、Azure Kinect 实验；文中实机部分为 100 次不同运动，缺少绝对真值时使用相对误差。
- 项目价值：参考噪声、样本量与运动跨度实验；区分相对一致性与真值准确度，不把特定条件下的排名普遍化。
- 状态：阅读摘要、数据声明与实机评价章节；[论文链接的代码/数据仓库](https://github.com/ienebuse/hand-eye-calibration) 未下载或运行，复现语言和依赖仍待检查。

## 4. Yang 等：主动选择下一最佳视角

Yang, J., Rebello, J., & Waslander, S. L. (2023). *Next-best-view selection for robot eye-in-hand calibration*. arXiv:2303.06766.

- 来源：[元数据与摘要](https://arxiv.org/abs/2303.06766)、[全文](https://arxiv.org/pdf/2303.06766)。本记录按预印本标识引用，未填写未经核验的会议 DOI。
- 问题与方法：以非线性优化和参数不确定性估计为基础，用信息增益选择下一机器人位姿；正文采用 AX=YB 建模。
- 条件：仿真及 EPSON C4L 六轴机器人、Ensenso N35 相机、4×4 对称圆点板；对比随机与最大距离选择。
- 项目价值：直接关联主动采样；简单旋转轴覆盖只是可比较的代理，不能称为等价信息增益。
- 状态：阅读摘要、建模和实验设置章节；本次未核实作者代码仓库，不能写成已有代码可直接复现。

## 5. RegHEC：公开点云代码的替代路线

Xing, S., Jing, F., & Tan, M. (2023). *RegHEC: Hand-eye calibration via simultaneous multi-view point clouds registration of arbitrary object*. arXiv:2304.14092.

- 来源：[预印本](https://arxiv.org/abs/2304.14092)、[作者仓库](https://github.com/Shiyu-Xing/RegHEC)。未补写期刊 DOI。
- 问题与方法：联合配准多视点点云与求手眼关系；贝叶斯优化粗对齐后接加速 ICP。
- 条件：摘要及仓库介绍真实机器人、多种物体、点云和配对末端位姿；仓库包含示例数据及 C++ 实现。
- 项目价值：参考数据配对、真值/配准评价边界；依赖三维点云，与当前单目平面板主线不同，不作为第一阶段必做项。
- 状态：只读摘要和仓库 README；未编译、未验证其精度或 Windows 兼容性。

## 6. EasyHeC：自动标定与空间探索

Chen, L., Qin, Y., Zhou, X., & Su, H. (2023). *EasyHeC: Accurate and automatic hand-eye calibration via differentiable rendering and space exploration*. arXiv:2305.01191.

- 来源：[预印本](https://arxiv.org/abs/2305.01191)、[作者仓库](https://github.com/ootts/EasyHeC)。仓库标注 RA-L 2023；此处保留已核对的预印本标识，未猜测正式 DOI。
- 问题与方法：通过可微渲染优化相机位姿，结合一致性驱动的关节空间探索，实现无标记自动标定。
- 条件：摘要报告合成和真实数据；原仓库列有 Ubuntu、NVIDIA GPU 和 PyTorch 等要求。
- 项目价值：参考闭环自动选择观测的思想；条件和复杂度超出当前五依赖的基础环境。
- 状态：只读摘要与仓库 README，未安装深度学习或仿真组件，也未声称论文已复现。

## 本项目的阅读顺序与证据边界

先读 Tsai–Lenz 的坐标建模，再看 Enebuse 的实验评价和 Yang 的主动采样。双四元数属于进阶求解，RegHEC 与 EasyHeC 用于拓宽方法地图。后两项均有可定位的作者代码，但“有代码”不等于“本项目 Windows 环境可直接运行”。

这里的项目参考价值是针对当前路线的分析判断，不是原作者对本项目的结论。六篇文献均不作为项目已实现创新或达到精度的证据。原有 `文献/` 中的七份 PDF 本轮仅做文件清点，没有逐篇精读，不计入这六篇联网调研。
