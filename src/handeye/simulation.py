"""Eye-in-Hand 理想位姿观测仿真；无图像、视野或机器人运动学模型。"""

from dataclasses import dataclass
from numbers import Real, Integral

import numpy as np
from scipy.spatial.transform import Rotation

from .calibration import motion_diagnostics, pose_stack
from .transforms import invert_transform, make_transform, validate_transform


def nonnegative_integer(value, name):
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Integral) or value < 0:
        raise ValueError(f"{name} 必须为非负整数")
    return int(value)


def nonnegative_real(value, name):
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Real) or not np.isfinite(value) or value < 0:
        raise ValueError(f"{name} 必须为有限非负实数")
    return float(value)


@dataclass(frozen=True)
class SceneConfig:
    handeye_rotvec_rad: tuple = (0.2, -0.15, 0.3)
    handeye_translation_m: tuple = (0.05, 0.02, 0.10)
    target_rotvec_rad: tuple = (0.0, 0.0, 0.0)
    target_translation_m: tuple = (0.6, 0.0, 0.3)

    def truth(self):
        # 统一检查旋转向量、平移的形状及类型，避免 SciPy 隐式接受其它形状。
        for value in (self.handeye_rotvec_rad, self.target_rotvec_rad,
                      self.handeye_translation_m, self.target_translation_m):
            array = np.asarray(value)
            if array.shape != (3,) or array.dtype.kind not in "iuf" or not np.all(np.isfinite(array)):
                raise ValueError("场景参数须为有限实数三维向量")
        x = make_transform(Rotation.from_rotvec(self.handeye_rotvec_rad).as_matrix(), self.handeye_translation_m)
        y = make_transform(Rotation.from_rotvec(self.target_rotvec_rad).as_matrix(), self.target_translation_m)
        return x, y


@dataclass(frozen=True)
class SimulationData:
    t_b_g: np.ndarray
    t_c_t: np.ndarray
    t_g_c_true: np.ndarray
    t_b_t_true: np.ndarray
    seed: int


def generate_dataset(n_samples=20, *, seed=20261118, scene=None):
    """生成非退化 G_i 及 Q_i=inv(G_i X)Y；至少三帧，默认20帧。

    非退化按奇异值诊断；极少数不满足时明确失败，不暗中更换种子。
    随机流固定每帧抽取顺序，较短样本序列是同 seed 较长序列的前缀。
    """
    n_samples = nonnegative_integer(n_samples, "n_samples")
    seed = nonnegative_integer(seed, "seed")
    if n_samples < 3:
        raise ValueError("至少需要三组位姿")
    scene = SceneConfig() if scene is None else scene
    if not isinstance(scene, SceneConfig):
        raise ValueError("scene 必须为 SceneConfig")
    x, y = scene.truth()
    rng = np.random.default_rng(seed)
    gripper, observations = [], []
    for _ in range(n_samples):
        axis = rng.normal(size=3)
        axis /= np.linalg.norm(axis)
        angle = rng.uniform(0.25, 1.2)
        r = Rotation.from_rotvec(axis * angle).as_matrix()
        t = np.array([0.35, 0, 0.35]) + rng.uniform(-0.2, 0.2, 3)
        g = make_transform(r, t)
        gripper.append(g)
        observations.append(invert_transform(g @ x) @ y)
    gripper, observations = np.stack(gripper), np.stack(observations)
    if not motion_diagnostics(gripper)["nondegenerate"]:
        raise ValueError("当前随机场景运动激励不足；保留种子并检查配置")
    data = SimulationData(gripper, observations, x, y, seed)
    if closure_error(data) > 1e-12:
        raise ValueError("仿真几何闭环不一致")
    return data


def closure_error(data):
    """每帧 G X Q - Y 的最大绝对元素残差，仅用于理想数据几何核查。"""
    gripper, target = pose_stack(data.t_b_g), pose_stack(data.t_c_t)
    if len(gripper) != len(target):
        raise ValueError("仿真观测数量不匹配")
    x, y = validate_transform(data.t_g_c_true), validate_transform(data.t_b_t_true)
    return float(np.max(np.abs(gripper @ x @ target - y)))


def add_observation_noise(t_c_t, *, rotation_sigma_rad=0.0, translation_sigma_m=0.0, seed=0):
    """仅扰动相机观测。δθ~N(0,σr²I)，R'=Exp(δθ)R；t'=t+δt。

    左乘旋转噪声和独立相加的平移噪声均表达在相机 C 系。
    σr 是旋转向量每分量标准差，不是总转角标准差。
    全部水平共用标准正态样本再缩放，保证配对；不会扰动机器人位姿。
    """
    target = pose_stack(t_c_t)
    sr = nonnegative_real(rotation_sigma_rad, "rotation_sigma_rad")
    st = nonnegative_real(translation_sigma_m, "translation_sigma_m")
    seed = nonnegative_integer(seed, "seed")
    perturbations = np.random.default_rng(seed).normal(size=(len(target), 6))
    noisy = target.copy()
    delta_rotation = Rotation.from_rotvec(perturbations[:, :3] * sr).as_matrix()
    noisy[:, :3, :3] = delta_rotation @ target[:, :3, :3]
    noisy[:, :3, 3] += perturbations[:, 3:] * st
    return noisy
