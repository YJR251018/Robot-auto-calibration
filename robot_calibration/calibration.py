"""Chessboard detection, camera intrinsics and offline hand–eye calibration."""

from dataclasses import dataclass
from itertools import combinations
from pathlib import Path

import cv2
import numpy as np

from .geometry import MODES, checked_transform, rotation_angle_deg, solve_mount, transform_error


class CalibrationError(ValueError):
    def __init__(self, message, views):
        super().__init__(message)
        self.views = views


@dataclass(frozen=True)
class Chessboard:
    columns: int = 9
    rows: int = 6
    square_mm: float = 24.0

    def __post_init__(self):
        if type(self.columns) is not int or type(self.rows) is not int or min(self.columns, self.rows) < 3:
            raise ValueError("棋盘格至少需要 3 列和 3 行内角点。")
        if type(self.square_mm) not in (float, int) or not np.isfinite(self.square_mm) or self.square_mm <= 0:
            raise ValueError("方格边长必须是毫米为单位的正数。")

    @property
    def pattern(self):
        return self.columns, self.rows

    def points(self):
        points = np.zeros((self.rows * self.columns, 3), dtype=np.float32)
        points[:, :2] = np.indices((self.rows, self.columns))[::-1].reshape(2, -1).T * self.square_mm
        return points


@dataclass(frozen=True)
class Intrinsics:
    matrix: np.ndarray
    distortion: np.ndarray
    image_size: tuple[int, int]

    @classmethod
    def from_record(cls, record):
        try:
            matrix = np.asarray(record["camera_matrix"], dtype=float)
            distortion = np.asarray(record["distortion"], dtype=float).ravel()
            size = record["image_size"]
        except (KeyError, TypeError, ValueError, OverflowError) as exc:
            raise ValueError("内参 JSON 应包含 camera_matrix、distortion 和 image_size。") from exc
        if (
            matrix.shape != (3, 3) or not np.isfinite(matrix).all()
            or matrix[0, 0] <= 0 or matrix[1, 1] <= 0
            or not np.allclose(matrix[[0, 1, 2, 2, 2], [1, 0, 0, 1, 2]], [0, 0, 0, 0, 1])
        ):
            raise ValueError("camera_matrix 必须是有效的 3 × 3 针孔相机内参矩阵。")
        if distortion.size not in {4, 5, 8, 12, 14} or not np.isfinite(distortion).all():
            raise ValueError("distortion 必须是 4、5、8、12 或 14 个有限数值。")
        if not isinstance(size, list) or len(size) != 2 or any(type(n) is not int or n < 1 for n in size):
            raise ValueError("image_size 必须是两个正整数 [宽, 高]。")
        return cls(matrix, distortion, tuple(size))

    def record(self):
        return {
            "camera_matrix": self.matrix.tolist(),
            "distortion": self.distortion.ravel().tolist(),
            "image_size": list(self.image_size),
        }


def read_image(path, color=False):
    data = np.fromfile(path, dtype=np.uint8)
    flag = cv2.IMREAD_COLOR if color else cv2.IMREAD_GRAYSCALE
    image = cv2.imdecode(data, flag) if data.size else None
    if image is None:
        raise ValueError("无法解码图像")
    return image


def find_corners(gray, board, orient=False):
    found, corners = cv2.findChessboardCornersSB(gray, board.pattern, flags=cv2.CALIB_CB_NORMALIZE_IMAGE)
    if not found:
        raise ValueError("未检测到完整棋盘格")
    if orient:
        # Opposite outer squares differ in intensity when one inner dimension is odd.
        grid = corners.reshape(board.rows, board.columns, 2)
        first = grid[0, 0] + 0.45 * (2 * grid[0, 0] - grid[0, 1] - grid[1, 0])
        last = grid[-1, -1] + 0.45 * (2 * grid[-1, -1] - grid[-1, -2] - grid[-2, -1])
        samples = []
        for xy in (first, last):
            x, y = np.round(xy).astype(int)
            if not (1 <= x < gray.shape[1] - 1 and 1 <= y < gray.shape[0] - 1):
                raise ValueError("棋盘格边缘出画，无法统一角点方向")
            samples.append(float(np.median(gray[y - 1:y + 2, x - 1:x + 2])))
        if abs(samples[0] - samples[1]) < 20:
            raise ValueError("棋盘格两端对比度不足，无法统一角点方向")
        if samples[0] > samples[1]:
            corners = corners[::-1].copy()
    return corners.reshape(-1, 1, 2)


def reprojection_rms(points, corners, rotation_vector, translation, intrinsics):
    projected, _ = cv2.projectPoints(points, rotation_vector, translation, intrinsics.matrix, intrinsics.distortion)
    differences = projected.reshape(-1, 2) - corners.reshape(-1, 2)
    return float(np.sqrt(np.mean(np.sum(differences**2, axis=1))))


def check_image(path, board, expected_size=None, orient=False):
    path = Path(path)
    entry = {"image": path.name, "accepted": False}
    try:
        gray = read_image(path)
        size = gray.shape[1], gray.shape[0]
        if expected_size is not None and size != expected_size:
            raise ValueError(f"图像尺寸 {size[0]} × {size[1]} 与 {expected_size[0]} × {expected_size[1]} 不一致")
        corners = find_corners(gray, board, orient)
    except (OSError, ValueError, cv2.error) as exc:
        entry["reason"] = str(exc)
        return entry, None, None
    entry["accepted"] = True
    return entry, corners, size


def calibrate_intrinsics(paths, board):
    records = []
    accepted = []
    corners = []
    image_size = None
    points = board.points()
    for path in paths:
        entry, observed, size = check_image(path, board, image_size)
        records.append(entry)
        if entry["accepted"]:
            if any(
                min(np.max(np.abs(observed - previous)), np.max(np.abs(observed - previous[::-1]))) < 0.1
                for previous in corners
            ):
                entry.update(accepted=False, reason="角点位置与已有照片重复")
                continue
            image_size = size
            accepted.append(entry)
            corners.append(observed)
    if len(accepted) < 5:
        raise CalibrationError(f"内参标定至少需要 5 张有效照片，目前有效 {len(accepted)} 张。", records)
    try:
        rms, matrix, distortion, rotations, translations = cv2.calibrateCamera(
            [points] * len(accepted), corners, image_size, None, None
        )
    except cv2.error as exc:
        raise CalibrationError("内参未能求解，请补采不同位置和倾角的图像。", records) from exc
    if not np.isfinite(rms):
        raise CalibrationError("内参求解误差异常，请补采不同位置和倾角的图像。", records)
    intrinsics = Intrinsics.from_record(Intrinsics(matrix, distortion, image_size).record())
    for entry, corners_i, rotation, translation in zip(accepted, corners, rotations, translations, strict=True):
        entry["reprojection_rms_px"] = reprojection_rms(points, corners_i, rotation, translation, intrinsics)
    return {
        "schema_version": 1, **intrinsics.record(), "reprojection_rms_px": float(rms), "views": records,
        "chessboard": {"columns": board.columns, "rows": board.rows, "square_mm": board.square_mm},
    }


def estimate_mount(mode, paired_paths, board, intrinsics, max_reprojection_px=1.0):
    if mode not in MODES:
        raise ValueError("请选择有效的手眼标定模式。")
    if (board.rows + board.columns) % 2 == 0:
        raise ValueError("手眼标定要求棋盘格的内角点行列数一奇一偶，以统一角点方向。")
    if not np.isfinite(max_reprojection_px) or max_reprojection_px <= 0:
        raise ValueError("重投影误差上限必须是大于零的有限像素值。")

    points = board.points()
    records, arm_poses, board_poses = [], [], []
    for path, arm_pose in paired_paths:
        if arm_pose is None:
            records.append({"image": path.name, "accepted": False, "reason": "缺少配对的末端位姿"})
            continue
        entry, corners, _ = check_image(path, board, intrinsics.image_size, orient=True)
        records.append(entry)
        if not entry["accepted"]:
            continue
        try:
            success, rotation_vector, translation = cv2.solvePnP(
                points, corners, intrinsics.matrix, intrinsics.distortion, flags=cv2.SOLVEPNP_ITERATIVE
            )
        except cv2.error:
            entry.update(accepted=False, reason="PnP 无法从该图像估计板位姿")
            continue
        if not success or not np.isfinite(translation).all() or not np.isfinite(rotation_vector).all():
            entry.update(accepted=False, reason="PnP 未得到有效板位姿")
            continue
        rotation = cv2.Rodrigues(rotation_vector)[0]
        if (points @ rotation.T + translation.ravel())[:, 2].min() <= 0:
            entry.update(accepted=False, reason="PnP 结果把角点置于相机后方")
            continue
        error = reprojection_rms(points, corners, rotation_vector, translation, intrinsics)
        if not np.isfinite(error):
            entry.update(accepted=False, reason="重投影误差无法计算")
            continue
        entry["reprojection_rms_px"] = error
        if error > max_reprojection_px:
            entry.update(accepted=False, reason="重投影误差超过设定上限")
            continue
        observed = np.eye(4)
        observed[:3, :3] = rotation
        observed[:3, 3] = translation.ravel()
        arm_poses.append(arm_pose)
        board_poses.append(observed)

    if len(arm_poses) < 3:
        raise CalibrationError(f"手眼标定至少需要 3 组有效的图像和位姿，目前有效 {len(arm_poses)} 组。", records)
    try:
        mount, fixed_pose_estimates = solve_mount(mode, arm_poses, board_poses)
    except (ValueError, np.linalg.LinAlgError) as exc:
        raise CalibrationError(str(exc), records) from exc
    positions = np.array([pose[:3, 3] for pose in fixed_pose_estimates])
    fixed_board = np.eye(4)
    fixed_board[:3, 3] = positions.mean(0)
    u, _, vt = np.linalg.svd(np.mean([pose[:3, :3] for pose in fixed_pose_estimates], axis=0))
    fixed_board[:3, :3] = u @ np.diag([1, 1, np.linalg.det(u @ vt)]) @ vt
    rotation_differences = [
        rotation_angle_deg(a[:3, :3].T @ b[:3, :3])
        for a, b in combinations(fixed_pose_estimates, 2)
    ]
    return {
        "schema_version": 1,
        "mode": mode,
        "from_frame": "camera",
        "to_frame": MODES[mode],
        "length_unit": "mm",
        "chessboard": {"columns": board.columns, "rows": board.rows, "square_mm": board.square_mm},
        "intrinsics": intrinsics.record(),
        "matrix": mount.tolist(),
        "fixed_board_estimate": {
            "to_frame": "base" if mode == "eye-in-hand" else "gripper", "matrix": fixed_board.tolist(),
        },
        "max_reprojection_px": max_reprojection_px,
        "views": records,
        "in_sample_consistency": {
            "board_frame": "base" if mode == "eye-in-hand" else "gripper",
            "position_rms_about_centroid_mm": float(np.sqrt(np.mean(np.sum((positions - positions.mean(0))**2, axis=1)))),
            "mean_pairwise_rotation_deg": float(np.mean(rotation_differences)),
        },
    }


def compare_truth(result, truth):
    for key in ("mode", "from_frame", "to_frame", "length_unit"):
        if result[key] != truth.get(key):
            raise ValueError(f"演示真值中的 {key} 与标定结果不一致。")
    return transform_error(checked_transform(truth.get("matrix"), "演示真值"), np.array(result["matrix"]))
