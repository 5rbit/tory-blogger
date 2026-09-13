"""네이버 검색 API — 키워드별 상위 노출 블로그 분석 (개인 블로그 비율, 경쟁 제목).
문서: https://developers.naver.com/docs/serviceapi/search/blog/blog.md
인증: X-Naver-Client-Id, X-Naver-Client-Secret. 일 25,000회.
"""
from __future__ import annotations
import json, re, time
from datetime import date
import requests
from src.common import DATA, KeywordCandidate, env, get_logger
log = get_logger(__name__)

URL = "https://openapi.naver.com/v1/search/blog.json"
CACHE_DIR = DATA / "keywords" / "cache"
# 기업·공식 계정으로 보이는 블로그 ID 패턴 (개인 아님으로 판정)
CORP_PATTERNS = re.compile(r"official|corp|company|_kr$|^kr_|store|shop|brand|edu$|academy|center|group|inc$|lab$", re.I)

def _headers() -> dict[str, str]:
    cid, sec = env("NAVER_CLIENT_ID"), env("NAVER_CLIENT_SECRET")
    if not (cid and sec):
        raise RuntimeError("NAVER_CLIENT_ID / NAVER_CLIENT_SECRET 이 .env 에 필요합니다")
    return {"X-Naver-Client-Id": cid, "X-Naver-Client-Secret": sec}

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
    r = s.get(URL, headers=_headers(), params={"query": query, "display": display, "sort": "sim"}, timeout=15)
    if r.status_code != 200:
        raise RuntimeError(f"검색 API {r.status_code}: {r.text[:200]}")
    return r.json().get("items", [])

def enrich_with_serp(cands: list[KeywordCandidate], dry_run: bool = False, use_cache: bool = True) -> list[KeywordCandidate]:
    """각 키워드의 상위 10개 결과를 분석해 personal_ratio 와 경쟁 정보를 채운다."""
    if dry_run or not env("NAVER_CLIENT_ID"):
        log.info("[dry-run] 검색 API 생략, personal_ratio=0.5 가정")
        for c in cands:
            c.personal_ratio = 0.5
        return cands
    cp = CACHE_DIR / f"serp-{date.today():%Y-W%V}.json"
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
