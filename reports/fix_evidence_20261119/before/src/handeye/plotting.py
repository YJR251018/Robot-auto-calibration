"""只从实际 summary.csv 生成英文 Matplotlib 科研图；无 GUI。"""

import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def plot_results(summary_csv, output_dir):
    with Path(summary_csv).open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    output = Path(output_dir)
    methods = sorted({r["method"] for r in rows})
    specs = [("rotation_noise", "rotation_sigma_deg", "Rotation noise sigma (deg/component)"),
             ("translation_noise", "translation_sigma_mm", "Translation noise sigma (mm/component)"),
             ("sample_count", "n_samples", "Number of pose pairs")]
    paths = []
    for experiment, xkey, xlabel in specs:
        fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), constrained_layout=True)
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
        plt.close(fig)
        paths.append(path)
    return paths


def rows_for(rows, experiment, key):
    return next(r[key] for r in rows if r["experiment"] == experiment)
