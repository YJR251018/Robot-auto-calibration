"""W2 投影实验CLI，结果只写项目内新目录。"""
import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
os.environ.setdefault('MPLCONFIGDIR', str(ROOT/'.venv/matplotlib-cache'))
from handeye.projection_experiment import ProjectionConfig, run_projection  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description='W2 projection and visibility geometry experiment')
    parser.add_argument('--config', type=Path, default=ROOT/'configs/w2_projection_v0_1.json')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not args.output.resolve().is_relative_to(ROOT):
        parser.error('输出只能位于项目内')
    config = ProjectionConfig.from_dict(json.loads(args.config.read_text(encoding='utf-8')))
    print(json.dumps(run_projection(config, args.output), ensure_ascii=False, indent=2))


if __name__=='__main__':
    main()
