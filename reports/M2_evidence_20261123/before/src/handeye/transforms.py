"""右手坐标系刚体变换；列向量，长度为米，默认角度为弧度。

T_A_B 将 B 系坐标映射到 A 系：p_A = R_A_B @ p_B + t_A_B。
组合次序：T_A_C = T_A_B @ T_B_C（右侧先作用）。
矩阵本身不携带坐标系或单位标签，调用者须检查两者匹配。
"""

from numbers import Real

import numpy as np

DEFAULT_ATOL = 1e-9


def _tolerance(atol):
    if isinstance(atol, (bool, np.bool_)) or not isinstance(atol, Real):
        raise ValueError("atol 必须是有限正实数")
    if not np.isfinite(atol) or atol <= 0:
        raise ValueError("atol 必须是有限正实数")
    return float(atol)


def _real_array(value, name):
    try:
        array = np.asarray(value)
        if array.dtype.kind not in "iuf":
            raise ValueError("只接受实数数组")
        array = array.astype(float, copy=True)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} 必须是实数数组") from exc
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{name} 不得包含 NaN 或无穷大")
    return array


def rotation_matrix(axis, angle, *, degrees=False):
    """绕 x/y/z 轴按右手定则创建 3×3 旋转矩阵。

    示例：rotation_matrix('z', np.pi / 2) 将 x 方向映射到 y 方向。
    默认 angle 为弧度；仅在 degrees=True 时接受角度值。
    不提供含糊的多轴欧拉角接口，避免内禀/外禀顺序混用。
    """
    if not isinstance(axis, str) or axis.lower() not in ("x", "y", "z"):
        raise ValueError("axis 必须为 'x'、'y' 或 'z'")
    if not isinstance(degrees, (bool, np.bool_)):
        raise ValueError("degrees 必须为布尔值")
    if isinstance(angle, (bool, np.bool_)) or not isinstance(angle, Real):
        raise ValueError("angle 必须为有限实数")
    if not np.isfinite(angle):
        raise ValueError("angle 必须为有限实数")
    radians = np.deg2rad(angle) if degrees else float(angle)
    c, s = np.cos(radians), np.sin(radians)
    if axis.lower() == "x":
        return np.array([[1, 0, 0], [0, c, -s], [0, s, c]], dtype=float)
    if axis.lower() == "y":
        return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]], dtype=float)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]], dtype=float)


def is_rotation_matrix(matrix, *, atol=DEFAULT_ATOL):
    """判断是否属于 SO(3)：R.T @ R≈I 且 det(R)≈+1。

    形状错误、反射、缩放、非有限或非实数输入返回 False。
    使用绝对容差 atol，rtol=0；非法容差抛出 ValueError。
    """
    atol = _tolerance(atol)
    try:
        matrix = _real_array(matrix, "rotation")
    except ValueError:
        return False
    if matrix.shape != (3, 3):
        return False
    with np.errstate(over="ignore", invalid="ignore"):
        orthogonal = np.allclose(matrix.T @ matrix, np.eye(3), atol=atol, rtol=0)
        determinant = np.linalg.det(matrix)
    return bool(orthogonal and np.isclose(determinant, 1.0, atol=atol, rtol=0))


def make_transform(rotation, translation, *, atol=DEFAULT_ATOL):
    """构造 T_A_B=[R_A_B,t_A_B;0,0,0,1]，平移单位为米。

    rotation 必须为有效的 (3,3) 旋转；translation 只接受 (3,)，
    表示 B 系原点在 A 系中的坐标。不自动修正非法旋转矩阵。
    """
    atol = _tolerance(atol)
    rotation = _real_array(rotation, "rotation")
    if not is_rotation_matrix(rotation, atol=atol):
        raise ValueError("rotation 必须是有效的 3×3 旋转矩阵（det=+1）")
    translation = _real_array(translation, "translation")
    if translation.shape != (3,):
        raise ValueError("translation 形状必须为 (3,)，单位为米")
    transform = np.eye(4)
    transform[:3, :3] = rotation
    transform[:3, 3] = translation
    return transform


def validate_transform(transform, *, atol=DEFAULT_ATOL):
    """检查 4×4 刚体变换并返回独立浮点副本；非法输入抛出 ValueError。

    末行须在绝对容差内等于 [0,0,0,1]，不接受一般投影矩阵。
    """
    atol = _tolerance(atol)
    transform = _real_array(transform, "transform")
    if transform.shape != (4, 4):
        raise ValueError("transform 形状必须为 (4,4)")
    if not np.allclose(transform[3], [0, 0, 0, 1], atol=atol, rtol=0):
        raise ValueError("transform 末行必须为 [0,0,0,1]")
    if not is_rotation_matrix(transform[:3, :3], atol=atol):
        raise ValueError("transform 左上角必须为有效旋转矩阵")
    return transform


def invert_transform(transform, *, atol=DEFAULT_ATOL):
    """T_A_B → T_B_A；用 R.T 和 -R.T @ t 求刚体逆变换。"""
    transform = validate_transform(transform, atol=atol)
    inverse = np.eye(4)
    inverse[:3, :3] = transform[:3, :3].T
    inverse[:3, 3] = -inverse[:3, :3] @ transform[:3, 3]
    return inverse


def compose_transforms(first, second, *others, atol=DEFAULT_ATOL):
    """按给定顺序相乘：compose(T_A_B,T_B_C)=T_A_C。

    至少两个矩阵；每个都须为合法刚体变换。不会自动识别坐标系不匹配。
    """
    result = validate_transform(first, atol=atol)
    for transform in (second, *others):
        result = result @ validate_transform(transform, atol=atol)
    return result


def transform_points(transform, points, *, atol=DEFAULT_ATOL):
    """用 T_A_B 将 B 系点转换到 A 系；输入/输出长度均为米。

    points 支持单点 (3,) 或点集 (N,3)。点集按行存储，但每个点仍遵循
    列向量公式；实现为 points @ R.T + t。空点集 (0,3) 合法。
    """
    transform = validate_transform(transform, atol=atol)
    points = _real_array(points, "points")
    if points.shape == (3,):
        return transform[:3, :3] @ points + transform[:3, 3]
    if points.ndim == 2 and points.shape[1] == 3:
        return points @ transform[:3, :3].T + transform[:3, 3]
    raise ValueError("points 形状必须为 (3,) 或 (N,3)")
