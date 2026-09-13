#!/usr/bin/env python3
"""일요일 밤: data/reports/raw 의 CSV → 주간 리포트."""
import sys; from pathlib import Path; sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import click
from src.common import set_experiment, list_experiments
from src.analytics.report import build_report
from src.common import get_logger
log = get_logger('weekly_report')

@click.command()
@click.option("--exp", default=None, help="실험 ID (experiments/<id>)")
@click.option("--all", "run_all", is_flag=True, help="모든 실험을 순서대로 실행")
@click.option("--dry-run", is_flag=True)
def main(exp, run_all, dry_run):
    for e in (list_experiments() if run_all else [exp]):
        set_experiment(e)
        log.info("=== 실험: %s ===", e or "(기본)")
        run(dry_run)

def run(dry_run):
    build_report(dry_run=dry_run)

if __name__ == "__main__":
    main()
