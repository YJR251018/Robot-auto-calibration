"""可复算实验：无噪声关卡、配对噪声/样本量、逐次结果与失败记录。"""

import csv
from dataclasses import asdict, dataclass, field
import hashlib
import json
from pathlib import Path
import platform

import cv2
import matplotlib
import numpy as np
import scipy

from .calibration import METHODS, calibrate_hand_eye, motion_diagnostics
from .metrics import pose_error
from .simulation import (SceneConfig, add_observation_noise, closure_error,
                         generate_dataset, nonnegative_integer, nonnegative_real)


@dataclass(frozen=True)
class ExperimentConfig:
    repeats: int = 30
    seed_start: int = 20261118
    noise_seed_start: int = 20271118
    noise_sample_count: int = 20
    sample_counts: tuple = (8, 12, 20)
    rotation_noise_deg: tuple = (0.0, 0.1, 0.3, 0.6, 1.0)
    translation_noise_mm: tuple = (0.0, 0.1, 0.5, 1.0, 2.0)
    sample_rotation_noise_deg: float = 0.3
    sample_translation_noise_mm: float = 0.5
    rotation_threshold_rad: float = 1e-6
    translation_threshold_m: float = 1e-6
    methods: tuple = ("PARK", "TSAI")
    scene: SceneConfig = field(default_factory=SceneConfig)

    def validate(self):
        if nonnegative_integer(self.repeats, "repeats") < 2:
            raise ValueError("重复次数至少为2，才能定义样本标准差")
        nonnegative_integer(self.seed_start, "seed_start")
        nonnegative_integer(self.noise_seed_start, "noise_seed_start")
        if nonnegative_integer(self.noise_sample_count, "noise_sample_count") < 15:
            raise ValueError("基准/噪声实验至少15帧")
        if not self.sample_counts or any(nonnegative_integer(n, "sample_counts") < 3 for n in self.sample_counts):
            raise ValueError("sample_counts 不得为空，且每项至少3帧")
        for name in ("sample_counts", "rotation_noise_deg", "translation_noise_mm", "methods"):
            values = getattr(self, name)
            if not values or len(set(values)) != len(values):
                raise ValueError(f"{name} 不得为空或包含重复项")
        for name in ("rotation_noise_deg", "translation_noise_mm"):
            for value in getattr(self, name):
                nonnegative_real(value, name)
        for name in ("sample_rotation_noise_deg", "sample_translation_noise_mm",
                     "rotation_threshold_rad", "translation_threshold_m"):
            value = nonnegative_real(getattr(self, name), name)
            if "threshold" in name and value == 0:
                raise ValueError("验收阈值必须大于零")
        if any(method not in METHODS for method in self.methods):
            raise ValueError("未知求解方法")
        if not isinstance(self.scene, SceneConfig):
            raise ValueError("scene 必须是 SceneConfig")
        self.scene.truth()

    @classmethod
    def from_dict(cls, data):
        data = dict(data)
        if "scene" in data:
            data["scene"] = SceneConfig(**data["scene"])
        result = cls(**data)
        result.validate()
        return result


FIELDS = ["experiment", "condition", "method", "repeat", "n_samples", "seed", "noise_seed",
          "rotation_sigma_deg", "translation_sigma_mm", "status", "failure_stage", "message",
          "rotation_error_deg", "translation_error_mm", "baseline_pass", "closure_max_abs",
          "axis_ratio", "translation_design_ratio", "data_file", "estimate_file"]


def _write_json(path, content):
    path.write_text(json.dumps(content, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def summarize_records(records):
    """每条件/方法全量计数；统计量只对成功结果计算，明确其条件性。"""
    groups = {}
    for row in records:
        groups.setdefault((row["experiment"], row["condition"], row["method"]), []).append(row)
    summary = []
    for key, rows in groups.items():
        ok = [row for row in rows if row["status"] == "ok"]
        first = rows[0]
        item = {name: first[name] for name in ("experiment", "condition", "method", "n_samples",
                                              "rotation_sigma_deg", "translation_sigma_mm")}
        item.update(total=len(rows), succeeded=len(ok), failed=len(rows)-len(ok),
                    failure_rate=(len(rows)-len(ok))/len(rows))
        for metric in ("rotation_error_deg", "translation_error_mm"):
            values = np.array([row[metric] for row in ok], dtype=float)
            stats = {
                "mean": float(np.mean(values)) if len(values) else None,
                "std": float(np.std(values, ddof=1)) if len(values) >= 2 else None,
                "median": float(np.median(values)) if len(values) else None,
                "q25": float(np.quantile(values, 0.25)) if len(values) else None,
                "q75": float(np.quantile(values, 0.75)) if len(values) else None,
                "max": float(np.max(values)) if len(values) else None,
            }
            item.update({f"{metric}_{stat}": value for stat, value in stats.items()})
        summary.append(item)
    return summary


def _write_csv(path, rows, fields):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def run_experiment(config, output_dir):
    """创建全新结果目录。无噪声任何一次失败时保存日志后停止，不出噪声图。"""
    config.validate()
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=False)
    (output / "raw").mkdir()
    (output / "estimates").mkdir()
    _write_json(output / "config.json", asdict(config))
    _write_json(output / "environment.json", {
        "python": platform.python_version(), "numpy": np.__version__, "scipy": scipy.__version__,
        "opencv": cv2.__version__, "matplotlib": matplotlib.__version__,
        "length_unit": "m", "angle_unit": "rad", "bit_generator": "PCG64",
        "rotation_noise": "left multiplication Exp(delta_theta) R, independent translation addition in C",
        "generator": "normal axis; angle U[0.25,1.2] rad; t=[0.35,0,0.35]+U[-0.2,0.2]^3 m",
        "limitations": "ideal pose observations; no image/FOV/detection/robot reachability model",
    })
    _write_json(output / "run_status.json", {"status": "running"})
    records = []
    max_samples = max(config.noise_sample_count, *config.sample_counts)

    def execute_condition(experiment, condition, n_samples, rotation_deg, translation_mm, writer, handle):
        for repeat in range(config.repeats):
            seed, noise_seed = config.seed_start + repeat, config.noise_seed_start + repeat
            common = dict(experiment=experiment, condition=condition, repeat=repeat, n_samples=n_samples,
                          seed=seed, noise_seed=noise_seed, rotation_sigma_deg=rotation_deg,
                          translation_sigma_mm=translation_mm)
            stem = f"{experiment}_{condition}_{repeat:03d}"
            try:
                # 先生成最大长度，再截前缀，保证不同 N 的几何和噪声完全配对。
                data = generate_dataset(max_samples, seed=seed, scene=config.scene)
                noisy_all = add_observation_noise(data.t_c_t, rotation_sigma_rad=np.deg2rad(rotation_deg),
                                                 translation_sigma_m=translation_mm/1000, seed=noise_seed)
                g, q = data.t_b_g[:n_samples], noisy_all[:n_samples]
                diagnostics = motion_diagnostics(g)
                closure = closure_error(data)
                data_path = f"raw/{stem}.npz"
                np.savez_compressed(output / data_path, t_b_g=g, t_c_t=q,
                                    t_c_t_ideal=data.t_c_t[:n_samples],
                                    t_g_c_true=data.t_g_c_true, t_b_t_true=data.t_b_t_true,
                                    seed=seed, noise_seed=noise_seed,
                                    rotation_sigma_rad=np.deg2rad(rotation_deg), translation_sigma_m=translation_mm/1000)
                generation_error = None
            except ValueError as exc:
                generation_error = f"{type(exc).__name__}: {exc}"
            for method in config.methods:
                row = dict(common, method=method, status="error", failure_stage="generation", message="",
                           rotation_error_deg=None, translation_error_mm=None, baseline_pass=None,
                           closure_max_abs=None, axis_ratio=None, translation_design_ratio=None,
                           data_file="", estimate_file="")
                if generation_error is not None:
                    row["message"] = generation_error
                else:
                    row.update(data_file=data_path, closure_max_abs=closure,
                               axis_ratio=diagnostics["axis_second_first_ratio"],
                               translation_design_ratio=diagnostics["translation_min_max_ratio"])
                    try:
                        estimate = calibrate_hand_eye(g, q, method=method)
                        error = pose_error(estimate, data.t_g_c_true)
                    except Exception as exc:
                        # 包括意外异常：记录类型/消息，保留该次失败，不填零误差。
                        row.update(failure_stage="solve_or_evaluate", message=f"{type(exc).__name__}: {exc}")
                    else:
                        estimate_path = f"estimates/{stem}_{method}.json"
                        _write_json(output / estimate_path, {"T_G_C_estimated": estimate.tolist()})
                        row.update(status="ok", failure_stage="", rotation_error_deg=error.rotation_deg,
                                   translation_error_mm=error.translation_mm, estimate_file=estimate_path)
                        if experiment == "baseline":
                            passed = (error.rotation_rad < config.rotation_threshold_rad and
                                      error.translation_m < config.translation_threshold_m and closure < 1e-12)
                            row["baseline_pass"] = bool(passed)
                            if not passed:
                                row["message"] = "无噪声验收阈值未通过"
                records.append(row)
                writer.writerow(row)
            handle.flush()

    try:
        with (output / "trials.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDS)
            writer.writeheader()
            execute_condition("baseline", "clean", config.noise_sample_count, 0.0, 0.0, writer, handle)
            baseline_pass = all(row["status"] == "ok" and row["baseline_pass"] for row in records)
            _write_json(output / "baseline_gate.json", {
                "passed": baseline_pass, "trials": len(records),
                "rotation_threshold_rad": config.rotation_threshold_rad,
                "translation_threshold_m": config.translation_threshold_m,
            })
            if baseline_pass:
                for index, sigma in enumerate(config.rotation_noise_deg):
                    execute_condition("rotation_noise", f"r{index:02d}", config.noise_sample_count, sigma, 0.0, writer, handle)
                for index, sigma in enumerate(config.translation_noise_mm):
                    execute_condition("translation_noise", f"t{index:02d}", config.noise_sample_count, 0.0, sigma, writer, handle)
                for n in config.sample_counts:
                    execute_condition("sample_count", f"n{n:03d}", n,
                                      config.sample_rotation_noise_deg, config.sample_translation_noise_mm, writer, handle)
        summary = summarize_records(records)
        _write_csv(output / "summary.csv", summary, list(summary[0]))
        _write_json(output / "summary.json", summary)
        if baseline_pass:
            from .plotting import plot_results
            plot_results(output / "summary.csv", output)
        final_status = {
            "status": "complete" if baseline_pass else "stopped_baseline_failed",
            "baseline_passed": baseline_pass,
            "trials": len(records), "solver_failures": sum(r["status"] != "ok" for r in records),
        }
        _write_json(output / "run_status.json", final_status)
        lines = ["# M1 V0.1 实际实验结果", "", f"运行状态：{final_status['status']}。",
                 f"求解记录 {len(records)} 条，失败 {final_status['solver_failures']} 条。",
                 "无噪声关卡：" + ("通过。" if baseline_pass else "失败；已停止噪声和采样数实验。"), "",
                 "所有数值见 trials.csv 和 summary.csv；配置见 config.json。",
                 "同一重复/条件的两方法共享完全相同观测；不同 N 使用共同长序列前缀。",
                 "噪声标准差为三分量标准差；统计标准差 ddof=1，图中误差棒为均值±1样本标准差（不是置信区间）。",
                 "统计仅针对成功求解，同时列出失败数；失败误差留空，不按0处理。", "",
                 "理想位姿观测不等价于真实图像测量，未模拟视野、检测、遮挡、运动约束或系统误差。",
                 "这些结果用于验证基础实验闭环，不证明实机精度、方法普遍优劣或创新。"]
        (output / "RESULTS.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
        hashes = {p.relative_to(output).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in output.rglob("*") if p.is_file()}
        _write_json(output / "artifact_hashes.json", hashes)
        return final_status
    except Exception as exc:
        _write_json(output / "run_status.json", {"status": "failed", "message": f"{type(exc).__name__}: {exc}",
                                                 "recorded_trials": len(records)})
        raise
