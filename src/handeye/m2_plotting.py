"""读取已保存统计绘图；只呈现实际结果，无 GUI。"""
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

COLORS = {'ordered':'#737373', 'random':'#0072B2', 'rotation_farthest':'#D55E00'}


def plot_m2(folder):
    folder = Path(folder)
    summary = json.loads((folder/'summary.json').read_text(encoding='utf-8'))
    paired = json.loads((folder/'paired.json').read_text(encoding='utf-8'))
    # 三种单图对应：误差、配对收益、失败分母；不强制虚构缺失的主比较。
    selected = [r for r in summary if r['method']=='PARK' and r['condition']=='mixed']
    if not selected:
        selected = [r for r in summary if r['method']=='PARK' and r['condition']!='baseline']
        selected = [r for r in selected if r['condition']==selected[0]['condition']] if selected else []
    label = selected[0]['condition'] if selected else 'comparison unavailable'
    with plt.rc_context({'font.size':10, 'axes.spines.top':False, 'axes.spines.right':False,
                         'pdf.fonttype':42, 'savefig.dpi':180}):
        for kind in ('error_vs_samples', 'paired_difference', 'failure_rate'):
            fig, ax = plt.subplots(figsize=(7.2, 4.8), layout='constrained')
            try:
                if kind=='error_vs_samples':
                    for strategy, color in COLORS.items():
                        group = sorted([r for r in selected if r['strategy']==strategy], key=lambda r:r['n_samples'])
                        ok = [r for r in group if r['point_rmse_mm_mean'] is not None]
                        if ok:
                            means = [r['point_rmse_mm_mean'] for r in ok]
                            sd = [r['point_rmse_mm_std'] if r['point_rmse_mm_std'] is not None else np.nan for r in ok]
                            ax.errorbar([r['n_samples'] for r in ok], means, yerr=sd, marker='o', capsize=4,
                                        label=strategy, color=color)
                    ax.set(xlabel='Selected poses (including initialization)', ylabel='Held-out point RMSE (mm)',
                           title=f'PARK / {label}: mean ± sample SD')
                    if ax.get_legend_handles_labels()[0]:
                        ax.legend(frameon=False)
                    else:
                        ax.text(.5, .5, 'No successful comparison', ha='center', transform=ax.transAxes)
                elif kind=='paired_difference':
                    pairs = paired['pairs']
                    if pairs:
                        ax.scatter([r['repeat'] for r in pairs], [r['delta_mm'] for r in pairs], color='#0072B2')
                        ax.axhline(0, color='black', lw=1, ls='--')
                        ci = paired['ci95_mm']
                        interval = 'CI unavailable' if ci is None else f'95% paired bootstrap CI [{ci[0]:.3f}, {ci[1]:.3f}] mm'
                        ax.set_title(f"PARK / mixed / N=20; paired n={len(pairs)}\n{interval}")
                    else:
                        ax.text(.5, .5, 'Primary paired comparison unavailable', ha='center', transform=ax.transAxes)
                    ax.set(xlabel='Independent repeat ID', ylabel='Farthest − random: point RMSE (mm)')
                else:
                    group = sorted(selected, key=lambda r:(r['strategy'], r['n_samples']))
                    x = np.arange(len(group))
                    ax.bar(x, [r['failure_rate'] for r in group], color=[COLORS[r['strategy']] for r in group])
                    for i, row in enumerate(group):
                        ax.text(i, row['failure_rate']+.025, f"{row['failed']}/{row['total']}", ha='center', fontsize=8)
                    ax.set_xticks(x, [f"{r['strategy']}\nN={r['n_samples']}" for r in group], rotation=30, ha='right')
                    ax.set(ylabel='Failed / attempted', ylim=(0, 1.15), title=f'PARK / {label}: failures retained')
                ax.grid(axis='y', alpha=.2)
                fig.savefig(folder/f'{kind}.png')
                fig.savefig(folder/f'{kind}.pdf')
            finally:
                plt.close(fig)
