"""刚体误差：内部弧度/米，报告时显式换为度/毫米。"""

from dataclasses import dataclass

import numpy as np
from scipy.spatial.transform import Rotation

from .transforms import is_rotation_matrix, validate_transform


def rotation_error_rad(estimate, reference):
    """返回 R_est R_ref.T 的主旋转角 [0,π]；近零/近π也保持数值稳定。"""
    if not is_rotation_matrix(estimate) or not is_rotation_matrix(reference):
        raise ValueError("旋转误差输入必须是有效的 3×3 旋转矩阵")
    relative = np.asarray(estimate, dtype=float) @ np.asarray(reference, dtype=float).T
    return float(Rotation.from_matrix(relative).magnitude())


def translation_error_m(estimate, reference):
    """两个 (3,) 实数平移向量的欧氏距离，单位米。"""
    values = []
    for value in (estimate, reference):
        array = np.asarray(value)
        if array.shape != (3,) or array.dtype.kind not in "iuf" or not np.all(np.isfinite(array)):
            raise ValueError("平移误差输入须为有限实数 (3,) 向量，单位米")
        values.append(array.astype(float))
    return float(np.linalg.norm(values[0] - values[1]))


@dataclass(frozen=True)
class PoseError:
    rotation_rad: float
    translation_m: float

    @property
    def rotation_deg(self):
        return float(np.rad2deg(self.rotation_rad))

    @property
    def translation_mm(self):
        return self.translation_m * 1000


def pose_error(estimate, reference):
    """比较同方向、同单位的两个 4×4 位姿，不把异单位残差混在一起。"""
    estimate, reference = validate_transform(estimate), validate_transform(reference)
    return PoseError(rotation_error_rad(estimate[:3, :3], reference[:3, :3]),
                     translation_error_m(estimate[:3, 3], reference[:3, 3]))
