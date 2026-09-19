#!/usr/bin/env python3
"""진입로·진출로 대중교통 표를 만들어 초안의 '## ⚠️ 주의사항' 앞에 넣는다 (초안 없이 출력만도 가능).
사용: python scripts/transit_table.py --exp hiker --entry "북한산 우이동" --exit "북한산 구기동" [초안.md]
"""
import sys, re; from pathlib import Path; sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import click
from src.common import get_logger, set_experiment
from src.research.transit import to_markdown
log = get_logger("transit_table")

@click.command()
@click.argument("draft", required=False, type=click.Path(exists=True, path_type=Path))
@click.option("--exp", default=None)
@click.option("--entry", required=True, help="들머리 (config/trailheads.yaml 키)")
@click.option("--exit", "exit_", default=None, help="날머리 (다르면)")
@click.option("--weekday", is_flag=True, help="평일 배차 기준 (기본: 토·일)")
@click.option("--dry-run", is_flag=True)
def main(draft, exp, entry, exit_, weekday, dry_run):
    set_experiment(exp)
    block = to_markdown(entry, exit_, dry_run, on_weekend=not weekday)
    if not draft or dry_run:
        print(block)
    if draft and not dry_run:
        text = draft.read_text(encoding="utf-8")
        pat = re.compile(r"## (?:🚌 )?대중교통.*?(?=\n## |\Z)", re.S)
        text = pat.sub(block, text) if pat.search(text) else (text.replace("## ⚠️ 주의사항", block + "\n\n## 주의사항", 1) if "## ⚠️ 주의사항" in text else text.rstrip() + "\n\n" + block + "\n")
        draft.write_text(text, encoding="utf-8"); log.info("대중교통 블록 반영: %s", draft)

if __name__ == "__main__":
    main()
