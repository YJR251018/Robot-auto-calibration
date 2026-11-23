# 基础代码与使用示例

## 运行方式

在项目根目录的 PowerShell 中：

```powershell
.\.venv\Scripts\python.exe examples\basic_transforms.py
.\.venv\Scripts\python.exe -m pytest -q
```

测试的 src 搜索路径由 pytest.ini 指定；示例脚本只调整当前进程的 `sys.path`，不修改 Windows 环境变量。

## 模块接口

| 接口 | 输入与输出 |
| --- | --- |
| rotation_matrix(axis, angle, degrees=False) | x/y/z 单轴 → (3,3) 旋转；弧度默认 |
| is_rotation_matrix(R, atol=1e-9) | 同时检查正交与 det=+1，非法矩阵返回 False |
| make_transform(R, t) | (3,3) 与 (3,) → (4,4) |
| validate_transform(T) | 验证刚体约束，返回独立浮点副本 |
| invert_transform(T) | 返回逆变换 |
| compose_transforms(T_A_B, T_B_C, ...) | 从左到右相乘，右边先作用 |
| transform_points(T_A_B, points_B) | (3,) 单点或 (N,3) 点集 → A 系坐标 |

数值输入可用整型/浮点数组或嵌套列表；不接受复数、字符串、NaN、无穷大或不匹配的形状。除判断旋转的接口以外，非法输入抛出带说明的 `ValueError`。非法 atol 总会抛出 ValueError。空点集 `(0,3)` 合法。
只接受 `(3,)` 平移，不猜测 `(3,1)` 或 `(1,3)` 的含义。函数不修改输入，不会把非法旋转“自动修正”为合法矩阵。容差是数值检查尺度，不是实验精度目标。

## 已知数值例子

末端到基座的坐标变换用 `T_B_E` 表示：末端原点位于基座 `[1,2,0]` 米处，轴向相对基座绕 z 正转 90°。相机原点在末端系为 `[0.1,0,0.2]` 米，轴向与末端一致。

```python
import numpy as np
from handeye import rotation_matrix, make_transform, compose_transforms, transform_points

T_B_E = make_transform(rotation_matrix("z", 90, degrees=True), [1, 2, 0])
T_E_C = make_transform(np.eye(3), [0.1, 0, 0.2])
T_B_C = compose_transforms(T_B_E, T_E_C)
p_B = transform_points(T_B_C, [1, 0, 0])
```

手算：`p_E=[1.1,0,0.2]`；绕 z 转 90° 得 `[0,1.1,0.2]`；再加基座平移得 `p_B=[1,3.1,0.2]` 米。
完整可执行版本在 `examples/basic_transforms.py`，包含结果断言和逆变换恢复检查。不要直接在未配置 src 搜索路径的交互解释器里复制 import；先运行完整示例最方便。

## 测试设计为什么可信

测试既有手算的非交换例子，也用 SciPy Rotation 和 NumPy 通用矩阵逆作独立参照。固定种子 0、7、20261118 各检查 30 组随机变换，每组还检查 10 个点；随机循环是性质检查，不冒充独立科研重复试验。
测试覆盖反射、缩放、退化矩阵、末行错误、错误形状、非有限数、复数以及输入不被修改。
测试不证明未来机器人数据的时间配对、单位或坐标系标签正确，这些仍需要数据接口测试。
