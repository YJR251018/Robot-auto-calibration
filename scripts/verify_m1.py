"""核验两次独立运行的原始数据、CSV、完整性及成功结果复算。"""

import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from handeye.calibration import calibrate_hand_eye  # noqa: E402
from handeye.metrics import pose_error  # noqa: E402


def verify(first, second):
    first, second = Path(first), Path(second)
    for folder in (first, second):
        status = json.loads((folder/"run_status.json").read_text(encoding="utf-8"))
        if status["status"] != "complete" or not status["baseline_passed"]:
            raise ValueError("只复核完整且通过无噪声关卡的实验")
        manifest = json.loads((folder/"artifact_hashes.json").read_text(encoding="utf-8"))
        for name, digest in manifest.items():
            if hashlib.sha256((folder/name).read_bytes()).hexdigest() != digest:
                raise ValueError(f"实验文件哈希不匹配: {folder/name}")
    compared = ["trials.csv", "summary.csv", "config.json", "summary.json", "baseline_gate.json"]
    for name in compared:
        if (first/name).read_bytes() != (second/name).read_bytes():
            raise ValueError(f"独立重跑结果不一致: {name}")
    with (first/"trials.csv").open(encoding="utf-8", newline="") as handle:
        records = list(csv.DictReader(handle))
    paths = sorted({r["data_file"] for r in records if r["data_file"]})
    for name in paths:
        with np.load(first/name, allow_pickle=False) as a, np.load(second/name, allow_pickle=False) as b:
            if set(a.files) != set(b.files):
                raise ValueError(f"原始数据字段不一致: {name}")
            for key in a.files:
                np.testing.assert_array_equal(a[key], b[key], err_msg=f"{name}:{key}")
    # 直接从保存的观测再次调用 OpenCV，真值只传给误差函数。
    replayed = 0
    for row in records:
        if row["status"] != "ok":
            continue
        with np.load(first/row["data_file"], allow_pickle=False) as data:
            estimate = calibrate_hand_eye(data["t_b_g"], data["t_c_t"], method=row["method"])
            error = pose_error(estimate, data["t_g_c_true"])
        np.testing.assert_allclose([error.rotation_deg, error.translation_mm],
                                   [float(row["rotation_error_deg"]), float(row["translation_error_mm"])],
                                   atol=1e-12, rtol=0)
        replayed += 1
    with (first/"summary.csv").open(encoding="utf-8", newline="") as handle:
        summaries = list(csv.DictReader(handle))
    for summary in summaries:
        selected = [row for row in records if all(row[k] == summary[k] for k in ("experiment", "condition", "method"))]
        success = [row for row in selected if row["status"] == "ok"]
        assert int(summary["total"]) == len(selected)
        assert int(summary["failed"]) == len(selected)-len(success)
        for metric in ("rotation_error_deg", "translation_error_mm"):
            values = np.array([float(row[metric]) for row in success])
            if len(values):
                np.testing.assert_allclose(float(summary[metric+"_mean"]), values.mean(), atol=1e-14, rtol=0)
            if len(values) > 1:
                np.testing.assert_allclose(float(summary[metric+"_std"]), values.std(ddof=1), atol=1e-14, rtol=0)
    return {"result": "PASS", "identical_tables": compared, "identical_raw_datasets": len(paths),
            "replayed_successful_solves": replayed, "audited_summary_rows": len(summaries),
            "note": "重跑与重放用于复算验证，未增加独立统计样本数"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--first", type=Path, required=True)
    parser.add_argument("--second", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    if not args.report.resolve().is_relative_to(ROOT):
        parser.error("报告仅可写入项目内")
    result = verify(args.first, args.second)
    with args.report.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
