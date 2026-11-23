"""只从实际 summary.csv 生成英文 Matplotlib 科研图；无 GUI。"""

import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def plot_results(summary_csv, output_dir):
    with Path(summary_csv).open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        columns = set(reader.fieldnames or [])
    output = Path(output_dir)
    methods = sorted({r["method"] for r in rows})
    specs = [("rotation_noise", "rotation_sigma_deg", "Rotation noise sigma (deg/component)"),
             ("translation_noise", "translation_sigma_mm", "Translation noise sigma (mm/component)"),
             ("sample_count", "n_samples", "Number of pose pairs")]
    required = {"experiment", "method", "n_samples", "rotation_sigma_deg", "translation_sigma_mm",
                "failed", "total", "rotation_error_deg_mean", "rotation_error_deg_std",
                "translation_error_mm_mean", "translation_error_mm_std"}
    missing_columns = required - columns
    if missing_columns:
        raise ValueError(f"summary.csv 缺少必需列: {', '.join(sorted(missing_columns))}")
    missing_experiments = {spec[0] for spec in specs} - {r["experiment"] for r in rows}
    if missing_experiments:
        raise ValueError(f"summary.csv 缺少实验类型: {', '.join(sorted(missing_experiments))}")
    paths = []
    for experiment, xkey, xlabel in specs:
        fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), constrained_layout=True)
        try:
            for method in methods:
                selected = sorted([r for r in rows if r["experiment"] == experiment and r["method"] == method],
                                  key=lambda r: float(r[xkey]))
                if not selected:
                    continue
                x = [float(r[xkey]) for r in selected]
                failures = sum(int(r["failed"]) for r in selected)
                total = sum(int(r["total"]) for r in selected)
                label = f"{method} (failures {failures}/{total})"
                for ax, metric, ylabel in zip(axes, ("rotation_error_deg", "translation_error_mm"),
                                             ("Rotation error (deg)", "Translation error (mm)")):
                    mean = [float(r[metric+"_mean"]) if r[metric+"_mean"] else np.nan for r in selected]
                    std = [float(r[metric+"_std"]) if r[metric+"_std"] else 0 for r in selected]
                    ax.errorbar(x, mean, yerr=std, marker="o", capsize=3, linewidth=1.5, label=label)
                    ax.set(xlabel=xlabel, ylabel=ylabel)
                    ax.grid(alpha=0.25)
                    ax.legend(fontsize=8)
            if experiment == "sample_count":
                subtitle = f"rotation sigma={rows_for(rows,experiment,'rotation_sigma_deg')} deg, translation sigma={rows_for(rows,experiment,'translation_sigma_mm')} mm"
            else:
                subtitle = f"N={rows_for(rows,experiment,'n_samples')}; other noise component = 0"
            fig.suptitle(f"{experiment.replace('_', ' ').title()} | {subtitle}\nMean +/- 1 sample SD; ideal pose observations", fontsize=11)
            path = output / f"{experiment}.png"
            fig.savefig(path, dpi=180)
            paths.append(path)
        finally:
            plt.close(fig)
    return paths


def rows_for(rows, experiment, key):
    for row in rows:
        if row["experiment"] == experiment:
            return row[key]
    raise ValueError(f"实验类型 '{experiment}' 在 summary.csv 中不存在")
