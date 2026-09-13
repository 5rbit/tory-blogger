"""네이버 검색 API — 상위 노출 블로그 분석 (개인 블로그 비율).
문서: https://developers.naver.com/docs/serviceapi/search/blog/blog.md
"""
from __future__ import annotations
from src.common import KeywordCandidate, env, get_logger
log = get_logger(__name__)

def enrich_with_serp(cands: list[KeywordCandidate], dry_run: bool = False) -> list[KeywordCandidate]:
    """각 키워드의 상위 10개 결과에서 개인 블로그 비율을 계산해 채운다."""
    if dry_run or not env("NAVER_CLIENT_ID"):
        log.info("[dry-run] 검색 API 생략, personal_ratio=0.5 가정")
        for c in cands:
            c.personal_ratio = 0.5
        return cands
    # TODO: GET https://openapi.naver.com/v1/search/blog.json?query=...&display=10
    # TODO: bloggerlink 가 blog.naver.com 이고 기업 계정 패턴이 아니면 개인으로 판정
    raise NotImplementedError("검색 API 연동 예정 (로드맵 1–2주차)")
