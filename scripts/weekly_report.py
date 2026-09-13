#!/usr/bin/env python3
"""일요일 밤: data/reports/raw 의 CSV → 주간 리포트."""
import sys; from pathlib import Path; sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import click
from src.analytics.report import build_report

@click.command()
@click.option("--dry-run", is_flag=True)
def main(dry_run):
    build_report(dry_run=dry_run)

if __name__ == "__main__":
    main()
