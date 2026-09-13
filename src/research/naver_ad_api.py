"""네이버 검색광고 API — 키워드 도구(연관 키워드·월 검색량·경쟁도).
문서: https://naver.github.io/searchad-apidoc/  (GET /keywordstool)
인증: X-Timestamp, X-API-KEY, X-Customer, X-Signature(HMAC-SHA256 of "{ts}.{method}.{uri}", base64)
"""
from __future__ import annotations
import base64, hashlib, hmac, json, time
from datetime import date
from pathlib import Path
import requests
from src.common import DATA, KeywordCandidate, env, get_logger, pipeline_config
log = get_logger(__name__)

BASE_URL = "https://api.searchad.naver.com"
URI = "/keywordstool"
MAX_HINTS = 5                     # hintKeywords 는 호출당 최대 5개
COMP = {"낮음": 0.3, "중간": 0.6, "높음": 0.9}
CACHE_DIR = DATA / "keywords" / "cache"

def _signature(ts: str, method: str, uri: str, secret: str) -> str:
    msg = f"{ts}.{method}.{uri}".encode()
    return base64.b64encode(hmac.new(secret.encode(), msg, hashlib.sha256).digest()).decode()

def _headers(method: str, uri: str) -> dict[str, str]:
    key, secret, customer = env("NAVER_AD_API_KEY"), env("NAVER_AD_SECRET"), env("NAVER_AD_CUSTOMER_ID")
    if not (key and secret and customer):
        raise RuntimeError("NAVER_AD_API_KEY / NAVER_AD_SECRET / NAVER_AD_CUSTOMER_ID 가 .env 에 필요합니다")
    ts = str(int(time.time() * 1000))
    return {"Content-Type": "application/json; charset=UTF-8", "X-Timestamp": ts, "X-API-KEY": key,
            "X-Customer": customer, "X-Signature": _signature(ts, method, uri, secret)}

def _to_int(v) -> int:
    """'< 10' 같은 문자열 값도 정수로."""
    if isinstance(v, (int, float)):
        return int(v)
    s = str(v).strip()
    if s.startswith("<"):          # "< 10" 은 보수적으로 0 처리
        return 0
    s = s.replace(",", "")
    return int(s) if s.isdigit() else 0

def _to_float(v) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0

def parse_keyword_list(items: list[dict], source: str = "searchad") -> list[KeywordCandidate]:
    out = []
    for it in items:
        pc, mo = _to_int(it.get("monthlyPcQcCnt")), _to_int(it.get("monthlyMobileQcCnt"))
        out.append(KeywordCandidate(
            keyword=it["relKeyword"].strip(), volume=pc + mo,
            competition=COMP.get(it.get("compIdx", "중간"), 0.6), source=source,
            extra={"pc": pc, "mobile": mo, "compIdx": it.get("compIdx"),
                   "clicks": _to_float(it.get("monthlyAvePcClkCnt")) + _to_float(it.get("monthlyAveMobileClkCnt"))}))
    return out

def query_keywordstool(hints: list[str], session: requests.Session | None = None) -> list[dict]:
    """hintKeywords 로 연관 키워드 원본 목록을 받는다 (5개 단위로 나눠 호출)."""
    s = session or requests.Session()
    result: list[dict] = []
    for i in range(0, len(hints), MAX_HINTS):
        chunk = [h.replace(" ", "") for h in hints[i:i + MAX_HINTS]]   # 검색광고는 공백 제거 키워드 사용
        params = {"hintKeywords": ",".join(chunk), "showDetail": "1"}
        r = s.get(BASE_URL + URI, headers=_headers("GET", URI), params=params, timeout=30)
        if r.status_code != 200:
            raise RuntimeError(f"검색광고 API {r.status_code}: {r.text[:200]}")
        result += r.json().get("keywordList", [])
        time.sleep(0.5)   # 초당 호출 제한 대비
    return result

def _cache_path(week: str) -> Path:
    return CACHE_DIR / f"{week}.json"

def fetch_keyword_stats(seeds: list[str], dry_run: bool = False, use_cache: bool = True) -> list[KeywordCandidate]:
    """시드 키워드로 연관 키워드와 월 검색량을 가져온다. 주 단위 캐시로 호출을 아낀다."""
    if dry_run or not env("NAVER_AD_API_KEY"):
        log.info("[dry-run] 검색광고 API 생략, 시드 %d개 반환", len(seeds))
        return [KeywordCandidate(keyword=s, volume=1000, competition=0.5, source="seed") for s in seeds]
    week = date.today().strftime("%Y-W%V")
    cp = _cache_path(week)
    if use_cache and cp.exists():
        log.info("캐시 사용: %s", cp)
        raw = json.loads(cp.read_text(encoding="utf-8"))
    else:
        raw = query_keywordstool(seeds)
        cp.parent.mkdir(parents=True, exist_ok=True)
        cp.write_text(json.dumps(raw, ensure_ascii=False, indent=1), encoding="utf-8")
        log.info("검색광고 API: 연관 키워드 %d개 수신, 캐시 저장", len(raw))
    cfg = pipeline_config()["research"]
    cands = parse_keyword_list(raw)
    seen: set[str] = set()
    filtered = []
    for c in sorted(cands, key=lambda c: c.volume, reverse=True):
        if c.keyword in seen or c.volume < cfg["min_monthly_volume"]:
            continue
        seen.add(c.keyword); filtered.append(c)
    log.info("월 검색량 %d 이상 키워드 %d개", cfg["min_monthly_volume"], len(filtered))
    return filtered[: cfg["candidates_per_week"]]
