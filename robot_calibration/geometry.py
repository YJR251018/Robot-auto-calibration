"""Rigid transforms and the shared AX=XB solver."""

from itertools import combinations

import numpy as np


MODES = {"eye-in-hand": "gripper", "eye-to-hand": "base"}


def make_transform(rotation_vector_deg, translation_mm):
    """Construct a rigid transform from an axis-angle vector in degrees and a translation in mm."""
    transform = np.eye(4)
    transform[:3, 3] = translation_mm
    vector = np.asarray(rotation_vector_deg, dtype=float)
    magnitude = np.linalg.norm(vector)
    if magnitude != 0:
        x, y, z = vector / magnitude
        angle = np.deg2rad(magnitude)
        cross = np.array([[0, -z, y], [z, 0, -x], [-y, x, 0]])
        transform[:3, :3] += np.sin(angle) * cross + (1 - np.cos(angle)) * (cross @ cross)
    return transform


def checked_transform(value, label):
    try:
        transform = np.asarray(value, dtype=float)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{label}必须是 4 × 4 数值矩阵。") from exc
    if transform.shape != (4, 4) or not np.isfinite(transform).all():
        raise ValueError(f"{label}必须是有限的 4 × 4 数值矩阵。")
    if not np.allclose(transform[3], [0, 0, 0, 1], atol=1e-8, rtol=0):
        raise ValueError(f"{label}最后一行必须是 [0, 0, 0, 1]。")
    rotation = transform[:3, :3]
    if not np.allclose(rotation.T @ rotation, np.eye(3), atol=1e-4, rtol=0) or not np.isclose(
        np.linalg.det(rotation), 1, atol=1e-4, rtol=0
    ):
        raise ValueError(f"{label}的左上角必须是有效的三维旋转矩阵。")
    return transform


def rotation_angle_deg(rotation):
    skew = rotation - rotation.T
    sine = np.linalg.norm([skew[2, 1], skew[0, 2], skew[1, 0]]) / 2
    cosine = (np.trace(rotation) - 1) / 2
    return float(np.rad2deg(np.arctan2(sine, cosine)))


def transform_error(reference, estimated):
    return {
        "translation_mm": float(np.linalg.norm(estimated[:3, 3] - reference[:3, 3])),
        "rotation_deg": rotation_angle_deg(reference[:3, :3].T @ estimated[:3, :3]),
    }


def solve_hand_eye(gripper_to_base, board_to_camera):
    """Solve AX=XB from matched absolute poses; return the rotation and translation."""
    if len(gripper_to_base) != len(board_to_camera) or len(gripper_to_base) < 3:
        raise ValueError("手眼标定至少需要 3 组一一配对的位姿。")

    identity = np.eye(3)
    motion_pairs = []
    rotation_equations = []
    for i, j in combinations(range(len(gripper_to_base)), 2):
        a = np.linalg.solve(gripper_to_base[j], gripper_to_base[i])
        b = board_to_camera[j] @ np.linalg.inv(board_to_camera[i])
        motion_pairs.append((a, b))
        # Column-major vectorization of R_A R_X = R_X R_B.
        rotation_equations.append(np.kron(identity, a[:3, :3]) - np.kron(b[:3, :3].T, identity))

    _, singular_values, vectors = np.linalg.svd(np.vstack(rotation_equations), full_matrices=False)
    if singular_values[-2] <= singular_values[0] * 1e-9:
        raise ValueError("旋转方向不足，无法唯一求解。请补采绕不同轴旋转的位姿。")
    rotation = vectors[-1].reshape((3, 3), order="F")
    if np.linalg.det(rotation) < 0:
        rotation = -rotation
    u, _, vt = np.linalg.svd(rotation)
    rotation = u @ vt

    # With R_X known, solve (R_A - I) t_X = R_X t_B - t_A.
    lhs = np.vstack([a[:3, :3] - identity for a, _ in motion_pairs])
    rhs = np.concatenate([rotation @ b[:3, 3] - a[:3, 3] for a, b in motion_pairs])
    translation, _, rank, _ = np.linalg.lstsq(lhs, rhs, rcond=1e-9)
    if rank < 3:
        raise ValueError("位姿变化不足，无法唯一求解平移。请补采绕不同轴旋转的位姿。")
    return rotation, translation


def solve_mount(mode, gripper_to_base, board_to_camera):
    """Return camera-to-gripper or camera-to-base, plus the fixed-board pose estimates."""
    if mode not in MODES:
        raise ValueError(f"未知的手眼标定模式 {mode!r}。")
    reference_poses = gripper_to_base if mode == "eye-in-hand" else [
        np.linalg.inv(pose) for pose in gripper_to_base
    ]
    rotation, translation = solve_hand_eye(reference_poses, board_to_camera)
    mount = np.eye(4)
    mount[:3, :3] = rotation
    mount[:3, 3] = translation
    fixed_board_poses = [
        reference @ mount @ observed for reference, observed in zip(reference_poses, board_to_camera, strict=True)
    ]
    return mount, fixed_board_poses
