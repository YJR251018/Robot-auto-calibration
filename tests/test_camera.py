"""W2 投影手算、OpenCV交叉参照、视野边界与估计信息接口。"""
from dataclasses import replace
import inspect

import cv2
import numpy as np
import pytest
from scipy.spatial.transform import Rotation

from handeye.camera import (Camera, board_grid, project_points, measure_visibility,
                            predict_visibility, estimate_target_in_base)
from handeye.transforms import make_transform, rotation_matrix
from handeye.simulation import generate_dataset


def test_known_projection_and_board():
    camera=Camera()
    points=np.array([[0.,0.,0.],[.1,.2,0.]])
    pixels,depths=project_points(points,make_transform(np.eye(3),[0,0,1]),camera)
    np.testing.assert_allclose(pixels,[[640,480],[730,660]])
    np.testing.assert_array_equal(depths,[1,1])
    grid=board_grid()
    assert grid.shape==(63,3)
    np.testing.assert_allclose(grid.min(axis=0),[-.1,-.075,0])
    np.testing.assert_allclose(grid.max(axis=0),[.1,.075,0])


def test_projectpoints_opencv_crosscheck():
    camera=Camera(); q=make_transform(Rotation.from_rotvec([.2,-.3,.1]).as_matrix(),[.1,-.05,.7])
    points=board_grid(); before=points.copy()
    actual,_=project_points(points,q,camera)
    expected,_=cv2.projectPoints(points,Rotation.from_matrix(q[:3,:3]).as_rotvec(),q[:3,3],camera.matrix(),None)
    np.testing.assert_allclose(actual,expected.reshape(-1,2),atol=1e-10,rtol=0)
    np.testing.assert_array_equal(points,before)


@pytest.mark.parametrize('depth',[-1.,0.,1e-7,1e-6])
def test_nonpositive_or_near_zero_depth(depth):
    q=make_transform(np.eye(3),[0,0,depth])
    assert measure_visibility(q,Camera()).reason=='depth'
    with pytest.raises(ValueError,match='深度'):
        project_points([[0.,0.,0.]],q,Camera())


def test_exact_image_and_margin_boundaries():
    camera=Camera(width=100,height=80,fx=1,fy=1,cx=0,cy=0,margin=5)
    def check(u,v):
        return measure_visibility(make_transform(np.eye(3),[u,v,1]),camera,points=[[0.,0.,0.]])
    assert check(5,5).visible and check(94,74).visible
    assert check(4.999,5).reason=='margin'
    assert check(99,79).reason=='margin'
    assert check(99.001,79).reason=='outside_image'
    assert check(-.001,5).reason=='outside_image'


@pytest.mark.parametrize('kwargs',[{'fx':0},{'fy':True},{'width':True},{'height':2.5},{'margin':-1},
                                  {'margin':480},{'depth_epsilon':0},{'cx':np.nan}])
def test_bad_camera(kwargs):
    with pytest.raises(ValueError):
        replace(Camera(),**kwargs).validate()


@pytest.mark.parametrize('points',[[],[[True,False,True]],[[1,2]],[[np.inf,0,1]]])
def test_bad_projection_points(points):
    with pytest.raises(ValueError):
        project_points(points,np.eye(4),Camera())


def test_prediction_uses_estimates_and_target_is_fit_from_training():
    data=generate_dataset(12,seed=42)
    estimate=estimate_target_in_base(data.t_b_g,data.t_c_t,data.t_g_c_true)
    np.testing.assert_allclose(estimate,data.t_b_t_true,atol=1e-14)
    camera=Camera(); x=np.eye(4); g=np.eye(4); y=make_transform(np.eye(3),[0,0,1])
    assert predict_visibility(g,x,y,camera).visible
    moved=y.copy(); moved[0,3]=10
    assert not predict_visibility(g,x,moved,camera).visible
    assert set(inspect.signature(predict_visibility).parameters)=={'t_b_g','t_g_c_est','t_b_t_est','camera','points'}
    with pytest.raises(ValueError):
        estimate_target_in_base(data.t_b_g[:3],data.t_c_t[:4],data.t_g_c_true)
