"""RSS 소재 수집. ../blog/src/config/feeds.json 구조 재사용. 소재 발굴용으로만 사용(원문 재가공 금지)."""
from __future__ import annotations
from src.common import get_logger
log = get_logger(__name__)

def collect_topics(dry_run: bool = False) -> list[str]:
    if dry_run:
        log.info("[dry-run] RSS 수집 생략")
        return []
    # TODO: feedparser 로 feeds.json 의 enabled 피드 수집 → 제목만 이슈형 후보로 반환
    return []
