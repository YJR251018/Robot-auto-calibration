"""H扩展：机器人测量噪声不重生成相机观测；更大池保留数据前缀。"""
import numpy as np
import pytest

from handeye.m2_experiments import M2Config, Noise, perturb_poses, prepare_repeat, trial_inputs
from handeye.simulation import generate_dataset
from handeye.transforms import make_transform, rotation_matrix


def test_robot_noise_zero_and_independent_geometry():
    raw,selections=prepare_repeat(M2Config(repeats=2,candidate_count=20,holdout_count=5),0)
    selected=selections['ordered']; trial={'n_samples':8}
    g,q,ids=trial_inputs(raw,selected,trial,Noise('baseline'))
    np.testing.assert_array_equal(g,raw['candidate_g'][ids])
    np.testing.assert_array_equal(q,raw['candidate_q'][ids])
    noisy_g,same_q,_=trial_inputs(raw,selected,trial,Noise('robot',robot_rotation_deg=.1,robot_translation_mm=.2))
    np.testing.assert_array_equal(same_q,q)
    assert not np.array_equal(noisy_g,g)
    assert np.max(np.abs(noisy_g@raw['x_true']@same_q-raw['y_true']))>1e-6


def test_left_rotation_and_independent_translation_known_case():
    pose=make_transform(rotation_matrix('x',.3),[1,2,3])[None]
    z=np.array([[0.,0.,1.,3.,4.,0.]])
    out=perturb_poses(pose,z,rotation_rad=np.pi/2,translation_m=.001)
    rz=np.array([[0,-1,0],[1,0,0],[0,0,1]])
    np.testing.assert_allclose(out[0,:3,:3],rz@pose[0,:3,:3],atol=1e-15)
    np.testing.assert_allclose(out[0,:3,3],[1.003,2.004,3],atol=1e-15)
    np.testing.assert_array_equal(pose[0,:3,3],[1,2,3])


def test_60_and_120_candidate_and_noise_prefix():
    a,b=generate_dataset(60,seed=310000),generate_dataset(120,seed=310000)
    np.testing.assert_array_equal(a.t_b_g,b.t_b_g[:60])
    np.testing.assert_array_equal(a.t_c_t,b.t_c_t[:60])
    np.testing.assert_array_equal(np.random.default_rng(330000).normal(size=(60,6)),
                                  np.random.default_rng(330000).normal(size=(120,6))[:60])


@pytest.mark.parametrize('z,sr,st',[(np.zeros((1,5)),0,0),(np.full((1,6),np.nan),0,0),
                                  (np.zeros((1,6)),-1,0),(np.zeros((1,6)),True,0)])
def test_invalid_pose_noise(z,sr,st):
    with pytest.raises(ValueError):
        perturb_poses(np.eye(4)[None],z,rotation_rad=sr,translation_m=st)
