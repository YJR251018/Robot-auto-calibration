"""M2 完整重放；核验报告写到项目内新文件，不能写回被核验目录。"""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from handeye.m2_verification import compare_runs, verify_m2  # noqa: E402


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--run',type=Path,required=True)
    parser.add_argument('--compare',type=Path)
    parser.add_argument('--report',type=Path,required=True)
    args=parser.parse_args()
    report=args.report.resolve()
    if not report.is_relative_to(ROOT) or report.is_relative_to(args.run.resolve()) or (args.compare and report.is_relative_to(args.compare.resolve())):
        parser.error('核验报告必须在项目内且在实验目录之外')
    if report.exists():
        parser.error('核验报告已存在，拒绝覆盖')
    result={'verification':verify_m2(args.run)}
    if args.compare:
        result['second_verification']=verify_m2(args.compare)
        result['comparison']=compare_runs(args.run,args.compare)
    with report.open('x',encoding='utf-8') as f:
        json.dump(result,f,ensure_ascii=False,indent=2)
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
