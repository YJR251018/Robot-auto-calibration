"""已知数值、独立 SciPy 参照、随机性质与非法输入测试。"""

import numpy as np
import pytest
from scipy.spatial.transform import Rotation

from handeye import (
    compose_transforms, invert_transform, is_rotation_matrix, make_transform,
    rotation_matrix, transform_points, validate_transform,
)


@pytest.mark.parametrize("axis", ["x", "y", "z"])
@pytest.mark.parametrize("angle", [0, 0.3, -1.2, np.pi, np.pi - 1e-10])
def test_rotation_matches_scipy_and_is_so3(axis, angle):
    r = rotation_matrix(axis, angle)
    np.testing.assert_allclose(r, Rotation.from_euler(axis, angle).as_matrix(), atol=1e-12, rtol=0)
    np.testing.assert_allclose(r.T @ r, np.eye(3), atol=1e-12, rtol=0)
    assert np.linalg.det(r) == pytest.approx(1.0, abs=1e-12)
    assert is_rotation_matrix(r)


@pytest.mark.parametrize("axis,point,expected", [
    ("x", [0, 1, 0], [0, 0, 1]),
    ("y", [0, 0, 1], [1, 0, 0]),
    ("z", [1, 0, 0], [0, 1, 0]),
])
def test_right_hand_known_quarter_turn(axis, point, expected):
    r = rotation_matrix(axis, 90, degrees=True)
    np.testing.assert_allclose(r @ point, expected, atol=1e-12, rtol=0)


@pytest.mark.parametrize("bad", [np.eye(2), np.ones((3, 3)), np.diag([1, 1, -1]),
    np.diag([1, 1, 2]), [[1, 0], [0]], np.full((3, 3), np.nan),
    np.full((3, 3), np.inf), np.eye(3).astype(complex), [["a"]], None])
def test_invalid_rotations_return_false(bad):
    assert not is_rotation_matrix(bad)
    with pytest.raises(ValueError):
        make_transform(bad, [0, 0, 0])


@pytest.mark.parametrize("atol", [0, -1, np.nan, np.inf, True, "small"])
def test_invalid_tolerance(atol):
    with pytest.raises(ValueError):
        is_rotation_matrix(np.eye(3), atol=atol)
    with pytest.raises(ValueError):
        invert_transform(np.eye(4), atol=atol)


def test_tolerance_is_absolute_and_configurable():
    r = np.diag([1 + 2e-7, 1, 1])
    assert not is_rotation_matrix(r)
    assert is_rotation_matrix(r, atol=1e-6)


@pytest.mark.parametrize("axis,angle,degrees", [("q", 0, False), (None, 0, False),
    ("x", np.nan, False), ("y", np.inf, False), ("z", 1j, False),
    ("x", "90", False), ("x", True, False), ("x", 1, "yes")])
def test_invalid_rotation_arguments(axis, angle, degrees):
    with pytest.raises(ValueError):
        rotation_matrix(axis, angle, degrees=degrees)


@pytest.mark.parametrize("translation", [[1, 2], [[1], [2], [3]], [0, np.nan, 0],
    [0, 0, np.inf], [1j, 0, 0], ["1", "2", "3"], None])
def test_invalid_translation(translation):
    with pytest.raises(ValueError):
        make_transform(np.eye(3), translation)


def test_known_transform_and_inverse():
    t = make_transform(rotation_matrix("z", np.pi / 2), [1, 2, 3])
    expected = [[0, -1, 0, 1], [1, 0, 0, 2], [0, 0, 1, 3], [0, 0, 0, 1]]
    expected_inverse = [[0, 1, 0, -2], [-1, 0, 0, 1], [0, 0, 1, -3], [0, 0, 0, 1]]
    np.testing.assert_allclose(t, expected, atol=1e-12, rtol=0)
    inv = invert_transform(t)
    np.testing.assert_allclose(inv, expected_inverse, atol=1e-12, rtol=0)
    np.testing.assert_allclose(t @ inv, np.eye(4), atol=1e-12, rtol=0)
    np.testing.assert_allclose(inv @ t, np.eye(4), atol=1e-12, rtol=0)


def test_noncommuting_composition_and_known_point():
    t_b_e = make_transform(rotation_matrix("z", 90, degrees=True), [1, 2, 0])
    t_e_c = make_transform(np.eye(3), [0.1, 0, 0.2])
    t_b_c = compose_transforms(t_b_e, t_e_c)
    p_c = np.array([1, 0, 0])
    np.testing.assert_allclose(transform_points(t_b_c, p_c), [1, 3.1, 0.2], atol=1e-12, rtol=0)
    np.testing.assert_allclose(transform_points(t_b_c, p_c),
        transform_points(t_b_e, transform_points(t_e_c, p_c)), atol=1e-12, rtol=0)
    assert not np.allclose(t_b_c, compose_transforms(t_e_c, t_b_e))


@pytest.mark.parametrize("seed", [0, 7, 20261118])
def test_random_inverse_composition_and_point_roundtrip(seed):
    rng = np.random.default_rng(seed)
    for _ in range(30):
        a, b, c = [make_transform(Rotation.random(random_state=rng).as_matrix(),
            rng.uniform(-2, 2, 3)) for _ in range(3)]
        inverse = invert_transform(a)
        np.testing.assert_allclose(inverse, np.linalg.inv(a), atol=1e-12, rtol=0)
        np.testing.assert_allclose(a @ inverse, np.eye(4), atol=1e-12, rtol=0)
        np.testing.assert_allclose(inverse @ a, np.eye(4), atol=1e-12, rtol=0)
        np.testing.assert_allclose(compose_transforms(a, b, c), a @ b @ c, atol=1e-12, rtol=0)
        pts = rng.uniform(-1, 1, (10, 3))
        explicit = (a @ np.column_stack([pts, np.ones(10)]).T).T[:, :3]
        np.testing.assert_allclose(transform_points(a, pts), explicit, atol=1e-12, rtol=0)
        np.testing.assert_allclose(transform_points(inverse, transform_points(a, pts)),
            pts, atol=1e-12, rtol=0)


def bad_transforms():
    bottom = np.eye(4)
    bottom[3, 0] = 0.1
    reflected = np.diag([-1, 1, 1, 1])
    return [np.eye(3), np.zeros((4, 4)), bottom, reflected, np.full((4, 4), np.nan)]


@pytest.mark.parametrize("bad", bad_transforms())
def test_all_transform_operations_reject_invalid_input(bad):
    for operation in [lambda: validate_transform(bad), lambda: invert_transform(bad),
        lambda: compose_transforms(np.eye(4), bad), lambda: compose_transforms(bad, np.eye(4)),
        lambda: transform_points(bad, [0, 0, 0])]:
        with pytest.raises(ValueError):
            operation()


@pytest.mark.parametrize("points", [[1, 2], [[1, 2]], np.ones((3, 1)),
    np.ones((2, 3, 1)), [1, 0, np.nan], [1, np.inf, 0], [1j, 0, 0], None])
def test_invalid_points(points):
    with pytest.raises(ValueError):
        transform_points(np.eye(4), points)


def test_empty_batch_identity_and_input_not_modified():
    rotation, translation = np.eye(3), np.array([1, 2, 3])
    t = make_transform(rotation, translation)
    rotation[0, 0] = 2
    translation[0] = 99
    assert t[0, 0] == 1 and t[0, 3] == 1
    original = t.copy()
    points = np.array([[0, 0, 0], [1, 0, 0]])
    points_before = points.copy()
    assert transform_points(t, np.empty((0, 3))).shape == (0, 3)
    transformed = transform_points(t, points)
    np.testing.assert_array_equal(transformed, [[1, 2, 3], [2, 2, 3]])
    compose_transforms(t, np.eye(4))
    invert_transform(t)
    validated = validate_transform(t)
    validated[0, 3] = 999
    np.testing.assert_array_equal(t, original)
    np.testing.assert_array_equal(points, points_before)


def test_documented_eye_in_hand_closure_and_relative_motion_direction():
    """只验证文档中的坐标恒等式，不实现或调用标定求解器。"""
    x = make_transform(rotation_matrix("x", 0.2), [0.05, 0.02, 0.1])
    y = make_transform(rotation_matrix("y", -0.1), [0.6, 0, 0.3])
    g_i = make_transform(rotation_matrix("z", 0.4), [0.2, -0.1, 0.3])
    g_j = make_transform(rotation_matrix("y", -0.5), [-0.1, 0.2, 0.5])
    q_i = invert_transform(x) @ invert_transform(g_i) @ y
    q_j = invert_transform(x) @ invert_transform(g_j) @ y
    np.testing.assert_allclose(g_i @ x @ q_i, y, atol=1e-12, rtol=0)
    np.testing.assert_allclose(g_j @ x @ q_j, y, atol=1e-12, rtol=0)
    a = invert_transform(g_j) @ g_i
    b = q_j @ invert_transform(q_i)
    np.testing.assert_allclose(a @ x, x @ b, atol=1e-12, rtol=0)
    # 单独颠倒相机运动次序应破坏本例，防止测试使用可交换的退化数据。
    wrong_b = invert_transform(q_i) @ q_j
    assert not np.allclose(a @ x, x @ wrong_b)
