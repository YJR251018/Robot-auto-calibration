"""从项目根目录执行 M2；输出必须为项目内不存在的新目录。"""
import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
os.environ.setdefault('MPLCONFIGDIR', str(ROOT/'.venv/matplotlib-cache'))
from handeye.m2_experiments import M2Config, run_m2  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description='M2 offline sampling experiment')
    parser.add_argument('--config', type=Path, default=ROOT/'configs/m2_sampling_v0_1.json')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not args.output.resolve().is_relative_to(ROOT):
        parser.error('输出只能在当前项目目录内')
    config = M2Config.from_dict(json.loads(args.config.read_text(encoding='utf-8')))
    print(json.dumps(run_m2(config, args.output), ensure_ascii=False, indent=2))


if __name__=='__main__':
    main()
