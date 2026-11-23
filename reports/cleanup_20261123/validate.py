"""本轮整理核验；只输出位置与类别，不打印疑似隐私内容。"""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'reports/cleanup_20261123'
before=json.loads((OUT/'before_manifest.json').read_text(encoding='utf-8'))
def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()
moves={'INITIALIZATION.md':'docs/history/INITIALIZATION.md','CONTINUE WORK.md':'plans/archive/M1_TASK_20261118.md'}
allowed={'README.md','AGENTS.md','.gitignore','docs/README.md','src/README.md'}
changes=[]
for name,h in before.items():
    p=ROOT/name
    if name in moves:
        assert not p.exists() and digest(ROOT/moves[name])==h,name
    else:
        assert p.exists(),name
        if digest(p)!=h:
            changes.append(name)
            assert name in allowed,name
assert set(changes)==allowed,changes
for name in ('README.md','AGENTS.md'):
    assert digest(ROOT/f'docs/history/{name[:-3]}_before_cleanup_20261123.md')==before[name]

experiments=[]
for folder in sorted((ROOT/'experiments').iterdir()):
    if not folder.is_dir() or not (folder/'artifact_hashes.json').exists(): continue
    manifest=json.loads((folder/'artifact_hashes.json').read_text(encoding='utf-8'))
    for name,h in manifest.items():
        p=(folder/name).resolve()
        assert p.is_relative_to(folder.resolve()),str(p)
        assert digest(p)==h,f'{folder.name}/{name}'
    status=json.loads((folder/'run_status.json').read_text(encoding='utf-8'))
    assert status['status']=='complete',folder
    experiments.append({'run':folder.name,'hashed_files':len(manifest)})

counts={k:sum(int(s.get(k,0)) for s in ET.parse(OUT/'pytest.xml').getroot().iter('testsuite')) for k in ('tests','failures','errors','skipped')}
assert counts=={'tests':226,'failures':0,'errors':0,'skipped':0}
pip=subprocess.run([str(ROOT/'.venv/Scripts/python.exe'),'-m','pip','check'],cwd=ROOT,capture_output=True)
assert pip.returncode==0
(OUT/'pip_check.txt').write_bytes(pip.stdout+pip.stderr)

paths=subprocess.run(['git','ls-files','--cached','--others','--exclude-standard','-z'],cwd=ROOT,capture_output=True,check=True).stdout.decode('utf-8').split('\0')
paths=sorted({p for p in paths if p and (ROOT/p).is_file()})
private=[p for p in paths if p.startswith(('文献/','.venv/','.pytest_cache/')) or p.endswith('.docx') or p=='reports/proposal_text_local.txt']
assert not private,private
credential=re.compile(r'gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{30,}|sk-[A-Za-z0-9_-]{24,}|AKIA[0-9A-Z]{16}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----')
phone=re.compile(r'(?<![\dA-Za-z.])1[3-9]\d{9}(?![\dA-Za-z.])')
labels=re.compile(r'(?:联系电话|手机号码|身份证号|学号|电子邮箱|家庭住址)\s*[:：]')
findings=[]
for name in paths:
    p=ROOT/name
    if p.suffix.lower() not in {'.py','.md','.txt','.json','.csv','.xml','.yml','.yaml','.patch'}: continue
    try: content=p.read_text(encoding='utf-8-sig')
    except UnicodeError: continue
    if credential.search(content): findings.append({'path':name,'category':'credential'})
    # 手机/隐私字段仅检查文字说明；浮点CSV、哈希、DOI数字不当作身份证或手机号。
    if p.suffix.lower() in {'.md','.txt'}:
        if phone.search(content): findings.append({'path':name,'category':'phone_review'})
        if labels.search(content): findings.append({'path':name,'category':'pii_label_review'})
assert not findings,findings

link_errors=[]; checked_links=0
for name in ('README.md','docs/README.md','experiments/README.md','reports/README.md','plans/README.md'):
    p=ROOT/name
    for target in re.findall(r'\]\(([^)]+)\)',p.read_text(encoding='utf-8')):
        if target.startswith(('http://','https://','#')):continue
        if not (p.parent/target.split('#')[0]).exists():link_errors.append([name,target])
        checked_links+=1
assert not link_errors,link_errors
result={'result':'PASS','existing_files_checked':len(before),'changed_existing':changes,'moves_content_preserved':moves,
        'no_existing_scientific_data_or_source_changes':True,'experiment_hashes':experiments,'pytest':counts,
        'publish_candidate_files':len(paths),'secret_or_pii_findings':findings,'navigation_links_checked':checked_links,
        'note':'Original proposal/PDFs/private extracted text and environment excluded; historical manifests retained as old snapshots'}
(OUT/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
