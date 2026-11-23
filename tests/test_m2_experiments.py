"""M2 真实求解链、故障落盘、种子配对和独立核验。"""
from dataclasses import asdict, replace
import csv
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import numpy as np
import pytest

import handeye.m2_experiments as m2
from handeye.calibration import CalibrationError
from handeye.m2_verification import verify_m2


def tiny(**kwargs):
    values = dict(repeats=2,candidate_count=22,holdout_count=5,sample_counts=(8,),methods=('PARK',),
                  conditions=(m2.Noise('baseline'),m2.Noise('mixed',.3,.5)),bootstrap_repeats=20,
                  candidate_seed=410000,holdout_seed=420000,noise_seed=430000,selection_seed=440000,robot_noise_seed=450000)
    values.update(kwargs)
    return m2.M2Config(**values)


def rows(folder):
    with (folder/'trials.csv').open(encoding='utf-8',newline='') as f:
        return list(csv.DictReader(f))


@pytest.fixture(scope='module')
def complete_run(tmp_path_factory):
    folder=tmp_path_factory.mktemp('m2')/'complete'
    status=m2.run_m2(tiny(),folder)
    assert status['completed']==12 and status['failed']==0
    return folder


def test_real_chain_replay_and_no_overwrite(complete_run):
    result=verify_m2(complete_run)
    assert result['replayed_successes']==12
    assert len(list(complete_run.glob('*.png')))==3
    assert len(list(complete_run.glob('*.pdf')))==3
    with pytest.raises(FileExistsError):
        m2.run_m2(tiny(),complete_run)
    assert all(r['condition']=='baseline' for r in rows(complete_run)[:6])


def test_raw_pairing_and_holdout_are_independent(complete_run):
    with np.load(complete_run/'raw/repeat_000.npz',allow_pickle=False) as d:
        assert not np.array_equal(d['candidate_g'][:5],d['holdout_g'])
        np.testing.assert_array_equal(d['camera_standard_noise'],np.random.default_rng(430000).normal(size=(22,6)))
        raw={k:d[k] for k in d.files}
    noise=m2.Noise('mixed',.3,.5)
    g1,q1,_=m2.trial_inputs(raw,{'ids':[0,5,3,8]}, {'n_samples':4},noise)
    g2,q2,_=m2.trial_inputs(raw,{'ids':[8,3,5,0]}, {'n_samples':4},noise)
    np.testing.assert_array_equal(q1,q2[::-1])
    np.testing.assert_array_equal(g1,g2[::-1])
    np.testing.assert_array_equal(g1,raw['candidate_g'][[0,5,3,8]])


def test_tampering_is_rejected(complete_run,tmp_path):
    copied=tmp_path/'copy'; shutil.copytree(complete_run,copied)
    with (copied/'trials.csv').open('a',encoding='utf-8') as f:
        f.write('tampered\n')
    with pytest.raises(ValueError,match='哈希'):
        verify_m2(copied)


@pytest.mark.parametrize('phase,error', [('solve',NameError),('evaluate',ValueError)])
def test_unexpected_after_baseline_persists_and_stops(tmp_path,monkeypatch,phase,error):
    name='calibrate_hand_eye' if phase=='solve' else 'evaluate_estimate'
    original=getattr(m2,name); calls=0
    def inject(*args,**kwargs):
        nonlocal calls
        calls+=1
        if calls==7:
            raise error('M2 injected unexpected')
        return original(*args,**kwargs)
    monkeypatch.setattr(m2,name,inject)
    folder=tmp_path/'unexpected'
    with pytest.raises(error,match='injected'):
        m2.run_m2(tiny(),folder)
    assert calls==7 and len(rows(folder))==7
    last=rows(folder)[-1]
    assert last['failure_stage']==phase and last['status']=='error'
    assert all(last[key]=='' for key in m2.METRICS)
    assert 'M2 injected unexpected' in (folder/'traceback.txt').read_text(encoding='utf-8')
    status=json.loads((folder/'run_status.json').read_text(encoding='utf-8'))
    assert status['status']=='failed' and status['completed']==7
    assert not (folder/'summary.json').exists() and not list(folder.glob('*.png'))


def test_expected_solver_failures_are_counted(tmp_path,monkeypatch):
    original=m2.calibrate_hand_eye; calls=0
    def inject(*args,**kwargs):
        nonlocal calls
        calls+=1
        if calls>6:
            raise CalibrationError('expected rejection')
        return original(*args,**kwargs)
    monkeypatch.setattr(m2,'calibrate_hand_eye',inject)
    folder=tmp_path/'expected'
    status=m2.run_m2(tiny(),folder)
    assert status['status']=='complete' and status['failed']==6
    assert all(r['point_rmse_mm']=='' for r in rows(folder)[6:])
    assert not (folder/'traceback.txt').exists()
    assert verify_m2(folder,replay=False)['trials']==12


def test_bad_baseline_prevents_noise(tmp_path,monkeypatch):
    monkeypatch.setattr(m2,'calibrate_hand_eye',lambda *args,**kwargs: np.eye(4))
    folder=tmp_path/'bad-baseline'
    with pytest.raises(RuntimeError,match='无噪声'):
        m2.run_m2(tiny(),folder)
    assert len(rows(folder))==1
    assert not json.loads((folder/'baseline_gate.json').read_text(encoding='utf-8'))['passed']
    assert not (folder/'summary.json').exists()


@pytest.mark.parametrize('change', [dict(repeats=True),dict(candidate_count=7),dict(sample_counts=(8,8)),
    dict(holdout_seed=410000),dict(initial_ids=(0,0)),dict(sample_counts=(False,)),
    dict(conditions=(m2.Noise('baseline',.1),)),dict(conditions=(m2.Noise('baseline'),m2.Noise('mixed',-1)))])
def test_invalid_config(change):
    with pytest.raises(ValueError):
        tiny(**change).validate()


def test_paired_statistics_known_values_and_failures():
    records=[]
    for repeat in range(3):
        for strategy in ('random','rotation_farthest'):
            records.append(dict(condition='mixed',method='PARK',n_samples=20,repeat=repeat,strategy=strategy,
                                status='error' if repeat==2 and strategy=='random' else 'ok',
                                point_rmse_mm=(10 if strategy=='random' else 9)+repeat))
    result=m2.paired_comparison(records,tiny())
    assert result['eligible_repeats']==3 and result['paired_success']==2
    assert result['mean_delta_mm']==-1 and result['ci95_mm']==[-1,-1]


def test_selector_receives_only_planned_poses(monkeypatch):
    original=m2.select_poses; seen=[]
    def guard(poses,**kwargs):
        assert isinstance(poses,np.ndarray) and poses.shape==(22,4,4)
        assert set(kwargs)=={'candidate_ids','initial_ids','n_samples','strategy','seed'}
        result=original(poses,**kwargs); seen.append(result.ids); return result
    monkeypatch.setattr(m2,'select_poses',guard)
    m2.prepare_repeat(tiny(),0)
    changed=replace(tiny(),scene=m2.SceneConfig(handeye_translation_m=(.7,.2,.4)))
    m2.prepare_repeat(changed,0)
    assert seen[:3]==seen[3:]


def test_cli_rejects_existing_and_outside_output(complete_run,tmp_path):
    root=Path(__file__).resolve().parents[1]
    config=tmp_path/'config.json'; config.write_text(json.dumps(asdict(tiny())),encoding='utf-8')
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONIOENCODING='utf8',MPLCONFIGDIR=str(root/'.venv/matplotlib-cache'))
    for output in (complete_run,root.parent/'M2_FORBIDDEN_TEST_OUTPUT'):
        result=subprocess.run([sys.executable,str(root/'scripts/run_m2.py'),'--config',str(config),'--output',str(output)],
                               cwd=root,env=env,capture_output=True,text=True,encoding='utf-8')
        assert result.returncode!=0
    assert not (root.parent/'M2_FORBIDDEN_TEST_OUTPUT').exists()
