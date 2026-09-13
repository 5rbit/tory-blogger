#!/usr/bin/env python3
"""월요일 새벽: 키워드 발굴 → 주간 캘린더 → 사람 승인 대기."""
import sys; from pathlib import Path; sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import click
from src.common import get_logger, pipeline_config
from src.research import naver_ad_api, naver_search_api, feed_collector
from src.planner.calendar import write_week_plan
log = get_logger("weekly_plan")

@click.command()
@click.option("--dry-run", is_flag=True)
def main(dry_run):
    cfg = pipeline_config()
    log.info("1/4 검색광고 API")
    cands = naver_ad_api.fetch_keyword_stats(cfg["topic"]["seed_keywords"], dry_run)
    log.info("2/4 검색 API 상위 노출 분석")
    cands = naver_search_api.enrich_with_serp(cands, dry_run)
    log.info("3/4 RSS 소재 %d개", len(feed_collector.collect_topics(dry_run)))
    log.info("4/4 주간 캘린더")
    path = write_week_plan(cands)
    log.info("승인 필요: %s 의 status 를 approved 로 바꾸세요", path)

if __name__ == "__main__":
    main()
