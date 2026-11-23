"""只依赖计划机器人位姿的离线选择；不接受相机观测、真值或留出集。"""
from dataclasses import dataclass
from numbers import Integral

import numpy as np
from scipy.spatial.transform import Rotation

from .calibration import pose_stack

STRATEGIES = ('ordered', 'random', 'rotation_farthest')


def _integer(value, name):
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Integral) or value < 0:
        raise ValueError(f'{name} 必须为非负整数')
    return int(value)


def _ids(values, name):
    try:
        result = tuple(_integer(x, name) for x in values)
    except TypeError as exc:
        raise ValueError(f'{name} 必须为整数序列') from exc
    if not result or len(set(result)) != len(result):
        raise ValueError(f'{name} 必须非空且无重复')
    return result


@dataclass(frozen=True)
class Selection:
    ids: tuple
    scores_rad: tuple


def select_poses(t_b_g, *, candidate_ids, initial_ids, n_samples, strategy, seed):
    """返回包含初始样本的有序 ID；短 N 是长 N 的前缀。

    rotation_farthest 最大化到已选姿态的最小主旋转角。
    分数差 <=1e-12 rad 视为数值并列，选最小 ID。它不保证可辨识性。
    ordered/random 不使用覆盖分数，日志中以 None 表示未计算。
    """
    g = pose_stack(t_b_g, minimum=1)
    ids, initial = _ids(candidate_ids, 'candidate_ids'), _ids(initial_ids, 'initial_ids')
    n, seed = _integer(n_samples, 'n_samples'), _integer(seed, 'seed')
    if len(ids) != len(g) or not set(initial) <= set(ids):
        raise ValueError('候选 ID 须与位姿一一对应，初始 ID 须属于候选集')
    if not len(initial) <= n <= len(ids):
        raise ValueError('n_samples 必须在初始样本数与候选数之间')
    if strategy not in STRATEGIES:
        raise ValueError(f'strategy 必须为 {STRATEGIES}')
    selected, scores = list(initial), [None]*len(initial)
    remaining = sorted(set(ids)-set(initial))
    if strategy in ('ordered', 'random'):
        if strategy == 'random':
            remaining = np.random.default_rng(seed).permutation(remaining).tolist()
        selected.extend(remaining[:n-len(initial)])
        scores.extend([None]*(n-len(initial)))
    else:
        index = {value: i for i, value in enumerate(ids)}
        rotations = g[:, :3, :3]
        # 一次建立 O(M²) 距离表；评分循环不重复验证/SVD。
        distances = np.stack([Rotation.from_matrix(r @ rotations.transpose(0, 2, 1)).magnitude()
                              for r in rotations])
        while len(selected) < n:
            values = np.array([min(distances[index[c], index[s]] for s in selected) for c in remaining])
            best = float(values.max())
            position = next(i for i, v in enumerate(values) if abs(v-best) <= 1e-12)
            selected.append(remaining.pop(position))
            scores.append(float(values[position]))
    return Selection(tuple(selected), tuple(scores))
