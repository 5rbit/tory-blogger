"""진입로(들머리)·진출로(날머리) 대중교통 — 국토교통부 TAGO 버스 API (공공데이터포털, serviceKey = DATA_GO_KR_KEY).
  정류소: BusSttnInfoInqireService/getCrdntPrxmtSttnList (좌표 반경 500m)
  경유노선: BusRouteInfoInqireService/getSttnThrghRouteList (cityCode, nodeid)
  노선정보: BusRouteInfoInqireService/getRouteInfoIem (cityCode, routeId) → 첫차·막차·배차(평일/토/일)
지하철·시외버스 등 API 밖 정보는 config/trailheads.yaml 의 transit_manual 에 사람이 적는다.
서울 권역(좌표 자동 판별 또는 city: seoul)은 seoul_bus.py 의 서울시 정류소·노선 API 를 쓴다.
"""
from __future__ import annotations
import json, time
from dataclasses import dataclass, field
from datetime import date
import requests
from src.common import CONFIG, DATA, env, get_logger, load_yaml
log = get_logger(__name__)

STN = "http://apis.data.go.kr/1613000/BusSttnInfoInqireService/getCrdntPrxmtSttnList"
THRU = "http://apis.data.go.kr/1613000/BusRouteInfoInqireService/getSttnThrghRouteList"
INFO = "http://apis.data.go.kr/1613000/BusRouteInfoInqireService/getRouteInfoIem"
_CACHE = DATA / "trails" / "transit_cache.json"

@dataclass
class RouteInfo:
    stop: str
    stop_no: str
    route_no: str
    route_type: str
    first: str          # HHMM
    last: str
    interval: str       # 평일 배차(분)
    interval_sat: str = ""
    interval_sun: str = ""
    origin: str = ""
    dest: str = ""
    source: str = "TAGO"

    @staticmethod
    def hhmm(v: str) -> str:
        v = str(v or "").strip()
        return f"{v[:2]}:{v[2:4]}" if len(v) >= 4 else v

def _items(r: requests.Response) -> list[dict]:
    if r.status_code != 200:
        raise RuntimeError(f"TAGO {r.status_code}: {r.text[:200]}")
    body = r.json().get("response", {}).get("body", {})
    it = (body.get("items") or {}).get("item") or []
    return it if isinstance(it, list) else [it]

def _p(**kw) -> dict:
    return {"serviceKey": env("DATA_GO_KR_KEY"), "_type": "json", "numOfRows": 50, "pageNo": 1, **kw}

def nearby_stops(lat: float, lon: float, session: requests.Session | None = None) -> list[dict]:
    s = session or requests.Session()
    return _items(s.get(STN, params=_p(gpsLati=lat, gpsLong=lon), timeout=20))

def routes_via_stop(city: str, node_id: str, session: requests.Session | None = None) -> list[dict]:
    s = session or requests.Session()
    return _items(s.get(THRU, params=_p(cityCode=city, nodeid=node_id), timeout=20))

def route_info(city: str, route_id: str, session: requests.Session | None = None) -> dict:
    s = session or requests.Session()
    it = _items(s.get(INFO, params=_p(cityCode=city, routeId=route_id), timeout=20))
    return it[0] if it else {}

def routes_near(lat: float, lon: float, max_stops: int = 3, dry_run: bool = False, session: requests.Session | None = None) -> list[RouteInfo]:
    """좌표 근처 정류소(가까운 순 max_stops개)를 지나는 모든 노선의 첫차·막차·배차. 결과는 캐시(주 단위)."""
    if dry_run or not env("DATA_GO_KR_KEY"):
        log.info("[dry-run] TAGO 생략")
        return [RouteInfo("(예시) 들머리 정류소", "12345", "120", "일반", "0430", "2300", "8", "10", "12", "기점", "종점")]
    key = f"{lat:.4f},{lon:.4f}:{date.today():%Y-W%V}"
    cache = json.loads(_CACHE.read_text()) if _CACHE.exists() else {}
    if key in cache:
        return [RouteInfo(**r) for r in cache[key]]
    out: list[RouteInfo] = []; seen: set[str] = set()
    for st in nearby_stops(lat, lon, session)[:max_stops]:
        city, node = str(st.get("citycode", "")), str(st.get("nodeid", ""))
        for rt in routes_via_stop(city, node, session):
            rid = str(rt.get("routeid", ""))
            if rid in seen:
                continue
            seen.add(rid); info = route_info(city, rid, session); time.sleep(0.1)
            out.append(RouteInfo(stop=st.get("nodenm", ""), stop_no=str(st.get("nodeno", "")), route_no=str(info.get("routeno") or rt.get("routeno", "")),
                                 route_type=str(info.get("routetp") or rt.get("routetp", "")), first=str(info.get("startvehicletime", "")),
                                 last=str(info.get("endvehicletime", "")), interval=str(info.get("intervaltime", "")),
                                 interval_sat=str(info.get("intervalsattime", "")), interval_sun=str(info.get("intervalsuntime", "")),
                                 origin=str(info.get("startnodenm", "")), dest=str(info.get("endnodenm", ""))))
    cache[key] = [r.__dict__ for r in out]
    _CACHE.parent.mkdir(parents=True, exist_ok=True); _CACHE.write_text(json.dumps(cache, ensure_ascii=False))
    log.info("TAGO: 정류소 %d개 노선 %d개", min(max_stops, len(out) and max_stops), len(out))
    return out

def manual_routes(trailhead: str) -> list[RouteInfo]:
    th = load_yaml(CONFIG / "trailheads.yaml").get(trailhead) or {}
    return [RouteInfo(stop=m.get("stop", ""), stop_no="", route_no=m.get("route", ""), route_type=m.get("type", "지하철"),
                      first=str(m.get("first", "")).replace(":", ""), last=str(m.get("last", "")).replace(":", ""),
                      interval=str(m.get("interval", "")), origin="", dest=m.get("note", ""), source="수동")
            for m in th.get("transit_manual", [])]

def transit_for(trailhead: str, dry_run: bool = False) -> list[RouteInfo]:
    """수동 항목 + (서울 권역이면 서울버스 API, 아니면 TAGO). 서울은 TAGO 에 없으므로 좌표로 자동 분기. 주 단위 캐시."""
    th = load_yaml(CONFIG / "trailheads.yaml").get(trailhead)
    if not th:
        log.warning("들머리 좌표 없음: %s", trailhead); return manual_routes(trailhead)
    lat, lon = th["lat"], th["lon"]
    from src.research import seoul_bus
    use_seoul = th.get("city") == "seoul" or (th.get("city") is None and seoul_bus.in_seoul(lat, lon))
    if dry_run or not env("DATA_GO_KR_KEY"):
        return manual_routes(trailhead) + routes_near(lat, lon, dry_run=True)
    if use_seoul:
        key = f"seoul:{lat:.4f},{lon:.4f}:{date.today():%Y-W%V}"
        cache = json.loads(_CACHE.read_text()) if _CACHE.exists() else {}
        if key not in cache:
            cache[key] = [r.__dict__ for r in seoul_bus.routes_near(lat, lon)]
            _CACHE.parent.mkdir(parents=True, exist_ok=True); _CACHE.write_text(json.dumps(cache, ensure_ascii=False))
        return manual_routes(trailhead) + [RouteInfo(**r) for r in cache[key]]
    return manual_routes(trailhead) + routes_near(lat, lon, dry_run=dry_run)

def to_markdown(entry: str, exit_: str | None, dry_run: bool = False, on_weekend: bool = True) -> str:
    def table(title: str, rows: list[RouteInfo]) -> str:
        col = "배차(토·일)" if on_weekend else "배차(평일)"
        lines = [f"### {title}", "| 정류장 | 노선 | 첫차 | 막차 | " + col + " | 비고 |", "|---|---|---|---|---|---|"]
        for r in sorted(rows, key=lambda r: (r.source != "수동", r.first)):
            iv = (r.interval_sat or r.interval_sun or r.interval) if on_weekend else r.interval
            note = f"{r.origin}→{r.dest}" if r.origin and r.dest else r.dest
            lines.append(f"| {r.stop} | {r.route_no} ({r.route_type}) | {r.hhmm(r.first)} | {r.hhmm(r.last)} | {iv}분 | {note} |")
        if len(rows) == 0:
            lines.append("| (정보 없음 — 수동 확인) | | | | | |")
        return "\n".join(lines)
    out = ["## 대중교통", table(f"진입로 · {entry}", transit_for(entry, dry_run))]
    if exit_ and exit_ != entry:
        out.append(table(f"진출로 · {exit_} (막차 기준으로 하산 시각을 잡으세요)", transit_for(exit_, dry_run)))
    out.append("*출처: 국토교통부 TAGO · 서울특별시 버스 정보 · 시간표는 변경될 수 있으니 출발 전 확인*")
    return "\n\n".join(out)
