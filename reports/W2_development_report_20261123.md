# W2 投影与可见性验收报告

日期：2026-11-23，Asia/Shanghai。W2作为 M2 任务书 H4 的余量任务继续实施；本阶段已完成。尚未实施 W3/PnP、像素噪声或真实图像检测。

## 完成内容与文件

- `src/handeye/camera.py`：严格相机参数校验、63个板点、零畸变投影、测量/预测可见性、从训练估计Y_hat。采用T_A_B、米/弧度、pixel输出。
- `projection_experiment.py`：保存全部候选、独立测量/预测接口、前20可见样本的PARK/TSAI无噪声验收、CSV/JSON/NPZ及图。
- `projection_verification.py`：30种子原始数据再生成、60次实际OpenCV重求解、3000次预测重放、哈希及汇总核验。
- `scripts/run_projection.py`、`verify_projection.py`：输出限项目内新目录，核验报告限实验目录外新文件。
- `tests/test_camera.py`、`test_projection_experiment.py`：31项投影手算/边界、实际求解链和失败保护测试。
- `configs/w2_projection_v0_1.json`、`docs/W2_projection_guide.md`：正式协议参数与中文教学/复现材料。

生成分布与验收标准提前固定于 `reports/W2_protocol_20261123.md`；正式运行前再保存配置/代码哈希于 `W2_evidence_20261123/protocol_freeze.json`。开发种子610000与正式510000…510029分离，没有根据正式结果改变阈值。

## 实测与复核

| 检查 | 结果 |
| --- | --- |
| 首次W2测试 | 新模块缺失导致收集错误，已保留红灯日志 |
| camera模块 | 20项通过 |
| W2集成 | 31项通过 |
| 本轮最终完整pytest | **226通过，0失败/错误/跳过，17.11秒** |
| 正式候选 | 30种子×120=3600，全部保存 |
| 实际可见/拒收 | 1941/1659；画面外1542，余量拒收117 |
| 每种子最少可见 | 55，均满足预定20训练样本 |
| 无噪声手眼恢复 | 60次，全部通过，原阈值未放宽 |
| 理想训练后预测 | 3000候选，0错判 |
| OpenCV投影对照 | 最大绝对差4.55e-13pixel，小于预定1e-8pixel |

产物：`experiments/W2_projection_20261123/`。完整核验通过于 `reports/W2_evidence_20261123/formal_verification.json`。

另用独立的K乘齐次点矩阵、直接画面不等式与通用np.linalg.inv复算全部3600个投影/原因和3000个预测，结果一致；不是仅重复调用被测投影函数。记录在 `independent_numeric_audit.json`。两张实际投影PNG已查看，轴/单位/可见或margin拒收原因清晰；图是合成点示意。

## 失败处理与保护

意外NameError故障注入证实当前种子原始候选已落盘，run_status记录failed、seed、phase、traceback；没有输出成功汇总。候选不足时不暗中更换种子。已有结果目录拒绝覆盖；哈希篡改可被核验入口拒绝。

保留原有M1和M2源码/测试/实验。W2新增模块和结果目录；README、AGENTS、规范与progress仅更新当前入口/约定。未安装依赖或修改系统、提交、上传。精确差异与已有文件保护结果见本轮最终交付清单。

## 实际命令

```powershell
.\.venv\Scripts\python.exe -W error -m pytest tests/test_camera.py tests/test_projection_experiment.py -q -p no:cacheprovider --basetemp=.venv\W2-integration-temp --junitxml=reports\W2_evidence_20261123\integration.xml
.\.venv\Scripts\python.exe -W error scripts/run_projection.py --config configs/w2_projection_v0_1.json --output experiments/W2_projection_20261123
.\.venv\Scripts\python.exe -W error scripts/verify_projection.py --run experiments/W2_projection_20261123 --report reports/W2_evidence_20261123/formal_verification.json
.\.venv\Scripts\python.exe -W error -m pytest -q -p no:cacheprovider --basetemp=.venv\M2-W2-final-temp --junitxml=reports\W2_evidence_20261123\full_final.xml
```

均在项目根目录运行，进程内PYTHONDONTWRITEBYTECODE=1、PYTHONIOENCODING=utf8、MPLCONFIGDIR指向项目.venv缓存。日志保存于W2_evidence_20261123；测试临时文件限定项目.venv。

## 局限与下一步

当前理想训练几乎精确恢复X/Y，因此零错判只验证几何、方向和实现。训练集先由仿真测量端挑选可见样本，是验收协议，不能用来宣称未知可见性下的自主采样收益。板为无厚度双面几何点集，无真实遮挡、畸变、检测误差或机器人约束。

下一阶段W3按周计划先冻结像素噪声/PnP协议，检查平面多解和可观测选解规则；不以真值选择PnP分支。W4才作有限尝试预算下的主动采样比较。当前不对这些未实现任务作结果声明。
