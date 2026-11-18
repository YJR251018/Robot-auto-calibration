"""GUI and command-line entry points for the calibration workbench."""

import argparse
from pathlib import Path

import cv2
import numpy as np

from .calibration import CalibrationError, Chessboard, Intrinsics, calibrate_intrinsics, compare_truth, estimate_mount
from .data import list_images, load_pose_pairs, read_json, write_json
from .demo import generate_demo
from .geometry import MODES
from .sampling import load_candidates, recommend_poses


def main():
    parser = argparse.ArgumentParser(description="机器人相机标定工作台")
    commands = parser.add_subparsers(dest="command")
    commands.add_parser("gui", help="打开桌面工作台")
    demo = commands.add_parser("demo", help="生成一组含模拟图像的演示数据")
    demo.add_argument("mode", choices=MODES)
    demo.add_argument("directory", type=Path)
    recommend = commands.add_parser("recommend", help="离线筛选并排序眼在手上候选位姿")
    recommend.add_argument("--calibration", type=Path, required=True)
    recommend.add_argument("--poses", type=Path, required=True)
    recommend.add_argument("--images", type=Path, required=True)
    recommend.add_argument("--candidates", type=Path, required=True)
    recommend.add_argument("--out", type=Path, required=True)
    recommend.add_argument("--min-margin-px", type=float, default=18.0)
    intrinsics_parser = commands.add_parser("intrinsics", help="标定单目相机内参")
    hand_eye = commands.add_parser("hand-eye", help="估计手眼变换")
    hand_eye.add_argument("mode", choices=MODES)
    hand_eye.add_argument("--poses", type=Path, required=True)
    hand_eye.add_argument("--intrinsics", type=Path, required=True)
    hand_eye.add_argument("--max-reprojection-px", type=float, default=1.0)
    hand_eye.add_argument("--truth", type=Path, help="与演示真值比较")
    for command in (intrinsics_parser, hand_eye):
        command.add_argument("--images", type=Path, required=True)
        command.add_argument("--out", type=Path, required=True)
        command.add_argument("--columns", type=int, default=9, help="每行内角点数")
        command.add_argument("--rows", type=int, default=6, help="每列内角点数")
        command.add_argument("--square-mm", type=float, default=24.0, help="方格边长（毫米）")

    args = parser.parse_args()
    try:
        if args.command in (None, "gui"):
            from .app import launch

            launch()
            return
        if args.command == "demo":
            print(generate_demo(args.directory, args.mode).resolve())
            return
        if args.command == "recommend":
            ranking = recommend_poses(
                read_json(args.calibration), load_pose_pairs(args.poses, args.images),
                load_candidates(read_json(args.candidates)), args.min_margin_px,
            )
            write_json(args.out, ranking)
            print(f"视野通过 {len(ranking['ranked'])}，拒绝 {len(ranking['rejected'])}。输出 {args.out.resolve()}")
            return
        board = Chessboard(args.columns, args.rows, args.square_mm)
        if args.command == "intrinsics":
            result = calibrate_intrinsics(list_images(args.images), board)
        else:
            intrinsics = Intrinsics.from_record(read_json(args.intrinsics))
            pairs = load_pose_pairs(args.poses, args.images)
            result = estimate_mount(args.mode, pairs, board, intrinsics, args.max_reprojection_px)
            if args.truth:
                result["synthetic_truth_error"] = compare_truth(result, read_json(args.truth))
        write_json(args.out, result)
        print(f"有效观测 {sum(view['accepted'] for view in result['views'])} / {len(result['views'])}")
        print(f"结果已写入 {args.out.resolve()}")
    except CalibrationError as exc:
        reasons = [f"  {view['image']}：{view['reason']}" for view in exc.views if view.get("reason")]
        parser.exit(1, f"标定失败：{exc}\n" + "\n".join(reasons) + "\n")
    except (ValueError, OSError, cv2.error, np.linalg.LinAlgError) as exc:
        parser.exit(1, f"标定失败：{exc}\n")


if __name__ == "__main__":
    main()
