# 机器人自动手眼标定

广东工业大学机械专业本科生大创项目。先用 Python/OpenCV 研究 Eye-in-Hand 仿真，再研究采样、视野和标定精度。

当前已完成 **M1 基础闭环、M2 离线采样与独立留出评价、三项扩展、W2 投影与可见性**。下一阶段为 W3 像素噪声与 PnP，尚未实施。当前没有 GUI 或机器人硬件控制。

## 从这里开始

| 入口 | 用途 |
| --- | --- |
| [本轮交付报告](reports/M2_tonight_completion_20261123.md) | 已实现范围、测试与结果限制 |
| [文档导航](docs/README.md) | 坐标规范与本科生学习材料 |
| [实验索引](experiments/README.md) | 正式实验、复现与开发小实验的位置 |
| [报告索引](reports/README.md) | 开发、修复、核验和历史证据 |
| [周计划](plans/WEEK_PLAN_20261123.md) / [实际进度](plans/progress.json) | 后续任务与可续做位置 |
| [独立审查](reviews/second_review.md) | Claude 对 M1 修复的第二轮审查；M2/W2 待独立复审 |

## 安装与运行

以下命令在项目根目录 PowerShell 执行。已有 `.venv` 时直接使用，无需重新创建或激活。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PYTHONIOENCODING='utf8'
$env:MPLCONFIGDIR="$PWD\.venv\matplotlib-cache"
.\.venv\Scripts\python.exe -W error -m pytest -q -p no:cacheprovider --basetemp=.venv\local-test-temp
.\.venv\Scripts\python.exe scripts\run_m2.py --config configs\m2_smoke.json --output experiments\M2_my_smoke
.\.venv\Scripts\python.exe scripts\verify_m2.py --run experiments\M2_my_smoke --report reports\M2_my_verification.json
```

实验输出目录和核验报告必须不存在，重复运行请换名字；核验报告放在实验目录外。`basetemp` 会用于测试临时文件，只能指定专用临时目录。五项直接依赖是 NumPy、SciPy、opencv-python、Matplotlib、pytest；锁定版本见 requirements-lock.txt。本机验证环境为 Windows/Python 3.12，其他环境尚未作兼容性保证。

## 当前验证范围

- 上轮完整测试 226 项通过；整理后的实际复查结果见[整理与上传记录](reports/repository_cleanup_20261123.md)。
- M2 主实验与三个扩展合计 8640 次正式求解，W2 另有 60 次；全部成功并完成原始观测重放。各设置共享配对种子，重放不增加独立重复数。
- W2 有 3600 个几何候选，1941 个满足当前可见性规则。预测无错判的验证使用理想训练，不能外推到像素噪声或粗初值。
- 当前数据为理想位姿/合成二维投影点；没有真实角点检测、PnP、可达性、碰撞或实机精度验证。启发式收益和研究假设不等于创新性成果。

## 目录

```text
src/handeye/      数学、仿真、求解、采样、评价、投影
tests/           自动测试
scripts/         实验运行与核验 CLI
configs/         冻结实验配置
examples/        基础教学例子
docs/            当前规范、学习材料及 history 历史记录
plans/           任务书、周计划、进度；archive 为旧任务书
experiments/     原始数据、估计、统计、图和完整性清单
reports/         开发报告、修复记录及证据
reviews/         他人的独立审查产物
research_output/ 文献整理成果
```

坐标统一采用 `T_A_B`：B→A，右手系、列向量、内部米/弧度，详见 [PROJECT_SPEC](docs/PROJECT_SPEC.md)。旧初始化说明和旧任务书已归档至 docs/history 与 plans/archive；科研数据保持原路径以保留复现关系。

公开 Git 仓库包含代码、配置、报告与合成实验数据。私人申报书、提取的申报文本、下载论文全文、虚拟环境和缓存只保留本机，由 .gitignore 排除。项目尚未声明开源许可证，不为第三方材料推定再分发权限。
