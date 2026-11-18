import shutil
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import cv2
import numpy as np

from robot_calibration.calibration import (
    Chessboard, Intrinsics, calibrate_intrinsics, compare_truth, estimate_mount, find_corners,
)
from robot_calibration.data import list_images, load_pose_pairs, read_json, write_json
from robot_calibration.demo import DEMO_BOARD, DEMO_INTRINSICS, demo_views, generate_demo
from robot_calibration.experiment import compare_rotation_spread
from robot_calibration.geometry import make_transform, solve_mount
from robot_calibration.sampling import load_candidates, recommend_poses


class CalibrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = cls.enterClassContext(TemporaryDirectory(prefix="calibration-tests-"))
        cls.root = Path(root)
        cls.demo = {
            mode: generate_demo(cls.root / "中文样例" / mode, mode)
            for mode in ("eye-in-hand", "eye-to-hand")
        }

    def test_both_modes_from_images_recover_known_transforms(self):
        for mode, target in (("eye-in-hand", "gripper"), ("eye-to-hand", "base")):
            with self.subTest(mode=mode):
                root = self.demo[mode]
                original_intrinsics = Intrinsics.from_record(read_json(root / "intrinsics.json"))
                pairs = load_pose_pairs(root / "poses.json", root / "images")
                result = estimate_mount(mode, pairs, DEMO_BOARD, original_intrinsics)
                self.assertEqual(result["from_frame"], "camera")
                self.assertEqual(result["to_frame"], target)
                self.assertEqual(sum(item["accepted"] for item in result["views"]), 15)
                error = compare_truth(result, read_json(root / "truth.json"))
                self.assertLess(error["translation_mm"], 1.0)
                self.assertLess(error["rotation_deg"], 0.1)

    def test_intrinsics_export_can_be_reimported(self):
        root = self.demo["eye-in-hand"]
        result = calibrate_intrinsics(list_images(root / "images"), DEMO_BOARD)
        output = self.root / "内参结果.json"
        write_json(output, result)
        reread = Intrinsics.from_record(read_json(output))
        self.assertEqual(reread.image_size, DEMO_INTRINSICS.image_size)
        self.assertLess(result["reprojection_rms_px"], 0.2)
        self.assertLess(max(row["reprojection_rms_px"] for row in result["views"]), 0.25)
        np.testing.assert_allclose(reread.matrix, DEMO_INTRINSICS.matrix, atol=10)

    def test_180_degree_view_uses_the_same_physical_target_corner(self):
        image, _ = demo_views(DEMO_BOARD, DEMO_INTRINSICS, 27)[0]
        original = find_corners(image, DEMO_BOARD, orient=True)
        rotated = find_corners(cv2.rotate(image, cv2.ROTATE_180), DEMO_BOARD, orient=True)
        target = np.array([image.shape[1] - 1, image.shape[0] - 1]) - original
        np.testing.assert_allclose(rotated, target, atol=0.3)

    def test_missing_and_unpaired_images_are_reported(self):
        source = self.demo["eye-in-hand"]
        folder = self.root / "配对检查"
        folder.mkdir()
        images = folder / "images"
        shutil.copytree(source / "images", images)
        (images / "view_01.png").unlink()
        shutil.copyfile(images / "view_02.png", images / "额外图片.png")
        pairs = load_pose_pairs(source / "poses.json", images)
        result = estimate_mount("eye-in-hand", pairs, DEMO_BOARD, DEMO_INTRINSICS)
        rejected = {entry["image"]: entry["reason"] for entry in result["views"] if not entry["accepted"]}
        self.assertEqual(set(rejected), {"view_01.png", "额外图片.png"})
        self.assertIn("缺少配对", rejected["额外图片.png"])

    def test_rejects_duplicate_pose_filenames(self):
        root = self.demo["eye-in-hand"]
        manifest = read_json(root / "poses.json")
        manifest["samples"].append(dict(manifest["samples"][0], image="VIEW_01.PNG"))
        path = self.root / "duplicates.json"
        write_json(path, manifest)
        with self.assertRaisesRegex(ValueError, "重复"):
            load_pose_pairs(path, root / "images")

    def test_rejects_pose_with_wrong_unit(self):
        root = self.demo["eye-in-hand"]
        manifest = read_json(root / "poses.json")
        manifest["length_unit"] = "m"
        path = self.root / "base-in-metres.json"
        write_json(path, manifest)
        with self.assertRaisesRegex(ValueError, "length_unit"):
            load_pose_pairs(path, root / "images")

    def test_same_axis_motion_is_rejected(self):
        mount = make_transform([8, -12, 20], [30, -20, 70])
        board_in_base = make_transform([0, 0, 0], [0, 0, 800])
        arm_poses = [make_transform([angle, 0, 0], [0, 0, 0]) for angle in (5, 15, 25, 35, 50)]
        board_poses = [np.linalg.solve(arm @ mount, board_in_base) for arm in arm_poses]
        with self.assertRaisesRegex(ValueError, "旋转方向不足"):
            solve_mount("eye-in-hand", arm_poses, board_poses)

    def test_hand_eye_rejects_ambiguous_board_and_threshold(self):
        with self.assertRaisesRegex(ValueError, "一奇一偶"):
            estimate_mount("eye-in-hand", [], Chessboard(8, 6, 24), DEMO_INTRINSICS)
        with self.assertRaisesRegex(ValueError, "误差上限"):
            estimate_mount("eye-in-hand", [], DEMO_BOARD, DEMO_INTRINSICS, float("nan"))

    def test_pose_recommendation_filters_out_of_view_and_ranks_visible_poses(self):
        root = self.demo["eye-in-hand"]
        pairs = load_pose_pairs(root / "poses.json", root / "images")
        output = estimate_mount("eye-in-hand", pairs, DEMO_BOARD, DEMO_INTRINSICS)
        candidates = load_candidates(read_json(root / "candidate_poses.json"))
        ranking = recommend_poses(output, pairs, candidates, min_margin_px=10.0)
        self.assertGreaterEqual(len(ranking["ranked"]), 5)
        self.assertFalse(ranking["robot_path_checked"])
        rejected = {row["id"]: row for row in ranking["rejected"]}
        self.assertLess(rejected["candidate-outside"]["projected_margin_px"], 0)
        self.assertIsNone(rejected["candidate-behind"]["projected_margin_px"])
        scores = [row["rotation_information_gain"] for row in ranking["ranked"]]
        self.assertGreater(scores[0], scores[-1])
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_legacy_demo_reproduces_documented_noise_result(self):
        root = Path(__file__).resolve().parents[1]
        run = subprocess.run(
            [sys.executable, "-X", "utf8", str(root / "first_handeye_experiment.py"), "--noise-mm", "1"],
            capture_output=True, encoding="utf-8", check=True,
        )
        self.assertIn("1.909793 mm", run.stdout)

    def test_noiseless_rotation_experiment_recovers_truth_in_both_scenarios(self):
        output = compare_rotation_spread(2, translation_noise_mm=0, rotation_noise_deg=0)
        self.assertEqual(len(output["trials"]), 4)
        for row in output["trials"]:
            self.assertLess(row["translation_mm"], 1e-7)
            self.assertLess(row["rotation_deg"], 1e-7)

    def test_failed_demo_generation_allows_retry(self):
        destination = self.root / "retry-demo"
        with patch("robot_calibration.demo.write_json", side_effect=PermissionError("test failure")):
            with self.assertRaises(PermissionError):
                generate_demo(destination, "eye-to-hand")
        self.assertEqual(list(destination.iterdir()), [])
        generate_demo(destination, "eye-to-hand")
        self.assertTrue((destination / "truth.json").is_file())


if __name__ == "__main__":
    unittest.main()
