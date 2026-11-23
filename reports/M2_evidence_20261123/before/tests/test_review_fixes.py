"""审查回归：失败落盘、理想前缀、绘图资源和既有保护行为。

本文件中的故障注入/小表格仅用于测试，不是科研实验数据。
"""

import csv
from dataclasses import asdict
import json
import os
from pathlib import Path
import subprocess
import sys

from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import numpy as np
import pytest

import handeye.calibration as calibration
import handeye.experiments as experiments
from handeye.calibration import CalibrationError, calibrate_hand_eye, motion_diagnostics
from handeye.experiments import ExperimentConfig, run_experiment
from handeye.plotting import plot_results, rows_for
from handeye.simulation import generate_dataset
from handeye.transforms import make_transform, rotation_matrix


def config(**kwargs):
    return ExperimentConfig(repeats=2, rotation_noise_deg=(0.1,),
                            translation_noise_mm=(0.5,), sample_counts=(8,), **kwargs)


def read_trials(folder):
    with (folder / "trials.csv").open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


@pytest.fixture(autouse=True)
def close_only_test_figures():
    original = set(plt.get_fignums())
    yield
    for number in set(plt.get_fignums()) - original:
        plt.close(number)


@pytest.mark.parametrize("phase,error_type", [("solve", NameError), ("solve", TypeError),
                                             ("evaluate", ValueError)])
def test_unexpected_error_persisted_then_reraised(tmp_path, monkeypatch, phase, error_type):
    target = "calibrate_hand_eye" if phase == "solve" else "pose_error"
    real = getattr(experiments, target)
    calls = 0

    def raise_programmer_error_after_baseline(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 5:  # 2 repeats × 2 methods 已通过无噪声关卡。
            raise error_type("FIX_injected_programming_error")
        return real(*args, **kwargs)

    monkeypatch.setattr(experiments, target, raise_programmer_error_after_baseline)
    folder = tmp_path / "unexpected"
    with pytest.raises(error_type, match="FIX_injected_programming_error"):
        run_experiment(config(), folder)
    assert calls == 5
    rows = read_trials(folder)
    assert len(rows) == 5  # 当前失败行也必须先落盘，不能只留下基线。
    assert rows[-1]["status"] == "error"
    assert rows[-1]["failure_stage"] == f"unexpected_{phase}"
    assert rows[-1]["rotation_error_deg"] == rows[-1]["translation_error_mm"] == ""
    trace = (folder / rows[-1]["traceback_file"]).read_text(encoding="utf-8")
    assert "Traceback (most recent call last)" in trace
    assert "raise_programmer_error_after_baseline" in trace
    assert error_type.__name__ in trace and "FIX_injected_programming_error" in trace
    status = json.loads((folder / "run_status.json").read_text(encoding="utf-8"))
    assert status["status"] == "failed" and status["recorded_trials"] == 5
    assert status["failure_stage"] == f"unexpected_{phase}"
    assert (folder / status["traceback_file"]).is_file()
    assert not (folder / "summary.csv").exists()
    assert not list(folder.glob("*.png"))


@pytest.mark.parametrize("error_type", [CalibrationError, ValueError])
def test_expected_solver_failure_still_continues_and_keeps_rows(tmp_path, monkeypatch, error_type):
    real = experiments.calibrate_hand_eye
    calls = 0

    def expected_failure(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls > 4:
            raise error_type("expected data or solver failure")
        return real(*args, **kwargs)

    monkeypatch.setattr(experiments, "calibrate_hand_eye", expected_failure)
    folder = tmp_path / "expected"
    status = run_experiment(config(), folder)
    assert status["status"] == "complete" and status["solver_failures"] == 12
    rows = read_trials(folder)
    assert len(rows) == 16
    assert all(r["status"] == "error" and r["rotation_error_deg"] == "" for r in rows[4:])
    assert not (folder / "traceback.txt").exists()


@pytest.mark.parametrize("kind", ["identical", "pure_translation", "single_axis", "tiny_angle"])
def test_degenerate_diagnostic_and_adapter_do_not_call_opencv(monkeypatch, kind):
    poses = np.repeat(np.eye(4)[None], 15, axis=0)
    if kind == "pure_translation":
        poses[:, 0, 3] = np.linspace(0, 1, 15)
    if kind in ("single_axis", "tiny_angle"):
        maximum = 1.0 if kind == "single_axis" else 1e-10
        poses = np.stack([make_transform(rotation_matrix("z", angle), [angle, 0, 0])
                          for angle in np.linspace(0, maximum, 15)])
    diagnostics = motion_diagnostics(poses)
    assert diagnostics["nondegenerate"] is False
    assert diagnostics["axis_second_first_ratio"] == 0.0
    calls = []
    monkeypatch.setattr(calibration.cv2, "calibrateHandEye", lambda *a, **k: calls.append(True))
    with pytest.raises(ValueError, match="机器人运动退化或近退化"):
        calibrate_hand_eye(poses, generate_dataset(15).t_c_t)
    assert calls == []


def test_opencv_reflection_output_is_rejected(monkeypatch):
    data = generate_dataset(15)
    monkeypatch.setattr(calibration.cv2, "calibrateHandEye",
                        lambda *a, **k: (np.diag([1.0, 1.0, -1.0]), np.zeros((3, 1))))
    with pytest.raises(CalibrationError, match=r"det=\+1"):
        calibrate_hand_eye(data.t_b_g, data.t_c_t)


def test_logged_closure_uses_actual_ideal_prefix(tmp_path, monkeypatch):
    checked_lengths = []
    real = experiments.closure_error

    def observe_length(data):
        checked_lengths.append(len(data.t_b_g))
        return real(data)

    monkeypatch.setattr(experiments, "closure_error", observe_length)
    folder = tmp_path / "prefix"
    run_experiment(config(methods=("PARK",), seed_start=20261121), folder)
    assert checked_lengths[-2:] == [8, 8]
    for row in read_trials(folder):
        with np.load(folder / row["data_file"], allow_pickle=False) as raw:
            expected = float(np.max(np.abs(raw["t_b_g"] @ raw["t_g_c_true"] @
                                           raw["t_c_t_ideal"] - raw["t_b_t_true"])))
        assert float(row["closure_max_abs"]) == expected


def write_plot_input(path, *, missing_experiment=None, missing_column=None):
    rows = []
    for experiment in ("baseline", "rotation_noise", "translation_noise", "sample_count"):
        if experiment == missing_experiment or missing_experiment == "all":
            continue
        row = dict(experiment=experiment, method="PARK", n_samples=20,
                   rotation_sigma_deg=0.1, translation_sigma_mm=0.5,
                   failed=0, total=2, rotation_error_deg_mean=0.1, rotation_error_deg_std=0.01,
                   translation_error_mm_mean=0.5, translation_error_mm_std=0.05)
        if missing_column:
            row.pop(missing_column)
        rows.append(row)
    fields = list(rows[0]) if rows else ["experiment", "method"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


@pytest.mark.parametrize("missing", ["rotation_noise", "translation_noise", "sample_count", "all"])
def test_plot_missing_experiment_is_explicit_and_creates_no_figures(tmp_path, missing):
    table = tmp_path / "missing.csv"
    write_plot_input(table, missing_experiment=missing)
    original = set(plt.get_fignums())
    with pytest.raises(ValueError, match="缺少.*(实验类型|必需列)"):
        plot_results(table, tmp_path)
    assert set(plt.get_fignums()) == original
    assert not list(tmp_path.glob("*.png"))


def test_plot_missing_column_is_explicit_before_drawing(tmp_path):
    table = tmp_path / "column.csv"
    write_plot_input(table, missing_column="translation_error_mm_std")
    original = set(plt.get_fignums())
    with pytest.raises(ValueError, match="缺少必需列.*translation_error_mm_std"):
        plot_results(table, tmp_path)
    assert set(plt.get_fignums()) == original


def test_plot_closes_figure_on_save_failure(tmp_path, monkeypatch):
    table = tmp_path / "complete.csv"
    write_plot_input(table)
    original = set(plt.get_fignums())

    def fail_save(*args, **kwargs):
        raise OSError("FIX_simulated_disk_error")

    monkeypatch.setattr(Figure, "savefig", fail_save)
    with pytest.raises(OSError, match="FIX_simulated_disk_error"):
        plot_results(table, tmp_path)
    assert set(plt.get_fignums()) == original


def test_rows_for_missing_type_has_domain_error():
    with pytest.raises(ValueError, match="实验类型.*sample_count"):
        rows_for([], "sample_count", "n_samples")


def test_cli_unexpected_error_is_nonzero_with_traceback(tmp_path):
    root = Path(__file__).resolve().parents[1]
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(asdict(config())), encoding="utf-8")
    folder = tmp_path / "cli_failed"
    # 独立进程中注入故障，不编辑CLI或真实求解模块。
    bootstrap = """
import runpy, sys
import handeye.experiments as exp
real = exp.calibrate_hand_eye
calls = 0
def fail_after_baseline(*args, **kwargs):
    global calls
    calls += 1
    if calls > 4:
        raise NameError('FIX_cli_programmer_error')
    return real(*args, **kwargs)
exp.calibrate_hand_eye = fail_after_baseline
sys.argv = ['run_m1.py', '--config', sys.argv[1], '--output', sys.argv[2]]
runpy.run_path('scripts/run_m1.py', run_name='__main__')
"""
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root / "src")
    env["PYTHONIOENCODING"] = "utf-8"
    result = subprocess.run([sys.executable, "-c", bootstrap, str(config_file), str(folder)],
                            cwd=root, env=env, capture_output=True, text=True, encoding="utf-8")
    assert result.returncode != 0
    assert "Traceback (most recent call last)" in result.stderr
    assert "FIX_cli_programmer_error" in result.stderr
    status = json.loads((folder / "run_status.json").read_text(encoding="utf-8"))
    assert status["status"] == "failed" and status["recorded_trials"] == 5
