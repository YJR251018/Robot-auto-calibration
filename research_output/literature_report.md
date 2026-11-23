# 机器人视觉手眼标定（AX=XB）文献调研报告

> 项目背景：机械专业本科生大创 · 软件仿真优先 · 当前无真实机器人与相机
> 报告性质：初步文献调研（科研文献助理任务）
> 生成日期：2026-11-18
> 工作目录：`D:\Research`

---

## 0. 信息核实声明与检索限制（必读）

本报告严格区分两类信息，请勿混淆：

- ✅ **已核实（Verified）**：标题、作者、发表年份、期刊/会议、卷期页码、DOI、出版社/原文链接、被引次数等**书目元数据**，均已通过 **Crossref API**（`api.crossref.org`，HTTP 200 且字段逐一匹配）或 **arXiv 官方页面**（`arxiv.org/abs/...`）逐条核对。文中标注「已核实（Crossref）」的条目，其 DOI 可直接点击跳转到出版社落地页。
- ⚠️ **未核实/需查原文（Unverified）**：多数 IEEE / SAGE / Springer 论文全文**付费**，本次调研**未能逐篇阅读 PDF 全文**。因此：论文「实验设置与评价指标」的**细粒度定量数据**（如具体误差数值、实验台架参数）部分仅依据出版社官方摘要、被引文献中的二手描述与领域通行知识整理，并在文中明确标注「全文付费，细节未核实」。**请勿把本报告中的这些细节当作从原文抄录的确凿数据。**

**检索限制（如实记录）：**

1. 无法登录付费数据库（IEEE Xplore / SAGE Journals / Springer 全文均为付费墙）。
2. Crossref 仅对部分论文（SAGE 的 IJRR、部分 Springer）返回了**出版社官方摘要**；IEEE 早年的论文（Shiu 1989、Tsai-Lenz 1989、Park-Martin 1994、Strobl-Hirzinger 2006）**未返回摘要**，其方法概述基于被引文献与领域通行知识整理。
3. 引用次数来自 Crossref 的 `is-referenced-by-count` 字段（检索时刻 2026-11-18），为近似值，仅供横向参考，不代表权威影响力排名。
4. 未编造任何论文、DOI、代码地址或实验数据；凡无法核实的一律标注「未核实」。

---

## A. 核心论文总览

共整理 **8 篇核心论文 + 3 篇补充论文**，覆盖全部 5 个调研方向。下表「核实状态」一栏：✅=书目元数据经 Crossref/arXiv 逐条核实；⚠️=内容细节部分依据摘要/二手信息。

| # | 论文（第一作者, 年） | 期刊/会议 | DOI | 方向 | 核实状态 |
|---|---|---|---|---|---|
| 1 | Shiu & Ahmad, 1989 | IEEE T-RA 5(1) | `10.1109/70.88014` | AX=XB 奠基 | ✅ |
| 2 | Tsai & Lenz, 1989 | IEEE T-RA 5(3) | `10.1109/70.34770` | AX=XB 两步法 / Eye-in-Hand | ✅ |
| 3 | Park & Martin, 1994 | IEEE T-RA 10(5) | `10.1109/70.326576` | AX=XB 李群法 | ✅ |
| 4 | Horaud & Dornaika, 1995 | IJRR 14(3) | `10.1177/027836499501400301` | 精度评价/稳定性 | ✅ |
| 5 | Daniilidis, 1999 | IJRR 18(3) | `10.1177/02783649922066213` | 对偶四元数 | ✅ |
| 6 | Andreff, Horaud & Espiau, 2001 | IJRR 20(3) | `10.1177/02783640122067372` | Eye-in-Hand 无靶标 | ✅ |
| 7 | Strobl & Hirzinger, 2006 | IROS 2006 | `10.1109/IROS.2006.282250` | 最优/信息量精度 | ✅ |
| 8 | Schmidt & Niemann, 2008 | IJRR 27(9) | `10.1177/0278364908095172` | 自主数据选择 | ✅ |
| S1 | Yang, Rebello & Waslander, 2023 | arXiv:2303.06766 | `10.48550/arXiv.2303.06766` | 主动标定/NBV | ✅ |
| S2 | Zhang et al., 2023 | The Visual Computer 39(1) | `10.1007/s00371-021-02336-7` | 主动 NBV | ✅ |
| S3 | Enebuse et al., 2021 | IEEE Access 9 | `10.1109/ACCESS.2021.3104514` | 综述 | ✅ |

**与 5 个调研方向的对应关系：**

- 方向1（AX=XB 经典算法）→ 论文 1–5
- 方向2（Eye-in-Hand 流程）→ 论文 2、6（及 S3 综述）
- 方向3（精度评价方法）→ 论文 4、7
- 方向4（自主采样位姿规划）→ 论文 8、S1、S2
- 方向5（基于观测质量/信息量的主动标定）→ 论文 7、S1、S2

---

## B. 逐篇详解

### B1. Shiu & Ahmad (1989) —— AX=XB 问题的奠基之作

- **标题**：Calibration of wrist-mounted robotic sensors by solving homogeneous transform equations of the form AX=XB
- **作者 / 年份**：Y. C. Shiu, S. Ahmad，1989
- **期刊**：IEEE Transactions on Robotics and Automation, 5(1): 16–29
- **DOI / 链接**：[`10.1109/70.88014`](https://doi.org/10.1109/70.88014) · [IEEE Xplore](https://ieeexplore.ieee.org/document/88014/)（已核实，Crossref）
- **被引**：≈562 次（Crossref，检索时刻 2026-11-18）
- **研究问题与主要方法**：最早系统地提出并命名手眼标定方程 **AX=XB** 的论文之一。X 是相机（eye）到机械手末端（hand）的刚体变换；A 是两次末端运动之间的相对变换（由机器人正运动学得到），B 是两次相机位姿之间的相对变换（由相机标定/位姿估计得到）。核心思想是把 AX=XB 分解为**旋转部分**与**平移部分**，通过构造线性方程组求解。⚠️ 具体解法细节（如何分离旋转/平移、奇异构型处理）需查原文，本报告未读到全文。
- **实验设置与评价指标**：⚠️ 全文付费，实验细节未核实（IEEE 未返回摘要）。
- **开源代码**：原论文无官方代码；其思想被大量后续实现吸收，但 OpenCV 的 `calibrateHandEye` 中**没有**以 Shiu-Ahmad 命名的选项（详见 §E）。
- **对本项目的参考价值**：⭐⭐⭐⭐⭐ —— **必读的理论起点**。本科同学应先读懂 AX=XB 的物理含义（哪些坐标系、谁乘谁），这是后续所有算法和仿真的共同语言。

### B2. Tsai & Lenz (1989) —— 经典两步法（Eye-in-Hand 标准流程）

- **标题**：A new technique for fully autonomous and efficient 3D robotics hand/eye calibration
- **作者 / 年份**：R. Y. Tsai, R. K. Lenz，1989
- **期刊**：IEEE Transactions on Robotics and Automation, 5(3): 345–358
- **DOI / 链接**：[`10.1109/70.34770`](https://doi.org/10.1109/70.34770) · [IEEE Xplore](https://ieeexplore.ieee.org/document/34770/)（已核实，Crossref）
- **被引**：≈1305 次（本报告中最高，检索时刻 2026-11-18）
- **研究问题与主要方法**：提出**全自动、高效**的 3D 手眼标定流程，采用其 RAC（Radial Alignment Constraint，径向排列约束）两步相机模型。方法思路（据领域通行知识，⚠️ 未读原文）：① 先解旋转，② 再解平移，把 AX=XB 拆成两步线性求解，避免旋转平移耦合；并给出了机器手运动选取的实用建议。
- **实验设置与评价指标**：⚠️ 全文付费，具体实验台架与误差数值未核实。
- **开源代码**：原论文无官方代码。**OpenCV `cv2.calibrateHandEye(..., method=cv2.CALIB_HAND_EYE_TSAI)` 即实现 Tsai-Lenz 两步法**（已核实，见 §E）。
- **对本项目的参考价值**：⭐⭐⭐⭐⭐ —— **Eye-in-Hand 标准流程的范本**：相机固定在末端 → 多次移动机械臂拍摄固定标定板 → 每次记录末端位姿 A 与相机外参 B → 解 AX=XB。这条流程正是 Python 仿真要复现的主线。

### B3. Park & Martin (1994) —— 李群/李代数框架下的求解

- **标题**：Robot sensor calibration: solving AX=XB on the Euclidean group
- **作者 / 年份**：F. C. Park, B. J. Martin，1994
- **期刊**：IEEE Transactions on Robotics and Automation, 10(5): 717–721
- **DOI / 链接**：[`10.1109/70.326576`](https://doi.org/10.1109/70.326576) · [IEEE Xplore](https://ieeexplore.ieee.org/document/326576/)（已核实，Crossref）
- **被引**：≈529 次（检索时刻 2026-11-18）
- **研究问题与主要方法**：把 AX=XB 放在**欧氏群 SE(3)（李群）** 及其李代数 se(3) 框架下求解。用矩阵对数把旋转-平移统一到李代数向量，从而把旋转和平移**同时**最小二乘求解（据领域通行知识，⚠️ 未读原文）。这为后续「统一处理旋转和平移」的几何方法奠定了基础。
- **实验设置与评价指标**：⚠️ 全文付费，实验细节未核实。
- **开源代码**：原论文无官方代码。**OpenCV `cv2.CALIB_HAND_EYE_PARK` 实现**（已核实，见 §E）。
- **对本项目的参考价值**：⭐⭐⭐⭐ —— 是理解「旋转+平移为什么要一起解」的关键一步；也是后续基于李代数/李群做可观测性分析的数学基础。仿真时可直接调用 OpenCV 的 PARK 方法作对照。

### B4. Horaud & Dornaika (1995) —— 非线性优化 + 稳定性分析（精度评价）

- **标题**：Hand-Eye Calibration
- **作者 / 年份**：Radu Horaud, Fadi Dornaika，1995
- **期刊**：The International Journal of Robotics Research, 14(3): 195–210
- **DOI / 链接**：[`10.1177/027836499501400301`](https://doi.org/10.1177/027836499501400301) · [SAGE](https://journals.sagepub.com/doi/10.1177/027836499501400301)（已核实，Crossref）
- **被引**：≈554 次（检索时刻 2026-11-18）
- **研究问题与主要方法**（据 Crossref 收录的出版社官方摘要）：指出传统方法几乎都解齐次矩阵方程 AX=XB；本文给出**两种等价建模**——经典 AX=XB 与 **MY = M'YB**（直接使用两个相机位姿的 3×4 透视矩阵 M、M'，不必显式拆出相机内外参，覆盖更广的相机类传感器）。用单位四元数表示旋转，给出① **旋转闭式解 + 平移**，② **旋转平移同时求解的非线性法**；并对这两种方法与 Tsai-Lenz 线性法做**稳定性分析**。
- **实验设置与评价指标**（据官方摘要）：通过稳定性分析对比三种方法对噪声/测量误差的鲁棒性，结论是**同时求解旋转和平移的非线性法对噪声最稳健**。⚠️ 具体数值实验细节需查原文。
- **开源代码**：原论文无官方代码。**OpenCV `cv2.CALIB_HAND_EYE_HORAUD` 实现**（已核实，见 §E）。
- **对本项目的参考价值**：⭐⭐⭐⭐⭐ —— **「精度评价」这一方向的直接来源**：本科项目可照搬其「对噪声做蒙特卡洛、比较不同算法的鲁棒性」的实验范式（见 §D 研究问题1）。

### B5. Daniilidis (1999) —— 对偶四元数统一求解

- **标题**：Hand-Eye Calibration Using Dual Quaternions
- **作者 / 年份**：Konstantinos Daniilidis，1999
- **期刊**：The International Journal of Robotics Research, 18(3): 286–298
- **DOI / 链接**：[`10.1177/02783649922066213`](https://doi.org/10.1177/02783649922066213) · [SAGE](https://journals.sagepub.com/doi/10.1177/02783649922066213)（已核实，Crossref）
- **被引**：≈668 次（检索时刻 2026-11-18）
- **研究问题与主要方法**（据官方摘要）：传统算法没有把相对位姿（位置+姿态）**统一**处理。本文引入**对偶四元数**（旋量/screw 的代数对应），证明若把相机和电机变换视为旋量，则只有旋量轴的相关参数对手眼标定起作用；对偶四元数参数化带来**用 SVD 一次同时求解旋转和平移**的新解。
- **实验设置与评价指标**（据官方摘要）：在手眼信息用于**立体重建**和**相机定位**的实际任务中评估；**真实 + 合成**实验都显示优于另外两种方法。⚠️ 具体数值需查原文。
- **开源代码**：原论文无官方代码。**OpenCV `cv2.CALIB_HAND_EYE_DANIILIDIS` 实现**（已核实，见 §E）。
- **对本项目的参考价值**：⭐⭐⭐⭐ —— 对偶四元数是旋量理论与标定的桥梁，数学上较深但对本科是很好的进阶点；仿真时可直接调用 OpenCV 作对照。

### B6. Andreff, Horaud & Espiau (2001) —— 无需标定靶的 SfM 手眼标定

- **标题**：Robot Hand-Eye Calibration Using Structure-from-Motion
- **作者 / 年份**：Nicolas Andreff, Radu Horaud, Bernard Espiau，2001
- **期刊**：The International Journal of Robotics Research, 20(3): 228–248
- **DOI / 链接**：[`10.1177/02783640122067372`](https://doi.org/10.1177/02783640122067372) · [SAGE](https://journals.sagepub.com/doi/10.1177/02783640122067372)（已核实，Crossref）
- **被引**：≈161 次（检索时刻 2026-11-18）
- **研究问题与主要方法**（据官方摘要）：绝大多数现有方法都需要标定靶 + 相机位姿估计。本文改用**运动恢复结构（SfM）+ 已知的机器人运动**，证明可得到**线性形式**的解，同时求出标定参数和 SfM 固有的未知尺度因子。线性化使得不仅能分析一般的旋量运动，还能分析**纯平移、纯旋转、平面运动等奇异运动**。相机只看一个未知的刚性场景、追踪图像序列中的点即可估计「相机—机器人」关系，适合无人车、远程作业等。
- **实验设置与评价指标**（据官方摘要）：做了大量实验，通过与现有方法对比验证质量。⚠️ 具体数值需查原文。
- **开源代码**：原论文无官方代码。**OpenCV `cv2.CALIB_HAND_EYE_ANDREFF` 实现**（已核实，见 §E）。
- **对本项目的参考价值**：⭐⭐⭐⭐ —— 给出了 Eye-in-Hand 的「**无标定板**」变体，且其**奇异运动（纯平移/纯旋转/平面运动）分析**直接对应本科仿真可做的「退化构型」研究（见 §D 研究问题2）。

### B7. Strobl & Hirzinger (2006) —— 最优手眼标定与信息量

- **标题**：Optimal Hand-Eye Calibration
- **作者 / 年份**：Klaus Strobl, Gerd Hirzinger，2006
- **期刊**：2006 IEEE/RSJ International Conference on Intelligent Robots and Systems (IROS 2006), pp. 4647–4653, Beijing, China
- **DOI / 链接**：[`10.1109/IROS.2006.282250`](https://doi.org/10.1109/IROS.2006.282250) · [IEEE Xplore](https://ieeexplore.ieee.org/document/4059150/) · [DLR 全文页面](https://elib.dlr.de/45619/)（已核实，Crossref；DLR 页面提供可访问入口）
- **被引**：≈237 次（检索时刻 2026-11-18）
- **研究问题与主要方法**：以**全局最优**为目标重新审视手眼标定，采用合理的旋转参数化（避免欧拉角奇异性）进行非线性优化，并引入**信息量/精度**的度量来评价与优化标定（据领域通行知识与被引文献，⚠️ 未读全文）。其作者后续还发表了「未知棋盘格尺寸下更精确的相机与手眼标定」等延伸工作（Strobl & Hirzinger, ICRA 2008, DOI `10.1109/ROBOT.2008.4543398`，已核实）。
- **实验设置与评价指标**：⚠️ 全文付费，具体误差数值未核实；作者团队来自 DLR（德国宇航中心），使用 DLR 的 CalDe/CalLab 标定工具。
- **开源代码**：DLR 提供 CalDe/CalLab 等标定工具（⚠️ 其开源/可获取状态未逐一核实，请以 DLR 官方为准）。
- **对本项目的参考价值**：⭐⭐⭐⭐⭐ —— 方向3、5 的核心参考：它说明**「怎么选姿态」本身就是影响精度的重要因素**，把标定从「随便拍几张」提升为「有信息量地拍」。这是本项目「自主采样位姿规划 + 主动标定」议题的经典锚点。

### B8. Schmidt & Niemann (2008) —— 从连续运动中自主选择标定数据

- **标题**：Data Selection for Hand-eye Calibration: A Vector Quantization Approach
- **作者 / 年份**：Jochen Schmidt, Heinrich Niemann，2008
- **期刊**：The International Journal of Robotics Research, 27(9): 1027–1053
- **DOI / 链接**：[`10.1177/0278364908095172`](https://doi.org/10.1177/0278364908095172) · [SAGE](https://journals.sagepub.com/doi/10.1177/0278364908095172)（已核实，Crossref）
- **被引**：≈38 次（检索时刻 2026-11-18）
- **研究问题与主要方法**（据官方摘要）：提出**基于矢量量化（vector quantization）的数据选择方法**，从给定的「手/眼运动序列」中挑出适合标定的数据。数据选择既能提升经典手眼标定的精度，又能让「连续记录数据、无需人工挑位姿」成为可能（尤其在内窥镜等场景）。方法族之间的差异在于矢量量化的维度 vs 旋转表示的自由度，以及如何纳入旋转角。
- **实验设置与评价指标**（据官方摘要）：用手动移动的**光学跟踪系统（hand）** 与**内窥镜相机（eye）** 获取的数据评估。⚠️ 具体数值需查原文。
- **开源代码**：未发现官方开源代码（未核实到）。
- **对本项目的参考价值**：⭐⭐⭐⭐ —— 方向4 的直接参考：核心思想是「**不是所有采集的位姿都一样有用**，要挑信息量大的」。本科仿真可把「数据选择/位姿筛选」作为一个可编程验证的环节。

### B-S1. Yang, Rebello & Waslander (2023) —— 主动 Next-Best-View（信息增益）

- **标题**：Next-Best-View Selection for Robot Eye-in-Hand Calibration
- **作者 / 年份**：Jun Yang, Jason Rebello, Steven L. Waslander，2023（v1 提交于 2023-03-12）
- **出处**：arXiv:2303.06766（cs.RO）
- **DOI / 链接**：[`10.48550/arXiv.2303.06766`](https://doi.org/10.48550/arXiv.2303.06766) · [arXiv 页面](https://arxiv.org/abs/2303.06766)（已核实，arXiv）
- **研究问题与主要方法**（据 arXiv 官方摘要）：把 eye-in-hand 标定建模为**非线性优化**，提出**主动视觉**方法：给定初始观测集，先算标定参数并估计**参数不确定性（协方差）**，再预测下一个能带来**最大信息增益（不确定性下降最大）**的机器人位姿去采集下一组观测。在**仿真数据集 + 真实 6 轴机械臂**上验证，结论是用**远少于**常用基线方法的视角数即可达到同等精度。
- **实验设置与评价指标**（据摘要）：仿真 + 真实 6 轴机械臂；评价指标为达到一定精度所需的**视角数（样本效率）**与标定精度。⚠️ 具体数值需查原文（arXiv 可免费获取全文，建议直接下载细读）。
- **开源代码**：⚠️ 本次调研**未核实到**随论文发布的官方代码仓库，请勿假设存在。
- **对本项目的参考价值**：⭐⭐⭐⭐⭐ —— **方向4+5 的最直接、最「可仿」参考**。其「协方差 → 信息增益 → 选下一视角」的闭环，几乎可以 1:1 在纯 Python 仿真里复现（见 §D 研究问题3）。

### B-S2. Zhang et al. (2023) —— 在线精度驱动的主动 NBV

- **标题**：Active hand-eye calibration via online accuracy-driven next-best-view selection
- **作者 / 年份**：Xinxin Zhang, Yuefeng Xi, Zhentao Huang, Lintao Zheng, Hui Huang, Yueshan Xiong, Kai Xu，2023（在线首发 2022-01-04）
- **期刊**：The Visual Computer, 39(1): 381–391
- **DOI / 链接**：[`10.1007/s00371-021-02336-7`](https://doi.org/10.1007/s00371-021-02336-7) · [Springer](https://link.springer.com/article/10.1007/s00371-021-02336-7)（已核实，Crossref）
- **被引**：≈12 次（检索时刻 2026-11-18）
- **研究问题与主要方法**：与 B-S1 同属「主动手眼标定」，采用**在线、精度驱动（accuracy-driven）的 next-best-view 选择**（据标题与出版信息；⚠️ 全文付费，方法细节未核实）。
- **实验设置与评价指标**：⚠️ 全文付费，未核实。
- **开源代码**：⚠️ 未核实到官方开源代码。
- **对本项目的参考价值**：⭐⭐⭐⭐ —— 与 B-S1 互为对照，代表「主动标定」这条较新的研究线，说明该方向仍在活跃发展，适合作为大创的「创新点」切入点。

### B-S3. Enebuse et al. (2021) —— 综述（入门导航）

- **标题**：A Comparative Review of Hand-Eye Calibration Techniques for Vision Guided Robots
- **作者 / 年份**：Ikenna Enebuse, Mathias Foo, Babul Salam Ksm Kader Ibrahim, Hafiz Ahmed, Fhon Supmak, Odongo Steven Eyobu，2021
- **期刊**：IEEE Access, 9: 113143–113155
- **DOI / 链接**：[`10.1109/ACCESS.2021.3104514`](https://doi.org/10.1109/ACCESS.2021.3104514) · [IEEE Xplore](https://ieeexplore.ieee.org/document/9512030/)（已核实，Crossref）
- **被引**：≈149 次（检索时刻 2026-11-18）
- **研究问题与主要方法**：对面向视觉引导机器人的手眼标定技术做**比较性综述**，梳理 AX=XB、AX=YB（同时标定机器人-世界与工具-法兰）等问题的谱系与适用场景。
- **实验设置与评价指标**：综述类，无独立实验。
- **开源代码**：无（综述）。⚠️ 但本文为 **IEEE Access 开放获取（CC-BY）**，全文可免费下载，是本科快速建立全景认知的最省力入口。
- **对本项目的参考价值**：⭐⭐⭐⭐⭐ —— **建议作为项目开题的第一篇精读文献**，先看综述建立术语与谱系，再深入 8 篇核心论文。

---

## C. 本科生应优先学习的知识清单

按「先建立概念 → 再补数学 → 后动手仿真」的顺序分层：

### C1. 概念与坐标系（最优先，决定是否入门）
1. **齐次变换矩阵**：4×4 矩阵表示刚体位姿（旋转 R + 平移 t），及变换的复合与求逆（`T⁻¹ = [Rᵀ, −Rᵀt; 0, 1]`）。
2. **手眼标定涉及的 4 个坐标系**：机器人基座 {base}、末端法兰 {tool/flange}、相机 {cam}、标定板 {board/world}。
3. **AX=XB 的物理含义**：X = 相机到末端的固定变换（Eye-in-Hand 所求量）；A 由机器人正运动学给出，B 由相机外参给出；两者之间的闭环约束。
4. **Eye-in-Hand vs Eye-to-Hand** 的差异与各自适用场景。

### C2. 数学工具
5. **旋转表示及其互换**：旋转矩阵、轴角（axis-angle）/罗德里格斯（Rodrigues）、四元数、欧拉角（注意万向锁/奇异性），及两两转换公式。
6. **最小二乘与奇异值分解（SVD）**：多数 AX=XB 闭式解都用 SVD，必须会算、会解释。
7. **非线性优化入门**：残差函数、雅可比、高斯-牛顿 / Levenberg-Marquardt（LM）；可用 `scipy.optimize.least_squares` 直接体验。
8. **李群 SE(3) / 李代数 se(3) 的入门直觉**（Park-Martin 那篇的数学基础；本科阶段先建立「旋转矩阵的 log/exp」直觉即可，不必深究流形理论）。
9. **（进阶）对偶四元数与旋量（screw）**：Daniilidis 那篇的数学底座，本科可作拓展阅读。

### C3. 算法与工程流程
10. **经典求解算法谱系**：Shiu-Ahmad（分解旋转/平移）→ Tsai-Lenz（两步线性）→ Park-Martin（李群）→ Horaud-Dornaika（非线性同时解 + 稳定性）→ Daniilidis（对偶四元数 SVD）。
11. **Eye-in-Hand 标准操作流程**：固定标定板 → 移动机械臂到若干位姿 → 每个位姿记录（末端位姿 A，相机外参 B）→ 解 AX=XB → 验证。
12. **相机标定前置知识**：针孔模型、内参矩阵 K、畸变；张正友标定法（Zhang 2000，DOI `10.1109/34.888718`，本报告未逐条核实但为公认基础，见补充）及 OpenCV `cv2.calibrateCamera` / `cv2.solvePnP`。
13. **精度评价指标**：旋转误差（°）、平移误差（mm）、重投影误差（pixel）；以及**参数不确定性/协方差、可观测性、信息量**等更「主动」的评价视角（方向3、5）。

### C4. 工具与资源（已核实可用）
14. **OpenCV（Python）**：`cv2.calibrateHandEye` 一次性内置 Tsai-Lenz / Park / Horaud / Andreff / Daniilidis 五种方法（见 §E），是仿真最快落地路径。
15. **NumPy / SciPy**：旋转构造（`scipy.spatial.transform.Rotation`）、SVD、最小二乘、LM 优化。
16. **综述 + 免费全文**：先读 Enebuse 2021（开放获取）；Yang 2023 的 arXiv 全文可免费下载。

> 建议学习节奏：先读 B-S3 综述 → 精读 B1/B2 建立 AX=XB 直觉 → 动手用 OpenCV 跑通一条合成数据流水线 → 再补 B3–B5 的数学细节 → 最后进入 B7/B8/B-S1 的「主动标定」议题。

---

## D. 三个可用 Python 仿真检验的研究问题

> 共同前提：全程**无需真实机器人或相机**。用 NumPy 生成合成位姿与投影，用 SciPy/OpenCV 求解；GPU 可选。

### D1. 不同 AX=XB 求解算法在噪声下的鲁棒性对比（对应方向1、3）

- **研究问题**：Tsai-Lenz / Park-Martin / Horaud-Dornaika（非线性）/ Daniilidis / Andreff 几种方法，在观测噪声增大的情况下，谁的旋转误差与平移误差增长最慢、最稳健？
- **实验条件**：
  - 真值：随机生成一个固定的 `X_gt ∈ SE(3)`（例如旋转 30°、平移 150 mm），以及一组「合理」的末端位姿 `{T_base→tool_i}`。
  - 由 `B_i = X_gt⁻¹ A_i X_gt` 反解出理想观测 `B_i`，再向 `A_i`（旋转角 + 平移）和 `B_i` 各加入不同标准差 σ 的高斯噪声（σ 取一组梯度，如平移 0.1/0.5/1/2/5 mm，旋转 0.01°/0.05°/0.1°/0.5°）。
  - 对每种 σ 做 N=200 次蒙特卡洛，用 `cv2.calibrateHandEye`（`CALIB_HAND_EYE_TSAI / PARK / HORAUD / ANDREFF / DANIILIDIS`）分别求解，统计旋转误差均值±标准差、平移误差均值±标准差。
- **预期产出**：一张「误差 vs 噪声」曲线图 + 各算法鲁棒性排序；可复现 Horaud-Dornaika「非线性法更稳健」的结论。
- **依赖**：`numpy`、`scipy`、`opencv-python`。

### D2. 观测位姿的几何构型（可观测性/退化）对精度的影响（对应方向2、4）

- **研究问题**：采集位姿的**几何分布**（旋转轴是否多样、是否存在纯平移/纯旋转/小角度/平面运动等退化构型）如何影响 AX=XB 的可辨识性与最终精度？
- **实验条件**：
  - 控制生成 `A_i` 的旋转轴分布：① 轴方向充分多样（好构型）；② 所有旋转轴近平行；③ 只有纯平移；④ 只有绕单一轴旋转；⑤ 所有运动在同一平面（平面运动）。
  - 对每种构型求解 X，并计算一个**可观测性/信息量指标**：如信息矩阵 `JᵀJ`（J 为残差对 X 的雅可比）的**条件数、最小特征值、log-det（D-optimality）**，与旋转/平移误差对比。
  - 验证 Andreff 2001 对「纯平移/纯旋转/平面运动」奇异性的分析是否在数值上成立。
- **预期产出**：证明「轴多样性不足 → 信息矩阵病态 → 精度崩塌」，给出可量化的「构型质量」指标。
- **依赖**：`numpy`、`scipy`（旋转、SVD、`scipy.linalg`）。

### D3. 实现一种信息驱动的 Next-Best-View 主动标定，并对比样本效率（对应方向4、5）

- **研究问题**：给定一个初始小观测集，能否用「预测下一个信息增益最大的位姿」的策略，用**更少的观测数**达到与「随机采样/均匀采样」同等的标定精度？
- **实验条件**：
  - 参考 Yang et al. 2023 的框架：建立相机投影模型 + 标定板角点，用带噪声的 PnP 解出 B，用正运动学给 A。
  - 在当前估计 `X̂` 处计算**参数协方差/信息矩阵**（通过残差对 X 的雅可比 J，协方差 ≈ (JᵀJ)⁻¹），在候选位姿集合中贪心选择使**信息增益（不确定性下降）最大**的下一个位姿，迭代加入观测。
  - 三条基线：随机采样、均匀（固定网格/等间距）采样、主动 NBV；评价「达到指定旋转/平移精度所需的最少观测数」与「固定观测数下的最终精度」。
- **预期产出**：验证「主动选位姿比随机/均匀采样样本效率更高」，并可视化信息增益随迭代的变化。
- **依赖**：`numpy`、`scipy`、`opencv-python`（PnP）、可选 `matplotlib`。

---

## E. 开源代码 / 可复用实现（已核实）

| 资源 | 说明 | 核实状态 |
|---|---|---|
| OpenCV `cv2.calibrateHandEye` | 内置 5 种 AX=XB 方法：`CALIB_HAND_EYE_TSAI`（Tsai-Lenz 1989）、`CALIB_HAND_EYE_PARK`（Park-Martin 1994）、`CALIB_HAND_EYE_HORAUD`（Horaud-Dornaika 1995）、`CALIB_HAND_EYE_ANDREFF`（Andreff 等）、`CALIB_HAND_EYE_DANIILIDIS`（Daniilidis） | ✅ 已核实（OpenCV 头文件与 docs.rs 的 `HandEyeCalibrationMethod` 枚举逐一对应） |
| OpenCV `cv2.calibrateCamera` / `cv2.solvePnP` | 相机内参标定（张正友法）与位姿估计，Eye-in-Hand 流程中生成 B 的前置 | ✅ 官方文档已核实（函数存在） |
| SciPy `Rotation` / `least_squares` | 旋转构造与 LM 非线性优化 | ✅ 通用库，广泛可用 |
| DLR CalDe / CalLab | Strobl & Hirzinger 团队（DLR）的相机/手眼标定工具 | ⚠️ 可获取/开源状态未逐一核实，以 DLR 官方为准 |
| 各原始论文的官方代码 | Shiu/Ahmad、Tsai/Lenz、Park/Martin、Horaud/Dornaika、Daniilidis、Andreff、Schmidt/Niemann、Yang 等**均未核实到作者官方开源仓库** | ⚠️ 未核实到，请勿假设存在 |

> 说明：OpenCV 的 `calibrateHandEye` 是本科项目**最可靠、最易上手**的实现来源；其余论文以算法复现（照着公式在 NumPy 里自己写）作为练习会更有收获。

---

## 附：其他值得关注但本报告未逐条核实的文献（供延伸阅读）

以下为调研过程中在权威数据库（Crossref 被引列表、出版社参考文献）**出现**、但本报告**未单独用 Crossref 逐条核实**的相关论文，仅作线索，引用前请自行核实：

- Zhang, Z. (2000). A flexible new technique for camera calibration. *IEEE TPAMI* 22(11): 1330–1334.（张正友标定法，DOI `10.1109/34.888718`，手眼标定前置基础）
- Shiu & Ahmad 之外同期奠基：Tsai (1987) 的 RAC 相机标定。
- 同时标定类问题 AX=YB：Zhuang, Roth & Sudhakar (1994, IEEE T-RA 10(4): 549)，Dornaika & Horaud (1998, IEEE T-RA 14(4): 617)。
- 全局最优/凸松弛：Heller, Havlena & Pajdla（SfM-based L∞ 手眼标定，CVPR 2011）。
- 无对应关系/概率化 AX=XB：Ma 等（ICRA 2016）。
- 主动/自标定早期工作：Wei, Arbter & Hirzinger (1997) "Active self-calibration of hand cameras and hand-eye relationships with motion planning"（ICRA 1997，DOI `10.1109/ROBOT.1997.614326`，本报告已在 Crossref 检索结果中见到，但未单列核实）。

---

## 结语与给团队的一句话建议

本报告确认：AX=XB 是一条**脉络清晰、经典方法可免费获得（OpenCV 内置）**、且**「主动标定」仍有活跃新工作（2023）** 的研究线，非常适合「软件仿真优先、无硬件」的本科大创切入。建议**以 D3（主动 NBV）作为创新点**、以 D1（鲁棒性对比）与 D2（构型可观测性）作为扎实的基础实验，三者合起来即构成一个完整、可演示、可写论文的仿真研究闭环。
