r"""运行：.\.venv\Scripts\python.exe examples\basic_transforms.py。"""

from pathlib import Path
import sys

import numpy as np

# 尚未打包安装；仅将本项目 src 加到当前进程的导入路径。
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from handeye import (  # noqa: E402
    compose_transforms, invert_transform, make_transform,
    rotation_matrix, transform_points,
)


def main():
    # B：基座，E：末端，C：相机；所有长度用米。
    t_b_e = make_transform(rotation_matrix("z", 90, degrees=True), [1, 2, 0])
    t_e_c = make_transform(np.eye(3), [0.1, 0, 0.2])
    t_b_c = compose_transforms(t_b_e, t_e_c)
    point_c = np.array([1.0, 0.0, 0.0])
    point_b = transform_points(t_b_c, point_c)
    recovered_c = transform_points(invert_transform(t_b_c), point_b)
    expected_b = np.array([1.0, 3.1, 0.2])
    np.testing.assert_allclose(point_b, expected_b, atol=1e-12, rtol=0)
    np.testing.assert_allclose(recovered_c, point_c, atol=1e-12, rtol=0)
    np.set_printoptions(precision=6, suppress=True)
    print("T_B_C (C -> B; translation in metres):\n", t_b_c)
    print("point_C:", point_c)
    print("point_B:", point_b)
    print("recovered_C:", recovered_c)
    print("Known-value and round-trip checks: PASS")


if __name__ == "__main__":
    main()
