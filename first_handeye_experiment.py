"""眼在手上标定入门实验。在已知答案的仿真中估计相机安装位姿。"""

import argparse
import numpy as np

from robot_calibration.geometry import make_transform, solve_hand_eye, transform_error


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
    estimated = np.eye(4)
    estimated[:3, :3] = rotation
    estimated[:3, 3] = translation
    error = transform_error(true_camera_to_gripper, estimated)

    print(f"仿真采样：{len(gripper_to_base)} 组 | 视觉平移噪声：{args.noise_mm:g} mm（每轴标准差）")
    print("相机在末端坐标系下的真实位置 (mm)：", true_camera_to_gripper[:3, 3])
    print("相机在末端坐标系下的估计位置 (mm)：", np.round(translation, 6))
    print(f"平移误差：{error['translation_mm']:.6f} mm | 旋转误差：{error['rotation_deg']:.6f} 度")


if __name__ == "__main__":
    main()
