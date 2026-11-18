# 机器人相机标定工具

在桌面工作台中检查棋盘格照片与机器人位姿，计算相机内参或手眼变换，并导出可复查的 JSON 结果。面向机器人视觉开发、实验教学和校内自动标定研究。

## 快速开始

已在 Windows 11、Python 3.12、Tkinter 8.6、NumPy 2.4.6 和 OpenCV 5.0.0 环境验证。Tkinter 随本次验证使用的 Windows Python 安装提供。

```powershell
python -m pip install -r requirements.txt
python -m robot_calibration
```

在项目目录运行以上命令。首次体验可任选一个模式，依次点击 **载入演示数据 → 运行标定 → 导出 JSON**。每种模式提供 15 张模拟棋盘格照片。手眼演示同时提供配对的机器人末端位姿和用于对照的已知变换。

| 模式 | 安装配置与输入 | 导出结果 |
|---|---|---|
| 相机内参 | 同一台相机拍摄的棋盘格照片、内角点行列数、方格边长 | 内参矩阵、畸变系数、整体和逐帧重投影误差 |
| 眼在手上 | 相机装在机器人末端，棋盘格固定。输入相机内参、图像与末端位姿 | 相机到机器人末端的变换 |
| 眼在手外 | 相机固定，棋盘格装在机器人末端。输入相机内参、图像与末端位姿 | 相机到机器人基座的变换 |

手眼结果包含变换方向、长度单位、使用的内参、有效样本和拒绝原因。界面中的板位姿离散程度用于检查参与求解的样本是否一致。仿真额外显示与真值相比的误差。

## 导入实采数据

1. 采集同一分辨率的棋盘格照片。记录实际方格边长（mm）、内角点列数与行数。手眼模式要求行列一奇一偶，例如 **9 × 6 个内角点**，用对角的黑白格统一角点方向。拍摄时保留完整棋盘格和白边。
2. 先在 **相机内参** 模式标定，或准备符合下述格式的内参文件。每次改变相机分辨率、镜头焦距或图像裁剪方式时，核对对应的内参。
3. 机器人停稳后记录实际末端位姿，用图像名作为配对键。同一次采集中使用同一套基座、末端和长度单位约定，并采集绕不同轴转动的画面。
4. 在手眼模式选择照片目录、位姿 JSON 和相机内参。运行后在样本表检查拒绝原因与重投影误差。现场控制器导出的欧拉角或四元数需先按厂商约定转换成 4 × 4 矩阵。

### 位姿文件

`poses.json` 声明 `frame` 为 `gripper_to_base`，`length_unit` 为 `mm`。每项矩阵把末端坐标中的点变换到机器人基座坐标。右上角一列为平移，最下一行是 `[0, 0, 0, 1]`。下面只展示一条记录，实际至少准备 3 组有效且旋转轴多样的位姿。

```json
{
  "frame": "gripper_to_base",
  "length_unit": "mm",
  "samples": [
    {
      "image": "view_01.png",
      "matrix": [
        [1, 0, 0, 350],
        [0, 1, 0, 100],
        [0, 0, 1, 520],
        [0, 0, 0, 1]
      ]
    }
  ]
}
```

相机内参可直接使用工作台导出的 JSON。手眼模式读取 `camera_matrix`、`distortion` 和 `image_size`，尺寸顺序为 `[宽, 高]`。内参求解至少需要 5 张角点完整、尺寸一致且位置有变化的照片。

## 命令行复现

下面的命令在空的 `calibration-demo` 目录生成一份眼在手上样例，然后求解手眼变换并给出下一拍的推荐排序。生成 `eye-to-hand` 样例时使用另一个空目录。

```powershell
$demo = '.\calibration-demo'
python -m robot_calibration demo eye-in-hand $demo
python -m robot_calibration intrinsics --images "$demo\images" --out "$demo\calculated-intrinsics.json"
python -m robot_calibration hand-eye eye-in-hand --images "$demo\images" --poses "$demo\poses.json" --intrinsics "$demo\intrinsics.json" --truth "$demo\truth.json" --out "$demo\hand-eye.json"
python -m robot_calibration recommend --calibration "$demo\hand-eye.json" --images "$demo\images" --poses "$demo\poses.json" --candidates "$demo\candidate_poses.json" --out "$demo\recommendation.json"
```

`recommend` 从眼在手上结果恢复棋盘格在基座中的估计位姿，先筛除预测出画或边距不足的候选，再按对旋转采样方向的补充排序。候选文件使用 `candidates` 数组，每项包含唯一的 `id` 和末端到基座的 `matrix`，坐标与单位字段和位姿文件一致。推荐结果仅用于离线评估，实机执行前仍需由控制器检查可达性与路径。

### 研究仿真与测试

```powershell
python -m robot_calibration.experiment --trials 40 --seed 42 --out .\rotation-coverage.json
python -m unittest discover -s tests -v
```

每轮比较同样 15 组位姿。两组共享转角幅度、平移和视觉噪声，只改变旋转轴分布。JSON 包含逐轮结果、中位数和第 90 百分位，可用于复查采样条件与误差差异。

原入门仿真可用 `python .\first_handeye_experiment.py --noise-mm 1` 复跑，输出仍为平移误差约 1.910 mm、旋转误差约 0°。该入门实验只给平移输入加噪。

## 项目结构

| 路径 | 用途 |
|---|---|
| `robot_calibration/app.py` | Tkinter 桌面工作台 |
| `robot_calibration/calibration.py`、`geometry.py` | 角点、内参、PnP 与手眼求解 |
| `robot_calibration/demo.py`、`sampling.py`、`experiment.py` | 可生成演示数据、位姿推荐、旋转覆盖仿真 |
| `tests/` | 数据导入、求解与桌面流程测试 |
| [任务回顾](./任务回顾.md) | 本轮实现、验证结果和实机准备 |

## 后续实机验证

从一批人工采集的眼在手上数据做离线验证，再接入机器人控制器、路径校验和按图像质量补采。实机对照比较人工选点、固定轨迹和筛选加补采。各组使用相同初始样本、求解器和拍摄预算，并记录失败拍摄与复拍。具备独立基座坐标参考与测量条件时，再评估绝对三维位置误差。

标定坐标约定可参阅 [OpenCV 手眼标定文档](https://docs.opencv.org/4.13.0/d9/d0c/group__calib3d.html)。固定轨迹基线参考冯东远《打磨机器人工具工件高精度自动标定系统开发》（广东工业大学，2025）第 3.4 节。

## 许可证

本项目尚未指定开源许可证。
