"""独立留出评价。真值仅在本模块用于事后评价，不参与采样或求解。"""
import numpy as np
from scipy.spatial.transform import Rotation

from .calibration import pose_stack
from .transforms import validate_transform


def board_reference_points():
    """T 系虚拟板的四角和中心，单位米；不意味着相机可见。"""
    return np.array([[-.10, -.075, 0], [-.10, .075, 0], [.10, -.075, 0],
                     [.10, .075, 0], [0, 0, 0]])


def heldout_metrics(t_g_c, t_b_g, t_c_t, t_b_t, *, points=None):
    """用独立的理想 G/Q 评价 X_hat；返回米/弧度指标及逐帧点 RMSE。

    point_rmse_m 对所有留出帧和点的平方距离求均值再开方；
    同一估计下的帧和点不是独立统计重复。不修改任何输入。
    """
    x, y = validate_transform(t_g_c), validate_transform(t_b_t)
    g, q = pose_stack(t_b_g, minimum=1), pose_stack(t_c_t, minimum=1)
    if len(g) != len(q):
        raise ValueError('留出 G/Q 必须一一配对')
    p = np.asarray(board_reference_points() if points is None else points)
    if p.ndim != 2 or p.shape[1] != 3 or len(p) == 0 or p.dtype.kind not in 'iuf' or not np.all(np.isfinite(p)):
        raise ValueError('points 必须为非空有限实数 (K,3) 点集，单位米')
    p = p.astype(float)
    closure = g @ x @ q
    predicted = np.einsum('hij,kj->hki', closure[:, :3, :3], p) + closure[:, None, :3, 3]
    reference = p @ y[:3, :3].T + y[:3, 3]
    distances = np.linalg.norm(predicted-reference, axis=-1)
    angles = Rotation.from_matrix(closure[:, :3, :3] @ y[:3, :3].T).magnitude()
    translations = np.linalg.norm(closure[:, :3, 3]-y[:3, 3], axis=1)
    return {
        'point_rmse_m': float(np.sqrt(np.mean(distances**2))),
        'point_max_m': float(np.max(distances)),
        'frame_point_rmse_m': np.sqrt(np.mean(distances**2, axis=1)).tolist(),
        'closure_rotation_rmse_rad': float(np.sqrt(np.mean(angles**2))),
        'closure_translation_rmse_m': float(np.sqrt(np.mean(translations**2))),
    }
