"""项目根目录运行；只写项目内新目录，拒绝覆盖已有实验。"""

import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".venv/matplotlib-cache"))

from handeye.experiments import ExperimentConfig, run_experiment  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="M1 Eye-in-Hand pose-level simulation")
    parser.add_argument("--config", type=Path, default=ROOT / "configs/m1_v0_1.json")
    parser.add_argument("--output", type=Path, required=True, help="New directory inside project")
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT):
        parser.error("输出目录必须位于当前项目内")
    try:
        config = ExperimentConfig.from_dict(json.loads(args.config.read_text(encoding="utf-8")))
        status = run_experiment(config, output)
    except (ValueError, TypeError, OSError) as exc:
        parser.exit(2, f"M1 failed: {type(exc).__name__}: {exc}\n")
    print(json.dumps(status, ensure_ascii=False, indent=2))
    return 0 if status["baseline_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
