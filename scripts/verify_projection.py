"""W2核验报告写入项目内新的外部文件，保持实验哈希不变。"""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from handeye.projection_verification import verify_projection  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    report = args.report.resolve()
    if not report.is_relative_to(ROOT) or report.is_relative_to(args.run.resolve()) or report.exists():
        parser.error('报告须位于项目内、实验目录外，且不存在')
    result = verify_projection(args.run)
    with report.open('x', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__=='__main__':
    main()
