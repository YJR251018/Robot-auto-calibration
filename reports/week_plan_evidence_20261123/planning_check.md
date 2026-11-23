# 周计划制定与现场核验记录

日期：2026-11-23，Asia/Shanghai。此次仅制定计划并核验现有环境；**尚未实施 M2 或 W1—W7 开发**。

## 已实际完成

- 阅读项目 AGENTS、README、坐标约定、已有模拟方案和当前主要源代码，完整阅读第二轮独立审查及上一轮修复报告。
- 确认当前位于项目目录，分支为 fix/m1-review-20261119；已有未提交成果保持原状，本次没有创建开发分支、提交或推送。
- 确认 docs/PROJECT_SPEC.md 尚不存在，已列为今晚任务；没有假称读过该规范。
- 实际运行完整 pytest：**143 通过，0 失败、0 错误、0 跳过，35.01 秒，退出码 0**。
- 新建 plans 下四个计划/续做文件，W1—W7 全部标为 not_started。
- 查阅 OpenCV 官方投影与 PnP 接口文档，为后续任务写明方向和实现时的版本核验要求；没有重复文献检索。

## 本次新增入口

- [本周计划](../../plans/WEEK_PLAN_20261123.md)：七天目标、前置条件、优先级和验收门槛。
- [今晚任务书](../../plans/TONIGHT_M2_20261123.md)：M2 分阶段开发、2160 次计划实验、公平对照和交付要求。
- [每日启动说明](../../plans/DAILY_RUNBOOK.md)：可复制指令及 W2—W7 的实施细则。
- [进度记录](../../plans/progress.json)：后续执行者核对证据后更新，不代表定时任务。

## 实际关键命令

以下在 D:\Research\Robot-auto-calibration 中执行，未重新安装依赖。

```powershell
git status --short --branch
git log -3 --oneline
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PYTHONIOENCODING='utf8'
$env:MPLCONFIGDIR="$PWD\.venv\matplotlib-cache"
.\.venv\Scripts\python.exe -W error -m pytest -q -p no:cacheprovider --basetemp=.venv\week-plan-20261123-temp --junitxml=reports\week_plan_evidence_20261123\baseline.xml
```

测试标准输出保存于 [baseline.txt](baseline.txt)，结构化结果保存于 [baseline.xml](baseline.xml)。另使用项目 Python 计算原有文件 SHA-256、核对计划链接和进度 JSON；使用文件编辑工具新建计划文本。

## 保护与限制

原有 4133 个非缓存文件均未改变或删除，核验见 [planning_verification.json](planning_verification.json)。本次新增计划与核验材料，测试临时产物位于项目 .venv；未修改源代码、原测试、规范文档、已有实验、独立审查、文献或申报书。

仍待执行：今晚任务书所有开发阶段、正式实验及后续六天任务。2160 次是协议计划数，不是已经完成的求解数。账户剩余额度无法查询，未设置自动化或承诺后台持续执行；每个后续阶段要求及时保存续做状态。
