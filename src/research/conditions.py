"""발행 직전 현황 결합 — 날씨(기상청 단기예보), 단풍(연간 예측표), 탐방로 통제(수동 기록 + 확인 링크).
날씨: data.go.kr 기상청_단기예보 조회서비스 getVilageFcst (serviceKey = DATA_GO_KR_KEY). 3일 예보, 3시간 간격.
"""
from __future__ import annotations
import math
from datetime import date, datetime, timedelta
import requests
from src.common import CONFIG, env, get_logger, load_yaml
log = get_logger(__name__)

KMA_URL = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst"
SKY = {"1": "맑음", "3": "구름많음", "4": "흐림"}
PTY = {"0": "", "1": "비", "2": "비/눈", "3": "눈", "4": "소나기"}

# ---- 기상청 격자 변환 (Lambert Conformal Conic, 공식 상수) -----------------
def latlon_to_grid(lat: float, lon: float) -> tuple[int, int]:
    RE, GRID, SLAT1, SLAT2, OLON, OLAT, XO, YO = 6371.00877, 5.0, 30.0, 60.0, 126.0, 38.0, 43, 136
    re = RE / GRID
    slat1, slat2, olon, olat = map(math.radians, (SLAT1, SLAT2, OLON, OLAT))
    sn = math.tan(math.pi * 0.25 + slat2 * 0.5) / math.tan(math.pi * 0.25 + slat1 * 0.5)
    sn = math.log(math.cos(slat1) / math.cos(slat2)) / math.log(sn)
    sf = math.tan(math.pi * 0.25 + slat1 * 0.5) ** sn * math.cos(slat1) / sn
    ro = re * sf / math.tan(math.pi * 0.25 + olat * 0.5) ** sn
    ra = re * sf / math.tan(math.pi * 0.25 + math.radians(lat) * 0.5) ** sn
    theta = math.radians(lon) - olon
    theta = (theta + math.pi) % (2 * math.pi) - math.pi
    theta *= sn
    return int(ra * math.sin(theta) + XO + 0.5), int(ro - ra * math.cos(theta) + YO + 0.5)

def _base_datetime(now: datetime) -> tuple[str, str]:
    """단기예보는 02,05,08,11,14,17,20,23시 발표. 직전 발표 시각을 고른다 (발표 후 10분 여유)."""
    hours = [2, 5, 8, 11, 14, 17, 20, 23]
    t = now - timedelta(minutes=10)
    h = max([x for x in hours if x <= t.hour], default=None)
    if h is None:
        t -= timedelta(days=1); h = 23
    return t.strftime("%Y%m%d"), f"{h:02d}00"

def forecast(lat: float, lon: float, target: date, dry_run: bool = False) -> dict:
    """target 날짜의 06/09/12/15시 하늘·강수·기온·풍속 요약."""
    if dry_run or not env("DATA_GO_KR_KEY"):
        log.info("[dry-run] 기상청 예보 생략")
        return {"date": target.isoformat(), "slots": [], "summary": "(예보 미조회)"}
    nx, ny = latlon_to_grid(lat, lon)
    bd, bt = _base_datetime(datetime.now())
    params = {"serviceKey": env("DATA_GO_KR_KEY"), "numOfRows": 1000, "pageNo": 1, "dataType": "JSON",
              "base_date": bd, "base_time": bt, "nx": nx, "ny": ny}
    r = requests.get(KMA_URL, params=params, timeout=20)
    if r.status_code != 200:
        raise RuntimeError(f"기상청 API {r.status_code}: {r.text[:200]}")
    items = r.json()["response"]["body"]["items"]["item"]
    day = target.strftime("%Y%m%d")
    by_time: dict[str, dict] = {}
    for it in items:
        if it["fcstDate"] == day:
            by_time.setdefault(it["fcstTime"], {})[it["category"]] = it["fcstValue"]
    slots = []
    for t in ["0600", "0900", "1200", "1500"]:
        v = by_time.get(t)
        if v:
            slots.append({"time": t[:2] + "시", "sky": PTY.get(v.get("PTY", "0")) or SKY.get(v.get("SKY", ""), ""),
                          "temp": v.get("TMP"), "pop": v.get("POP"), "wind": v.get("WSD")})
    summary = ", ".join(f"{s['time']} {s['sky']} {s['temp']}℃ 강수 {s['pop']}%" for s in slots) or "(해당 날짜 예보 없음: 3일 이내만 조회 가능)"
    return {"date": target.isoformat(), "slots": slots, "summary": summary, "grid": (nx, ny)}

# ---- 단풍 -----------------------------------------------------------------
def foliage_status(mountain: str, on: date) -> str | None:
    cfg = load_yaml(CONFIG / "foliage.yaml")
    m = next((v for k, v in cfg.get("mountains", {}).items() if k in mountain or mountain in k), None)
    if not m:
        return None
    first, peak = date.fromisoformat(str(m["first"])), date.fromisoformat(str(m["peak"]))
    d = (peak - on).days
    if on < first:
        return f"첫 단풍 예상 {first:%m/%d}, 절정 {peak:%m/%d} (아직 {(first - on).days}일 전)"
    if d > 3:
        return f"단풍 진행 중, 절정 {peak:%m/%d} 까지 {d}일"
    if d >= -3:
        return f"단풍 절정 시기 ({peak:%m/%d} 전후)"
    return f"절정({peak:%m/%d}) 지남, 낙엽 진행"

# ---- 통제 -----------------------------------------------------------------
def closures_for(park: str, on: date) -> tuple[list[dict], list[str]]:
    cfg = load_yaml(CONFIG / "closures.yaml")
    hits = [c for c in cfg.get("closures") or [] if c.get("park") == park and date.fromisoformat(str(c["until"])) >= on]
    return hits, cfg.get("check_urls", [])

# ---- 초안에 넣을 블록 --------------------------------------------------------
def conditions_block(trailhead: str, mountain: str, target: date, dry_run: bool = False) -> str:
    th = load_yaml(CONFIG / "trailheads.yaml").get(trailhead)
    lines = [f"## 이번 주말 현황 ({target:%m/%d} 기준)"]
    if th:
        fc = forecast(th["lat"], th["lon"], target, dry_run)
        lines.append(f"- 날씨({trailhead}): {fc['summary']}")
        park = th.get("park") or mountain
    else:
        lines.append(f"- 날씨: (들머리 좌표 미등록: config/trailheads.yaml 에 '{trailhead}' 추가)")
        park = mountain
    fs = foliage_status(mountain, target)
    if fs:
        lines.append(f"- 단풍: {fs}")
    hits, urls = closures_for(park, target)
    if hits:
        lines += [f"- ⚠️ 통제: {c['trail']} ({c['reason']}, {c['until']} 까지)" for c in hits]
    else:
        lines.append("- 통제: 기록된 통제 없음. 발행 전 확인 → " + (urls[0] if urls else ""))
    return "\n".join(lines)
