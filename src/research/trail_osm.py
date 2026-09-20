"""OpenStreetMap 등산로로 코스 자동 생성 — 들머리 좌표 → 정상(natural=peak) 최단 경로 (Dijkstra).
산림청 파일이 없을 때의 대안. 출처 표기 필수: © OpenStreetMap contributors (ODbL). 결과는 주 단위 캐시.
"""
from __future__ import annotations
import heapq, json, math
from datetime import date
import requests
from src.common import CONFIG, DATA, get_logger, load_yaml
from src.media.course_viz import Course, Segment, haversine_km, path_length_km
log = get_logger(__name__)

OVERPASS = ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter"]
HEADERS = {"User-Agent": "tory-blogger/0.1 (hiking course viz)", "Content-Type": "text/plain; charset=utf-8"}
WAY_TYPES = "path|footway|track|steps|bridleway|unclassified|service|residential|living_street|pedestrian"
ATTRIBUTION = "© OpenStreetMap contributors (ODbL)"
_CACHE = DATA / "trails" / "osm_cache.json"

def _query(q: str) -> dict:
    last = None
    for url in OVERPASS:
        try:
            r = requests.post(url, data=q.encode("utf-8"), headers=HEADERS, timeout=240)
            if r.status_code == 200:
                return r.json()
            last = f"{url} {r.status_code}"
        except requests.RequestException as e:
            last = str(e)
    raise RuntimeError(f"Overpass 실패: {last}")

def find_peak(mountain: str, near: tuple[float, float] | None = None, radius_km: float = 8) -> dict | None:
    """natural=peak 중 이름이 맞는 것. 여러 개면 가장 높은 것(ele) 또는 near 에 가까운 것."""
    if near:
        lat, lon = near; d = radius_km / 111.0
        area = f"({lat - d},{lon - d},{lat + d},{lon + d})"
    else:
        area = "(33,124,39,132)"
    js = _query(f'[out:json][timeout:60];node["natural"="peak"]["name"~"{mountain}"]{area};out;')
    els = js.get("elements", [])
    if not els:
        return None
    def ele(e):
        try: return float(str(e["tags"].get("ele", "0")).replace("m", ""))
        except ValueError: return 0.0
    els.sort(key=lambda e: (-ele(e), haversine_km((e["lon"], e["lat"]), (near[1], near[0])) if near else 0))
    return els[0]

def fetch_ways(bbox: tuple[float, float, float, float]) -> list[dict]:
    s, w, n, e = bbox
    js = _query(f'[out:json][timeout:200];way["highway"~"^({WAY_TYPES})$"]({s},{w},{n},{e});out geom;')
    return js.get("elements", [])

def _snap(graph_nodes: dict, pt: tuple[float, float]) -> int:
    return min(graph_nodes, key=lambda k: haversine_km(graph_nodes[k], pt))

def shortest_path(ways: list[dict], start: tuple[float, float], goal: tuple[float, float]) -> tuple[list[tuple[float, float]], list[dict]]:
    """way 들로 그래프 → Dijkstra. 반환: (좌표열 (lon,lat), 지나간 way 태그 목록)."""
    nodes: dict[int, tuple[float, float]] = {}; adj: dict[int, list[tuple[int, float, int]]] = {}
    for w in ways:
        ids = w.get("nodes", []); geom = w.get("geometry", [])
        for nid, g in zip(ids, geom):
            nodes[nid] = (g["lon"], g["lat"])
        for a, b in zip(ids, ids[1:]):
            d = haversine_km(nodes[a], nodes[b]); adj.setdefault(a, []).append((b, d, w["id"])); adj.setdefault(b, []).append((a, d, w["id"]))
    if not nodes:
        raise RuntimeError("경로 데이터 없음")
    s, g = _snap(nodes, start), _snap(nodes, goal)
    dist = {s: 0.0}; prev: dict[int, tuple[int, int]] = {}; pq = [(0.0, s)]
    while pq:
        d, u = heapq.heappop(pq)
        if u == g: break
        if d > dist.get(u, 1e18): continue
        for v, wgt, wid in adj.get(u, []):
            nd = d + wgt
            if nd < dist.get(v, 1e18):
                dist[v] = nd; prev[v] = (u, wid); heapq.heappush(pq, (nd, v))
    if g not in dist:
        raise RuntimeError("들머리에서 정상까지 연결된 등산로를 찾지 못함")
    path, wids = [g], []
    while path[-1] != s:
        u, wid = prev[path[-1]]; path.append(u); wids.append(wid)
    path.reverse(); wids.reverse()
    by_id = {w["id"]: w for w in ways}
    return [nodes[n] for n in path], [by_id[w].get("tags", {}) for w in wids]

def naismith_min(length_km: float, gain_m: float) -> int:
    """소요시간 근사: 12분/km + 10분/100m 상승."""
    return int(round(length_km * 12 + gain_m / 100 * 10))

def build_course(mountain: str, trailhead: str, n_segments: int = 3, margin_km: float = 0.8) -> Course:
    """설정의 들머리 좌표에서 OSM 정상까지 경로를 찾아 Course 로. 구간은 거리 기준 n 등분, 이름은 '들머리→구간k→정상'."""
    th = load_yaml(CONFIG / "trailheads.yaml").get(trailhead)
    if not th:
        raise RuntimeError(f"config/trailheads.yaml 에 '{trailhead}' 가 없습니다")
    key = f"{mountain}|{trailhead}|{date.today():%Y-W%V}"
    cache = json.loads(_CACHE.read_text()) if _CACHE.exists() else {}
    if key not in cache:
        peak = find_peak(mountain, near=(th["lat"], th["lon"]))
        if not peak:
            raise RuntimeError(f"OSM 에서 '{mountain}' 봉우리를 찾지 못함")
        s, n = sorted([th["lat"], peak["lat"]]); w, e = sorted([th["lon"], peak["lon"]])
        d = margin_km / 111.0; ways = fetch_ways((s - d, w - d, n + d, e + d))
        coords, tags = shortest_path(ways, (th["lon"], th["lat"]), (peak["lon"], peak["lat"]))
        cache[key] = {"peak": {"name": peak["tags"].get("name", mountain), "lat": peak["lat"], "lon": peak["lon"], "ele": peak["tags"].get("ele")},
                      "coords": coords, "context": [[(g["lon"], g["lat"]) for g in wy.get("geometry", [])] for wy in ways if wy.get("tags", {}).get("highway") in ("path", "footway", "track", "steps")][:400]}
        _CACHE.parent.mkdir(parents=True, exist_ok=True); _CACHE.write_text(json.dumps(cache, ensure_ascii=False))
        log.info("OSM 경로: %s → %s (%s), 점 %d개, 주변 way %d개", trailhead, cache[key]["peak"]["name"], peak["tags"].get("ele", "?"), len(coords), len(ways))
    c = cache[key]; coords = [tuple(p) for p in c["coords"]]; total = path_length_km(coords)
    # 거리 기준 n 등분
    cum = [0.0]
    for i in range(1, len(coords)): cum.append(cum[-1] + haversine_km(coords[i - 1], coords[i]))
    cuts = [0] + [next(i for i, v in enumerate(cum) if v >= total * k / n_segments) for k in range(1, n_segments)] + [len(coords) - 1]
    names = [trailhead.split(" ", 1)[-1]] + [f"{k}/{n_segments} 지점" for k in range(1, n_segments)] + [c["peak"]["name"]]
    segs = []
    for k in range(n_segments):
        sc = coords[cuts[k]:cuts[k + 1] + 1]
        segs.append(Segment(name=f"{names[k]} → {names[k + 1]}", coords=sc, length_km=round(path_length_km(sc), 2)))
    course = Course(mountain, segs, context_lines=[[tuple(p) for p in line] for line in c["context"]])
    course.source = ATTRIBUTION
    return course

def fill_times(course: Course) -> None:
    """고도가 채워진 뒤 호출: 구간별 상행·하행 시간과 난이도(경사)."""
    for s in course.segments:
        gain = sum(max(0, s.elev[i + 1] - s.elev[i]) for i in range(len(s.elev) - 1)) if s.elev else 0
        s.up_min = naismith_min(s.length_km, gain); s.down_min = int(s.up_min * 0.7)
        grade = gain / max(s.length_km * 1000, 1) * 100
        s.difficulty = "쉬움" if grade < 8 else "보통" if grade < 15 else "어려움" if grade < 25 else "매우어려움"
