"""导出暂存Git树，核验字节、发布边界及凭据后供独立检出测试。"""
from pathlib import Path
from collections import Counter
import hashlib
import json
import re
import shutil
import subprocess
import tarfile

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'reports/cleanup_20261123'
DEST=ROOT/'.venv/publish_checkout_20261123'
assert not DEST.exists(), 'Fresh checkout directory must be new'
tree=subprocess.run(['git','write-tree'],cwd=ROOT,capture_output=True,check=True).stdout.decode().strip()
archive=ROOT/'.venv/publish_checkout_20261123.tar'
with archive.open('xb') as f:
    subprocess.run(['git','archive','--format=tar',tree],cwd=ROOT,stdout=f,check=True)
DEST.mkdir()
with tarfile.open(archive,'r') as tar:
    for member in tar:
        target=(DEST/member.name).resolve()
        assert target.is_relative_to(DEST.resolve())
        if member.isdir(): target.mkdir(parents=True,exist_ok=True); continue
        assert member.isfile(), 'Unexpected link/device in Git export'
        target.parent.mkdir(parents=True,exist_ok=True)
        with tar.extractfile(member) as source, target.open('xb') as output:
            shutil.copyfileobj(source,output)

secret=re.compile(r'(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{30,}|sk-[A-Za-z0-9_-]{24,}|AKIA[0-9A-Z]{16}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)')
findings=[]; files=[]; total=0
for p in DEST.rglob('*'):
    if not p.is_file(): continue
    name=p.relative_to(DEST).as_posix(); files.append(name); total+=p.stat().st_size
    assert p.suffix.lower()!='.docx' and not name.startswith(('文献/','local_only/','.venv/','.git/'))
    assert not name.endswith('proposal_text_local.txt') and '/__pycache__/' not in name
    assert not name.startswith('reports/cleanup_20261123/before/')
    original=ROOT/name
    assert original.exists(),name
    assert hashlib.sha256(p.read_bytes()).digest()==hashlib.sha256(original.read_bytes()).digest(),f'Git changed bytes: {name}'
    if p.suffix.lower() in {'.py','.md','.txt','.json','.csv','.patch','.xml','.yaml','.yml'}:
        try: content=p.read_text(encoding='utf-8-sig')
        except UnicodeError: continue
        if secret.search(content): findings.append(name)
assert not findings, 'Credential pattern in staged content; examine local report'
result={'result':'PASS','tested_tree_sha':tree,'files':len(files),'bytes':total,'MiB':round(total/1024**2,2),
        'byte_identity_checked':len(files),'credential_findings':findings,'private_materials_excluded':True,
        'groups':dict(Counter(name.split('/')[0] for name in files)),
        'export_directory':'.venv/publish_checkout_20261123','note':'Fresh export from staged Git tree; test logs added to final commit afterwards'}
(OUT/'staged_review.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
