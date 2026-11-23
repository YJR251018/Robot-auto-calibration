# 今晚科研准备验收报告

执行日期：2026-11-18（Asia/Shanghai）。项目根目录：`D:\Research\Robot-auto-calibration`。

## 1. 完成概况

| 任务 | 结果 | 实际边界 |
| --- | --- | --- |
| Task 1 环境与结构 | 完成复查并扩展最小结构 | 复用已有 .venv，不重装依赖 |
| Task 2 坐标变换 | 完成 | 旋转、齐次矩阵、求逆、组合、单点/点集；无手眼求解器 |
| Task 3 自动测试 | 完成 | 最终 75 项通过、0 失败、0 跳过 |
| Task 4 文献初调 | 完成六篇定向初调 | 阅读范围逐项标注，不是全面综述或代码复现 |
| Task 5 研究文档 | 完成 | 五类主题及背景、使用说明、检索日志；实验方案尚未执行 |
| Task 6 验收报告 | 本文 | 测试原始日志及机器可读验证记录另存 |

本次顺序为环境复查 → 基础实现 → 首轮测试 → 联网文献 → 研究文档 → 最终复核及报告。没有使用子代理、付费 API、真实硬件、GUI 或外部自动控制。

## 2. 环境实测

- Python 3.12.0，解释器为项目 `.venv\Scripts\python.exe`；Git 2.54.0.windows.1。
- NumPy 2.5.5、SciPy 1.18.1、opencv-python 5.1.0.95（cv2 5.1.0）、Matplotlib 3.11.2、pytest 9.2.0。
- `pip check` 返回 `No broken requirements found.`。
- 现有 requirements.txt、requirements-lock.txt 和 .gitignore 完整保留；未安装软件或更改系统设置。
- 当前会话起始目录为 D:\Research，实际所有本轮项目命令均指定仓库子目录为工作目录。

## 3. 文件交付与保留情况

### 源码、测试和配置

| 文件 | 内容 |
| --- | --- |
| src/handeye/__init__.py | 导出基础接口 |
| src/handeye/transforms.py | 7 个公开坐标变换接口，中文说明和输入验证 |
| examples/basic_transforms.py | 已知数值、坐标链与逆变换示例 |
| tests/test_transforms.py | 新增 70 个 pytest 测试用例，含参数化用例 |
| pytest.ini | tests 搜索范围及 src 导入路径 |

### 科研与学习文档

- [阅读入口](../docs/README.md)
- [申报书背景与当前范围](../docs/project_context.md)
- [Eye-in-Hand 坐标约定](../docs/eye_in_hand_frames.md)
- [基础知识笔记](../docs/handeye_basics.md)
- [代码使用说明](../docs/transforms_usage.md)
- [技术路线](../docs/technical_roadmap.md)
- [第一阶段仿真实验方案](../docs/simulation_plan.md)
- [待验证研究假设](../docs/research_questions.md)
- [六篇文献初调](../docs/literature_review.md)
- [检索与核验记录](../docs/literature_search_log.md)

### 记录与已有文件

- README.md、AGENTS.md、src/README.md：检查内容后只追加本轮说明；原始字节完整保留为前缀，并备份在 `reports/baseline_2026-11-18/`。没有覆盖原有正文。
- 原始基线包括 16 个已有文件的 SHA-256；其中 13 个本轮完整不变，另 3 个只追加。申报书和文献 PDF 的原文件均经哈希核对未变。
- 原有 `tests/test_environment.py` 的 5 项导入测试继续保留。
- `proposal_text_local.txt`：本地提取的申报书文字及线性化公式，含表格内的个人资料，只供本项目本地查阅；未上传，也未将个人信息用于网络查询。
- `opencv_handeye_api.txt`：当前安装版本的函数说明，读取接口文档不等于运行求解器。
- `test_results.txt`、`pytest-results.xml`、`example_output.txt`、`dependency_check.txt`：实际运行日志。
- `git_diff_check.txt`、`git_status_final.txt`：Git 工作区检查结果；`verification_results.json`：命令、退出码与保留核验结果。
- `file_inventory.json`：本轮文件清单及是否新增/追加/未变；`link_audit.json`：最终本地 Markdown 链接检查。

申报书和 7 份已有本地论文没有改写；本地 PDF 只清点，未逐篇阅读。没有恢复历史删除的旧代码，也没有创建 Git 提交或远程操作。

## 4. 实际运行的关键命令

以下命令均在项目根目录执行。目录和已有内容还通过 Get-ChildItem、rg、Get-Content 做只读检查。

```powershell
Get-Location
git -c core.quotepath=false status --short
python --version
git --version
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest -q --junitxml=reports\pytest-results.xml
.\.venv\Scripts\python.exe examples\basic_transforms.py
# 最终复核把 Python 警告视为错误：
.\.venv\Scripts\python.exe -W error -m pytest -q --junitxml=reports\pytest-results.xml
.\.venv\Scripts\python.exe -W error examples\basic_transforms.py
git diff --check
```

另使用项目 Python 的标准库 `zipfile`、`xml.etree.ElementTree` 只读提取 DOCX 的正文、表格及 OMML 文本，用 `hashlib` 生成和核对基线，用 `subprocess.run` 捕获上述最终命令的 stdout/stderr 与退出码。`cv2.calibrateHandEye.__doc__` 仅被保存为文本。
最终复核为进程临时指定 PYTHONIOENCODING=utf-8 和项目 `.venv/matplotlib-cache` 的 MPLCONFIGDIR；不修改系统环境变量。

## 5. 测试结果与质量边界

首轮：74 passed in 5.44s，0 失败。增加一项文档坐标闭环/相对运动方向回归测试后，最终：

```text
75 passed in 0.76s
No broken requirements found.
Known-value and round-trip checks: PASS
```

pytest、示例、pip check、git diff --check 的退出码均为 0。最终使用 `-W error`，没有出现 Python 警告。
JUnit XML、文本日志和 JSON 记录支持复查；耗时是本次机器实测，不是性能基准。

测试内容包括：

1. 三轴、负角、零角、接近 π 的旋转，对照 SciPy；同时检查正交和 det=+1。
2. 手算已知矩阵、两侧逆乘积为 I，并对照 NumPy 通用逆。
3. 非交换的矩阵组合、逐段点变换与合成变换一致。
4. 固定种子 0、7、20261118，各 30 组随机性质检查；每组 10 个点的恢复。
5. 非法形状、反射、缩放、错误末行、NaN、Inf、复数及错误参数处理；输入不被修改。
6. 与文档一致的 `G_i X Q_i=Y` 和相对运动 AX=XB 恒等式；这不是求解器恢复真值实验。

通过这些测试只能证明已覆盖的基础行为。矩阵不带单位和坐标标签，代码无法识别数值合法但方向、时间配对或米/毫米错误的真实数据。

## 6. 遇到的问题及处理

- **DOCX 输出编码错误**：提取文件已经保存，但首次控制台打印遇到 GBK 无法编码的不换行空格。改为 UTF-8 输出后成功读取研究段落；随后补充提取 OMML 的公式文字。原文档未修改。
- **示例的反斜杠警告**：路径写在普通文档字符串中引发 invalid escape sequence，改为原始字符串；最终 `-W error` 复核运行通过。
- **网络文献访问受限**：PMC 验证码改用 PLOS 公开原文；Daniilidis 高校 PDF 超时后保留摘要级记录；Park 的 IEEE 页验证受阻，不计入六篇已整理记录。没有绕过限制或付费。
- **OpenCV 文档版本差异**：网页为 4.13.0、本机为 5.1.0，保存本机接口 docstring 并明确正式求解前必须再做真值测试。
- **Git 历史状态**：多份旧算法和研究文档的删除是本轮开始前已有状态，继续保留。Git 的 LF→CRLF 提示是现有换行配置，检查未发现空白错误，未改系统或仓库配置。
- **历史初始化表述**：旧 README/AGENTS/src 说明保留，追加当前阶段入口，避免把历史初始化范围误作本轮成果范围。

当前没有必须申请额外权限才能完成本轮交付的阻碍，也没有进行提权操作。

## 7. 尚未完成的内容

- 手眼求解器调用、已知真值数据生成、噪声实验和结果图表。
- 可见性筛选、主动采样、质量反馈补采与机器人位姿规划的实现及效果验证。
- 对六篇论文全部正文、外部代码及依赖的复现；Park 论文补读与本地七份论文的精读。
- 相机内参、PnP、真实图像采集、机器人接口和任何实机误差指标。
- 安装包发布、GUI、机器人硬件及控制。今晚未作这些工作，不影响基础任务验收。

申报书的预期成果、仿真协议中的验收阈值和未来创新假设均未记为实测成果。

## 8. 明天建议检查与决定

1. 先运行下方两条命令，再手算示例的 `[1,3.1,0.2]` 米，检查坐标命名是否容易理解。
2. 确认接受本项目统一的 `T_A_B: B→A`、米、弧度约定；未来 E 表示法兰还是工具系需在接设备前明确。
3. 决定下一步是否按仿真协议先做 20 帧非退化、无噪声的 OpenCV 求解验证；拟先 PARK，再 TSAI 比较，尚未执行。
4. Git 原有删除文件是否需另行整理恢复，由你决定；本次不混入恢复工作。
5. 核对申报路线与文献初调，选择先精读 Tsai–Lenz、误差评价或 NBV；不要急着同时引入深度学习和硬件。

```powershell
Set-Location D:\Research\Robot-auto-calibration
.\.venv\Scripts\python.exe examples\basic_transforms.py
.\.venv\Scripts\python.exe -m pytest -q
```

## 9. 下一次学习的三个核心知识点

1. **坐标变换方向与矩阵乘法顺序**：通过非交换例子理解为什么右侧先作用，为什么逆平移不是 -t。
2. **SO(3)、SE(3) 与数值验证**：正交性、det=+1、浮点容差，以及合法矩阵与物理方向正确是两回事。
3. **固定板闭环与 AX=XB 的来源**：先画 G、X、Q、Y 的坐标链，再理解旋转激励和退化；之后才进入求解器和主动采样。
