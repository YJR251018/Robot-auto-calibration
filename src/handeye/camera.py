"""零畸变针孔投影与可见性；米→pixel，光学系 x右/y下/z前。"""
from dataclasses import dataclass
from numbers import Integral, Real

import numpy as np

from .calibration import pose_stack
from .transforms import invert_transform, make_transform, validate_transform


def _finite_real(value, name, *, positive=False):
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Real) or not np.isfinite(value):
        raise ValueError(f'{name} 必须为有限实数')
    if positive and value <= 0:
        raise ValueError(f'{name} 必须为正数')
    return float(value)


@dataclass(frozen=True)
class Camera:
    width: int = 1280
    height: int = 960
    fx: float = 900.0
    fy: float = 900.0
    cx: float = 640.0
    cy: float = 480.0
    margin: float = 16.0
    depth_epsilon: float = 1e-6

    def validate(self):
        for name in ('width', 'height'):
            value = getattr(self, name)
            if isinstance(value, (bool, np.bool_)) or not isinstance(value, Integral) or value < 2:
                raise ValueError(f'{name} 必须为至少2的整数')
        for name in ('fx', 'fy', 'depth_epsilon'):
            _finite_real(getattr(self, name), name, positive=True)
        for name in ('cx', 'cy', 'margin'):
            _finite_real(getattr(self, name), name)
        if not 0 <= self.margin < min(self.width-1, self.height-1)/2:
            raise ValueError('margin 必须非负且保留非空画面')

    def matrix(self):
        self.validate()
        return np.array([[self.fx, 0., self.cx], [0., self.fy, self.cy], [0., 0., 1.]])


def board_grid():
    """T系 9×7 点，行优先，间距0.025m；几何矩形无厚度/遮挡。"""
    x, y = np.meshgrid(np.arange(-4, 5)*.025, np.arange(-3, 4)*.025)
    return np.column_stack((x.ravel(), y.ravel(), np.zeros(x.size)))


def _camera_points(points, t_c_t, camera):
    if not isinstance(camera, Camera):
        raise ValueError('camera 必须是 Camera')
    camera.validate()
    q = validate_transform(t_c_t)
    p = np.asarray(points)
    if p.ndim != 2 or p.shape[1] != 3 or not len(p) or p.dtype.kind not in 'iuf' or not np.all(np.isfinite(p)):
        raise ValueError('points 须为非空有限实数 (K,3)，单位米')
    with np.errstate(over='ignore', invalid='ignore'):
        result = p.astype(float) @ q[:3, :3].T + q[:3, 3]
    if not np.all(np.isfinite(result)):
        raise ValueError('变换后点坐标非有限')
    return result


def _pixels(p, camera):
    with np.errstate(over='ignore', invalid='ignore'):
        pixels = p[:, :2]/p[:, 2, None]*[camera.fx, camera.fy] + [camera.cx, camera.cy]
    if not np.all(np.isfinite(pixels)):
        raise ValueError('投影像素非有限')
    return pixels


def project_points(points, t_c_t, camera):
    """T系点经 T_C_T 投影；所有深度须 >depth_epsilon，否则显式拒收。"""
    p = _camera_points(points, t_c_t, camera)
    if np.any(p[:, 2] <= camera.depth_epsilon):
        raise ValueError('点深度必须大于 depth_epsilon')
    return _pixels(p, camera), p[:, 2].copy()


@dataclass(frozen=True)
class Visibility:
    visible: bool
    reason: str
    pixels: np.ndarray | None
    depths_m: np.ndarray


def measure_visibility(t_c_t, camera, *, points=None):
    """测量端使用实际Q；先深度、再画面、再余量，边界包含像素中心。"""
    p = _camera_points(board_grid() if points is None else points, t_c_t, camera)
    depths = p[:, 2].copy()
    if np.any(depths <= camera.depth_epsilon):
        return Visibility(False, 'depth', None, depths)
    pixels = _pixels(p, camera)
    upper = np.array([camera.width-1, camera.height-1])
    if np.any(pixels < 0) or np.any(pixels > upper):
        return Visibility(False, 'outside_image', pixels, depths)
    if np.any(pixels < camera.margin) or np.any(pixels > upper-camera.margin):
        return Visibility(False, 'margin', pixels, depths)
    return Visibility(True, 'visible', pixels, depths)


def predict_visibility(t_b_g, t_g_c_est, t_b_t_est, camera, *, points=None):
    """规划端只使用候选G与已有估计；不接收真实Q或真值容器。"""
    g, x, y = (validate_transform(t) for t in (t_b_g, t_g_c_est, t_b_t_est))
    predicted_q = invert_transform(g @ x) @ y
    return measure_visibility(predicted_q, camera, points=points)


def estimate_target_in_base(t_b_g, t_c_t, t_g_c_est):
    """由已采训练观测的 G X_hat Q 均值估计Y；平移均值+旋转SVD投影。

    仅对训练观测调用，不接收固定板真值。旋转均值不唯一/病态时拒绝。
    """
    g, q = pose_stack(t_b_g), pose_stack(t_c_t)
    if len(g) != len(q):
        raise ValueError('训练G/Q数量必须相等')
    x = validate_transform(t_g_c_est)
    poses = g @ x @ q
    u, s, vt = np.linalg.svd(poses[:, :3, :3].mean(axis=0))
    if s[-1] <= 1e-12 or np.linalg.det(u @ vt) <= 0:
        raise ValueError('训练观测的旋转均值病态或不唯一')
    return make_transform(u @ vt, poses[:, :3, 3].mean(axis=0))
