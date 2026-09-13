"""네이버 검색 API — 키워드별 상위 노출 블로그 분석 (개인 블로그 비율, 경쟁 제목).

2026년 6월부터 검색 API는 네이버클라우드 NAVER API HUB 로 이관됐다 (기본).
  문서: https://api.ncloud-docs.com/docs/naver-api-hub-search-blog
  URL : https://naverapihub.apigw.ntruss.com/search/v1/blog
  헤더: X-NCP-APIGW-API-KEY-ID / X-NCP-APIGW-API-KEY  (.env: NAVER_NCP_KEY_ID / NAVER_NCP_KEY)
  한도: 일 25,000회, 월 775,000회, 초당 50회. 현재 무료.
기존 개발자센터 키(X-Naver-Client-Id/Secret, openapi.naver.com)는 2027-06-30 까지만 동작 → 폴백.
"""
from __future__ import annotations
import json, re, time
from datetime import date
import requests
from src.common import data_dir, KeywordCandidate, env, get_logger
log = get_logger(__name__)

HUB_URL = "https://naverapihub.apigw.ntruss.com/search/v1/blog"
LEGACY_URL = "https://openapi.naver.com/v1/search/blog.json"
def cache_dir(): return data_dir() / "keywords" / "cache"
# 기업·공식 계정으로 보이는 블로그 ID 패턴 (개인 아님으로 판정)
CORP_PATTERNS = re.compile(r"official|corp|company|_kr$|^kr_|store|shop|brand|edu$|academy|center|group|inc$|lab$", re.I)

def has_credentials() -> bool:
    return bool((env("NAVER_NCP_KEY_ID") and env("NAVER_NCP_KEY")) or (env("NAVER_CLIENT_ID") and env("NAVER_CLIENT_SECRET")))

def _endpoint() -> tuple[str, dict[str, str]]:
    """API HUB 키가 있으면 HUB, 없으면 구 개발자센터 키로 폴백."""
    kid, key = env("NAVER_NCP_KEY_ID"), env("NAVER_NCP_KEY")
    if kid and key:
        return HUB_URL, {"X-NCP-APIGW-API-KEY-ID": kid, "X-NCP-APIGW-API-KEY": key}
    cid, sec = env("NAVER_CLIENT_ID"), env("NAVER_CLIENT_SECRET")
    if cid and sec:
        log.warning("구 개발자센터 키 사용 중 (2027-06-30 종료). NAVER API HUB 키로 옮기세요")
        return LEGACY_URL, {"X-Naver-Client-Id": cid, "X-Naver-Client-Secret": sec}
    raise RuntimeError("NAVER_NCP_KEY_ID / NAVER_NCP_KEY (API HUB) 가 .env 에 필요합니다")

def _headers() -> dict[str, str]:
    return _endpoint()[1]

def _strip_tags(s: str) -> str:
    return re.sub(r"<[^>]+>", "", s or "").replace("&quot;", '"').replace("&amp;", "&")

def is_personal(item: dict) -> bool:
    """blog.naver.com 개인 블로그로 보이는지 판정."""
    link = item.get("bloggerlink") or item.get("link") or ""
    m = re.search(r"blog\.naver\.com/([A-Za-z0-9_\-]+)", link)
    if not m:
        return False                           # 티스토리·기업 사이트 등
    return not CORP_PATTERNS.search(m.group(1))

def analyze(items: list[dict]) -> dict:
    n = len(items) or 1
    personal = sum(is_personal(i) for i in items)
    naver = sum(1 for i in items if "blog.naver.com" in (i.get("bloggerlink") or i.get("link") or ""))
    recent = sum(1 for i in items if str(i.get("postdate", ""))[:4] >= str(date.today().year - 1))
    return {"personal_ratio": personal / n, "naver_ratio": naver / n, "recent_ratio": recent / n,
            "top_titles": [_strip_tags(i.get("title", "")) for i in items[:5]],
            "avg_desc_len": sum(len(_strip_tags(i.get("description", ""))) for i in items) // n}

def search_blog(query: str, display: int = 10, session: requests.Session | None = None) -> list[dict]:
    s = session or requests.Session()
    url, headers = _endpoint()
    r = s.get(url, headers=headers, params={"query": query, "display": display, "sort": "sim", "format": "json"}, timeout=15)
    if r.status_code != 200:
        raise RuntimeError(f"검색 API {r.status_code}: {r.text[:200]}")
    return r.json().get("items", [])

def enrich_with_serp(cands: list[KeywordCandidate], dry_run: bool = False, use_cache: bool = True) -> list[KeywordCandidate]:
    """각 키워드의 상위 10개 결과를 분석해 personal_ratio 와 경쟁 정보를 채운다."""
    if dry_run or not has_credentials():
        log.info("[dry-run] 검색 API 생략, personal_ratio=0.5 가정")
        for c in cands:
            c.personal_ratio = 0.5
        return cands
    cp = cache_dir() / f"serp-{date.today():%Y-W%V}.json"
    cache: dict[str, dict] = json.loads(cp.read_text(encoding="utf-8")) if (use_cache and cp.exists()) else {}
    sess = requests.Session()
    hits = 0
    for c in cands:
        if c.keyword not in cache:
            cache[c.keyword] = analyze(search_blog(c.keyword, session=sess))
            hits += 1
            time.sleep(0.1)
        a = cache[c.keyword]
        c.personal_ratio = a["personal_ratio"]
        c.extra.update({"serp": a})
    cp.parent.mkdir(parents=True, exist_ok=True)
    cp.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
    log.info("검색 API 호출 %d회 (캐시 %d개), 개인 블로그 비율 평균 %.0f%%", hits, len(cache) - hits,
             100 * sum(c.personal_ratio for c in cands) / max(len(cands), 1))
    return cands
