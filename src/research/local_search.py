"""NAVER API HUB 지역 검색 — 들머리 주변 식당 목록 (하산 후 맛집 섹션용).
URL: https://naverapihub.apigw.ntruss.com/search/v1/local  (구: openapi.naver.com/v1/search/local.json)
display 최대 5. 결과: title, category, address, roadAddress, mapx, mapy, link
"""
from __future__ import annotations
import re
import requests
from src.common import get_logger
from src.research.naver_search_api import _endpoint, has_credentials, HUB_URL, LEGACY_URL
log = get_logger(__name__)

def _local_url(url: str) -> str:
    return url.replace("/search/v1/blog", "/search/v1/local").replace("/v1/search/blog.json", "/v1/search/local.json")

def restaurants_near(trailhead: str, keyword: str = "맛집", display: int = 5, dry_run: bool = False) -> list[dict]:
    """'{들머리} {맛집}' 으로 지역 검색. 직접 간 곳 표시는 사람이 초안에서 O/X 로 채운다."""
    if dry_run or not has_credentials():
        log.info("[dry-run] 지역 검색 생략: %s", trailhead)
        return [{"title": f"(예시) {trailhead} 식당 {i+1}", "category": "한식", "roadAddress": "", "link": ""} for i in range(3)]
    url, headers = _endpoint()
    r = requests.get(_local_url(url), headers=headers, params={"query": f"{trailhead} {keyword}", "display": display, "sort": "comment"}, timeout=15)
    if r.status_code != 200:
        raise RuntimeError(f"지역 검색 API {r.status_code}: {r.text[:200]}")
    items = r.json().get("items", [])
    for it in items:
        it["title"] = re.sub(r"<[^>]+>", "", it.get("title", ""))
    return items

def to_markdown_table(items: list[dict]) -> str:
    rows = ["| 🍲 식당 | 분류 | 주소 | 직접 감 |", "|---|---|---|---|"]
    rows += [f"| {i['title']} | {i.get('category','')} | {i.get('roadAddress','')} | ❌ |" for i in items]
    return "\n".join(rows)
