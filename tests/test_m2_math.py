"""M2 已知数值、选择信息边界与前缀协议。"""
import inspect

import numpy as np
import pytest

from handeye.evaluation import heldout_metrics
from handeye.sampling import select_poses
from handeye.simulation import generate_dataset
from handeye.transforms import make_transform, rotation_matrix


def identities(n=3):
    return np.repeat(np.eye(4)[None], n, axis=0)


def test_heldout_truth_and_inputs_unchanged():
    data = generate_dataset(20, seed=320001)
    originals = [a.copy() for a in (data.t_b_g, data.t_c_t, data.t_g_c_true, data.t_b_t_true)]
    result = heldout_metrics(data.t_g_c_true, data.t_b_g, data.t_c_t, data.t_b_t_true)
    assert result['point_rmse_m'] < 1e-12
    assert result['point_max_m'] < 1e-12
    assert len(result['frame_point_rmse_m']) == 20
    for a, b in zip(originals, (data.t_b_g, data.t_c_t, data.t_g_c_true, data.t_b_t_true)):
        np.testing.assert_array_equal(a, b)


def test_heldout_known_translation_and_rotation():
    g = q = identities()
    x = make_transform(np.eye(3), [.003, .004, 0])
    result = heldout_metrics(x, g, q, np.eye(4), points=[[0, 0, 0], [1, 0, 0]])
    assert result['point_rmse_m'] == pytest.approx(.005, abs=1e-15)
    assert result['closure_translation_rmse_m'] == pytest.approx(.005)
    x = make_transform(rotation_matrix('z', np.pi/2), [0, 0, 0])
    result = heldout_metrics(x, g, q, np.eye(4), points=[[0, 0, 0], [1, 0, 0]])
    assert result['point_rmse_m'] == pytest.approx(1.0)
    assert result['point_max_m'] == pytest.approx(np.sqrt(2))
    assert result['closure_rotation_rmse_rad'] == pytest.approx(np.pi/2)


@pytest.mark.parametrize('points', [[], [[np.nan, 0, 0]], [[True]*3], [[1, 2]], [1, 2, 3], [['1', '2', '3']]])
def test_heldout_bad_points(points):
    with pytest.raises(ValueError):
        heldout_metrics(np.eye(4), identities(), identities(), np.eye(4), points=points)


def test_heldout_bad_transforms_or_mismatched_lengths():
    with pytest.raises(ValueError):
        heldout_metrics(np.eye(4), identities(3), identities(4), np.eye(4))
    bad = identities(); bad[0, 0, 0] = -1
    with pytest.raises(ValueError):
        heldout_metrics(np.eye(4), bad, identities(), np.eye(4))


@pytest.mark.parametrize('strategy', ['ordered', 'random', 'rotation_farthest'])
def test_selection_deterministic_prefix_ids_and_no_mutation(strategy):
    poses = generate_dataset(30, seed=410001).t_b_g
    before = poses.copy()
    ids = np.arange(100, 130)
    kwargs = dict(candidate_ids=ids, initial_ids=[101, 103, 104, 106], strategy=strategy, seed=42)
    long = select_poses(poses, n_samples=20, **kwargs)
    short = select_poses(poses, n_samples=8, **kwargs)
    assert long.ids[:8] == short.ids
    assert long.ids == select_poses(poses, n_samples=20, **kwargs).ids
    assert len(set(long.ids)) == 20 and set(long.ids) <= set(ids)
    assert long.ids[:4] == (101, 103, 104, 106)
    np.testing.assert_array_equal(poses, before)


def test_farthest_known_choice_and_numeric_tie():
    angles = [0, np.pi/6, np.pi/2, -np.pi/2]
    poses = np.stack([make_transform(rotation_matrix('z', a), [0, 0, 0]) for a in angles])
    result = select_poses(poses, candidate_ids=[9, 6, 4, 2], initial_ids=[9], n_samples=3,
                          strategy='rotation_farthest', seed=0)
    assert result.ids == (9, 2, 4)
    np.testing.assert_allclose(result.scores_rad[1:], [np.pi/2, np.pi/2])


def test_selection_is_invariant_to_base_rotation_and_translations():
    poses = generate_dataset(25, seed=410002).t_b_g
    kwargs = dict(candidate_ids=list(range(25)), initial_ids=[0, 1, 2, 3], n_samples=20,
                  strategy='rotation_farthest', seed=42)
    changed = make_transform(rotation_matrix('x', .7), [3, 2, 1]) @ poses
    changed[:, :3, 3] += np.arange(25)[:, None]
    assert select_poses(poses, **kwargs).ids == select_poses(changed, **kwargs).ids
    assert set(inspect.signature(select_poses).parameters) == {
        't_b_g', 'candidate_ids', 'initial_ids', 'n_samples', 'strategy', 'seed'}


@pytest.mark.parametrize('override', [
    {'n_samples':True}, {'n_samples':4.5}, {'n_samples':21}, {'n_samples':2},
    {'initial_ids':[]}, {'initial_ids':[0, 0]}, {'initial_ids':[21]},
    {'initial_ids':[False]}, {'candidate_ids':[0]*20}, {'candidate_ids':list(range(19))},
    {'seed':True}, {'seed':-1}, {'strategy':'oracle'},
])
def test_invalid_selection(override):
    kwargs = dict(candidate_ids=list(range(20)), initial_ids=[0, 1, 2, 3], n_samples=8,
                  strategy='random', seed=0)
    kwargs.update(override)
    with pytest.raises(ValueError):
        select_poses(identities(20), **kwargs)
