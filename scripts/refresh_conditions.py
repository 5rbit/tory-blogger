#!/usr/bin/env python3
"""발행 직전: 초안에 '이번 주말 현황' 블록(날씨·단풍·통제)을 넣거나 갱신한다.
사용: python scripts/refresh_conditions.py --exp hiker data/hiker/drafts/xxx.md --trailhead "북한산 우이동" --mountain 북한산 [--date 2026-10-24]
"""
import sys, re; from pathlib import Path; sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from datetime import date, timedelta
import click
from src.common import get_logger, set_experiment
from src.research.conditions import conditions_block
log = get_logger("refresh_conditions")

def next_saturday(today: date) -> date:
    return today + timedelta(days=(5 - today.weekday()) % 7 or 7)

@click.command()
@click.argument("draft", type=click.Path(exists=True, path_type=Path))
@click.option("--exp", default=None)
@click.option("--trailhead", required=True, help="config/trailheads.yaml 의 키")
@click.option("--mountain", required=True)
@click.option("--date", "target", default=None, help="YYYY-MM-DD (기본: 다음 토요일)")
@click.option("--dry-run", is_flag=True)
def main(draft, exp, trailhead, mountain, target, dry_run):
    set_experiment(exp)
    t = date.fromisoformat(target) if target else next_saturday(date.today())
    block = conditions_block(trailhead, mountain, t, dry_run)
    text = draft.read_text(encoding="utf-8")
    pat = re.compile(r"## (?:🌤️ )?이번 주말 현황.*?(?=\n## |\n#[^#]|\Z)", re.S)
    if pat.search(text):
        text = pat.sub(block, text); log.info("현황 블록 갱신")
    elif "## ⚠️ 주의사항" in text:
        text = text.replace("## ⚠️ 주의사항", block + "\n\n## 주의사항", 1); log.info("현황 블록 삽입 (주의사항 앞)")
    else:
        text = text.rstrip() + "\n\n" + block + "\n"; log.info("현황 블록 추가 (끝)")
    if dry_run:
        print(block)
    else:
        draft.write_text(text, encoding="utf-8")
    log.info("대상: %s / %s / %s", trailhead, mountain, t)

if __name__ == "__main__":
    main()
