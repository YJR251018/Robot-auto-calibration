# 文献检索与核验记录

日期：2026-11-18，Asia/Shanghai。使用联网搜索及浏览工具，未使用付费 API、机构账号或上传申报书。查询只包含公开技术主题和论文题名。

## 预定范围

纳入：直接关联手眼建模、精度评价、位姿选择或自动标定；经典原始论文、作者预印本、原始研究及作者公开仓库。
不以年份淘汰经典论文；英文为主。排除只有二手介绍、无法确认身份或实验主张无法找到一手依据的材料。
允许以原始摘要形成初步记录，但逐项标注阅读范围；不能冒充全文精读或系统综述。

## 实际查询

围绕用户给定主题展开的实际关键词包括：

```text
Tsai Lenz 1989 A new technique for fully autonomous and efficient 3D robotics hand eye calibration 32699
Park Martin 1994 Robot sensor calibration solving AX XB Euclidean group
Daniilidis 1999 Hand eye calibration using dual quaternions
active hand eye calibration pose selection next best view open source github paper
"Robot sensor calibration" "10.1109" Park Martin
"Automatic Hand-Eye Calibration" robot pose selection open source
"Accuracy evaluation of hand-eye calibration techniques for vision-guided robots" authors 2022 plos
"Next-Best-View Selection for Robot Eye-in-Hand Calibration" github
"RegHEC" github
"Robot sensor calibration" "Park" site:edu pdf
"EasyHeC" github zju3dv
```

第一条末尾的 32699 只是检索时试用的数字，不是确认的 DOI。最终 Tsai DOI 已按实际来源记录为 10.1109/70.34770，不采用查询串猜 DOI。
检索服务没有提供可用于系统综述的完整去重总命中数，因此不报告虚构的筛选数量或 PRISMA 流程。

## 实际读取范围

| 编号 | 来源 | 核查到的内容 | 局限 |
| --- | --- | --- | --- |
| 1 Tsai–Lenz | 高校托管原论文 PDF | 题名、作者、1989 年、建模和实验设置段落 | 未逐表复核结果，未重现实验 |
| 2 Daniilidis | SAGE 出版社页 | 题名、作者、1999 年、DOI、摘要中的方法和实验类型 | 作者 PDF 请求超时；未购买全文 |
| 3 Enebuse | PLOS 原文 | 作者、2022 年、DOI、摘要、UR5e 实验、数据声明 | 未执行仓库代码 |
| 4 Yang | arXiv 页面及 PDF | 作者、2023 年、AX=YB、NBV、设备与对照 | 未核实代码，未核对全部结果 |
| 5 RegHEC | arXiv、作者 GitHub README | 作者、2023 年、配准方法、C++、示例数据说明 | 未读全部正文、未编译 |
| 6 EasyHeC | arXiv、作者 GitHub README | 作者、2023 年、方法、公开代码和原始环境要求 | 未安装、未复现，未核正式 DOI |

所有记录都能定位到一手摘要、原文或作者仓库。元数据核查不等于全面的方法有效性审查；没有进行完整的撤稿、利益冲突或版本历史审计。

## 访问问题与处理

- PMC 的 Enebuse 页面触发验证码，转而读取公开的 PLOS 原出版社页面；没有绕过验证码。
- Daniilidis 的作者高校 PDF 请求超时，保留出版社摘要级记录，不绕过付费限制。
- Park–Martin (1994) 为搜索候选。IEEE 页面要求 JavaScript/机器人验证；仅获得部分元数据，不将其算入本轮六篇有方法记录的文献。后续可从正式可访问来源补读。
- 部分搜索结果来自聚合站、论坛、课程页，只作定位线索，不用作实验结论的依据。
- 未下载整套仓库、外部可执行程序或论文附件；原有本地资料保持原样。

## 补充接口资料

[OpenCV 官方 calib3d 文档](https://docs.opencv.org/4.13.0/d9/d0c/group__calib3d.html) 用于核对输入/输出方向。当前机器是 OpenCV 5.1.0，因此另存本机函数 docstring。两者的版本差别在坐标约定中已标注，尚未执行手眼求解。
