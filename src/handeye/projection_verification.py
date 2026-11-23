"""W2 原始数组、预测、OpenCV重求解与计数核验；不重新筛选种子。"""
import csv
import json
from pathlib import Path

import numpy as np

from .m2_experiments import digest
from .projection_experiment import ProjectionConfig, aggregate, analyze_candidates, generate_projection_candidates


def verify_projection(folder):
    folder = Path(folder).resolve()
    def read(name):
        return json.loads((folder/name).read_text(encoding='utf-8'))
    def check(condition, message):
        if not condition:
            raise ValueError(message)
    status = read('run_status.json')
    check(status['status']=='complete', 'W2运行未完成')
    hashes = read('artifact_hashes.json')
    files = {p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file()}-{'artifact_hashes.json'}
    check(set(hashes)==files, 'W2产物清单不同')
    for name, expected in hashes.items():
        path = (folder/name).resolve()
        check(path.is_relative_to(folder), 'W2产物路径越界')
        check(digest(path)==expected, f'W2哈希不一致: {name}')
    config = ProjectionConfig.from_dict(read('config.json'))
    results, baseline, rows = [], [], []
    for repeat in range(config.repeats):
        seed = config.seed_start+repeat
        with np.load(folder/f'raw/seed_{seed}.npz', allow_pickle=False) as data:
            raw = {k:data[k] for k in ('g','q','points','x_true','y_true')}
            regenerated = generate_projection_candidates(config, seed)
            for key in raw:
                np.testing.assert_array_equal(raw[key], regenerated[key])
            replay_rows, result, checks, estimates, extra = analyze_candidates(raw, config, seed)
            for key, value in extra.items():
                np.testing.assert_array_equal(data[key], value)
            saved = read(f'estimates/seed_{seed}.json')
            check(saved==dict(methods=estimates, y_est=extra['y_est'].tolist()), 'W2估计重放不同')
        results.append(result); baseline.extend(checks); rows.extend(replay_rows)
    check(read('per_repeat.json')==results, 'W2逐种子结果不同')
    check(read('baseline.json')==baseline, 'W2基线结果不同')
    check(read('summary.json')==aggregate(results, baseline), 'W2汇总复算不同')
    with (folder/'candidates.csv').open(encoding='utf-8', newline='') as f:
        actual = list(csv.DictReader(f))
    expected = [{k:str(v) for k,v in row.items()} for row in rows]
    check(actual==expected, 'W2候选CSV不同或缺失/重复')
    check(status==dict(status='complete', completed_repeats=config.repeats,
                       candidates=len(rows), baseline_solves=len(baseline)), 'W2状态计数不一致')
    return dict(result='PASS', candidates=len(rows), regenerated_repeats=len(results),
                replayed_baseline_solves=len(baseline), prediction_evaluations=sum(r['predicted_candidates'] for r in results),
                note='重放不增加独立实验单位；可见性预测只验证理想训练场景')
