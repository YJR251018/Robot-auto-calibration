# 实验索引

数据目录保持原路径。只在全新目录运行；不要编辑冻结CSV、NPZ、估计或哈希。每个文件夹的RESULTS.md和run_status.json记录实际状态。

| 目录 | 类型 | 记录状态/次数 |
| --- | --- | --- |
| [M1_my_reproduction](M1_my_reproduction/RESULTS.md) | 重跑/重放验证 | complete / 840 |
| [M1_review_fix_smoke_20261119](M1_review_fix_smoke_20261119/RESULTS.md) | 开发/审查小实验 | complete / 40 |
| [M1_review_quick](M1_review_quick/RESULTS.md) | 开发/审查小实验 | complete / 60 |
| [M1_v0_1](M1_v0_1/RESULTS.md) | 正式 | complete / 840 |
| [M1_v0_1_reproduction](M1_v0_1_reproduction/RESULTS.md) | 重跑/重放验证 | complete / 840 |
| [M2_pool120_20261123](M2_pool120_20261123/RESULTS.md) | 正式 | complete / 2160 |
| [M2_robot_noise_20261123](M2_robot_noise_20261123/RESULTS.md) | 正式 | complete / 2160 |
| [M2_sampling_20261123](M2_sampling_20261123/RESULTS.md) | 正式 | complete / 2160 |
| [M2_scene2_20261123](M2_scene2_20261123/RESULTS.md) | 正式 | complete / 2160 |
| [M2_smoke_20261123_a](M2_smoke_20261123_a/RESULTS.md) | 开发/审查小实验 | complete / 144 |
| [M2_smoke_20261123_b](M2_smoke_20261123_b/RESULTS.md) | 开发/审查小实验 | complete / 144 |
| [W2_projection_20261123](W2_projection_20261123/RESULTS.md) | 正式 | complete / 60 |

M2每设置30个独立重复，共用配对种子；开发小实验和重放不能增加正式样本数。W2的3600个候选是几何样本，其无噪声求解为60次。

M1核验：scripts/verify_m1.py；M2核验：scripts/verify_m2.py；W2核验：scripts/verify_projection.py。报告写到本目录之外的项目内新文件。
