# 机器人自动手眼标定

机械专业本科生大创项目，基于 Python 和 OpenCV，先开展 Eye-in-Hand（相机安装在机器人末端）算法仿真，再研究自动采样与位姿规划。

**当前阶段：项目环境与目录初始化。尚未实现标定求解算法、GUI 或硬件控制。**

## 最小目录结构

```text
Robot-auto-calibration/
├── README.md                 # 项目说明与操作步骤
├── AGENTS.md                 # Codex 开发约定与当前范围
├── INITIALIZATION.md         # 本次实际命令、环境结果与待处理事项
├── requirements.txt          # 五项直接依赖
├── requirements-lock.txt     # 实际安装版本及传递依赖，安装成功后生成
├── .gitignore                # 排除虚拟环境和缓存
├── src/
│   └── README.md             # 源代码目录用途；暂不实现算法
├── tests/
│   └── test_environment.py   # 五项依赖的导入检查
├── .venv/                    # 本机虚拟环境，不提交 Git
└── 文献/                     # 已有资料，保留
```

项目根目录中的已有申报书同样保留。需要仿真数据、实验结果或研究记录时，再增加相应目录。

## Windows 环境与首次安装

以下命令均在 PowerShell 的项目目录中执行：

```powershell
Set-Location D:\Research\Robot-auto-calibration
python --version
py -0p
git --version
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest -q
```

本次检查到 Python 3.12.0（64 位）及 Git 2.54.0.windows.1；`python` 指向 `D:\Program Files\Python3.12\python.exe`，`py -3.12` 也可选择该解释器。`python3` 是 Windows 应用别名，本项目不依赖它。

`venv` 是 Python 自带的虚拟环境工具。也可使用 `py -3.12 -m venv .venv`，两种创建方式选择一种即可，不要重复创建已有环境。`.venv` 将项目依赖与全局 Python 隔离。

直接调用 `.venv\Scripts\python.exe` 不需要激活环境。可选激活命令为 `.\.venv\Scripts\Activate.ps1`；如果脚本被策略阻止，继续使用上述完整路径，无须修改系统执行策略。

## 依赖用途

| 安装名称 | 导入名称 | 用途 |
| --- | --- | --- |
| NumPy | numpy | 数组、矩阵与基础数值运算 |
| SciPy | scipy | 旋转表示、科学计算和后续优化 |
| opencv-python | cv2 | 图像处理与后续手眼标定实验 |
| Matplotlib | matplotlib | 仿真结果与误差可视化 |
| pytest | pytest | 自动化测试 |

`requirements.txt` 列出直接依赖；`requirements-lock.txt` 保存这次成功安装的全部版本，便于复现。复现环境时先创建 `.venv`，再执行：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe -m pytest -q
```

若有明确需求更新依赖，安装验证后再用以下命令重新记录版本：

```powershell
.\.venv\Scripts\python.exe -m pip freeze | Set-Content -Encoding utf8 requirements-lock.txt
```

## 本次初始化记录

实际检查、安装版本、测试结果和待处理事项见安装完成后生成的 `INITIALIZATION.md`。

Git 仓库已有历史，初始化前多份旧代码和文档已在工作区删除；本次按初始化要求创建 README、依赖清单和忽略规则，保留其余已有删除状态。不恢复旧代码、不提交 Git。


## 2026-11-18 夜间科研准备更新

上面的初始化说明保留为首次初始化记录。当前已增加坐标变换基础模块（src/handeye/）、示例（examples/）及自动测试；尚无标定求解器或自动采样策略。

先查看 [今晚验收报告](reports/tonight_report.md) 和 [学习文档入口](docs/README.md)。

```powershell
.\.venv\Scripts\python.exe examples\basic_transforms.py
.\.venv\Scripts\python.exe -m pytest -q
```

源码采用 src 布局，由 pytest.ini 指定测试导入路径；无需重新安装已有虚拟环境。
