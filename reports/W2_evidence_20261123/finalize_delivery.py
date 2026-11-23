"""最终文件保护、冻结代码一致性、差异和文档链接核验；不修改实验。"""
import difflib
import hashlib
import json
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT/'reports/M2_evidence_20261123'
OUT = ROOT/'reports/W2_evidence_20261123'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


before = json.loads((EVIDENCE/'before_manifest.json').read_text(encoding='utf-8'))
changed = [name for name, value in before.items() if (ROOT/name).is_file() and digest(ROOT/name)!=value]
missing = [name for name in before if not (ROOT/name).exists()]
assert not missing, missing
assert set(changed)=={'README.md', 'AGENTS.md', 'plans/progress.json'}, changed
continuation = json.loads((OUT/'continuation_manifest.json').read_text(encoding='utf-8'))
continuation_changed = [name for name,value in continuation.items() if digest(ROOT/name)!=value]
assert set(continuation_changed) <= {'README.md','AGENTS.md','plans/progress.json','docs/PROJECT_SPEC.md'}, continuation_changed

# 原有规范/资料/源代码均不删；README/AGENTS原内容的逐行顺序仍保留。
for name in ('README.md', 'AGENTS.md'):
    original = (EVIDENCE/'before'/name).read_text(encoding='utf-8').splitlines()
    current = iter((ROOT/name).read_text(encoding='utf-8').splitlines())
    assert all(any(line==candidate for candidate in current) for line in original), name

index = subprocess.run(['git','diff','--cached','--binary'], cwd=ROOT, capture_output=True, check=True).stdout
assert index==(EVIDENCE/'index_before.patch').read_bytes()
head = subprocess.run(['git','rev-parse','HEAD'], cwd=ROOT, capture_output=True, check=True).stdout
assert head==(EVIDENCE/'git_head_before.txt').read_bytes()
branch = subprocess.run(['git','branch','--show-current'], cwd=ROOT, capture_output=True, check=True).stdout.decode().strip()
assert branch=='feat/m2-sampling-20261123'

frozen_runs = {}
for name in ('M2_sampling_20261123','M2_robot_noise_20261123','M2_scene2_20261123','M2_pool120_20261123','W2_projection_20261123'):
    folder = ROOT/'experiments'/name
    hashes = json.loads((folder/'artifact_hashes.json').read_text(encoding='utf-8'))
    actual = {p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file()}-{'artifact_hashes.json'}
    assert set(hashes)==actual, name
    assert all(digest(folder/path)==value for path,value in hashes.items()), name
    code = json.loads((folder/'code_hashes.json').read_text(encoding='utf-8'))
    assert all(digest(ROOT/path)==value for path,value in code.items()), name
    frozen_runs[name] = dict(artifacts_checked=len(hashes), pinned_code_files_unchanged=len(code))

counts = {key:sum(int(s.get(key,0)) for s in ET.parse(OUT/'full_final.xml').getroot().iter('testsuite'))
          for key in ('tests','failures','errors','skipped')}
assert counts==dict(tests=226,failures=0,errors=0,skipped=0), counts

diffs = []
new_files = []
for folder in ('src','tests','scripts','configs','docs','plans'):
    for path in sorted((ROOT/folder).rglob('*')):
        if not path.is_file() or '__pycache__' in path.parts:
            continue
        relative = path.relative_to(ROOT).as_posix()
        baseline = EVIDENCE/'before'/relative
        old = baseline.read_text(encoding='utf-8').splitlines(keepends=True) if baseline.exists() else []
        current = path.read_text(encoding='utf-8').splitlines(keepends=True)
        if old!=current:
            diffs.extend(difflib.unified_diff(old,current,fromfile='before/'+relative if baseline.exists() else '/dev/null',tofile='after/'+relative))
        if relative not in before:
            new_files.append(relative)
for name in ('README.md','AGENTS.md'):
    diffs.extend(difflib.unified_diff((EVIDENCE/'before'/name).read_text(encoding='utf-8').splitlines(keepends=True),
                   (ROOT/name).read_text(encoding='utf-8').splitlines(keepends=True),fromfile='before/'+name,tofile='after/'+name))
(EVIDENCE/'changes.patch').write_text(''.join(diffs), encoding='utf-8')

documents = [ROOT/'README.md',ROOT/'docs/PROJECT_SPEC.md',ROOT/'docs/M2_sampling_guide.md',ROOT/'docs/W2_projection_guide.md',
             ROOT/'reports/M2_tonight_completion_20261123.md',ROOT/'reports/M2_development_report_20261123.md',
             ROOT/'reports/M2_extensions_20261123.md',ROOT/'reports/W2_development_report_20261123.md',ROOT/'reports/M2_review_request_20261123.md']
links = 0
for path in documents:
    content = path.read_text(encoding='utf-8')
    assert content.count('```')%2==0, path
    for target in re.findall(r'\]\(([^)]+)\)', content):
        if target.startswith(('http://','https://','#')):
            continue
        resolved = (path.parent/target.split('#')[0]).resolve()
        if resolved != (OUT/'delivery_verification.json').resolve():
            assert resolved.exists(), (path,target)
        links += 1

for name,args in [('git_status_after.txt',['status','--short','--branch']),('tracked_after.patch',['diff','--binary'])]:
    (OUT/name).write_bytes(subprocess.run(['git',*args],cwd=ROOT,capture_output=True,check=True).stdout)
whitespace = subprocess.run(['git','diff','--check'],cwd=ROOT,capture_output=True)
assert whitespace.returncode==0
(OUT/'git_diff_check.txt').write_bytes(whitespace.stdout+whitespace.stderr)
pip = subprocess.run([str(ROOT/'.venv/Scripts/python.exe'),'-m','pip','check'],cwd=ROOT,capture_output=True)
assert pip.returncode==0
(OUT/'pip_check.txt').write_bytes(pip.stdout+pip.stderr)

result = dict(result='PASS', existing_files_checked=len(before), changed_existing_only=changed, deleted_existing=missing,
              continuation_existing_changes=continuation_changed, head_unchanged=True, index_unchanged=True,
              branch=branch, final_pytest=counts, frozen_runs=frozen_runs, links_checked=links,
              new_source_config_doc_plan_files=new_files, diff_file='reports/M2_evidence_20261123/changes.patch')
(OUT/'delivery_verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
assert (OUT/'delivery_verification.json').is_file()

# 包含新增报告、证据、源码与正式结果的完整性清单；排除缓存和该清单自身。
paths = []
for folder in ('src','tests','scripts','configs','docs','plans'):
    paths.extend(p for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
paths.extend(documents)
paths.extend(p for p in (ROOT/'reports').glob('*20261123.md'))
paths.extend(p for evidence in (EVIDENCE,OUT) for p in evidence.rglob('*') if p.is_file() and 'before' not in p.relative_to(evidence).parts)
manifest = {p.relative_to(ROOT).as_posix():digest(p) for p in sorted(set(paths)) if p.name!='delivery_manifest.json'}
(OUT/'delivery_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
