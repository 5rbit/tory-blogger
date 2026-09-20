"""등산 코스 표현 자산 — 등산로 표준데이터(파일) → 고도 프로파일 / 구간 타임라인 표 / 난이도 레이더 / 요약 카드.

데이터: 산림청 '등산로정보' (전국등산로표준데이터) 를 GeoJSON(또는 GPX) 으로 받아 data/trails/ 에 둔다.
  https://www.forest.go.kr/kfsweb/kfi/kfs/trail/trailInformation.do?pblicDataId=PBD0000041&mn=NKFS_06_08_02
  SHP 는 QGIS/ogr2ogr 로 GeoJSON 변환: ogr2ogr -f GeoJSON -t_srs EPSG:4326 out.geojson in.shp
고도: open-elevation 공개 API (캐시). 파일에 고도(ele/z)가 있으면 그것을 쓴다.
"""
from __future__ import annotations
import json, math, re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
import requests
from src.common import CONFIG, data_dir, DATA, get_logger, load_yaml
from src.emoji import E, difficulty_emoji, boots
log = get_logger(__name__)

FIELD_MAP = {  # 산림청 등산로 SHP 속성명 → 내부 이름 (다른 출처는 config/trail_fields.yaml 로 덮어쓸 수 있음)
    "mountain": ["PMNTN_NM", "mntn_nm", "산이름", "name"],
    "segment": ["PMNTN_MTRQ", "PMNTN_SN", "구간명", "segment"],
    "length_km": ["PMNTN_LT", "등산로길이", "length"],
    "up_min": ["PMNTN_UPPL", "상행시간", "up_min"],
    "down_min": ["PMNTN_GODN", "하행시간", "down_min"],
    "difficulty": ["PMNTN_DFFL", "난이도", "difficulty"],
}

@dataclass
class Segment:
    name: str
    coords: list[tuple[float, float]]           # (lon, lat)
    length_km: float = 0.0
    up_min: int = 0
    down_min: int = 0
    difficulty: str = ""
    elev: list[float] = field(default_factory=list)

@dataclass
class Course:
    mountain: str
    segments: list[Segment]
    context_lines: list[list[tuple[float, float]]] = field(default_factory=list)   # 미니맵용 주변 등산로

    @property
    def points(self) -> list[tuple[float, float]]:
        pts: list[tuple[float, float]] = []
        for s in self.segments:
            pts += s.coords if not pts or pts[-1] != s.coords[0] else s.coords[1:]
        return pts

    @property
    def length_km(self) -> float:
        return sum(s.length_km or path_length_km(s.coords) for s in self.segments)

    @property
    def up_min(self) -> int:
        return sum(s.up_min for s in self.segments)

# ---- 기하 -------------------------------------------------------------------
def haversine_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    R = 6371.0088
    lon1, lat1, lon2, lat2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))

def path_length_km(coords: list[tuple[float, float]]) -> float:
    return sum(haversine_km(coords[i], coords[i + 1]) for i in range(len(coords) - 1))

def cumulative_km(coords: list[tuple[float, float]]) -> list[float]:
    out = [0.0]
    for i in range(1, len(coords)):
        out.append(out[-1] + haversine_km(coords[i - 1], coords[i]))
    return out

def resample(coords: list[tuple[float, float]], n: int = 60) -> list[tuple[float, float]]:
    if len(coords) <= n:
        return coords
    step = (len(coords) - 1) / (n - 1)
    return [coords[round(i * step)] for i in range(n)]

# ---- 데이터 로드 ---------------------------------------------------------------
def _get(props: dict, key: str):
    for k in FIELD_MAP[key]:
        if k in props and props[k] not in (None, ""):
            return props[k]
    return None

def _num(v, default=0.0) -> float:
    try:
        return float(str(v).replace(",", ""))
    except (TypeError, ValueError):
        return default

def load_geojson(path: Path) -> list[Segment]:
    gj = json.loads(path.read_text(encoding="utf-8"))
    segs = []
    for f in gj.get("features", []):
        g, p = f.get("geometry") or {}, f.get("properties") or {}
        lines = [g["coordinates"]] if g.get("type") == "LineString" else g.get("coordinates", []) if g.get("type") == "MultiLineString" else []
        for line in lines:
            coords = [(float(c[0]), float(c[1])) for c in line]
            elev = [float(c[2]) for c in line] if all(len(c) > 2 for c in line) else []
            segs.append(Segment(name=str(_get(p, "segment") or _get(p, "mountain") or path.stem), coords=coords,
                                length_km=_num(_get(p, "length_km")), up_min=int(_num(_get(p, "up_min"))),
                                down_min=int(_num(_get(p, "down_min"))), difficulty=str(_get(p, "difficulty") or ""), elev=elev,
                                ))
            segs[-1].__dict__["mountain"] = str(_get(p, "mountain") or "")
    return segs

def load_gpx(path: Path) -> list[Segment]:
    import xml.etree.ElementTree as ET
    ns = {"g": "http://www.topografix.com/GPX/1/1"}
    root = ET.parse(path).getroot()
    segs = []
    for trk in root.findall("g:trk", ns) or root.findall("trk"):
        name = (trk.findtext("g:name", default=path.stem, namespaces=ns) or path.stem)
        for seg in trk.findall(".//g:trkseg", ns) or trk.findall(".//trkseg"):
            pts = seg.findall("g:trkpt", ns) or seg.findall("trkpt")
            coords = [(float(p.get("lon")), float(p.get("lat"))) for p in pts]
            elev = [float(p.findtext("g:ele", default="nan", namespaces=ns)) for p in pts]
            elev = [] if any(math.isnan(e) for e in elev) else elev
            s = Segment(name=name, coords=coords, elev=elev); s.__dict__["mountain"] = name; segs.append(s)
    return segs

def find_course(mountain: str, segment_filter: list[str] | None = None, trails_dir: Path | None = None) -> Course | None:
    """data/trails/ 의 GeoJSON·GPX 에서 산 이름이 맞는 구간을 모은다. segment_filter 가 있으면 그 이름 순서대로."""
    d = trails_dir or (DATA / "trails")
    segs: list[Segment] = []
    for p in sorted(d.glob("*")):
        if p.suffix.lower() == ".geojson" or p.suffix.lower() == ".json":
            segs += load_geojson(p)
        elif p.suffix.lower() == ".gpx":
            segs += load_gpx(p)
    segs = [s for s in segs if mountain in (s.__dict__.get("mountain") or "") or mountain in s.name or mountain in Path(str(s.name)).stem]
    all_lines = [s.coords for s in segs]
    if segment_filter:
        chosen = [next((s for s in segs if f in s.name), None) for f in segment_filter]
        segs = [s for s in chosen if s]
    return Course(mountain, segs, context_lines=all_lines) if segs else None

def sample_course() -> Course:
    """파일이 없을 때 검증용: 북한산 우이동→백운대 형태의 가상 코스 (좌표·고도 근사)."""
    def seg(name, a, b, n, e0, e1, km, up, diff, wiggle=0.0012):
        coords = [(a[0] + (b[0] - a[0]) * i / n + wiggle * math.sin(i * 1.7), a[1] + (b[1] - a[1]) * i / n + wiggle * 0.6 * math.cos(i * 1.3)) for i in range(n + 1)]
        elev = [e0 + (e1 - e0) * (i / n) ** 1.3 for i in range(n + 1)]
        return Segment(name, coords, km, up, int(up * 0.7), diff, elev)
    c = Course("북한산(샘플)", [
        seg("우이동 → 도선사", (127.0129, 37.6625), (127.0040, 37.6580), 12, 120, 290, 1.8, 35, "쉬움"),
        seg("도선사 → 백운봉암문", (127.0040, 37.6580), (126.9930, 37.6605), 14, 290, 720, 1.6, 65, "보통"),
        seg("백운봉암문 → 백운대", (126.9930, 37.6605), (126.9898, 37.6612), 6, 720, 836, 0.4, 20, "어려움"),
    ])
    c.context_lines = [[(126.9898, 37.6612), (126.9850, 37.6560), (126.9800, 37.6500)], [(127.0040, 37.6580), (127.0080, 37.6520), (127.0110, 37.6470)],
                       [(126.9930, 37.6605), (126.9960, 37.6660), (127.0010, 37.6700)]]
    return c

# ---- 고도 ------------------------------------------------------------------------
_CACHE = DATA / "trails" / "elevation_cache.json"

def fetch_elevation(coords: list[tuple[float, float]], dry_run: bool = False) -> list[float]:
    cache = json.loads(_CACHE.read_text()) if _CACHE.exists() else {}
    keys = [f"{lat:.5f},{lon:.5f}" for lon, lat in coords]
    missing = [k for k in keys if k not in cache]
    if missing and not dry_run:
        r = requests.post("https://api.open-elevation.com/api/v1/lookup", timeout=60,
                          json={"locations": [{"latitude": float(k.split(",")[0]), "longitude": float(k.split(",")[1])} for k in missing]})
        if r.status_code == 200:
            for k, res in zip(missing, r.json().get("results", [])):
                cache[k] = res.get("elevation")
            _CACHE.parent.mkdir(parents=True, exist_ok=True); _CACHE.write_text(json.dumps(cache))
        else:
            log.warning("고도 API %s — 고도 없이 진행", r.status_code)
    return [float(cache.get(k) or 0.0) for k in keys]

def ensure_elevation(course: Course, dry_run: bool = False) -> None:
    for s in course.segments:
        if not s.elev or len(s.elev) != len(s.coords):
            pts = resample(s.coords, 40)
            e = fetch_elevation(pts, dry_run)
            # 리샘플 지점 고도를 원 좌표 수에 맞게 선형 보간
            n = len(s.coords)
            s.elev = [e[min(int(i * (len(e) - 1) / max(n - 1, 1) + 0.5), len(e) - 1)] for i in range(n)]

# ---- 1. 고도 프로파일 -----------------------------------------------------------------
def _font():
    import matplotlib
    from matplotlib import font_manager
    names = {f.name.lower().replace(" ", ""): f.name for f in font_manager.fontManager.ttflist}
    for want in ["applesdgothicneo", "applegothic", "nanumgothic", "malgungothic", "notosanscjkkr"]:
        if want in names:
            matplotlib.rcParams["font.family"] = names[want]; break
    matplotlib.rcParams["axes.unicode_minus"] = False

def elevation_profile(course: Course, out: Path, title: str | None = None) -> Path:
    import matplotlib; matplotlib.use("Agg"); _font()
    import matplotlib.pyplot as plt
    pts, elev, marks = [], [], []
    for s in course.segments:
        start = len(pts)
        pts += s.coords if not pts else s.coords[1:]
        elev += s.elev if not elev else s.elev[1:]
        marks.append((start, s.name.split("→")[0].strip()))
    marks.append((len(pts) - 1, course.segments[-1].name.split("→")[-1].strip()))
    x = cumulative_km(pts)
    fig, ax = plt.subplots(figsize=(10, 4), dpi=150)
    from src.media.design import tokens as _tk
    C = _tk()["color"]
    ax.fill_between(x, elev, min(elev) - 30, color=C["chart_fill"], alpha=0.35)
    ax.plot(x, elev, color=C["chart_line"], lw=2)
    for i, name in marks:
        ax.annotate(name, (x[i], elev[i]), textcoords="offset points", xytext=(0, 10), ha="center", fontsize=9)
        ax.plot(x[i], elev[i], "o", color=C["chart_point"], ms=5)
    gain = sum(max(0, elev[i + 1] - elev[i]) for i in range(len(elev) - 1))
    ax.set_xlabel("거리 (km)"); ax.set_ylabel("고도 (m)"); ax.grid(alpha=0.3)
    fig.tight_layout(); out.parent.mkdir(parents=True, exist_ok=True); fig.savefig(out); plt.close(fig)
    from src.media.design import add_title_band
    return add_title_band(out, [("icon", "mountain"), course.mountain, "·", ("icon", "trending_up"), "고도 프로파일", "·", ("icon", "ruler"), f"{x[-1]:.1f} km · 누적 상승 {gain:.0f} m"] if not title else [title])

# ---- 4. 구간 타임라인 표 ---------------------------------------------------------------
def timeline_table(course: Course, start: str = "09:00", lunch_min: int = 30) -> str:
    t = datetime.strptime(start, "%H:%M"); km = 0.0
    rows = [f"| {E['time']} 시각 | 지점 | {E['distance']} 누적 | 구간 소요 | 💪 난이도 |", "|---|---|---|---|---|",
            f"| {t:%H:%M} | {E['start']} {course.segments[0].name.split('→')[0].strip()} (출발) | 0.0 km | - | - |"]
    last = len(course.segments) - 1
    for i, s in enumerate(course.segments):
        km += s.length_km or path_length_km(s.coords); t += timedelta(minutes=s.up_min)
        icon = E["peak"] if i == last else "📍"
        rows.append(f"| {t:%H:%M} | {icon} {s.name.split('→')[-1].strip()} | {km:.1f} km | {s.up_min}분 | {difficulty_emoji(s.difficulty or None)} |")
    t += timedelta(minutes=lunch_min); rows.append(f"| {t:%H:%M} | {E['lunch']} 정상 휴식·점심 {lunch_min}분 | | | |")
    for i, s in enumerate(reversed(course.segments)):
        km += s.length_km or path_length_km(s.coords); t += timedelta(minutes=s.down_min or int(s.up_min * 0.7))
        icon = E["finish"] if i == last else "📍"
        rows.append(f"| {t:%H:%M} | {icon} {s.name.split('→')[0].strip()} (하산) | {km:.1f} km | {s.down_min or int(s.up_min*0.7)}분 | |")
    return "\n".join(rows)

# ---- 5. 난이도 레이더 -----------------------------------------------------------------
AXES = ["거리", "고도차", "경사", "기술", "접근성", "조망"]
from src.emoji import _LABEL_TO_LEVEL as TECH

def difficulty_scores(course: Course, access: int = 3, view: int = 4) -> dict[str, int]:
    """1~5 점수. 거리/고도차/경사/기술(구간 난이도 최댓값)은 데이터로, 접근성·조망은 사람이 준다."""
    km = course.length_km * 2
    elev = [e for s in course.segments for e in s.elev]
    gain = (max(elev) - min(elev)) if elev else 0
    slope = gain / max(course.length_km * 1000, 1) * 100
    def band(v, cuts): return 1 + sum(v > c for c in cuts)
    tech = max((TECH.get(s.difficulty.replace(" ", ""), 0) for s in course.segments), default=0) or band(slope, [8, 12, 16, 20])
    return {"거리": band(km, [6, 10, 14, 18]), "고도차": band(gain, [300, 500, 700, 900]),
            "경사": band(slope, [8, 12, 16, 20]), "기술": tech, "접근성": max(1, min(5, access)), "조망": max(1, min(5, view))}

def radar_chart(scores: dict[str, dict[str, int]], out: Path, title: str = "난이도 비교") -> Path:
    """{코스명: {축: 점수}} 여러 코스를 겹쳐 그린다."""
    import matplotlib; matplotlib.use("Agg"); _font()
    import matplotlib.pyplot as plt
    ang = [n / len(AXES) * 2 * math.pi for n in range(len(AXES))] + [0]
    fig = plt.figure(figsize=(5.5, 5.5), dpi=150); ax = plt.subplot(111, polar=True)
    for (name, sc), color in zip(scores.items(), ["#2f5d3a", "#c0392b", "#2980b9", "#8e44ad", "#d35400"]):
        vals = [sc[a] for a in AXES] + [sc[AXES[0]]]
        ax.plot(ang, vals, color=color, lw=2, label=name); ax.fill(ang, vals, color=color, alpha=0.15)
    ax.set_xticks(ang[:-1]); ax.set_xticklabels(AXES, fontsize=11); ax.set_ylim(0, 5); ax.set_yticks([1, 2, 3, 4, 5])
    ax.legend(loc="lower right", bbox_to_anchor=(1.15, -0.1), fontsize=9)
    fig.tight_layout(); out.parent.mkdir(parents=True, exist_ok=True); fig.savefig(out); plt.close(fig)
    from src.media.design import add_title_band
    return add_title_band(out, [("icon", "gauge"), title])

# ---- 6. 요약 카드 (디자인 토큰 + 자체 아이콘, 이모지 없음) ------------------------------
def summary_card(course: Course, out: Path, subtitle: str = "", season_note: str = "", size: int = 1080) -> Path:
    from PIL import Image, ImageDraw
    from src.media.design import tokens, font, draw_row, level_icons
    from src.emoji import _LABEL_TO_LEVEL, LEVEL_NAME
    T = tokens(); C, F, S = T["color"], T["font"], T["space"]; m = S["margin"]
    img = Image.new("RGB", (size, size), C["bg"]); d = ImageDraw.Draw(img)
    d.rectangle([0, 0, size, 14], fill=C["accent"])
    from src.media.design import pin
    draw_row(img, (m, 90), [("icon", "mountain"), course.mountain], F["title"], C["text"])
    # 경로 띠: 핀 아이콘(깃발→핀→산)을 선으로 잇고 아래에 지점 이름
    names = [s.name.split("→")[0].strip() for s in course.segments] + [course.segments[-1].name.split("→")[-1].strip()]
    if subtitle:
        d.text((m, 210), subtitle, font=font("subtitle"), fill=C["muted"])
    else:
        n = len(names); ph = 56; y0 = 215; x_left, x_right = m + 30, size - m - 30
        xs = [x_left + (x_right - x_left) * i / max(n - 1, 1) for i in range(n)]
        d.line([(xs[0], y0 + ph), (xs[-1], y0 + ph)], fill=C["muted"], width=4)
        lab = font(28)
        for i, (xc, name) in enumerate(zip(xs, names)):
            ic, fg = ("flag", "#2980B9") if i == 0 else (("mountain", C["chart_point"]) if i == n - 1 else ("pin", C["accent"]))
            pn = pin(ic, ph, fg, bg=C["bg"]); img.paste(pn, (int(xc - pn.width / 2), y0), pn)
            tw = d.textlength(name, font=lab); tx = min(max(xc - tw / 2, m), size - m - tw)
            d.text((tx, y0 + ph + 12), name, font=lab, fill=C["muted"])
    elev = [e for s in course.segments for e in s.elev]
    gain = f"{max(elev) - min(elev):.0f} m" if elev else "-"
    lvl = max((_LABEL_TO_LEVEL.get(s.difficulty.replace(" ", ""), 0) for s in course.segments), default=0) or 3
    rows = [("ruler", "거리(왕복)", f"{course.length_km * 2:.1f} km"), ("timer", "소요(상행)", f"{course.up_min // 60}시간 {course.up_min % 60}분"),
            ("trending_up", "고도차", gain), ("gauge", "난이도", LEVEL_NAME[lvl])]
    y = 360
    for ic, label, val in rows:
        d.rounded_rectangle([m, y, size - m, y + S["panel_h"]], radius=S["radius"], fill=C["panel"])
        draw_row(img, (m + 30, y + 38), [("icon", ic), label], F["label"], C["muted"])
        if ic == "gauge":
            w = level_icons(img, (size - m - 30, y + 34), lvl, F["value"], C.get("flame", C["accent"]), C["muted"], align="right")
            draw_row(img, (size - m - 30 - w - 24, y + 34), [val], F["value"], C["text"], align="right")
        else:
            draw_row(img, (size - m - 30, y + 30), [val], F["value"], C["text"], align="right")
        y += S["panel_h"] + S["panel_gap"]
    if season_note:
        draw_row(img, (m, y + 20), [("icon", "leaf"), season_note], F["season"], C["accent"])
    d.text((m, size - 80), "코스 데이터: 산림청 등산로정보 · 자세한 코스는 본문에서", font=font("caption"), fill=C["faint"])
    out.parent.mkdir(parents=True, exist_ok=True); img.save(out); return out

# ---- 전체 -----------------------------------------------------------------------------
def slug(s: str) -> str:
    return re.sub(r"[^\w가-힣]+", "_", s).strip("_")

def build_all(course: Course, out_dir: Path, start: str = "09:00", access: int = 3, view: int = 4, season_note: str = "", dry_run: bool = False,
              preset: str = "standard", layers: list[str] | None = None, on=None, lat: float | None = None, lon: float | None = None) -> dict:
    from src.media.profile import render
    ensure_elevation(course, dry_run)
    out_dir.mkdir(parents=True, exist_ok=True)
    if lat is None and course.segments:
        lon, lat = course.segments[0].coords[0]
    res = {"profile": render(course, out_dir / "profile.png", layers, preset, start, on, lat, lon),
           "radar": radar_chart({course.mountain: difficulty_scores(course, access, view)}, out_dir / "radar.png", f"{course.mountain} 난이도"),
           "card": summary_card(course, out_dir / "card.png", season_note=season_note),
           "timeline": timeline_table(course, start)}
    (out_dir / "timeline.md").write_text(res["timeline"], encoding="utf-8")
    return res
