"""从保存的 M2 原始数据重放，核查配置、索引、统计和估计。"""
import csv
import json
from pathlib import Path

import numpy as np

from .calibration import calibrate_hand_eye
from .m2_experiments import (M2Config, METRICS, digest, evaluate_estimate, paired_comparison,
                             summarize, trial_inputs, trial_plan)
from .sampling import select_poses


def _read(folder, name):
    return json.loads((folder/name).read_text(encoding='utf-8'))


def _check(condition, message):
    if not condition:
        raise ValueError(message)


def verify_m2(folder, *, replay=True):
    folder = Path(folder)
    status = _read(folder, 'run_status.json')
    _check(status['status']=='complete' and status['baseline_passed'], '只能验收已完成且基线通过的实验')
    hashes = _read(folder, 'artifact_hashes.json')
    actual_files = {p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file()}-{'artifact_hashes.json'}
    _check(set(hashes)==actual_files, '文件清单不一致')
    for name, expected in hashes.items():
        path = (folder/name).resolve()
        _check(path.is_relative_to(folder.resolve()), '产物路径越界')
        _check(digest(path)==expected, f'文件哈希不一致: {name}')
    config = M2Config.from_dict(_read(folder, 'config.json'))
    plan = trial_plan(config)
    _check(_read(folder, 'trial_plan.json')==plan, '计划与配置不一致')
    with (folder/'trials.csv').open(encoding='utf-8', newline='') as f:
        rows = list(csv.DictReader(f))
    _check([r['trial_id'] for r in rows]==[r['trial_id'] for r in plan], '试次缺失、重复或顺序错误')
    _check(status['completed']==len(rows)==status['planned'], '试次总计错误')
    _check(status['failed']==sum(r['status']!='ok' for r in rows), '失败计数错误')
    _check(status['succeeded']==sum(r['status']=='ok' for r in rows), '成功计数错误')
    selections = _read(folder, 'selections.json')
    raw_sets = {}
    for repeat in range(config.repeats):
        with np.load(folder/f'raw/repeat_{repeat:03d}.npz', allow_pickle=False) as data:
            raw = {k:data[k] for k in data.files}
        raw_sets[repeat] = raw
        np.testing.assert_array_equal(raw['candidate_ids'], np.arange(config.candidate_count))
        _check(len(raw['holdout_g'])==config.holdout_count, '留出数量错误')
        for strategy in config.strategies:
            expected = select_poses(raw['candidate_g'], candidate_ids=raw['candidate_ids'],
                                    initial_ids=config.initial_ids, n_samples=max(config.sample_counts),
                                    strategy=strategy, seed=config.selection_seed+repeat)
            saved = selections[str(repeat)][strategy]
            _check(saved['ids']==list(expected.ids), '选择顺序与固定协议不一致')
            _check(saved['scores_rad']==list(expected.scores_rad), '选择分数不一致')
    noises = {n.name:n for n in config.conditions}
    replayed = 0
    for row, planned in zip(rows, plan):
        for key, value in planned.items():
            _check(row[key]==str(value), f'试次元数据错误: {key}')
        repeat = int(row['repeat']); raw = raw_sets[repeat]
        for key in ('candidate_seed','holdout_seed','noise_seed','selection_seed','robot_noise_seed'):
            _check(int(row[key])==getattr(config,key)+repeat, f'种子错误: {key}')
        selection = selections[str(repeat)][row['strategy']]
        g, q, ids = trial_inputs(raw, selection, planned, noises[row['condition']])
        _check(json.loads(row['selection_ids'])==ids.tolist(), '采样前缀错误')
        closure = np.max(np.abs(raw['candidate_g'][ids] @ raw['x_true'] @ raw['candidate_q'][ids]-raw['y_true']))
        np.testing.assert_allclose(float(row['closure_max_abs']), closure, rtol=0, atol=1e-15)
        if row['status']=='ok':
            saved = _read(folder, row['estimate_file'])
            estimate = np.asarray(saved['t_g_c'])
            if replay:
                new_estimate = calibrate_hand_eye(g, q, method=row['method'])
                np.testing.assert_allclose(new_estimate, estimate, atol=1e-12, rtol=0)
                replayed += 1
            metrics, held = evaluate_estimate(estimate, raw)
            for metric in METRICS:
                np.testing.assert_allclose(float(row[metric]), metrics[metric], rtol=0, atol=1e-10)
            for key in held:
                np.testing.assert_allclose(saved['heldout'][key], held[key], rtol=0, atol=1e-12)
        else:
            _check(row['status']=='error' and all(row[m]=='' for m in METRICS) and bool(row['message']), '失败行非法')
    baseline = [r for r in rows if r['condition']=='baseline']
    _check(all(r['status']=='ok' and float(r['rotation_error_deg'])<np.rad2deg(1e-6)
               and float(r['translation_error_mm'])<.001 for r in baseline), '无噪声指标未通过')
    _check(_read(folder,'baseline_gate.json')=={'passed':True,'checked':len(baseline)}, '基线计数不一致')
    _check(_read(folder,'summary.json')==summarize(rows), '统计复算不一致')
    with (folder/'summary.csv').open(encoding='utf-8',newline='') as f:
        summary_csv=list(csv.DictReader(f))
    _check(summary_csv==[{k:'' if v is None else str(v) for k,v in r.items()} for r in summarize(rows)], '汇总 CSV 不一致')
    _check(_read(folder,'paired.json')==paired_comparison(rows,config), '配对复算不一致')
    return dict(result='PASS', trials=len(rows), replayed_successes=replayed, raw_datasets=len(raw_sets),
                note='重放不增加独立重复数；失败试次保留，未伪称成功重放')


def compare_runs(first, second):
    """同配置独立进程比较；排除时间戳、执行耗时与压缩文件元数据。"""
    first, second = Path(first), Path(second)
    _check(_read(first,'config.json')==_read(second,'config.json'), '两次配置不同')
    for name in ('summary.json','paired.json','baseline_gate.json','trial_plan.json'):
        _check(_read(first,name)==_read(second,name), f'独立重跑不同: {name}')
    for path in sorted((first/'raw').glob('*.npz')):
        with np.load(path,allow_pickle=False) as a, np.load(second/'raw'/path.name,allow_pickle=False) as b:
            _check(set(a.files)==set(b.files), '原始字段不同')
            for key in a.files:
                np.testing.assert_array_equal(a[key],b[key])
    a,b=_read(first,'selections.json'),_read(second,'selections.json')
    for repeat in a:
        for strategy in a[repeat]:
            for key in ('ids','scores_rad'):
                _check(a[repeat][strategy][key]==b[repeat][strategy][key], '选择结果不一致')
    def numerical_rows(folder):
        with (folder/'trials.csv').open(encoding='utf-8',newline='') as f:
            return [{k:v for k,v in r.items() if k not in ('selection_seconds','solve_seconds')} for r in csv.DictReader(f)]
    _check(numerical_rows(first)==numerical_rows(second),'试次非时间字段不一致')
    return dict(result='PASS', identical_trials=len(numerical_rows(first)))
