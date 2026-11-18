"""Rank offline eye-in-hand candidate poses by visibility and rotational observability."""

from itertools import combinations

import cv2
import numpy as np

from .calibration import Chessboard, Intrinsics
from .geometry import checked_transform


def load_candidates(record):
    if record.get("frame") != "gripper_to_base" or record.get("length_unit") != "mm":
        raise ValueError("候选文件必须声明 frame 为 gripper_to_base，length_unit 为 mm。")
    candidates = record.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise ValueError("候选文件必须提供非空的 candidates 列表。")
    ids, result = set(), []
    for item in candidates:
        identifier = item.get("id") if isinstance(item, dict) else None
        if not isinstance(identifier, str) or not identifier.strip() or identifier in ids:
            raise ValueError("每个候选位姿必须有不同的非空字符串 id。")
        ids.add(identifier)
        result.append((identifier, checked_transform(item.get("matrix"), identifier)))
    return result


def board_outline(board):
    """Use the four sides of the full checkerboard, including its one-square white border."""
    xs = np.linspace(-2 * board.square_mm, (board.columns + 1) * board.square_mm, 9)
    ys = np.linspace(-2 * board.square_mm, (board.rows + 1) * board.square_mm, 9)
    edges = np.concatenate([
        np.column_stack([xs, np.full_like(xs, y)]) for y in (ys[0], ys[-1])
    ] + [
        np.column_stack([np.full_like(ys, x), ys]) for x in (xs[0], xs[-1])
    ])
    return np.column_stack([edges, np.zeros(len(edges))])


def image_margin(board_to_camera, outline, intrinsics):
    rotation = board_to_camera[:3, :3]
    translation = board_to_camera[:3, 3]
    camera_points = outline @ rotation.T + translation
    if (camera_points[:, 2] <= 0).any():
        return None, "棋盘格部分位于相机后方"
    if np.dot(rotation[:, 2], camera_points.mean(axis=0)) <= 0:
        return None, "相机看向棋盘格背面"
    projected, _ = cv2.projectPoints(
        outline, cv2.Rodrigues(rotation)[0], translation, intrinsics.matrix, intrinsics.distortion
    )
    pixels = projected.reshape(-1, 2)
    if not np.isfinite(pixels).all():
        return None, "投影坐标不是有限数值"
    return float(min(pixels.min(), (np.array(intrinsics.image_size) - 1 - pixels).min())), ""


def motion_information(first, second):
    equation = first.T @ second - np.eye(3)
    return equation.T @ equation


def recommend_poses(calibration, pairs, candidates, min_margin_px=18.0):
    if calibration.get("mode") != "eye-in-hand" or calibration.get("to_frame") != "gripper":
        raise ValueError("位姿推荐需要眼在手上的手眼结果。")
    if calibration.get("from_frame") != "camera" or calibration.get("length_unit") != "mm":
        raise ValueError("手眼结果必须表示毫米为单位的相机到末端变换。")
    if not np.isfinite(min_margin_px) or min_margin_px < 0:
        raise ValueError("图像边距应是非负的有限像素值。")

    try:
        board = Chessboard(**calibration["chessboard"])
        intrinsics = Intrinsics.from_record(calibration["intrinsics"])
        fixed = calibration["fixed_board_estimate"]
        if fixed.get("to_frame") != "base":
            raise ValueError("眼在手上需要标定板到基座的估计变换。")
        fixed_board = checked_transform(fixed["matrix"], "棋盘格到基座")
        mount = checked_transform(calibration["matrix"], "相机到末端")
        used = {view["image"].casefold() for view in calibration["views"] if view["accepted"]}
    except (KeyError, TypeError, AttributeError) as exc:
        raise ValueError("手眼结果缺少位姿推荐需要的标定数据。") from exc

    rotations = [pose[:3, :3] for path, pose in pairs if pose is not None and path.name.casefold() in used]
    if len(rotations) != len(used) or len(rotations) < 3:
        raise ValueError("请提供当次标定使用的全套机器人位姿。")
    information = sum((motion_information(a, b) for a, b in combinations(rotations, 2)), np.zeros((3, 3)))
    baseline = np.linalg.eigvalsh(information)[0]
    outline = board_outline(board)
    camera_inverse = np.linalg.inv(mount)
    accepted, rejected = [], []
    for identifier, candidate in candidates:
        camera_pose = camera_inverse @ np.linalg.solve(candidate, fixed_board)
        margin, reason = image_margin(camera_pose, outline, intrinsics)
        row = {"id": identifier, "projected_margin_px": margin}
        if margin is None or margin < min_margin_px:
            row["reason"] = reason or "棋盘格出画或图像边距不足"
            rejected.append(row)
            continue
        updated = information + sum(motion_information(rotation, candidate[:3, :3]) for rotation in rotations)
        row["rotation_information_gain"] = float(max(0, np.linalg.eigvalsh(updated)[0] - baseline))
        accepted.append(row)

    accepted.sort(key=lambda row: (-row["rotation_information_gain"], -row["projected_margin_px"], row["id"]))
    return {
        "schema_version": 1, "mode": "eye-in-hand", "min_margin_px": min_margin_px,
        "source_accepted_views": len(rotations), "robot_path_checked": False,
        "ranked": accepted, "rejected": rejected,
    }
