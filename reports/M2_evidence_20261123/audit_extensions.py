"""四个独立协议结果的分层摘要；不合并为120个独立重复。"""
from pathlib import Path
import csv
import json
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'reports/M2_evidence_20261123'
results={}
for name in ('sampling','robot_noise','scene2','pool120'):
    folder=ROOT/f'experiments/M2_{name}_20261123'
    status=json.loads((folder/'run_status.json').read_text(encoding='utf-8'))
    assert status['status']=='complete' and status['completed']==2160
    verification=OUT/('formal_verification.json' if name=='sampling' else name+'_verification.json')
    assert json.loads(verification.read_text(encoding='utf-8'))['verification']['result']=='PASS'
    paired=json.loads((folder/'paired.json').read_text(encoding='utf-8'))
    summary=json.loads((folder/'summary.json').read_text(encoding='utf-8'))
    config=json.loads((folder/'config.json').read_text(encoding='utf-8'))
    means={s['strategy']:s['point_rmse_mm_mean'] for s in summary if s['condition']=='mixed' and s['method']=='PARK' and s['n_samples']==20}
    selection=json.loads((folder/'selections.json').read_text(encoding='utf-8'))
    results[name]={'status':status,'means_mm':means,'mean_delta_mm':paired['mean_delta_mm'],
                   'ci95_mm':paired['ci95_mm'],'farthest_worse_repeats':sum(p['delta_mm']>0 for p in paired['pairs']),
                   'mixed_noise':next(c for c in config['conditions'] if c['name']=='mixed'),
                   'median_farthest_selection_seconds':float(np.median([r['rotation_farthest']['seconds'] for r in selection.values()]))}
for repeat in range(30):
    with np.load(ROOT/f'experiments/M2_sampling_20261123/raw/repeat_{repeat:03d}.npz',allow_pickle=False) as a, np.load(ROOT/f'experiments/M2_pool120_20261123/raw/repeat_{repeat:03d}.npz',allow_pickle=False) as b:
        for key in ('candidate_g','candidate_q','camera_standard_noise','robot_standard_noise','candidate_ids'):
            np.testing.assert_array_equal(a[key],b[key][:60])
        for key in ('holdout_g','holdout_q','x_true','y_true','points'):
            np.testing.assert_array_equal(a[key],b[key])
def rows(name):
    with (ROOT/f'experiments/M2_{name}_20261123/trials.csv').open(encoding='utf-8',newline='') as f:
        return {r['trial_id']:r for r in csv.DictReader(f) if r['strategy']=='ordered'}
first,second=rows('sampling'),rows('pool120')
assert set(first)==set(second)
for tid,row in first.items():
    for metric in ('rotation_error_deg','translation_error_mm','point_rmse_mm'):
        assert row[metric]==second[tid][metric]
audit={'result':'PASS','results':results,'prefix_checked_repeats':30,'identical_ordered_trials':len(first),
       'total_formal_trials':sum(r['status']['completed'] for r in results.values()),
       'total_formal_failures':sum(r['status']['failed'] for r in results.values()),
       'note':'Separate settings with paired seed IDs; do not pool repeats or count replays as new data'}
(OUT/'extensions_audit.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
lines=['# M2 余量任务 H1—H3 验收报告','',
       '日期：2026-11-23。三项扩展在 A—G 验收后按顺序运行，配置提前冻结于 M2_evidence_20261123/extensions_freeze.json；未改动主实验。','',
       'H1：相机噪声为零，机器人测量旋转每分量0.1°、平移每分量0.2mm，分旋转/平移/混合条件。真实G生成Q后独立扰动测量G。',
       'H2：额外安装X与板位姿Y场景，具体参数见 configs/m2_scene2_v0_1.json；它是场景整体改变，不能归因于某一个单参数。',
       'H3：候选从60扩到120，共享前60帧和噪声前缀，初始与N不变。30个重复逐数组核对通过，ordered的720个试次误差逐字段完全一致。','',
       '| 设置 | 成功/计划 | ordered RMSE mm | random RMSE mm | farthest RMSE mm | 配对均值差mm | 95%配对bootstrap区间mm | farthest更差重复数 |',
       '| --- | --- | --- | --- | --- | --- | --- | --- |']
for name,r in results.items():
    m=r['means_mm']; ci=r['ci95_mm']; status=r['status']
    lines.append(f"| {name} | {status['succeeded']}/{status['planned']} | {m['ordered']:.6f} | {m['random']:.6f} | {m['rotation_farthest']:.6f} | {r['mean_delta_mm']:.6f} | [{ci[0]:.6f}, {ci[1]:.6f}] | {r['farthest_worse_repeats']}/30 |")
lines += ['', '表中为各设置的 mixed / PARK / N20，留出为理想观测。robot_noise 的 mixed 是机器人侧混合噪声，其余为相机侧；数值不宜当作同一噪声强度直接排名。', '',
          '主实验与三个扩展合计8640次正式求解，全部保存并实际重放。开发小实验另有2×144次及其重放，不能合并增加独立样本数。每个设置各30个重复，设置间共用种子形成配对，不能把四组拼成120个独立同分布重复。','',
          '三个扩展全部0失败；负结果保留为每组farthest更差的重复数。平均趋势只对这些预设仿真设置成立，不证明全局优势、实机精度或创新。','',
          '7项扩展单元测试通过；最终包含W2的全量测试另见最终交付记录。核心求解和选择源码未因扩展而修改。','',
          '实际命令及退出码：M2_evidence_20261123/extension_commands.json；每项完整日志与verification.json、extensions_audit.json同目录。每项独立实验目录中保存配置、原始NPZ、估计、CSV/JSON、PNG/PDF和哈希。','',
          '选择开销只是本机描述性计时；更大候选池的中位数见extensions_audit.json，不推断机器人采集用时。没有必要增加缓存重构，现有距离表已避免评分循环重复SVD。']
(ROOT/'reports/M2_extensions_20261123.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in audit.items() if k!='results'},indent=2))
print(json.dumps({name:{k:v for k,v in r.items() if k not in ('status','mixed_noise')} for name,r in results.items()},indent=2))
