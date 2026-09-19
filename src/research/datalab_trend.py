"""NAVER API HUB 데이터랩 검색어 트렌드 — 키워드의 월별 검색 비율 시계열로 '이맘때(피크)' 를 찾는다.
POST https://naverapihub.apigw.ntruss.com/datalab/v1/search  (JSON, 최대값=100 인 비율 시계열)
"""
from __future__ import annotations
from datetime import date, timedelta
import requests
from src.common import get_logger
from src.research.naver_search_api import _endpoint, has_credentials
log = get_logger(__name__)
TREND_PATH = "/datalab/v1/search"

def weekly_ratio(keywords: list[str], years: int = 3, dry_run: bool = False) -> dict[str, list[dict]]:
    """{keyword: [{period, ratio}, ...]} 주 단위, 최근 N년."""
    if dry_run or not has_credentials():
        log.info("[dry-run] 데이터랩 생략")
        return {k: [] for k in keywords}
    url, headers = _endpoint()
    base = url.split("/search/")[0] if "ntruss" in url else "https://openapi.naver.com"
    end = date.today(); start = end - timedelta(days=365 * years)
    body = {"startDate": start.isoformat(), "endDate": end.isoformat(), "timeUnit": "week",
            "keywordGroups": [{"groupName": k, "keywords": [k]} for k in keywords[:5]]}
    r = requests.post(base + TREND_PATH if "ntruss" in base else base + "/v1/datalab/search",
                      headers={**headers, "Content-Type": "application/json"}, json=body, timeout=20)
    if r.status_code != 200:
        raise RuntimeError(f"데이터랩 API {r.status_code}: {r.text[:200]}")
    return {g["title"]: g["data"] for g in r.json().get("results", [])}

def peak_weeks(series: list[dict]) -> list[int]:
    """연도별 피크 ISO 주차 목록. 매년 비슷한 주면 '이맘때' 로 본다."""
    by_year: dict[int, tuple[float, int]] = {}
    for pt in series:
        y, m, d = map(int, pt["period"].split("-"))
        wk = date(y, m, d).isocalendar()[1]
        if pt["ratio"] > by_year.get(y, (0, 0))[0]:
            by_year[y] = (pt["ratio"], wk)
    return [wk for _, wk in by_year.values()]

def publish_week(peaks: list[int], lead_weeks: int = 3) -> int | None:
    if not peaks:
        return None
    return round(sum(peaks) / len(peaks)) - lead_weeks
