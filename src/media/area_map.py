"""코스 주변 지도 — 지도 타일 없이 좌표만으로 그리는 정사각 이미지.
경로(경사 색), 주변 등산로(흐림), 번호 핀(들머리~정상), 정류장·식당·주차장 핀, 북쪽·축척·범례. GPX 내보내기 포함.
"""
from __future__ import annotations
import math
from pathlib import Path
from src.media.design import tokens, pin, badge, icon, add_title_band, draw_row
from src.media.profile import grade_color

CIRCLED = "①②③④⑤⑥⑦⑧⑨⑩"

def circled(i: int) -> str:
    return CIRCLED[i] if i < len(CIRCLED) else str(i + 1)

def waypoints(course) -> list[tuple[str, tuple[float, float], str]]:
    """[(번호+이름, (lon,lat), 아이콘)] 들머리→경유→정상."""
    pts = [(course.segments[0].name.split("→")[0].strip(), course.segments[0].coords[0], "flag")]
    for k, s in enumerate(course.segments):
        pts.append((s.name.split("→")[-1].strip(), s.coords[-1], "mountain" if k == len(course.segments) - 1 else "pin"))
    return [(f"{circled(i)} {n}", c, ic) for i, (n, c, ic) in enumerate(pts)]

def render(course, out: Path, stops: list[dict] | None = None, restaurants: list[dict] | None = None, parking: list[dict] | None = None,
           size_in: float = 7.2, view_cones: list[dict] | None = None) -> Path:
    """stops/restaurants/parking: [{"name", "lat", "lon"}]"""
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from PIL import Image
    from src.media.course_viz import _font, haversine_km
    _font(); T = tokens(); C = T["color"]
    fig, ax = plt.subplots(figsize=(size_in, size_in), dpi=150); ax.set_facecolor("#F4F7F2")
    for other in getattr(course, "context_lines", []) or []:
        ax.plot([q[0] for q in other], [q[1] for q in other], color="#B7C6BA", lw=1.2, alpha=0.9, zorder=1)
    # 경로: 경사 색
    for s in course.segments:
        cs, es = s.coords, s.elev if len(s.elev) == len(s.coords) else [0] * len(s.coords)
        for i in range(len(cs) - 1):
            dx = haversine_km(cs[i], cs[i + 1]) * 1000; g = abs(es[i + 1] - es[i]) / dx * 100 if dx > 0 else 0
            ax.plot([cs[i][0], cs[i + 1][0]], [cs[i][1], cs[i + 1][1]], color=grade_color(g), lw=4.5, solid_capstyle="round", zorder=2)
    lats = [q[1] for s in course.segments for q in s.coords]; lons = [q[0] for s in course.segments for q in s.coords]
    extra = [(d["lon"], d["lat"]) for d in (stops or []) + (restaurants or []) + (parking or [])]
    lats += [e[1] for e in extra]; lons += [e[0] for e in extra]
    ax.set_aspect(1 / math.cos(math.radians(sum(lats) / len(lats)))); ax.margins(0.18)
    ax.set_xticks([]); ax.set_yticks([])
    for sp in ax.spines.values(): sp.set_alpha(0.2)
    # 라벨(핀은 PIL 로)
    wps = waypoints(course); pins = []
    for label, (lon, lat), ic in wps:
        ax.annotate(label, (lon, lat), textcoords="offset points", xytext=(0, -13), ha="center", fontsize=8, color="#1F3D2B", fontweight="bold",
                    bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.8))
        pins.append((lon, lat, ic, "#2980B9" if ic == "flag" else (C["chart_point"] if ic == "mountain" else C["accent"]), 34))
    # 주변 시설: 지도에는 짧은 코드(B1·F1·P1)만, 이름은 하단 범례 띠에
    legend: list[tuple[str, str, list[str]]] = []
    for items, code, ic, color, title in [(stops or [], "B", "bus", "#2C3E50", "정류장"), (restaurants or [], "F", "food", "#8E5A1D", "식당"), (parking or [], "P", "map", "#555555", "주차")]:
        names = []
        for k, d in enumerate(items, 1):
            ax.annotate(f"{code}{k}", (d["lon"], d["lat"]), textcoords="offset points", xytext=(9, 4), ha="left", fontsize=7, color=color, fontweight="bold",
                        bbox=dict(boxstyle="round,pad=0.12", fc="white", ec=color, lw=0.6, alpha=0.9))
            pins.append((d["lon"], d["lat"], ic, color, 26)); names.append(f"{code}{k} {d['name']}")
        if names:
            legend.append((ic, title, names))
    if view_cones:
        draw_view_cones(ax, view_cones)
    # 북쪽·축척
    ax.annotate("N", xy=(0.95, 0.93), xytext=(0.95, 0.85), xycoords="axes fraction", textcoords="axes fraction", ha="center", fontsize=9, arrowprops=dict(arrowstyle="-|>", color="#333", lw=1.2))
    x0, x1 = ax.get_xlim(); y0, y1 = ax.get_ylim(); deg = 0.5 / (111.32 * math.cos(math.radians(sum(lats) / len(lats))))
    bx = x0 + (x1 - x0) * 0.05; by = y0 + (y1 - y0) * 0.05
    ax.plot([bx, bx + deg], [by, by], color="#333", lw=2.5); ax.text(bx + deg / 2, by + (y1 - y0) * 0.015, "500 m", ha="center", fontsize=8)
    fig.tight_layout(pad=0.4); fig.canvas.draw(); out.parent.mkdir(parents=True, exist_ok=True); fig.savefig(out)
    h_px = fig.get_size_inches()[1] * fig.dpi
    px = [(*ax.transData.transform((lon, lat)), ic, fg, sz) for lon, lat, ic, fg, sz in pins]; plt.close(fig)
    im = Image.open(out).convert("RGBA")
    for x, y, ic, fg, sz in sorted(px, key=lambda p: -p[1]):        # 위쪽(북)부터 붙여 아래 핀이 위에 오도록
        pn = pin(ic, sz, fg); im.paste(pn, (int(x - pn.width / 2), int(h_px - y - pn.height)), pn)
    im.convert("RGB").save(out)
    add_title_band(out, [("icon", "map"), f"{course.mountain} 코스 주변"])
    if legend:
        _legend_band(out, legend)
    return out

def _legend_band(png: Path, legend: list, size_px: int = 20) -> Path:
    """하단 범례: 아이콘 + '코드 이름' 목록을 줄별로."""
    from PIL import Image
    T = tokens(); C = T["color"]; line_h = int(size_px * 1.8); band = line_h * len(legend) + int(size_px * 0.8)
    img = Image.open(png).convert("RGB"); out = Image.new("RGB", (img.width, img.height + band), C["panel"]); out.paste(img, (0, 0))
    y = img.height + int(size_px * 0.4)
    for ic, title, names in legend:
        draw_row(out, (30, y), [("icon", ic), f"{title}:", "  ·  ".join(names)], size_px, C["text"], gap=int(size_px * 0.4)); y += line_h
    out.save(png); return png

def to_gpx(course, out: Path) -> Path:
    """코스 선형을 GPX 로 (독자가 트랭글·램블러에서 열 수 있게)."""
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<gpx version="1.1" creator="tory-blogger" xmlns="http://www.topografix.com/GPX/1/1">',
             f"  <trk><name>{course.mountain}</name>"]
    for s in course.segments:
        lines.append("    <trkseg>")
        for i, (lon, lat) in enumerate(s.coords):
            ele = f"<ele>{s.elev[i]:.0f}</ele>" if len(s.elev) == len(s.coords) else ""
            lines.append(f'      <trkpt lat="{lat:.6f}" lon="{lon:.6f}">{ele}</trkpt>')
        lines.append("    </trkseg>")
    for i, (label, (lon, lat), _) in enumerate(waypoints(course)):
        lines.append(f'  <wpt lat="{lat:.6f}" lon="{lon:.6f}"><name>{label}</name></wpt>')
    lines += ["  </trk>", "</gpx>"]
    out.parent.mkdir(parents=True, exist_ok=True); out.write_text("\n".join(lines), encoding="utf-8"); return out

def places_for_editor(course, stops=None, restaurants=None, parking=None) -> list[dict]:
    """네이버 에디터 '장소' 첨부 순서 (지도 번호와 동일). fill_editor 가 검색어로 사용."""
    out = [{"order": i + 1, "query": label.split(" ", 1)[1], "kind": "코스"} for i, (label, _, _) in enumerate(waypoints(course))]
    n = len(out)
    for items, kind in [(stops or [], "정류장"), (parking or [], "주차"), (restaurants or [], "식당")]:
        for d in items:
            n += 1; out.append({"order": n, "query": d["name"], "kind": kind})
    return out

def places_block(places: list[dict]) -> str:
    lines = ["<!-- 장소 첨부 순서 (fill_editor 가 읽음) -->", "<!-- places:"] + [f"{p['order']}. [{p['kind']}] {p['query']}" for p in places] + ["-->"]
    return "\n".join(lines)

# ---- 7. 조망 방향 부채꼴 ----------------------------------------------------------------------
def draw_view_cones(ax, cones: list[dict], color: str = "#2980B9"):
    """cones: [{"lat","lon","bearing"(도, 북=0 시계방향),"width"(도),"label"}] — 정상·전망대에서 보이는 방향."""
    import math
    from matplotlib.patches import Wedge
    x0, x1 = ax.get_xlim(); r = (x1 - x0) * 0.09
    for c in cones:
        theta = 90 - c["bearing"]; w = c.get("width", 50)
        asp = 1 / math.cos(math.radians(c["lat"]))
        ax.add_patch(Wedge((c["lon"], c["lat"]), r, theta - w / 2, theta + w / 2, color=color, alpha=0.18, zorder=1.5))
        ex, ey = c["lon"] + r * 1.15 * math.cos(math.radians(theta)), c["lat"] + r * 1.15 * math.sin(math.radians(theta)) / asp
        ax.annotate(c.get("label", "조망"), (ex, ey), ha="center", fontsize=7, color=color, fontweight="bold")
