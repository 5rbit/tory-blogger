"""한국관광공사 포토코리아 관광사진 API — 공공누리 1유형(출처 표기, 변경·상업 이용 허용) 사진 검색.
공공데이터포털 '한국관광공사_관광사진 정보_GW' (serviceKey = DATA_GO_KR_KEY, 개발계정 일 1,000회)
  검색: GET https://apis.data.go.kr/B551011/PhotoService1/gallerySearchList1?keyword=...
  응답: galContentId, galTitle, galWebImageUrl, galPhotographer, galPhotographyLocation, galPhotographyMonth, galSearchKeyword
주의: 관광정보 서비스(KorService2)의 관광지 사진은 3유형(변경 금지)이므로 AI 보정 대상에서 제외한다.
"""
from __future__ import annotations
import re
from dataclasses import dataclass
import requests
from src.common import env, get_logger
log = get_logger(__name__)

BASE = "https://apis.data.go.kr/B551011/PhotoService1"
SEARCH_OP = "gallerySearchList1"
ATTRIBUTION = "사진: 한국관광공사 포토코리아 · {photographer} (공공누리 1유형)"

@dataclass
class Photo:
    id: str
    title: str
    url: str
    photographer: str
    location: str
    month: str          # "YYYYMM"
    keywords: str

    def markdown(self, alt: str | None = None) -> str:
        cap = ATTRIBUTION.format(photographer=self.photographer or "촬영자 미상")
        return f"![{alt or self.title}]({self.url})\n*{cap}*"

def _params(**kw) -> dict:
    return {"serviceKey": env("DATA_GO_KR_KEY"), "MobileOS": "ETC", "MobileApp": "tory-blogger", "_type": "json",
            "numOfRows": 20, "pageNo": 1, "arrange": "A", **kw}

def parse_items(items: list[dict]) -> list[Photo]:
    return [Photo(id=str(i.get("galContentId", "")), title=i.get("galTitle", ""), url=i.get("galWebImageUrl", ""),
                  photographer=i.get("galPhotographer", ""), location=i.get("galPhotographyLocation", ""),
                  month=str(i.get("galPhotographyMonth", "")), keywords=i.get("galSearchKeyword", ""))
            for i in items if i.get("galWebImageUrl")]

def search(keyword: str, month: int | None = None, limit: int = 8, dry_run: bool = False,
           session: requests.Session | None = None) -> list[Photo]:
    """키워드(산 이름 등)로 검색. month 가 주어지면 같은 달(±1) 촬영분을 우선 정렬한다 ('이맘때' 사진)."""
    if dry_run or not env("DATA_GO_KR_KEY"):
        log.info("[dry-run] 포토코리아 검색 생략: %s", keyword)
        return [Photo(id=f"demo{i}", title=f"{keyword} 예시 {i+1}", url=f"https://example.com/{keyword}{i}.jpg",
                      photographer="한국관광공사", location=keyword, month="202510", keywords=keyword) for i in range(min(limit, 3))]
    s = session or requests.Session()
    r = s.get(f"{BASE}/{SEARCH_OP}", params=_params(keyword=keyword), timeout=20)
    if r.status_code != 200:
        raise RuntimeError(f"포토코리아 API {r.status_code}: {r.text[:200]}")
    body = r.json().get("response", {}).get("body", {})
    items = (body.get("items") or {}).get("item") or []
    photos = parse_items(items if isinstance(items, list) else [items])
    if month:
        def dist(p: Photo) -> int:
            try:
                m = int(p.month[-2:]); return min(abs(m - month), 12 - abs(m - month))
            except ValueError:
                return 12
        photos.sort(key=dist)
    log.info("포토코리아 '%s': %d장", keyword, len(photos))
    return photos[:limit]

SLOT = re.compile(r"^\[사진: ?(.*?)\]\s*$", re.M)

def fill_slots(markdown: str, photos: list[Photo]) -> tuple[str, int]:
    """[사진: 설명] 슬롯을 순서대로 실제 이미지+출처 캡션으로 바꾼다. 사진이 모자라면 남은 슬롯은 그대로 둔다."""
    it = iter(photos); n = 0
    def rep(m: re.Match) -> str:
        nonlocal n
        p = next(it, None)
        if p is None:
            return m.group(0)
        n += 1
        return p.markdown(alt=m.group(1) or p.title)
    return SLOT.sub(rep, markdown), n
