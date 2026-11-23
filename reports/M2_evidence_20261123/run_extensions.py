"""本轮证据用顺序执行器；每个扩展运行、核验通过后才进入下一个。"""
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
EVIDENCE=ROOT/'reports/M2_evidence_20261123'
progress=ROOT/'plans/progress.json'
commands=[]
for index,name in enumerate(('robot_noise','scene2','pool120'),start=1):
    state=json.loads(progress.read_text(encoding='utf-8'))
    state.update(current_task=f'M2_H{index}',next_action=f'Run and verify {name}',current_run_directory=f'experiments/M2_{name}_20261123')
    state['extension_tasks'][index-1]['status']='in_progress'
    progress.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')
    start=time.perf_counter()
    for phase,args in (
        ('run',['scripts/run_m2.py','--config',f'configs/m2_{name}_v0_1.json','--output',f'experiments/M2_{name}_20261123']),
        ('verify',['scripts/verify_m2.py','--run',f'experiments/M2_{name}_20261123','--report',f'reports/M2_evidence_20261123/{name}_verification.json'])):
        command=[sys.executable,'-W','error',*args]
        with (EVIDENCE/f'{name}_{phase}.txt').open('x',encoding='utf-8') as log:
            result=subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        commands.append({'command':command,'exit_code':result.returncode})
        (EVIDENCE/'extension_commands.json').write_text(json.dumps(commands,indent=2),encoding='utf-8')
        if result.returncode:
            raise RuntimeError(f'{name} {phase} failed; inspect saved log before continuing')
    state=json.loads(progress.read_text(encoding='utf-8'))
    state['extension_tasks'][index-1].update(status='done',evidence=f'reports/M2_evidence_20261123/{name}_verification.json')
    state.update(last_completed_checkpoint=f'H{index} {name}: 2160 trials and full replay passed',next_action='Next H extension or W2 after H3')
    progress.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'completed':name,'elapsed_seconds':time.perf_counter()-start}),flush=True)
