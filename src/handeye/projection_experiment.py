"""W2 固定协议：几何可见性及由训练估计预测的可见性；无像素噪声。"""
from collections import Counter
from dataclasses import asdict, dataclass, field
import csv
import json
from pathlib import Path
import platform
import traceback

import cv2
import numpy as np
import scipy
from scipy.spatial.transform import Rotation

from .calibration import calibrate_hand_eye, motion_diagnostics
from .camera import Camera, board_grid, estimate_target_in_base, measure_visibility, predict_visibility, project_points
from .m2_experiments import code_hashes, digest, write_json
from .metrics import pose_error
from .simulation import SceneConfig, nonnegative_integer
from .transforms import invert_transform, make_transform


@dataclass(frozen=True)
class ProjectionConfig:
    repeats: int = 30
    seed_start: int = 510000
    candidate_count: int = 120
    training_count: int = 20
    camera: Camera = field(default_factory=Camera)
    scene: SceneConfig = field(default_factory=SceneConfig)

    @classmethod
    def from_dict(cls, values):
        values = dict(values)
        for key, constructor in (('camera', Camera), ('scene', SceneConfig)):
            if key in values:
                values[key] = constructor(**values[key])
        result = cls(**values)
        result.validate()
        return result

    def validate(self):
        if nonnegative_integer(self.repeats, 'repeats') < 1:
            raise ValueError('repeats 至少1')
        nonnegative_integer(self.seed_start, 'seed_start')
        if not 3 <= nonnegative_integer(self.training_count, 'training_count') < nonnegative_integer(self.candidate_count, 'candidate_count'):
            raise ValueError('须有至少3个训练位姿和额外评价候选')
        if not isinstance(self.camera, Camera) or not isinstance(self.scene, SceneConfig):
            raise ValueError('camera/scene 类型错误')
        self.camera.validate(); self.scene.truth()


def generate_projection_candidates(config, seed):
    """生成端访问真值，G=Y inv(Q) inv(X)；不按可见性重采样。"""
    config.validate()
    seed = nonnegative_integer(seed, 'seed')
    rng = np.random.default_rng(seed)
    x, y = config.scene.truth()
    g, q = [], []
    for _ in range(config.candidate_count):
        r = Rotation.from_rotvec(rng.uniform(-.5, .5, 3)).as_matrix()
        t = rng.uniform([-.45, -.32, .35], [.45, .32, .9])
        observation = make_transform(r, t)
        q.append(observation)
        g.append(y @ invert_transform(observation) @ invert_transform(x))
    return dict(g=np.stack(g), q=np.stack(q), x_true=x, y_true=y, points=board_grid())


def analyze_candidates(raw, config, seed):
    """测量端判定后，以前20可见样本作理想训练；非主动采样对比。"""
    g, q, points = raw['g'], raw['q'], raw['points']
    closure = float(np.max(np.abs(g @ raw['x_true'] @ q-raw['y_true'])))
    if closure >= 1e-12:
        raise ValueError('W2 理想闭环失败')
    measured = [measure_visibility(observation, config.camera, points=points) for observation in q]
    visible_ids = [i for i, result in enumerate(measured) if result.visible]
    if len(visible_ids) < config.training_count:
        raise ValueError(f'seed={seed}: 可见候选不足，不重新抽取种子')
    train = visible_ids[:config.training_count]
    if not motion_diagnostics(g[train])['nondegenerate']:
        raise ValueError(f'seed={seed}: 训练运动退化')
    estimates, baseline = {}, []
    for method in ('PARK', 'TSAI'):
        x = calibrate_hand_eye(g[train], q[train], method=method)
        error = pose_error(x, raw['x_true'])
        baseline.append(dict(seed=seed, method=method, rotation_error_deg=error.rotation_deg,
                             translation_error_mm=error.translation_mm))
        if error.rotation_rad >= 1e-6 or error.translation_m >= 1e-6:
            raise ValueError(f'seed={seed}: {method} 无噪声恢复失败')
        estimates[method] = x.tolist()
    # 训练估计先得到Y_hat，规划端不接收Q_true、X_true或Y_true。
    x_est = np.asarray(estimates['PARK'])
    y_est = estimate_target_in_base(g[train], q[train], x_est)
    evaluated = [i for i in range(len(g)) if i not in train]
    predictions = {i:predict_visibility(g[i], x_est, y_est, config.camera, points=points) for i in evaluated}
    rows, pixel_errors = [], []
    for i, measurement in enumerate(measured):
        pixels, _ = project_points(points, q[i], config.camera)
        reference, _ = cv2.projectPoints(points, Rotation.from_matrix(q[i, :3, :3]).as_rotvec(),
                                         q[i, :3, 3], config.camera.matrix(), None)
        error = float(np.max(np.abs(pixels-reference.reshape(-1, 2))))
        if error >= 1e-8:
            raise ValueError('OpenCV投影对照超过预设阈值')
        pixel_errors.append(error)
        prediction = predictions.get(i)
        rows.append(dict(seed=seed, candidate_id=i, training=i in train, measured_visible=measurement.visible,
                         measured_reason=measurement.reason, predicted_visible='' if prediction is None else prediction.visible,
                         predicted_reason='' if prediction is None else prediction.reason,
                         min_depth_m=float(measurement.depths_m.min()), max_projection_error_px=error))
    incorrect = sum(predictions[i].visible != measured[i].visible for i in evaluated)
    result = dict(seed=seed, candidates=len(g), visible=len(visible_ids), rejected=len(g)-len(visible_ids),
                  reasons=dict(Counter(r.reason for r in measured)), training_ids=train,
                  predicted_candidates=len(evaluated), prediction_mismatches=incorrect,
                  closure_max_abs=closure, max_projection_error_px=max(pixel_errors))
    extra = dict(pixels=np.stack([r.pixels for r in measured]), depths_m=np.stack([r.depths_m for r in measured]),
                 measured_visible=np.array([r.visible for r in measured]),
                 training_ids=np.array(train), prediction_ids=np.array(evaluated),
                 predicted_visible=np.array([predictions[i].visible for i in evaluated]),
                 x_est=x_est, y_est=y_est)
    return rows, result, baseline, estimates, extra


def aggregate(results, baseline):
    reasons = Counter()
    for r in results:
        reasons.update(r['reasons'])
    return dict(repeats=len(results), candidates=sum(r['candidates'] for r in results),
                visible=sum(r['visible'] for r in results), rejected=sum(r['rejected'] for r in results),
                reasons=dict(reasons), min_visible_per_repeat=min(r['visible'] for r in results),
                predicted_candidates=sum(r['predicted_candidates'] for r in results),
                prediction_mismatches=sum(r['prediction_mismatches'] for r in results),
                baseline_solves=len(baseline), baseline_failures=0,
                max_closure_abs=max(r['closure_max_abs'] for r in results),
                max_projection_error_px=max(r['max_projection_error_px'] for r in results),
                max_rotation_error_deg=max(r['rotation_error_deg'] for r in baseline),
                max_translation_error_mm=max(r['translation_error_mm'] for r in baseline))


def plot_projection_examples(folder, raw, camera):
    """实际候选二维点示意；单图标清可见和越界，不模仿相机照片。"""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    results = [measure_visibility(q, camera, points=raw['points']) for q in raw['q']]
    for label, visible in (('visible', True), ('rejected', False)):
        index = next((i for i, r in enumerate(results) if r.visible==visible), None)
        if index is None:
            continue
        result = results[index]
        fig, ax = plt.subplots(figsize=(6.4, 5.2), layout='constrained')
        try:
            ax.scatter(result.pixels[:, 0], result.pixels[:, 1], s=14, color='#0072B2')
            from matplotlib.patches import Rectangle
            ax.add_patch(Rectangle((0, 0), camera.width-1, camera.height-1, fill=False, color='black'))
            ax.add_patch(Rectangle((camera.margin, camera.margin), camera.width-1-2*camera.margin,
                                  camera.height-1-2*camera.margin, fill=False, ls='--', color='#D55E00'))
            ax.set(xlabel='u (pixel)', ylabel='v (pixel)', title=f'Synthetic projected points: ID {index}, {result.reason}')
            ax.set_xlim(min(-40, result.pixels[:, 0].min()-30), max(camera.width+40, result.pixels[:, 0].max()+30))
            ax.set_ylim(max(camera.height+40, result.pixels[:, 1].max()+30), min(-40, result.pixels[:, 1].min()-30))
            ax.set_aspect('equal'); ax.grid(alpha=.2)
            fig.savefig(folder/f'projection_{label}.png', dpi=180)
            fig.savefig(folder/f'projection_{label}.pdf')
        finally:
            plt.close(fig)


def run_projection(config, output):
    config.validate()
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    (output/'raw').mkdir(); (output/'estimates').mkdir()
    write_json(output/'config.json', asdict(config))
    hashes = code_hashes()
    root = Path(__file__).resolve().parents[2]
    for name in ('run_projection.py', 'verify_projection.py'):
        path = root/'scripts'/name
        if path.exists():
            hashes[path.relative_to(root).as_posix()] = digest(path)
    write_json(output/'code_hashes.json', hashes)
    write_json(output/'environment.json', dict(python=platform.python_version(), opencv=cv2.__version__,
                                              numpy=np.__version__, scipy=scipy.__version__))
    write_json(output/'run_status.json', dict(status='running', completed_repeats=0))
    (output/'opencv_projectpoints_doc.txt').write_text(cv2.projectPoints.__doc__, encoding='utf-8')
    results, baseline = [], []
    phase, seed = 'prepare', config.seed_start
    try:
        with (output/'candidates.csv').open('w', encoding='utf-8', newline='') as f:
            writer = None
            for repeat in range(config.repeats):
                seed = config.seed_start+repeat
                phase = 'generate'
                raw = generate_projection_candidates(config, seed)
                # 即使分析失败也先保存当前候选；不会改种子补一个好样本。
                raw_path = output/f'raw/seed_{seed}.npz'
                np.savez_compressed(raw_path, **raw)
                phase = 'analyze'
                rows, result, checks, estimates, extra = analyze_candidates(raw, config, seed)
                phase = 'persist'
                np.savez_compressed(raw_path, **raw, **extra)
                write_json(output/f'estimates/seed_{seed}.json', dict(methods=estimates, y_est=extra['y_est'].tolist()))
                if writer is None:
                    writer = csv.DictWriter(f, fieldnames=list(rows[0])); writer.writeheader()
                writer.writerows(rows); f.flush()
                results.append(result); baseline.extend(checks)
                write_json(output/'per_repeat.json', results)
                write_json(output/'baseline.json', baseline)
                write_json(output/'run_status.json', dict(status='running', completed_repeats=len(results)))
                if repeat==0:
                    phase = 'plot'
                    plot_projection_examples(output, raw, config.camera)
        phase = 'summary'
        summary = aggregate(results, baseline)
        write_json(output/'summary.json', summary)
        (output/'RESULTS.md').write_text(
            '# W2 投影与可见性结果\n\n'
            f"{summary['repeats']}个固定种子，共{summary['candidates']}个候选；可见{summary['visible']}，"
            f"拒收{summary['rejected']}，原因{summary['reasons']}。最少可见数/种子={summary['min_visible_per_repeat']}。\n\n"
            f"{summary['baseline_solves']}次PARK/TSAI无噪声恢复通过。剩余候选预测{summary['predicted_candidates']}个，"
            f"错判{summary['prediction_mismatches']}。投影与OpenCV最大差{summary['max_projection_error_px']}pixel。\n\n"
            '预测只使用训练估计X_hat/Y_hat，评价端才读取真实Q。当前训练是理想观测，不能外推到像素噪声或粗初值。\n\n'
            '原始数据保存全部候选而非仅可见者；前20个可见候选只是几何验收训练，不是主动采样性能比较。\n'
            '图是合成二维投影点，不是相机照片；模型未含畸变、遮挡、真实角点检测、可达性和碰撞。\n', encoding='utf-8')
        write_json(output/'run_status.json', dict(status='complete', completed_repeats=len(results),
                                                  candidates=summary['candidates'], baseline_solves=len(baseline)))
        write_json(output/'artifact_hashes.json', {p.relative_to(output).as_posix():digest(p)
                                                   for p in sorted(output.rglob('*')) if p.is_file()})
        return summary
    except (Exception, KeyboardInterrupt) as exc:
        (output/'traceback.txt').write_text(traceback.format_exc(), encoding='utf-8')
        write_json(output/'run_status.json', dict(status='failed', completed_repeats=len(results),
                   seed=seed, failure_stage=phase, message=f'{type(exc).__name__}: {exc}', traceback_file='traceback.txt'))
        raise
