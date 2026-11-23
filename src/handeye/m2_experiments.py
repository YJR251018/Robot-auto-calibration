"""M2 冻结协议：共享候选/噪声、独立留出、先基线后噪声、逐次落盘。"""
from dataclasses import asdict, dataclass, field
import csv
import hashlib
import json
from pathlib import Path
import platform
import time
import traceback

import cv2
import numpy as np
import scipy
from scipy.spatial.transform import Rotation

from .calibration import CalibrationError, METHODS, calibrate_hand_eye, pose_stack
from .evaluation import board_reference_points, heldout_metrics
from .metrics import pose_error
from .sampling import STRATEGIES, select_poses
from .simulation import SceneConfig, generate_dataset, nonnegative_integer, nonnegative_real

ROOT = Path(__file__).resolve().parents[2]
METRICS = ('rotation_error_deg', 'translation_error_mm', 'point_rmse_mm', 'point_max_mm',
           'closure_rotation_rmse_deg', 'closure_translation_rmse_mm')


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def code_hashes():
    paths = sorted((ROOT/'src/handeye').glob('*.py')) + sorted((ROOT/'scripts').glob('*m2*.py'))
    return {p.relative_to(ROOT).as_posix(): digest(p) for p in paths}


@dataclass(frozen=True)
class Noise:
    name: str
    rotation_deg: float = 0.0
    translation_mm: float = 0.0
    robot_rotation_deg: float = 0.0
    robot_translation_mm: float = 0.0


@dataclass(frozen=True)
class M2Config:
    repeats: int = 30
    candidate_count: int = 60
    holdout_count: int = 20
    sample_counts: tuple = (8, 12, 20)
    initial_ids: tuple = (0, 1, 2, 3)
    strategies: tuple = STRATEGIES
    methods: tuple = ('PARK', 'TSAI')
    candidate_seed: int = 310000
    holdout_seed: int = 320000
    noise_seed: int = 330000
    selection_seed: int = 340000
    robot_noise_seed: int = 350000
    bootstrap_seed: int = 360000
    bootstrap_repeats: int = 2000
    conditions: tuple = field(default_factory=lambda: (Noise('baseline'), Noise('rotation', .3),
                                 Noise('translation', 0, .5), Noise('mixed', .3, .5)))
    scene: SceneConfig = field(default_factory=SceneConfig)

    @classmethod
    def from_dict(cls, values):
        values = dict(values)
        if 'scene' in values:
            values['scene'] = SceneConfig(**values['scene'])
        if 'conditions' in values:
            values['conditions'] = tuple(Noise(**x) for x in values['conditions'])
        config = cls(**values)
        config.validate()
        return config

    def validate(self):
        if nonnegative_integer(self.repeats, 'repeats') < 2:
            raise ValueError('至少两个独立重复')
        if nonnegative_integer(self.candidate_count, 'candidate_count') < 4:
            raise ValueError('候选数至少4')
        if nonnegative_integer(self.holdout_count, 'holdout_count') < 3:
            raise ValueError('留出数至少3')
        if nonnegative_integer(self.bootstrap_repeats, 'bootstrap_repeats') < 2:
            raise ValueError('bootstrap_repeats 至少2')
        for name in ('candidate_seed', 'holdout_seed', 'noise_seed', 'selection_seed', 'robot_noise_seed', 'bootstrap_seed'):
            nonnegative_integer(getattr(self, name), name)
        # 分离随机流区间；相同数字种子用于不同用途会产生非预期相关。
        starts = [getattr(self, name) for name in ('candidate_seed', 'holdout_seed', 'noise_seed', 'selection_seed', 'robot_noise_seed')]
        if any(abs(a-b) < self.repeats for i, a in enumerate(starts) for b in starts[i+1:]):
            raise ValueError('各随机流的种子区间必须分离')
        for name in ('sample_counts', 'initial_ids', 'strategies', 'methods', 'conditions'):
            values = getattr(self, name)
            if not values:
                raise ValueError(f'{name} 不可为空')
        if len(set(self.sample_counts)) != len(self.sample_counts) or len(set(self.initial_ids)) != len(self.initial_ids):
            raise ValueError('样本量或初始 ID 不可重复')
        for value in self.initial_ids:
            if nonnegative_integer(value, 'initial_ids') >= self.candidate_count:
                raise ValueError('初始 ID 超出候选范围')
        for value in self.sample_counts:
            n = nonnegative_integer(value, 'sample_counts')
            if not max(3, len(self.initial_ids)) <= n <= self.candidate_count:
                raise ValueError('样本量超出合法范围')
        for name, allowed in (('strategies', STRATEGIES), ('methods', METHODS)):
            values = getattr(self, name)
            if len(set(values)) != len(values) or any(x not in allowed for x in values):
                raise ValueError(f'{name} 包含重复或未知值')
        names = []
        for noise in self.conditions:
            if not isinstance(noise, Noise) or not isinstance(noise.name, str) or not noise.name.isidentifier():
                raise ValueError('噪声条件须有合法唯一名称')
            names.append(noise.name)
            for key, value in asdict(noise).items():
                if key != 'name':
                    nonnegative_real(value, key)
        if len(set(names)) != len(names) or names[0] != 'baseline' or self.conditions[0] != Noise('baseline'):
            raise ValueError('第一个条件必须是全零 baseline，名称不得重复')
        if not isinstance(self.scene, SceneConfig):
            raise ValueError('scene 类型错误')
        self.scene.truth()


def perturb_poses(poses, standard_noise, *, rotation_rad, translation_m):
    """在位姿的目标系左乘旋转、独立相加平移；不重生成几何观测。"""
    poses = pose_stack(poses, minimum=1)
    z = np.asarray(standard_noise)
    if z.shape != (len(poses), 6) or z.dtype.kind not in 'iuf' or not np.all(np.isfinite(z)):
        raise ValueError('标准噪声须为有限实数 (N,6)')
    sr = nonnegative_real(rotation_rad, 'rotation_rad')
    st = nonnegative_real(translation_m, 'translation_m')
    poses[:, :3, :3] = Rotation.from_rotvec(z[:, :3]*sr).as_matrix() @ poses[:, :3, :3]
    poses[:, :3, 3] += z[:, 3:]*st
    return poses


def trial_plan(config):
    """condition 在最外层，保证全部无噪声先于任何噪声试次。"""
    return [dict(trial_id=f'{noise.name}_{r:03d}_{strategy}_{n}_{method}', condition=noise.name,
                 repeat=r, strategy=strategy, n_samples=n, method=method)
            for noise in config.conditions for r in range(config.repeats)
            for strategy in config.strategies for n in config.sample_counts for method in config.methods]


def prepare_repeat(config, repeat):
    """生成端可以访问真值；选择器只收到 g 与 ID。"""
    data = generate_dataset(config.candidate_count, seed=config.candidate_seed+repeat, scene=config.scene)
    holdout = generate_dataset(config.holdout_count, seed=config.holdout_seed+repeat, scene=config.scene)
    raw = dict(candidate_g=data.t_b_g, candidate_q=data.t_c_t, holdout_g=holdout.t_b_g,
               holdout_q=holdout.t_c_t, x_true=data.t_g_c_true, y_true=data.t_b_t_true,
               candidate_ids=np.arange(config.candidate_count), holdout_ids=np.arange(config.holdout_count),
               camera_standard_noise=np.random.default_rng(config.noise_seed+repeat).normal(size=(config.candidate_count, 6)),
               robot_standard_noise=np.random.default_rng(config.robot_noise_seed+repeat).normal(size=(config.candidate_count, 6)),
               points=board_reference_points())
    selections = {}
    for strategy in config.strategies:
        start = time.perf_counter()
        selection = select_poses(raw['candidate_g'], candidate_ids=raw['candidate_ids'],
                                 initial_ids=config.initial_ids, n_samples=max(config.sample_counts),
                                 strategy=strategy, seed=config.selection_seed+repeat)
        selections[strategy] = dict(ids=list(selection.ids), scores_rad=list(selection.scores_rad),
                                    seconds=time.perf_counter()-start)
    return raw, selections


def trial_inputs(raw, selection, trial, noise):
    ids = np.asarray(selection['ids'][:trial['n_samples']], dtype=int)
    g = perturb_poses(raw['candidate_g'], raw['robot_standard_noise'],
                      rotation_rad=np.deg2rad(noise.robot_rotation_deg), translation_m=noise.robot_translation_mm/1000)
    q = perturb_poses(raw['candidate_q'], raw['camera_standard_noise'],
                      rotation_rad=np.deg2rad(noise.rotation_deg), translation_m=noise.translation_mm/1000)
    return g[ids], q[ids], ids


def evaluate_estimate(estimate, raw):
    error = pose_error(estimate, raw['x_true'])
    held = heldout_metrics(estimate, raw['holdout_g'], raw['holdout_q'], raw['y_true'], points=raw['points'])
    metrics = dict(rotation_error_deg=error.rotation_deg, translation_error_mm=error.translation_mm,
                   point_rmse_mm=held['point_rmse_m']*1000, point_max_mm=held['point_max_m']*1000,
                   closure_rotation_rmse_deg=float(np.rad2deg(held['closure_rotation_rmse_rad'])),
                   closure_translation_rmse_mm=held['closure_translation_rmse_m']*1000)
    if not all(np.isfinite(x) for x in metrics.values()):
        raise ValueError('评价产生非有限数值')
    return metrics, held


def summarize(rows):
    groups = {}
    for row in rows:
        key = (row['condition'], row['strategy'], row['method'], int(row['n_samples']))
        groups.setdefault(key, []).append(row)
    result = []
    for (condition, strategy, method, n), members in groups.items():
        ok = [r for r in members if r['status'] == 'ok']
        item = dict(condition=condition, strategy=strategy, method=method, n_samples=n,
                    total=len(members), success=len(ok), failed=len(members)-len(ok),
                    failure_rate=(len(members)-len(ok))/len(members))
        for metric in METRICS:
            values = np.asarray([float(r[metric]) for r in ok])
            stats = dict(mean=float(values.mean()) if len(values) else None,
                         std=float(values.std(ddof=1)) if len(values)>1 else None,
                         median=float(np.median(values)) if len(values) else None,
                         q25=float(np.quantile(values, .25)) if len(values) else None,
                         q75=float(np.quantile(values, .75)) if len(values) else None,
                         max=float(values.max()) if len(values) else None)
            item.update({metric+'_'+k: v for k, v in stats.items()})
        result.append(item)
    return result


def paired_comparison(rows, config):
    """预设主比较，负差值支持 farthest；只使用共同成功配对并披露分母。"""
    selected = [r for r in rows if r['condition']=='mixed' and r['method']=='PARK' and int(r['n_samples'])==20]
    groups = {s: {int(r['repeat']):r for r in selected if r['strategy']==s}
              for s in ('random', 'rotation_farthest')}
    pairs = []
    for repeat in sorted(set(groups['random']) & set(groups['rotation_farthest'])):
        a, b = groups['random'][repeat], groups['rotation_farthest'][repeat]
        if a['status']==b['status']=='ok':
            pairs.append(dict(repeat=repeat, delta_mm=float(b['point_rmse_mm'])-float(a['point_rmse_mm'])))
    values = np.asarray([p['delta_mm'] for p in pairs])
    result = dict(comparison='rotation_farthest - random; N=20, mixed, PARK, heldout point RMSE',
                  eligible_repeats=len(set(groups['random']) & set(groups['rotation_farthest'])),
                  paired_success=len(pairs), pairs=pairs, mean_delta_mm=None, ci95_mm=None,
                  bootstrap_seed=config.bootstrap_seed, bootstrap_repeats=config.bootstrap_repeats)
    if len(values):
        result['mean_delta_mm'] = float(values.mean())
    if len(values)>1:
        draws = np.random.default_rng(config.bootstrap_seed).choice(values, (config.bootstrap_repeats, len(values)), replace=True)
        result['ci95_mm'] = np.quantile(draws.mean(axis=1), [.025, .975]).tolist()
    return result


def write_csv(path, rows):
    with Path(path).open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)


def run_m2(config, output):
    """仅创建新目录；中断后另建运行，不支持不经核验的原地续跑。"""
    config.validate()
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    (output/'raw').mkdir(); (output/'estimates').mkdir()
    write_json(output/'config.json', asdict(config))
    write_json(output/'environment.json', dict(python=platform.python_version(), numpy=np.__version__,
                                              scipy=scipy.__version__, opencv=cv2.__version__))
    write_json(output/'code_hashes.json', code_hashes())
    plan = trial_plan(config)
    write_json(output/'trial_plan.json', plan)
    write_json(output/'run_status.json', dict(status='running', planned=len(plan), completed=0))
    rows, raw_sets, selections = [], {}, {}
    phase, current = 'prepare', None
    baseline_count = sum(t['condition']=='baseline' for t in plan)
    baseline_passed = False
    try:
        for repeat in range(config.repeats):
            raw, selection = prepare_repeat(config, repeat)
            raw_sets[repeat], selections[str(repeat)] = raw, selection
            np.savez_compressed(output/f'raw/repeat_{repeat:03d}.npz', **raw)
        write_json(output/'selections.json', selections)
        noises = {n.name:n for n in config.conditions}
        with (output/'trials.csv').open('w', newline='', encoding='utf-8') as f:
            writer = None
            for trial in plan:
                current = dict(trial, status='error', failure_stage='', message='', traceback_file='',
                               candidate_seed=config.candidate_seed+trial['repeat'], holdout_seed=config.holdout_seed+trial['repeat'],
                               noise_seed=config.noise_seed+trial['repeat'], selection_seed=config.selection_seed+trial['repeat'],
                               robot_noise_seed=config.robot_noise_seed+trial['repeat'], data_file=f"raw/repeat_{trial['repeat']:03d}.npz",
                               estimate_file='', selection_ids='', selection_seconds='', solve_seconds='', closure_max_abs='',
                               rotation_sigma_deg='', translation_sigma_mm='', robot_rotation_sigma_deg='', robot_translation_sigma_mm='',
                               **{metric:'' for metric in METRICS})
                if writer is None:
                    writer = csv.DictWriter(f, fieldnames=list(current)); writer.writeheader()
                phase = 'inputs'
                try:
                    raw = raw_sets[trial['repeat']]
                    selection = selections[str(trial['repeat'])][trial['strategy']]
                    noise = noises[trial['condition']]
                    g, q, ids = trial_inputs(raw, selection, trial, noise)
                    closure = float(np.max(np.abs(raw['candidate_g'][ids] @ raw['x_true'] @ raw['candidate_q'][ids]-raw['y_true'])))
                    if closure >= 1e-12:
                        raise ValueError('所选理想几何闭环失败')
                    current.update(selection_ids=json.dumps(ids.tolist()), selection_seconds=selection['seconds'],
                                   closure_max_abs=closure, rotation_sigma_deg=noise.rotation_deg, translation_sigma_mm=noise.translation_mm,
                                   robot_rotation_sigma_deg=noise.robot_rotation_deg, robot_translation_sigma_mm=noise.robot_translation_mm)
                    phase = 'solve'; start = time.perf_counter()
                    estimate = calibrate_hand_eye(g, q, method=trial['method'])
                    current['solve_seconds'] = time.perf_counter()-start
                    phase = 'evaluate'
                    metrics, held = evaluate_estimate(estimate, raw)
                    current.update(metrics, status='ok', estimate_file=f"estimates/{trial['trial_id']}.json")
                    phase = 'persist_estimate'
                    write_json(output/current['estimate_file'], dict(t_g_c=estimate.tolist(), heldout=held))
                except (Exception, KeyboardInterrupt) as exc:
                    current.update(status='error', failure_stage=phase, message=f'{type(exc).__name__}: {exc}')
                    current.update({metric:'' for metric in METRICS})
                    expected = phase=='solve' and isinstance(exc, (CalibrationError, ValueError))
                    if not expected:
                        current['traceback_file'] = 'traceback.txt'
                        write_json(output/'failure_context.json', dict(trial=current['trial_id'], phase=phase))
                        (output/'traceback.txt').write_text(traceback.format_exc(), encoding='utf-8')
                    rows.append(current); writer.writerow(current); f.flush()
                    if not expected:
                        raise
                else:
                    rows.append(current); writer.writerow(current); f.flush()
                if trial['condition']=='baseline':
                    passed = current['status']=='ok' and current['rotation_error_deg'] < np.rad2deg(1e-6) and current['translation_error_mm'] < .001
                    if not passed:
                        write_json(output/'baseline_gate.json', dict(passed=False, failed_trial=trial['trial_id'], checked=len(rows)))
                        raise RuntimeError('无噪声关卡失败，停止噪声实验')
                    if len(rows)==baseline_count:
                        baseline_passed = True
                        write_json(output/'baseline_gate.json', dict(passed=True, checked=baseline_count))
                if len(rows)%max(1, len(config.methods)*len(config.sample_counts)*len(config.strategies))==0:
                    write_json(output/'run_status.json', dict(status='running', planned=len(plan), completed=len(rows), baseline_passed=baseline_passed))
        phase = 'summary'
        summary, paired = summarize(rows), paired_comparison(rows, config)
        write_json(output/'summary.json', summary); write_csv(output/'summary.csv', summary)
        write_json(output/'paired.json', paired)
        phase = 'plot'
        from .m2_plotting import plot_m2
        plot_m2(output)
        failures = sum(r['status']!='ok' for r in rows)
        (output/'RESULTS.md').write_text(
            '# M2 实验结果\n\n'
            f'计划 {len(plan)} 次，实际 {len(rows)} 次，成功 {len(rows)-failures}，失败 {failures}。无噪声 {baseline_count} 次通过。\n\n'
            '独立重复单位是 repeat；重放、帧和板点不增加独立样本数。误差汇总条件于求解成功，同时报告失败率。\n\n'
            f"预设主比较（farthest-random，N20/mixed/PARK）有效配对 {paired['paired_success']}，均值差 {paired['mean_delta_mm']} mm，"
            f"95% 配对 bootstrap 区间 {paired['ci95_mm']} mm。负值表示 farthest 的留出点 RMSE 较低。\n\n"
            'error_vs_samples 图为均值±样本SD，不是置信区间；paired 图是按独立 repeat 的配对差值；failure_rate 图保留零失败。\n\n'
            'closure_max_abs 只检查实际所选理想 G/Q 的几何闭环。当前是位姿观测仿真，不包含视野、图像、机器人可达性或实际运动时间。\n'
            '未证明启发式最优或创新性；不同场景与噪声可能推翻当前趋势。\n', encoding='utf-8')
        status = dict(status='complete', planned=len(plan), completed=len(rows), succeeded=len(rows)-failures,
                      failed=failures, baseline_passed=baseline_passed, baseline_trials=baseline_count)
        write_json(output/'run_status.json', status)
        write_json(output/'artifact_hashes.json', {p.relative_to(output).as_posix():digest(p) for p in sorted(output.rglob('*')) if p.is_file()})
        return status
    except (Exception, KeyboardInterrupt) as exc:
        (output/'traceback.txt').write_text(traceback.format_exc(), encoding='utf-8')
        write_json(output/'run_status.json', dict(status='interrupted' if isinstance(exc, KeyboardInterrupt) else 'failed',
                   planned=len(plan), completed=len(rows), baseline_passed=baseline_passed,
                   failure_stage=phase, message=f'{type(exc).__name__}: {exc}', traceback_file='traceback.txt'))
        raise
