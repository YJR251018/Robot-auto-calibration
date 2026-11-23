"""OpenCV 适配器：仅接收观测，不接收仿真真值。"""

import cv2
import numpy as np
from scipy.spatial.transform import Rotation

from .transforms import make_transform, validate_transform

METHODS = {"PARK": cv2.CALIB_HAND_EYE_PARK, "TSAI": cv2.CALIB_HAND_EYE_TSAI}


class CalibrationError(RuntimeError):
    """求解器失败或返回非有限/非法刚体结果。"""


def pose_stack(poses, name="poses", minimum=3):
    """严格检查 (N,4,4) 观测，返回独立浮点副本。"""
    try:
        array = np.asarray(poses)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"{name} 必须为 (N,4,4) 实数数组") from exc
    if array.ndim != 3 or array.shape[1:] != (4, 4) or len(array) < minimum:
        raise ValueError(f"{name} 至少需要 {minimum} 帧，形状为 (N,4,4)")
    return np.stack([validate_transform(t) for t in array])


def motion_diagnostics(poses):
    """全帧对的运动激励数值诊断，不检查机器人可达性。

    至少两个独立旋转轴，且堆叠 (R_A-I) 为三列满秩。
    singular ratio <1e-3 被视为接近退化；不是通用精度保证。
    """
    poses = pose_stack(poses)
    rotation_vectors, translation_blocks = [], []
    for j in range(1, len(poses)):
        for i in range(j):
            relative_rotation = poses[j, :3, :3].T @ poses[i, :3, :3]
            vector = Rotation.from_matrix(relative_rotation).as_rotvec()
            if np.linalg.norm(vector) > 1e-8:
                rotation_vectors.append(vector)
            translation_blocks.append(relative_rotation - np.eye(3))
    vectors = np.asarray(rotation_vectors).reshape(-1, 3)
    axes = vectors / np.linalg.norm(vectors, axis=1, keepdims=True) if len(vectors) else np.zeros((3, 3))
    axis_s = np.pad(np.linalg.svd(axes, compute_uv=False), (0, max(0, 3-min(axes.shape))))[:3]
    trans_s = np.linalg.svd(np.vstack(translation_blocks), compute_uv=False)
    axis_ratio = float(axis_s[1] / axis_s[0]) if axis_s[0] > 0 else 0.0
    trans_ratio = float(trans_s[-1] / trans_s[0]) if trans_s[0] > 0 else 0.0
    return {
        "pair_count": len(translation_blocks),
        "rotation_axis_singular_values": axis_s.tolist(),
        "translation_design_singular_values": trans_s.tolist(),
        "axis_second_first_ratio": axis_ratio,
        "translation_min_max_ratio": trans_ratio,
        "nondegenerate": bool(axis_ratio >= 1e-3 and trans_ratio >= 1e-3),
    }


def calibrate_hand_eye(t_b_g, t_c_t, *, method="PARK"):
    """绝对位姿 T_B_G、T_C_T → 估计 T_G_C；平移均为米。

    R/t_gripper2base=G→B，R/t_target2cam=T→C，输出 cam2gripper=C→G。
    不生成观测，不访问 T_G_C 真值，不作真值相关初始化或结果替换。
    """
    if not isinstance(method, str) or method not in METHODS:
        raise ValueError(f"method 必须为 {tuple(METHODS)} 之一（大写）")
    gripper = pose_stack(t_b_g, "T_B_G")
    target = pose_stack(t_c_t, "T_C_T")
    if len(gripper) != len(target):
        raise ValueError("机器人位姿与相机观测必须一一配对，数量相等")
    if not motion_diagnostics(gripper)["nondegenerate"]:
        raise ValueError("机器人运动退化或近退化：需要不同方向的旋转激励")
    if not motion_diagnostics(target)["nondegenerate"]:
        raise ValueError("相机相对运动退化或近退化")
    try:
        rotation, translation = cv2.calibrateHandEye(
            [p[:3, :3].copy() for p in gripper],
            [p[:3, 3].reshape(3, 1).copy() for p in gripper],
            [p[:3, :3].copy() for p in target],
            [p[:3, 3].reshape(3, 1).copy() for p in target],
            method=METHODS[method],
        )
        return make_transform(rotation, np.asarray(translation).reshape(3))
    except (cv2.error, ValueError, TypeError) as exc:
        raise CalibrationError(f"OpenCV {method} 求解失败或结果非法: {exc}") from exc
