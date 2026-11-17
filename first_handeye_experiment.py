"""眼在手上标定入门实验。在已知答案的仿真中估计相机安装位姿。"""

import argparse
from itertools import combinations

import numpy as np


def make_transform(rotation_vector_deg, translation_mm):
    """根据旋转向量和三维平移创建 4×4 刚体变换。"""
    transform = np.eye(4)
    transform[:3, 3] = translation_mm
    magnitude = np.linalg.norm(rotation_vector_deg)
    if magnitude != 0:
        x, y, z = rotation_vector_deg / magnitude
        angle = np.deg2rad(magnitude)
        cross = np.array([[0, -z, y], [z, 0, -x], [-y, x, 0]])
        transform[:3, :3] += np.sin(angle) * cross + (1 - np.cos(angle)) * (cross @ cross)
    return transform


def solve_hand_eye(gripper_to_base, board_to_camera):
    """用 AX=XB 求解相机到末端的旋转和平移。"""
    identity = np.eye(3)
    rotation_equations = []
    motion_pairs = []
    for i, j in combinations(range(len(gripper_to_base)), 2):
        a = np.linalg.solve(gripper_to_base[j], gripper_to_base[i])
        b = board_to_camera[j] @ np.linalg.inv(board_to_camera[i])
        motion_pairs.append((a, b))
        # 把 R_A R_X = R_X R_B 写成关于 R_X 九个元素的线性方程。
        rotation_equations.append(np.kron(identity, a[:3, :3]) - np.kron(b[:3, :3].T, identity))

    _, _, vectors = np.linalg.svd(np.vstack(rotation_equations), full_matrices=False)
    rotation = vectors[-1].reshape((3, 3), order="F")
    if np.linalg.det(rotation) < 0:
        rotation = -rotation
    u, _, vt = np.linalg.svd(rotation)
    rotation = u @ vt

    # 已知 R_X 后，用最小二乘解 (R_A - I) t_X = R_X t_B - t_A。
    lhs = np.vstack([a[:3, :3] - identity for a, _ in motion_pairs])
    rhs = np.concatenate([rotation @ b[:3, 3] - a[:3, 3] for a, b in motion_pairs])
    translation, *_ = np.linalg.lstsq(lhs, rhs, rcond=None)
    return rotation, translation


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--noise-mm", type=float, default=0.0, help="视觉位姿的每轴平移噪声标准差")
    args = parser.parse_args()
    if not np.isfinite(args.noise_mm) or args.noise_mm < 0:
        parser.error("--noise-mm 需要是有限且非负的数值")

    rng = np.random.default_rng(42)
    true_camera_to_gripper = make_transform(np.array([8, -12, 20]), [30, -20, 70])
    board_to_base = np.eye(4)
    board_to_base[:3, 3] = [0, 0, 800]

    gripper_to_base = []
    board_to_camera = []
    for _ in range(15):
        arm_pose = make_transform(rng.uniform(-18, 18, 3), rng.uniform(-60, 60, 3))
        # 标定板固定：末端到基座 × 相机到末端 × 板到相机 = 板到基座。
        observed_board = np.linalg.solve(arm_pose @ true_camera_to_gripper, board_to_base)
        gripper_to_base.append(arm_pose)
        board_to_camera.append(observed_board)

    for observed_board in board_to_camera:
        observed_board[:3, 3] += rng.normal(0, args.noise_mm, 3)

    rotation, translation = solve_hand_eye(gripper_to_base, board_to_camera)
    translation_error = np.linalg.norm(translation - true_camera_to_gripper[:3, 3])
    delta = true_camera_to_gripper[:3, :3].T @ rotation
    skew = delta - delta.T
    sine = np.linalg.norm([skew[2, 1], skew[0, 2], skew[1, 0]]) / 2
    cosine = (np.trace(delta) - 1) / 2
    angle_error = np.rad2deg(np.arctan2(sine, cosine))

    print(f"仿真采样：{len(gripper_to_base)} 组 | 视觉平移噪声：{args.noise_mm:g} mm（每轴标准差）")
    print("相机在末端坐标系下的真实位置 (mm)：", true_camera_to_gripper[:3, 3])
    print("相机在末端坐标系下的估计位置 (mm)：", np.round(translation, 6))
    print(f"平移误差：{translation_error:.6f} mm | 旋转误差：{angle_error:.6f} 度")


if __name__ == "__main__":
    main()
