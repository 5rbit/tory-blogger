"""서울 시내버스 — 서울특별시 정류소정보조회·노선정보조회 서비스 (공공데이터포털, serviceKey = DATA_GO_KR_KEY).
  좌표 근접 정류소: http://ws.bus.go.kr/api/rest/stationinfo/getStationByPos?tmX=경도&tmY=위도&radius=500
  정류소 경유 노선:  http://ws.bus.go.kr/api/rest/stationinfo/getRouteByStation?arsId=
  노선 상세:         http://ws.bus.go.kr/api/rest/busRouteInfo/getRouteInfo?busRouteId=  → firstBusTm, lastBusTm, term, stStationNm, edStationNm, routeType
resultType=json 으로 요청하면 {"msgBody": {"itemList": [...]}} 형태.
활용신청: 서울특별시_정류소정보조회 서비스, 서울특별시_노선정보조회 서비스 (각각).
"""
from __future__ import annotations
import time
import requests
from src.common import env, get_logger
from src.research.transit import RouteInfo
log = get_logger(__name__)

BASE = "http://ws.bus.go.kr/api/rest"
ROUTE_TYPE = {"0": "공용", "1": "공항", "2": "마을", "3": "간선", "4": "지선", "5": "순환", "6": "광역", "7": "인천", "8": "경기", "9": "폐지"}
SEOUL_BBOX = (37.42, 37.72, 126.76, 127.20)   # lat_min, lat_max, lon_min, lon_max

def in_seoul(lat: float, lon: float) -> bool:
    a, b, c, d = SEOUL_BBOX
    return a <= lat <= b and c <= lon <= d

def _items(r: requests.Response) -> list[dict]:
    if r.status_code != 200:
        raise RuntimeError(f"서울버스 API {r.status_code}: {r.text[:200]}")
    j = r.json()
    hdr = j.get("msgHeader", {})
    if str(hdr.get("headerCd", "0")) not in ("0", "4"):    # 4 = 결과 없음
        raise RuntimeError(f"서울버스 API 오류 {hdr.get('headerCd')}: {hdr.get('headerMsg')}")
    it = (j.get("msgBody") or {}).get("itemList") or []
    return it if isinstance(it, list) else [it]

def _p(**kw) -> dict:
    return {"serviceKey": env("DATA_GO_KR_KEY"), "resultType": "json", **kw}

def stations_near(lat: float, lon: float, radius: int = 500, session: requests.Session | None = None) -> list[dict]:
    s = session or requests.Session()
    return _items(s.get(f"{BASE}/stationinfo/getStationByPos", params=_p(tmX=lon, tmY=lat, radius=radius), timeout=20))

def routes_at(ars_id: str, session: requests.Session | None = None) -> list[dict]:
    s = session or requests.Session()
    return _items(s.get(f"{BASE}/stationinfo/getRouteByStation", params=_p(arsId=ars_id), timeout=20))

def route_detail(route_id: str, session: requests.Session | None = None) -> dict:
    s = session or requests.Session()
    it = _items(s.get(f"{BASE}/busRouteInfo/getRouteInfo", params=_p(busRouteId=route_id), timeout=20))
    return it[0] if it else {}

def routes_near(lat: float, lon: float, max_stops: int = 3, session: requests.Session | None = None) -> list[RouteInfo]:
    out: list[RouteInfo] = []; seen: set[str] = set()
    stops = sorted(stations_near(lat, lon, session=session), key=lambda s: float(s.get("dist", 0) or 0))[:max_stops]
    for st in stops:
        ars = str(st.get("arsId", "")).strip()
        if not ars or ars == "0":
            continue
        for rt in routes_at(ars, session):
            rid = str(rt.get("busRouteId", ""))
            if rid in seen:
                continue
            seen.add(rid); d = route_detail(rid, session); time.sleep(0.1)
            out.append(RouteInfo(stop=st.get("stationNm", ""), stop_no=ars, route_no=str(d.get("busRouteNm") or rt.get("busRouteNm", "")),
                                 route_type=ROUTE_TYPE.get(str(d.get("routeType") or rt.get("busRouteType", "")), ""),
                                 first=str(d.get("firstBusTm", ""))[8:12] if len(str(d.get("firstBusTm", ""))) >= 12 else str(d.get("firstBusTm", "")).replace(":", "")[:4],
                                 last=str(d.get("lastBusTm", ""))[8:12] if len(str(d.get("lastBusTm", ""))) >= 12 else str(d.get("lastBusTm", "")).replace(":", "")[:4],
                                 interval=str(d.get("term", "")), origin=str(d.get("stStationNm", "")), dest=str(d.get("edStationNm", "")), source="서울버스"))
    log.info("서울버스: 정류소 %d개 노선 %d개", len(stops), len(out))
    return out
