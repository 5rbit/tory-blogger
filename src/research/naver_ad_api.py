"""네이버 검색광고 API — 키워드 월 검색량·경쟁도 조회.
문서: https://naver.github.io/searchad-apidoc/  (GET /keywordstool)
"""
from __future__ import annotations
from src.common import KeywordCandidate, env, get_logger
log = get_logger(__name__)

def fetch_keyword_stats(seeds: list[str], dry_run: bool = False) -> list[KeywordCandidate]:
    """시드 키워드로 연관 키워드와 월 검색량을 가져온다."""
    if dry_run or not env("NAVER_AD_API_KEY"):
        log.info("[dry-run] 검색광고 API 생략, 시드 %d개 반환", len(seeds))
        return [KeywordCandidate(keyword=s, volume=1000, competition=0.5, source="seed") for s in seeds]
    # TODO: HMAC-SHA256 서명 헤더(X-Timestamp, X-API-KEY, X-Customer, X-Signature) 생성
    # TODO: GET https://api.searchad.naver.com/keywordstool?hintKeywords=...&showDetail=1
    # TODO: monthlyPcQcCnt + monthlyMobileQcCnt → volume, compIdx(낮음/중간/높음) → competition
    raise NotImplementedError("검색광고 API 연동 예정 (로드맵 1–2주차)")
