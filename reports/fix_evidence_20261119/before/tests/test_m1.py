"""M1：独立数学参照、真实 OpenCV、输入边界、失败机制与可复算链路。"""

import csv
from dataclasses import replace
import json

import cv2
import numpy as np
import pytest
from scipy.spatial.transform import Rotation

import handeye.calibration as calibration
import handeye.experiments as experiments
from handeye.calibration import CalibrationError, calibrate_hand_eye, motion_diagnostics
from handeye.experiments import ExperimentConfig, run_experiment, summarize_records
from handeye.metrics import pose_error, rotation_error_rad, translation_error_m
from handeye.simulation import SceneConfig, add_observation_noise, closure_error, generate_dataset
from handeye.transforms import make_transform, rotation_matrix


@pytest.mark.parametrize("angle", [0.0, 1e-10, 0.2, np.pi-1e-10, np.pi])
def test_rotation_error_known_angles_and_symmetry(angle):
    r = rotation_matrix("z", angle)
    assert rotation_error_rad(r, np.eye(3)) == pytest.approx(angle, abs=1e-14)
    assert rotation_error_rad(np.eye(3), r) == pytest.approx(angle, abs=1e-14)


def test_error_units_and_known_numeric_result():
    estimate = make_transform(rotation_matrix("x", np.pi/2), [0.003, 0.004, 0])
    error = pose_error(estimate, np.eye(4))
    assert error.rotation_deg == pytest.approx(90)
    assert error.translation_m == pytest.approx(0.005)
    assert error.translation_mm == pytest.approx(5)
    assert translation_error_m([0, 0, 0], [0.003, 0.004, 0]) == pytest.approx(0.005)


@pytest.mark.parametrize("bad", [np.zeros((3, 3)), np.diag([1, 1, -1]), np.full((3, 3), np.nan)])
def test_rotation_metric_rejects_invalid(bad):
    with pytest.raises(ValueError):
        rotation_error_rad(bad, np.eye(3))


@pytest.mark.parametrize("bad", [[1, 2], [np.nan, 0, 0], [1j, 0, 0], ["1", "2", "3"]])
def test_translation_metric_rejects_invalid(bad):
    with pytest.raises(ValueError):
        translation_error_m(bad, [0, 0, 0])


@pytest.mark.parametrize("seed", [0, 1, 7, 20261118])
def test_simulation_closure_against_general_inverse_and_reproducibility(seed):
    data = generate_dataset(20, seed=seed)
    again = generate_dataset(20, seed=seed)
    for field in ("t_b_g", "t_c_t", "t_g_c_true", "t_b_t_true"):
        np.testing.assert_array_equal(getattr(data, field), getattr(again, field))
    # 独立使用 np.linalg.inv，不使用生成器的刚体求逆实现。
    expected_q = np.linalg.inv(data.t_b_g @ data.t_g_c_true) @ data.t_b_t_true
    np.testing.assert_allclose(data.t_c_t, expected_q, atol=1e-12, rtol=0)
    np.testing.assert_allclose(data.t_b_g @ data.t_g_c_true @ data.t_c_t,
                               np.repeat(data.t_b_t_true[None], 20, axis=0), atol=1e-12, rtol=0)
    assert closure_error(data) < 1e-12
    diag = motion_diagnostics(data.t_b_g)
    assert diag["nondegenerate"] and diag["axis_second_first_ratio"] > 0.1
    short = generate_dataset(8, seed=seed)
    np.testing.assert_array_equal(short.t_b_g, data.t_b_g[:8])
    assert not np.array_equal(data.t_b_g, generate_dataset(20, seed=seed+1).t_b_g)


@pytest.mark.parametrize("method", ["PARK", "TSAI"])
@pytest.mark.parametrize("scene", [SceneConfig(),
    SceneConfig(handeye_rotvec_rad=(-0.5, 0.2, 0.1), handeye_translation_m=(-0.12, 0.05, 0.03)),
    SceneConfig(handeye_rotvec_rad=(0, 0, 0), handeye_translation_m=(0, 0, 0))])
def test_actual_opencv_recovers_multiple_truths(method, scene):
    data = generate_dataset(20, seed=31, scene=scene)
    estimate = calibrate_hand_eye(data.t_b_g, data.t_c_t, method=method)
    error = pose_error(estimate, data.t_g_c_true)
    assert error.rotation_rad < 1e-6
    assert error.translation_m < 1e-6


def test_adapter_forwards_exact_directions_and_returns_opencv_output(monkeypatch):
    data = generate_dataset(15, seed=71)
    calls = []
    def fake_cv(rg, tg, rt, tt, *, method):
        calls.append(method)
        np.testing.assert_array_equal(rg, data.t_b_g[:, :3, :3])
        np.testing.assert_array_equal(np.array(tg).reshape(-1, 3), data.t_b_g[:, :3, 3])
        np.testing.assert_array_equal(rt, data.t_c_t[:, :3, :3])
        np.testing.assert_array_equal(np.array(tt).reshape(-1, 3), data.t_c_t[:, :3, 3])
        return np.eye(3), np.array([[1.0], [2.0], [3.0]])
    monkeypatch.setattr(calibration.cv2, "calibrateHandEye", fake_cv)
    result = calibrate_hand_eye(data.t_b_g, data.t_c_t, method="PARK")
    assert calls == [cv2.CALIB_HAND_EYE_PARK]
    np.testing.assert_array_equal(result, make_transform(np.eye(3), [1, 2, 3]))
    assert not np.allclose(result, data.t_g_c_true)


@pytest.mark.parametrize("result", [(np.full((3, 3), np.nan), np.zeros((3, 1))),
                                    (np.eye(3), np.full((3, 1), np.inf))])
def test_nonfinite_solver_outputs_rejected(monkeypatch, result):
    data = generate_dataset(15)
    monkeypatch.setattr(calibration.cv2, "calibrateHandEye", lambda *a, **k: result)
    with pytest.raises(CalibrationError):
        calibrate_hand_eye(data.t_b_g, data.t_c_t)


def test_solver_exception_rejected(monkeypatch):
    data = generate_dataset(15)
    def fail(*args, **kwargs):
        raise cv2.error("injected solver error")
    monkeypatch.setattr(calibration.cv2, "calibrateHandEye", fail)
    with pytest.raises(CalibrationError, match="injected"):
        calibrate_hand_eye(data.t_b_g, data.t_c_t)


def test_solver_input_checks_and_degenerate_motions():
    data = generate_dataset(15)
    cases = [(data.t_b_g[:2], data.t_c_t[:2]), (data.t_b_g, data.t_c_t[:4]),
             (np.repeat(np.eye(4)[None], 15, axis=0), data.t_c_t)]
    single_axis = np.stack([make_transform(rotation_matrix("z", t), [t, 0, 0]) for t in np.linspace(0, 1, 15)])
    cases.append((single_axis, data.t_c_t))
    for g, q in cases:
        with pytest.raises(ValueError):
            calibrate_hand_eye(g, q)
    bad = data.t_c_t.copy(); bad[0, 3, 0] = 1
    with pytest.raises(ValueError):
        calibrate_hand_eye(data.t_b_g, bad)
    with pytest.raises(ValueError):
        calibrate_hand_eye(data.t_b_g, data.t_c_t, method="BAD")


@pytest.mark.parametrize("count,seed", [(2, 0), (True, 0), (15.5, 0), (15, -1), (15, True)])
def test_generator_invalid_inputs(count, seed):
    with pytest.raises(ValueError):
        generate_dataset(count, seed=seed)


def test_noise_pairing_rotation_manifold_and_independent_units():
    data = generate_dataset(20)
    ideal = data.t_c_t.copy()
    zero = add_observation_noise(ideal, seed=8)
    np.testing.assert_array_equal(zero, ideal)
    noisy = add_observation_noise(ideal, rotation_sigma_rad=0.01, translation_sigma_m=0.001, seed=8)
    np.testing.assert_array_equal(noisy, add_observation_noise(ideal, rotation_sigma_rad=0.01, translation_sigma_m=0.001, seed=8))
    np.testing.assert_array_equal(noisy[:8], add_observation_noise(ideal[:8], rotation_sigma_rad=0.01, translation_sigma_m=0.001, seed=8))
    standardized = np.random.default_rng(8).normal(size=(20, 6))
    expected_r = Rotation.from_rotvec(standardized[:, :3]*0.01).as_matrix() @ ideal[:, :3, :3]
    np.testing.assert_allclose(noisy[:, :3, :3], expected_r, atol=1e-14, rtol=0)
    np.testing.assert_allclose(noisy[:, :3, 3]-ideal[:, :3, 3], standardized[:, 3:]*0.001, atol=1e-16, rtol=0)
    rotation_only = add_observation_noise(ideal, rotation_sigma_rad=0.01, seed=8)
    np.testing.assert_array_equal(rotation_only[:, :3, 3], ideal[:, :3, 3])
    translation_only = add_observation_noise(ideal, translation_sigma_m=0.001, seed=8)
    np.testing.assert_array_equal(translation_only[:, :3, :3], ideal[:, :3, :3])
    np.testing.assert_array_equal(ideal, data.t_c_t)


@pytest.mark.parametrize("kwargs", [{"rotation_sigma_rad": -1}, {"translation_sigma_m": np.nan}, {"seed": -1}])
def test_noise_invalid_inputs(kwargs):
    with pytest.raises(ValueError):
        add_observation_noise(generate_dataset(15).t_c_t, **kwargs)


def small_config():
    return ExperimentConfig(repeats=2, methods=("PARK",), rotation_noise_deg=(0.1,),
                            translation_noise_mm=(0.5,), sample_counts=(8,))


def test_experiment_reproducible_csv_saved_inputs_and_real_plots(tmp_path):
    config = small_config()
    first, second = tmp_path/"first", tmp_path/"second"
    status = run_experiment(config, first)
    assert status == run_experiment(config, second)
    assert status["baseline_passed"] and status["trials"] == 8
    for file in ("trials.csv", "summary.csv", "config.json"):
        assert (first/file).read_bytes() == (second/file).read_bytes()
    for file in ("rotation_noise.png", "translation_noise.png", "sample_count.png"):
        assert (first/file).read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
        assert (first/file).stat().st_size > 1000
    with (first/"trials.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        with np.load(first/row["data_file"]) as saved:
            computed = calibrate_hand_eye(saved["t_b_g"], saved["t_c_t"], method=row["method"])
            error = pose_error(computed, saved["t_g_c_true"])
            assert error.rotation_deg == float(row["rotation_error_deg"])
            assert error.translation_mm == float(row["translation_error_mm"])
    with pytest.raises(FileExistsError):
        run_experiment(config, first)


def test_baseline_failure_stops_before_noise_and_is_preserved(tmp_path, monkeypatch):
    monkeypatch.setattr(experiments, "calibrate_hand_eye", lambda *a, **k: np.eye(4))
    status = run_experiment(small_config(), tmp_path/"stopped")
    assert status["status"] == "stopped_baseline_failed"
    with (tmp_path/"stopped/trials.csv").open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 2 and all(r["experiment"] == "baseline" for r in rows)
    assert all(r["baseline_pass"] == "False" for r in rows)
    assert not (tmp_path/"stopped/rotation_noise.png").exists()


def test_noisy_solver_failures_are_retained_with_empty_errors(tmp_path, monkeypatch):
    real_solver = experiments.calibrate_hand_eye
    calls = 0
    def sometimes_fail(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls > 2:
            raise CalibrationError("intentional test failure")
        return real_solver(*args, **kwargs)
    monkeypatch.setattr(experiments, "calibrate_hand_eye", sometimes_fail)
    status = run_experiment(small_config(), tmp_path/"failure")
    assert status["solver_failures"] == 6 and status["trials"] == 8
    with (tmp_path/"failure/trials.csv").open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 8
    assert all(row["rotation_error_deg"] == "" and row["translation_error_mm"] == "" for row in rows[2:])
    assert all("intentional test failure" in row["message"] for row in rows[2:])
    summary = json.loads((tmp_path/"failure/summary.json").read_text(encoding="utf-8"))
    assert all(r["failed"] == 2 and r["rotation_error_deg_mean"] is None for r in summary[1:])


def test_summary_uses_sample_sd_and_includes_failures():
    common = dict(experiment="x", condition="x", method="PARK", n_samples=20,
                  rotation_sigma_deg=0, translation_sigma_mm=0)
    rows = [dict(common, status="ok", rotation_error_deg=x, translation_error_mm=x*2) for x in [1, 3]]
    rows.append(dict(common, status="error", rotation_error_deg=None, translation_error_mm=None))
    summary = summarize_records(rows)[0]
    assert summary["total"] == 3 and summary["failed"] == 1
    assert summary["rotation_error_deg_mean"] == 2
    assert summary["rotation_error_deg_std"] == pytest.approx(np.sqrt(2))


@pytest.mark.parametrize("changes", [{"repeats": 1}, {"noise_sample_count": 8}, {"sample_counts": ()},
    {"sample_counts": (2,)}, {"methods": ("BAD",)}, {"rotation_noise_deg": (-1,)},
    {"rotation_threshold_rad": 0}, {"translation_threshold_m": np.nan}])
def test_invalid_experiment_config(changes):
    with pytest.raises(ValueError):
        replace(small_config(), **changes).validate()
