# 目录整理、复查与Git发布记录

日期：2026-11-23。用户授权“整理文件夹，复查无问题后上传Git”。远程为公开仓库YJR251018/Robot-auto-calibration，拟推送当前feat/m2-sampling-20261123功能分支。

## 整理内容

- 重写根README、docs导航和src入口，清楚标注M2/W2当前成果与W3未开始，消除多个“当前阶段”混杂。
- 新增experiments/README、reports/README、plans/README，按正式实验、复现、开发小实验、验收和历史证据导航。
- 根INITIALIZATION.md原样移动到docs/history/INITIALIZATION.md。
- 根CONTINUE WORK.md原样移动到plans/archive/M1_TASK_20261118.md。
- 整理前README和AGENTS原文保存到docs/history；本轮原件副本另存cleanup_20261123/before供本地核验。
- 实验目录、原始NPZ/CSV/估计、他人审查、文献整理内容保留原路径和字节，防止破坏实验哈希或历史证据。
- .gitignore排除本机虚拟环境、缓存、根目录私人申报docx、proposal_text_local.txt、下载论文全文及本轮本地整理副本。它们保留在本机。

未删除已有数据。历史被用户删除的旧GUI/workbench代码保持现状；本轮提交会如实记录这些既有删除，以及当前src/handeye科研代码。旧版本仍可在Git历史查看，不恢复到工作区。

## 发布范围与验证

发布范围是当前科研代码、测试、配置、可公开文档、原审查报告及合成实验数据。原始实验总量约43MiB；完整版本化以支持从保存观测重放。来源文献链接保留，第三方PDF全文不入库。

本轮检查记录位于cleanup_20261123/：pytest.txt/xml、validation.json、fresh_checkout_pytest.txt/xml、staged_review.json。检查通过后才提交并推送，不强推、不合并main。最终提交和远程核验结果保存在本地push_result.json，并在回复中给出。

## 实际复查结果

- 工作目录完整pytest：226通过，14.78秒；干净Git导出副本：226通过，15.41秒。源码和测试内容未因整理而修改。
- 干净副本首次因专用临时目录的父路径未建立而产生28个setup错误；保留fresh_checkout_setup_red日志。创建本地临时父目录后完整通过，未修改算法或削弱测试。
- 原有13528个文件核验：仅5个入口/忽略规则文件有意修改，2个根文件原样移动；其他既有内容未变。52个导航链接通过，依赖pip check通过。
- 12个完整实验目录的产物哈希均通过，M2/W2既有全量重放证据保持不变。原审查与文献整理内容未变。
- 本机core.autocrlf=true。新增仓库.gitattributes的`* -text`保留文件字节，使源码指纹和冻结实验哈希在Git归档/检出后仍一致；没有改系统/全局Git配置。
- 原始日志和OpenCV说明中的尾随空白保留；生产源码使用识别CRLF行尾的Git空白检查通过。初次暂存检查日志保留，不能为消除提示而改写原证据。
- 第一次导出核验仅发现正在更新的source_whitespace.txt日志与当时暂存版本不同；源代码和实验数据字节一致。最终暂存复核以staged_review.json为准。

本机core.autocrlf=true会在入库时改变文本字节，因此新增.gitattributes的`* -text`，使源码指纹和冻结实验哈希在Git归档/检出后仍与原件一致。没有修改系统或全局Git配置。原始日志/OpenCV文档中的尾随空白保留，生产代码另行做空白检查。

新发布的入口文档有意更新；历史delivery_manifest记录的是旧时点，不覆盖为新的“相同哈希”。本轮用新的清单说明移动与改动，原实验内部哈希保持不变。

## 核验项目

1. 完整pytest和pip依赖一致性。
2. 正式M1/M2/W2实验状态、产物清单与哈希；M2/W2既有全量重放证据及独立数值审计。
3. 本次修改只涉及目录导航、历史归档及发布规则；源代码和测试未改动。
4. 暂存文件的隐私/凭据扫描和体积检查，确认私人文件与缓存不入库。
5. 从暂存Git树导出独立目录，重新运行完整测试，验证干净检出可用。
6. 推送后核对远程分支提交与本地HEAD一致。

这些检查不替代Claude对M2/W2的独立审查，不改变当前仿真简化条件。
