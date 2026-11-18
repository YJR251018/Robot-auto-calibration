"""Paired simulation of rotation-axis coverage under matched measurement noise."""

import argparse
from pathlib import Path

import numpy as np

from .data import write_json
from .geometry import make_transform, solve_mount, transform_error


def unit_rows(vectors):
    return vectors / np.linalg.norm(vectors, axis=1, keepdims=True)


def compare_rotation_spread(trials, seed=42, translation_noise_mm=1.0, rotation_noise_deg=0.1):
    if trials < 1:
        raise ValueError("试验次数至少为 1。")
    rng = np.random.default_rng(seed)
    sample_count = 15
    true_mount = make_transform([8, -12, 20], [30, -20, 70])
    board_to_base = make_transform([0, 0, 0], [0, 0, 800])
    results = []
    for trial in range(trials):
        # Match the angle magnitudes, translations and noise realizations per trial.
        angles = rng.uniform(-26, 26, sample_count)
        translations = rng.uniform(-60, 60, (sample_count, 3))
        rotations_noise = rng.normal(0, rotation_noise_deg, (sample_count, 3))
        positions_noise = rng.normal(0, translation_noise_mm, (sample_count, 3))
        direction_jitter = rng.normal(0, 0.055, (sample_count, 2))
        directions = {
            "clustered": unit_rows(np.column_stack([np.ones(sample_count), direction_jitter])),
            "spread": unit_rows(rng.normal(size=(sample_count, 3))),
        }
        for scenario, axes in directions.items():
            arm_poses, observed_poses = [], []
            for index, axis in enumerate(axes):
                arm_pose = make_transform(angles[index] * axis, translations[index])
                observed = np.linalg.solve(arm_pose @ true_mount, board_to_base)
                rotation_error = make_transform(rotations_noise[index], [0, 0, 0])
                observed[:3, :3] = rotation_error[:3, :3] @ observed[:3, :3]
                observed[:3, 3] += positions_noise[index]
                arm_poses.append(arm_pose)
                observed_poses.append(observed)
            estimate, _ = solve_mount("eye-in-hand", arm_poses, observed_poses)
            results.append({"trial": trial + 1, "scenario": scenario, **transform_error(true_mount, estimate)})

    summary = {}
    for scenario in ("clustered", "spread"):
        summary[scenario] = {}
        for metric in ("translation_mm", "rotation_deg"):
            estimates = [row[metric] for row in results if row["scenario"] == scenario]
            median, p90 = np.percentile(estimates, [50, 90])
            summary[scenario][metric] = {"median": float(median), "p90": float(p90)}
    return {
        "seed": seed, "trial_count": trials, "samples_per_trial": sample_count,
        "per_axis_translation_sigma_mm": translation_noise_mm, "per_axis_rotation_sigma_deg": rotation_noise_deg,
        "scenario_summary": summary, "trials": results,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trials", type=int, default=40)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.trials < 1 or args.seed < 0:
        parser.error("--trials 必须至少为 1，--seed 必须是非负整数。")
    result = compare_rotation_spread(args.trials, args.seed)
    write_json(args.out, result)
    for scenario, summary in result["scenario_summary"].items():
        print(f"{scenario}: 平移误差中位数 {summary['translation_mm']['median']:.3f} mm; "
              f"旋转误差中位数 {summary['rotation_deg']['median']:.3f}°")


if __name__ == "__main__":
    main()
