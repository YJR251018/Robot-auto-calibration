"""W2真实生成/求解/核验链和失败后的原始数据保护。"""
from dataclasses import asdict
import json
from pathlib import Path
import shutil

import numpy as np
import pytest

import handeye.projection_experiment as experiment
from handeye.projection_verification import verify_projection


@pytest.fixture(scope='module')
def completed(tmp_path_factory):
    folder = tmp_path_factory.mktemp('projection')/'run'
    config = experiment.ProjectionConfig(repeats=1, seed_start=610000)
    summary = experiment.run_projection(config, folder)
    assert summary['candidates']==120 and summary['baseline_solves']==2
    return folder


def test_real_projection_run_replay_and_no_overwrite(completed):
    result = verify_projection(completed)
    assert result['replayed_baseline_solves']==2
    assert result['prediction_evaluations']==100
    assert len(list(completed.glob('*.png')))==2
    with pytest.raises(FileExistsError):
        experiment.run_projection(experiment.ProjectionConfig(repeats=1), completed)


def test_unexpected_error_saves_current_seed_data(tmp_path, monkeypatch):
    def fail(*args, **kwargs):
        raise NameError('projection injected')
    monkeypatch.setattr(experiment, 'calibrate_hand_eye', fail)
    folder = tmp_path/'failed'
    with pytest.raises(NameError, match='injected'):
        experiment.run_projection(experiment.ProjectionConfig(repeats=1, seed_start=610000), folder)
    assert (folder/'raw/seed_610000.npz').is_file()
    status = json.loads((folder/'run_status.json').read_text(encoding='utf-8'))
    assert status['status']=='failed' and status['seed']==610000 and status['failure_stage']=='analyze'
    assert not (folder/'summary.json').exists()
    assert 'projection injected' in (folder/'traceback.txt').read_text(encoding='utf-8')


def test_prediction_interface_does_not_receive_truth(monkeypatch):
    original = experiment.predict_visibility
    calls = []
    def guard(g, x_est, y_est, camera, *, points):
        assert g.shape==x_est.shape==y_est.shape==(4,4)
        assert points.shape==(63,3)
        calls.append(1)
        return original(g, x_est, y_est, camera, points=points)
    monkeypatch.setattr(experiment, 'predict_visibility', guard)
    config = experiment.ProjectionConfig(repeats=1, seed_start=610000)
    raw = experiment.generate_projection_candidates(config, 610000)
    experiment.analyze_candidates(raw, config, 610000)
    assert len(calls)==100


def test_hash_tamper_rejected(completed, tmp_path):
    folder = tmp_path/'copied'; shutil.copytree(completed, folder)
    (folder/'summary.json').write_text('{}', encoding='utf-8')
    with pytest.raises(ValueError, match='哈希'):
        verify_projection(folder)


@pytest.mark.parametrize('kwargs', [dict(repeats=True),dict(seed_start=-1),dict(training_count=2),
    dict(candidate_count=20),dict(camera={}),dict(scene={})])
def test_bad_projection_config(kwargs):
    with pytest.raises(ValueError):
        experiment.ProjectionConfig(**kwargs).validate()


def test_board_outside_and_no_replacement_seed(tmp_path, monkeypatch):
    original = experiment.generate_projection_candidates
    def outside(config, seed):
        raw = original(config, seed)
        raw['q'][:,0,3] = 20
        # 保持新Q和G几何一致，否则会在闭环检查处提前失败。
        raw['g'] = np.stack([raw['y_true'] @ np.linalg.inv(q) @ np.linalg.inv(raw['x_true']) for q in raw['q']])
        return raw
    monkeypatch.setattr(experiment, 'generate_projection_candidates', outside)
    folder=tmp_path/'no-visible'
    with pytest.raises(ValueError, match='可见候选不足'):
        experiment.run_projection(experiment.ProjectionConfig(repeats=1,seed_start=610000), folder)
    assert list((folder/'raw').glob('*.npz'))==[folder/'raw/seed_610000.npz']
