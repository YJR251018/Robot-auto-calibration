# 项目初始化记录

日期：2026-11-18（Asia/Shanghai）。本记录只描述本次实际执行结果。

## 目录检查

- 初始工作目录为 `D:\Research`，并非仓库根目录。
- 发现已有子目录后，将后续项目操作的工作目录设为 `D:\Research\Robot-auto-calibration`。
- `git rev-parse --show-toplevel` 确认它是仓库根目录。
- 初始化前，磁盘上的项目资料包括 `.git/`、`文献/` 和项目申报书；没有发现现存的 AGENTS.md。
- Git 已有历史，且旧 README.md、requirements.txt、.gitignore、算法文件、两份测试和部分研究文档在本次操作前已经处于删除状态。
- 本次按用户初始化要求新写 README.md、requirements.txt、.gitignore；它们在 Git 中显示为修改。其余原有删除状态保留，没有恢复、删除旧代码或提交 Git。

## 环境检查结果

| 项目 | 实测结果 |
| --- | --- |
| Python | 3.12.0，64 位 |
| `python` 实际路径 | `D:\Program Files\Python3.12\python.exe` |
| Windows Python 启动器 | `py --version` 返回 3.12.0；`py -0p` 列出同一个 3.12 解释器 |
| `python3` | 检测到 WindowsApps 应用别名；未将其作为可用解释器运行验证 |
| Git | 2.54.0.windows.1 |
| Git 优先路径 | `C:\Program Files\Git\cmd\git.exe` |
| 虚拟环境工具 | 标准库 `venv` 可导入，创建成功 |
| pip | 创建环境时为 23.2.1；未升级 |
| ensurepip | 可用，自带 pip 23.2.1 |
| SSL | OpenSSL 3.0.11 19 Sep 2023 |
| PowerShell 执行策略 | LocalMachine 为 RemoteSigned，其余作用域为 Undefined；未修改 |
| 虚拟环境路径 | `D:\Research\Robot-auto-calibration\.venv` |

Windows 中使用 `python -m venv .venv` 创建虚拟环境；`py -3.12 -m venv .venv` 是本机可选择的另一种方式，本次实际只执行前一种。后续直接调用 `.venv\Scripts\python.exe`，没有激活环境或修改执行策略。

## 创建内容与用途

| 路径 | 用途 |
| --- | --- |
| README.md | 项目目标、目录结构、Windows 安装与验证步骤、依赖用途 |
| requirements.txt | 五项直接依赖，不预设未经验证的版本 |
| requirements-lock.txt | 由 pip freeze 生成的实际安装版本快照，包含必要的传递依赖 |
| AGENTS.md | 中文教学、开发范围、虚拟环境、资料保护和验证约定 |
| .gitignore | 排除 .venv、Python 缓存、pytest 缓存和本地编辑器设置 |
| src/README.md | 保留 src 目录，说明未来源码用途；无算法实现 |
| tests/test_environment.py | 用 pytest 分别导入 numpy、scipy、cv2、matplotlib、pytest |
| INITIALIZATION.md | 本次实际环境、操作、结果与待处理事项 |
| .venv/ | 项目隔离环境及已安装依赖，不提交 Git |

运行测试还自动生成了已被忽略的 `.pytest_cache/` 和 Python 字节码缓存。

## 实际执行的主要命令

目录检查通过 `Get-Location`、`Get-ChildItem -Force`、`rg --files -g AGENTS.md`、`Get-Content` 完成；查找的 AGENTS.md 不存在，因此部分只读查找返回非零退出码，并非 Python 或项目故障。

环境和 Git 检查：

```powershell
Get-Command python,python3,py,git -All -ErrorAction SilentlyContinue
python --version
py --version
py -0p
git --version
python -m pip --version
Get-ExecutionPolicy -List
git rev-parse --show-toplevel
git status --short
git ls-files
```

另通过 `python -c` 检查 `sys.executable`、64 位架构、`venv`、`ensurepip` 和 SSL 信息。

创建环境与安装（以下按实际尝试顺序列出）：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -c "import sys; print('Python:', sys.version); print('executable:', sys.executable); print('venv active:', sys.prefix != sys.base_prefix)"
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
# 以上首次失败；随后在允许联网的执行环境中重试同一条安装命令，也失败。
.\.venv\Scripts\python.exe -m pip cache list --format=abspath
# 只读 DNS/HTTPS 检查后，以下第三次安装成功：
.\.venv\Scripts\python.exe -m pip install --only-binary=:all: --retries 1 --timeout 20 -r requirements.txt
```

`--only-binary=:all:` 只接受预编译包，避免初始项目需要本机编译工具；`--retries` 和 `--timeout` 限制连接重试及超时。没有更换安装源。

验证与版本快照：

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -c "import sys, numpy, scipy, cv2, matplotlib, pytest; print('Python:', sys.version.split()[0]); print('Interpreter:', sys.executable); print('NumPy:', numpy.__version__); print('SciPy:', scipy.__version__); print('OpenCV:', cv2.__version__); print('Matplotlib:', matplotlib.__version__); print('pytest:', pytest.__version__)"
$dependencySnapshot = .\.venv\Scripts\python.exe -m pip freeze
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
$dependencySnapshot | Set-Content -LiteralPath requirements-lock.txt -Encoding utf8
git check-ignore .venv\pyvenv.cfg
git diff --check
git -c core.quotepath=false status --short
```

实际执行时在 pytest、pip check 之后同样检查了退出码，失败时不会继续报告成功。项目文本文件通过补丁工具创建，版本快照通过上述 PowerShell 命令写入。

## 网络错误与处理

1. 首次安装出现 `getaddrinfo failed`（11001），无法解析下载源；之后的 `No matching distribution found for numpy` 是连接失败导致的结果，没有证据表明是 NumPy 不兼容。
2. 在允许联网的执行环境重试后，索引可访问，但 `files.pythonhosted.org` 仍发生域名解析失败（11001/11002）。两次安装均退出码 1。
3. 用 Python 的 socket 和 urllib 对 `pypi.org`、`files.pythonhosted.org`、`pypi.tuna.tsinghua.edu.cn` 做只读检查。后一次检查中三个域名均解析成功，PyPI 与清华镜像的 NumPy 索引均返回 HTTP 200。
4. 官方源连通恢复后，第三次安装成功（退出码 0）。未实际使用镜像安装，未修改 DNS、代理或全局 pip 配置，也未升级 Python、Git 或 pip。

## 最终验证

| 包 | 实际安装版本 |
| --- | --- |
| numpy | 2.5.5 |
| scipy | 1.18.1 |
| opencv-python | 5.1.0.95（`cv2.__version__` 为 5.1.0） |
| matplotlib | 3.11.2 |
| pytest | 9.2.0 |

- 五项导入测试：`5 passed in 2.28s`，退出码 0。
- 依赖一致性：`No broken requirements found.`，退出码 0。
- 已确认测试解释器来自本项目 `.venv`。
- 已确认 `.venv/pyvenv.cfg` 被 Git 忽略。
- `git diff --check` 未发现空白错误；Git 提示部分文本未来可能由 LF 转为 CRLF，这是当前仓库换行设置提示，本次未修改该设置。

## 尚未解决与后续范围

- 当前无阻碍初始化的环境问题；网络曾发生间歇性解析失败，未来重新安装仍可能需要先检查连接。
- Git 中原有多份文件的删除状态尚未处理；后续由用户另行决定是否需要旧内容，本次没有创建 Git 提交。
- 当前验证仅覆盖依赖导入及包依赖一致性，不证明未来标定算法正确，也不验证相机、机器人或 GUI。
- 下一阶段需先明确坐标变换约定、仿真输入输出和评价指标，再开始 Eye-in-Hand 仿真；本次未开展算法开发。
