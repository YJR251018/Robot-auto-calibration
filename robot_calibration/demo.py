"""Deterministic synthetic images and paired robot poses for a complete offline demo."""

from contextlib import ExitStack
from pathlib import Path

import cv2
import numpy as np

from .calibration import Chessboard, Intrinsics
from .data import write_json
from .geometry import MODES, make_transform


DEMO_BOARD = Chessboard()
DEMO_INTRINSICS = Intrinsics(np.array([[925., 0, 482], [0, 905., 357], [0, 0, 1]]), np.zeros(5), (960, 720))


def chessboard_texture(board, tile=64):
    """Return a checkerboard with a white border exactly one square wide."""
    texture = np.full(((board.rows + 3) * tile, (board.columns + 3) * tile), 245, dtype=np.uint8)
    for row in range(board.rows + 1):
        for column in range(board.columns + 1):
            if (row + column) % 2 == 0:
                texture[(row + 1) * tile:(row + 2) * tile, (column + 1) * tile:(column + 2) * tile] = 15
    return texture


def demo_views(board, intrinsics, seed):
    """Produce 15 views with varied tilt, roll, apparent size and image position."""
    texture = chessboard_texture(board)
    height, width = texture.shape
    source = np.float32([[-.5, -.5], [width - .5, -.5], [width - .5, height - .5], [-.5, height - .5]])
    board_width, board_height = (board.columns + 1) * board.square_mm, (board.rows + 1) * board.square_mm
    margin = board.square_mm
    outer = np.float64([
        [-2 * margin, -2 * margin, 0], [board_width, -2 * margin, 0],
        [board_width, board_height, 0], [-2 * margin, board_height, 0],
    ])
    center = board.points().mean(axis=0)
    rng = np.random.default_rng(seed)
    views = []
    for index in range(250):
        euler_like = rng.uniform([-34, -36, -34], [34, 36, 34])
        if index % 6 == 4:
            euler_like[2] += 145
        rotation = make_transform(euler_like, [0, 0, 0])[:3, :3]
        translation = rng.uniform([-121, -91, 385], [121, 91, 725]) - rotation @ center
        rvec = cv2.Rodrigues(rotation)[0]
        projected, _ = cv2.projectPoints(outer, rvec, translation, intrinsics.matrix, intrinsics.distortion)
        projected = projected.reshape(4, 2)
        size = np.array(intrinsics.image_size)
        if (projected < 13).any() or (projected > size - 13).any():
            continue
        warp = cv2.getPerspectiveTransform(source, projected.astype(np.float32))
        image = cv2.warpPerspective(texture, warp, intrinsics.image_size, borderValue=166)
        image = cv2.GaussianBlur(image, (3, 3), 0.55)
        observed = np.eye(4)
        observed[:3, :3] = rotation
        observed[:3, 3] = translation
        views.append((image, observed))
        if len(views) == 15:
            return views
    raise RuntimeError("未能生成完整的演示数据集。")


def generate_demo(directory, mode):
    if mode not in MODES:
        raise ValueError("请选择有效的演示模式。")
    destination = Path(directory)
    destination.mkdir(parents=True, exist_ok=True)
    if any(destination.iterdir()):
        raise ValueError(f"演示目录必须是空目录 {destination}")

    if mode == "eye-in-hand":
        mount = make_transform([8, -12, 20], [30, -20, 70])
        fixed_board = make_transform([6, 9, -17], [420, -220, 680])
    else:
        mount = make_transform([-5, 16, 13], [530, 100, 590])
        fixed_board = make_transform([3, 7, -11], [20, -35, 110])

    with ExitStack() as rollback:
        images = destination / "images"
        images.mkdir()
        rollback.callback(images.rmdir)
        samples = []
        seed = 27 if mode == "eye-in-hand" else 71
        inverse_mount = np.linalg.inv(mount)
        inverse_board = np.linalg.inv(fixed_board)
        for index, (image, observed) in enumerate(demo_views(DEMO_BOARD, DEMO_INTRINSICS, seed), 1):
            path = images / f"view_{index:02d}.png"
            success, encoded = cv2.imencode(".png", image)
            if not success:
                raise RuntimeError(f"无法写入演示图像 {path.name}。")
            rollback.callback(path.unlink, missing_ok=True)
            encoded.tofile(path)
            if mode == "eye-in-hand":
                arm_pose = fixed_board @ np.linalg.inv(observed) @ inverse_mount
            else:
                arm_pose = mount @ observed @ inverse_board
            samples.append({"image": path.name, "matrix": arm_pose.tolist()})

        for name in ("poses.json", "intrinsics.json", "candidate_poses.json", "truth.json"):
            rollback.callback((destination / name).unlink, missing_ok=True)
        write_json(destination / "poses.json", {"frame": "gripper_to_base", "length_unit": "mm", "samples": samples})
        write_json(destination / "intrinsics.json", DEMO_INTRINSICS.record())
        if mode == "eye-in-hand":
            write_demo_candidates(destination, fixed_board, mount)
        write_json(destination / "truth.json", {
            "mode": mode, "from_frame": "camera", "to_frame": MODES[mode], "length_unit": "mm",
            "matrix": mount.tolist(),
        })
        rollback.pop_all()
    return destination


def write_demo_candidates(destination, fixed_board, mount):
    new_views = [pose for _, pose in demo_views(DEMO_BOARD, DEMO_INTRINSICS, seed=28)[:6]]
    named_views = [(f"candidate-{index:02d}", view) for index, view in enumerate(new_views, 1)]
    outside = new_views[0].copy()
    outside[0, 3] += 1200
    behind = new_views[0].copy()
    behind[2, 3] -= 1800
    named_views.extend([("candidate-outside", outside), ("candidate-behind", behind)])
    inverse_mount = np.linalg.inv(mount)
    candidates = [
        {"id": name, "matrix": (fixed_board @ np.linalg.inv(view) @ inverse_mount).tolist()}
        for name, view in named_views
    ]
    write_json(destination / "candidate_poses.json", {
        "frame": "gripper_to_base", "length_unit": "mm", "candidates": candidates,
    })
