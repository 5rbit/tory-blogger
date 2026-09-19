"""고도 프로파일 — 레이어 조합형. 프리셋으로 밀도를 고른다.
레이어: slope_fill(경사 색칠) time_axis(상단 시간축) markers(아이콘 마커) hardest(최대 경사 구간) foliage_band(고도별 단풍 띠)
        sun(일출·일몰선, 헤드랜턴 구간) roundtrip(하산 점선) minimap(경로 미니맵: 북쪽·축척·주변 등산로) stats(하단 수치 스트립)
"""
from __future__ import annotations
import math
from datetime import date, datetime, timedelta
from pathlib import Path
from src.common import CONFIG, load_yaml, get_logger
from src.media.design import tokens, icon, badge, pin, add_title_band, draw_row, font
log = get_logger(__name__)

PRESETS = {
    "basic":    ["markers", "stats"],
    "standard": ["slope_fill", "time_axis", "markers", "hardest", "stats"],
    "season":   ["slope_fill", "time_axis", "markers", "hardest", "stats", "foliage_band", "sun"],
    "full":     ["slope_fill", "time_axis", "markers", "hardest", "stats", "foliage_band", "sun", "roundtrip", "minimap"],
}
GRADE_COLORS = [(6, "#7AA874"), (12, "#D9C15A"), (18, "#E8963E"), (99, "#C0392B")]   # 경사 % 상한, 색

def grade_color(pct: float) -> str:
    for lim, c in GRADE_COLORS:
        if pct <= lim:
            return c
    return GRADE_COLORS[-1][1]

# ---- 일몰 (NOAA 근사, API 불필요) --------------------------------------------------------
def sun_time(lat: float, lon: float, d: date, rising: bool, tz_hours: int = 9) -> datetime:
    """NOAA 근사 일출/일몰 (지방시, API 불필요)."""
    n = d.timetuple().tm_yday
    lng_hour = lon / 15.0; t = n + (((6 if rising else 18) - lng_hour) / 24)
    M = (0.9856 * t) - 3.289
    L = (M + 1.916 * math.sin(math.radians(M)) + 0.020 * math.sin(math.radians(2 * M)) + 282.634) % 360
    RA = math.degrees(math.atan(0.91764 * math.tan(math.radians(L)))) % 360
    RA += (math.floor(L / 90) * 90) - (math.floor(RA / 90) * 90); RA /= 15
    sinDec = 0.39782 * math.sin(math.radians(L)); cosDec = math.cos(math.asin(sinDec))
    cosH = (math.cos(math.radians(90.833)) - sinDec * math.sin(math.radians(lat))) / (cosDec * math.cos(math.radians(lat)))
    H = math.degrees(math.acos(max(-1, min(1, cosH)))); H = (360 - H) if rising else H; H /= 15
    T = H + RA - (0.06571 * t) - 6.622
    UT = (T - lng_hour) % 24; local = (UT + tz_hours) % 24
    return datetime.combine(d, datetime.min.time()) + timedelta(hours=local)

def sunset_time(lat: float, lon: float, d: date, tz_hours: int = 9) -> datetime:
    return sun_time(lat, lon, d, rising=False, tz_hours=tz_hours)

def sunrise_time(lat: float, lon: float, d: date, tz_hours: int = 9) -> datetime:
    return sun_time(lat, lon, d, rising=True, tz_hours=tz_hours)

# ---- 단풍 고도 띠 -------------------------------------------------------------------------
def foliage_threshold(mountain: str, on: date, descent_m_per_day: float = 40.0) -> tuple[float, str] | None:
    """on 날짜에 '이 고도 이상 절정' 기준 고도. 예측표의 peak 는 기준 고도(ref_alt, 기본 700m)에서의 절정일."""
    cfg = load_yaml(CONFIG / "foliage.yaml")
    m = next((v for k, v in cfg.get("mountains", {}).items() if k in mountain or mountain in k), None)
    if not m:
        return None
    peak = date.fromisoformat(str(m["peak"])); ref = float(m.get("ref_alt", 700))
    delta_days = (on - peak).days
    thr = ref - descent_m_per_day * delta_days          # 날이 지날수록 절정 고도가 내려온다
    return thr, f"단풍 절정 {int(thr)}m 이상" if delta_days >= 0 else f"단풍 절정 {int(thr)}m 이상 (예상)"

# ---- 본체 --------------------------------------------------------------------------------
def render(course, out: Path, layers: list[str] | None = None, preset: str = "standard", start: str = "09:00",
           on: date | None = None, lat: float | None = None, lon: float | None = None, pois: list[dict] | None = None) -> Path:
    """pois: [{"km": 1.4, "icon": "pin", "label": "도선사"}] 추가 마커 (화장실·약수터 등)."""
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    from src.media.course_viz import cumulative_km, _font, path_length_km
    from PIL import Image
    _font(); T = tokens(); C = T["color"]; L = set(layers if layers is not None else PRESETS[preset])
    on = on or date.today()

    # 좌표·고도·시간 이어붙이기
    pts, elev, seg_bounds = [], [], []           # seg_bounds: (start_idx, end_idx, segment)
    for s in course.segments:
        i0 = len(pts) - 1 if pts else 0
        pts += s.coords if not pts else s.coords[1:]
        elev += s.elev if not elev else s.elev[1:]
        seg_bounds.append((max(i0, 0), len(pts) - 1, s))
    x = np.array(cumulative_km(pts)); y = np.array(elev, dtype=float)
    # 시간 매핑 (거리→분): 구간별 상행 시간을 거리에 비례 배분
    tmin = np.zeros_like(x)
    for i0, i1, s in seg_bounds:
        seg_len = x[i1] - x[i0]
        tmin[i0:i1 + 1] = tmin[i0] + (x[i0:i1 + 1] - x[i0]) / max(seg_len, 1e-9) * s.up_min if seg_len > 0 else tmin[i0]
        if i1 + 1 < len(tmin): tmin[i1 + 1:] = tmin[i1]
    t0 = datetime.strptime(start, "%H:%M")
    # 왕복
    if "roundtrip" in L:
        xr = x[-1] + (x[-1] - x[::-1]); yr = y[::-1]
        down = sum((s.down_min or int(s.up_min * 0.7)) for s in course.segments)
        tr = tmin[-1] + 30 + (xr - x[-1]) / max(xr[-1] - x[-1], 1e-9) * down    # 정상 30분 휴식
    fig, ax = plt.subplots(figsize=(11, 4.6), dpi=150)
    base = y.min() - 30
    ys_all = np.concatenate([y, yr[1:]]) if "roundtrip" in L else y; third = max(len(ys_all) // 3, 1)
    left_low = ys_all[:third].mean() <= ys_all[-third:].mean()      # 프로파일이 낮은 쪽 = 빈 공간이 많은 쪽

    # 1) 경사 색칠 / 기본 채우기
    if "slope_fill" in L:
        for i in range(len(x) - 1):
            dx = (x[i + 1] - x[i]) * 1000; g = abs(y[i + 1] - y[i]) / dx * 100 if dx > 0 else 0
            ax.fill_between(x[i:i + 2], y[i:i + 2], base, color=grade_color(g), alpha=0.45, linewidth=0)
    else:
        ax.fill_between(x, y, base, color=C["chart_fill"], alpha=0.35)
    ax.plot(x, y, color=C["chart_line"], lw=2)
    if "roundtrip" in L:
        ax.plot(xr, yr, color=C["chart_line"], lw=1.5, ls="--", alpha=0.7)
        ax.fill_between(xr, yr, base, color=C["chart_fill"], alpha=0.15)

    # 4) 최대 경사 구간
    if "hardest" in L and len(x) > 3:
        win = 0.3; best = (0, 0, 0)
        for i in range(len(x)):
            j = i
            while j + 1 < len(x) and x[j + 1] - x[i] <= win: j += 1
            if j > i:
                g = (y[j] - y[i]) / ((x[j] - x[i]) * 1000) * 100
                if g > best[2]: best = (i, j, g)
        i, j, g = best
        if g > 0:
            ax.axvspan(x[i], x[j], color=C["chart_point"], alpha=0.12)
            ax.annotate(f"최대 경사 {g:.0f}%", ((x[i] + x[j]) / 2, base + (y.max() - y.min()) * 0.05), ha="center", va="bottom", fontsize=9, color=C["chart_point"], fontweight="bold",
                        bbox=dict(boxstyle="round,pad=0.25", fc="white", ec=C["chart_point"], alpha=0.9))

    # 5) 단풍 띠
    if "foliage_band" in L and (fb := foliage_threshold(course.mountain, on)):
        thr, label = fb
        if thr < y.max():
            ax.axhspan(max(thr, base), y.max() + 40, color="#E8963E", alpha=0.10)
            on_left = left_low and "minimap" not in L
            ax.text(0.01 if on_left else 0.99, max(thr, base) + 8, label, transform=ax.get_yaxis_transform(), fontsize=9, color="#B35C00",
                    ha="left" if on_left else "right", va="bottom")

    # 2) 시간 축
    if "time_axis" in L:
        xs_all = np.concatenate([x, xr[1:]]) if "roundtrip" in L else x
        ts_all = np.concatenate([tmin, tr[1:]]) if "roundtrip" in L else tmin
        sec = ax.secondary_xaxis("top", functions=(lambda k: np.interp(k, xs_all, ts_all), lambda m: np.interp(m, ts_all, xs_all)))
        total = ts_all[-1]; step = 30 if total <= 240 else 60
        ticks = np.arange(0, total + 1, step)
        xt = np.interp(ticks, ts_all, xs_all); keep = []; last = -1e9
        for i, xv in enumerate(xt):
            if xv - last > (xs_all[-1] - xs_all[0]) * 0.04: keep.append(i); last = xv
        ticks = ticks[keep]
        sec.set_xticks(ticks); sec.set_xticklabels([(t0 + timedelta(minutes=float(m))).strftime("%H:%M") for m in ticks], fontsize=8)
        sec.set_xlabel(f"예상 시각 ({start} 출발)", fontsize=9)
        # 6) 일출·일몰선 + 헤드랜턴 구간
        if "sun" in L and lat is not None and lon is not None:
            day0 = datetime.combine(on, t0.time())
            sr = sunrise_time(lat, lon, on); ss = sunset_time(lat, lon, on)
            sr_min = (sr - day0).total_seconds() / 60; ss_min = (ss - day0).total_seconds() / 60
            notes = []; line_xs = []
            span = xs_all[-1] - xs_all[0]; rng = y.max() - y.min()
            def vline(xs, label, color, ls):
                ax.axvline(xs, color=color, ls=ls, lw=1.5)
                ax.text(xs, base + rng * 0.30, label, color=color, fontsize=8, ha="center", va="bottom", rotation=90,
                        bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.85))
                line_xs.append(xs)
            if sr_min > 0:                                  # 출발이 일출 전 → 어두운 구간
                xs = float(np.interp(min(sr_min, total), ts_all, xs_all))
                ax.axvspan(xs_all[0], xs, color="#2C3E50", alpha=0.10); vline(xs, f"일출 {sr:%H:%M}", "#E67E22", "-.")
                notes.append(f"헤드랜턴 {int(min(sr_min, total))}분")
            else:
                notes.append(f"일출 {sr:%H:%M}")
            if 0 < ss_min < total:
                xs = float(np.interp(ss_min, ts_all, xs_all))
                ax.axvspan(xs, xs_all[-1], color="#2C3E50", alpha=0.10); vline(xs, f"일몰 {ss:%H:%M}", "#6C3483", ":")
                notes.append("일몰 후 하산 주의")
            else:
                notes.append(f"일몰 {ss:%H:%M} · 여유 {int(ss_min - total)}분")
            # 안내문은 선과 반대편, 선이 없으면 빈 쪽
            right = (left_low if not line_xs else (min(line_xs) - xs_all[0]) < span * 0.5)
            ax.text(0.99 if right else 0.01, 0.96, " · ".join(notes), transform=ax.transAxes, ha="right" if right else "left", va="top", fontsize=8, color="#6C3483")

    ax.set_xlabel("거리 (km)"); ax.set_ylabel("고도 (m)"); ax.grid(alpha=0.3)
    ax.set_ylim(base, y.max() + (y.max() - y.min()) * 0.22)
    fig.tight_layout(); out.parent.mkdir(parents=True, exist_ok=True)

    # 3) 마커 (아이콘은 저장 후 PIL 로 붙임)
    marks = [(0, "flag", course.segments[0].name.split("→")[0].strip())]
    for k, (i0, i1, s) in enumerate(seg_bounds):
        marks.append((i1, "mountain" if k == len(seg_bounds) - 1 else "pin", s.name.split("→")[-1].strip()))
    fig.canvas.draw(); px_marks = []; mini_px = []
    for i, ic, label in marks:
        px, py = ax.transData.transform((x[i], y[i])); px_marks.append((px, py, ic, label))
        if "markers" not in L:
            ax.plot(x[i], y[i], "o", color=C["chart_point"], ms=5)
        ax.annotate(label, (x[i], y[i]), textcoords="offset points", xytext=(0, 14 if "markers" in L else 8), ha="center", fontsize=9)
    for p in pois or []:
        xi = float(p["km"]); yi = float(np.interp(xi, x, y)); px, py = ax.transData.transform((xi, yi))
        px_marks.append((px, py, p.get("icon", "pin"), "")); ax.annotate(p.get("label", ""), (xi, yi), textcoords="offset points", xytext=(0, -16), ha="center", fontsize=8, color="#555")

    # 8) 미니맵: 주변 등산로(흐림) + 이 코스 + 들머리/정상 라벨 + 북쪽 화살표 + 축척
    if "minimap" in L:
        ins = ax.inset_axes([0.03 if left_low else 0.73, 0.58, 0.24, 0.38]); lons = [p[0] for p in pts]; lats = [p[1] for p in pts]
        ins.set_facecolor("#F7F9F5")
        for other in (getattr(course, "context_lines", None) or []):          # 같은 산의 다른 구간
            ins.plot([q[0] for q in other], [q[1] for q in other], color="#9FB3A3", lw=0.8, alpha=0.7)
        ins.plot(lons, lats, color=C["chart_line"], lw=2)
        ins.annotate(marks[0][2], (lons[0], lats[0]), textcoords="offset points", xytext=(0, -11), fontsize=6, color="#2980B9", ha="center")
        ins.annotate(marks[-1][2], (lons[-1], lats[-1]), textcoords="offset points", xytext=(0, -11), fontsize=6, color=C["chart_point"], ha="center")
        aspect = 1 / math.cos(math.radians(sum(lats) / len(lats))); ins.set_aspect(aspect)
        ins.margins(0.25); ins.set_xticks([]); ins.set_yticks([])
        ins.annotate("N", xy=(0.92, 0.80), xytext=(0.92, 0.62), xycoords="axes fraction", textcoords="axes fraction", ha="center", fontsize=7,
                     arrowprops=dict(arrowstyle="-|>", color="#333", lw=1))
        # 축척 500 m
        x0, x1 = ins.get_xlim(); yl0, yl1 = ins.get_ylim(); deg = 0.5 / (111.32 * math.cos(math.radians(sum(lats) / len(lats))))
        bx = x0 + (x1 - x0) * 0.06; by = yl0 + (yl1 - yl0) * 0.08
        ins.plot([bx, bx + deg], [by, by], color="#333", lw=2); ins.text(bx + deg / 2, by + (yl1 - yl0) * 0.03, "500 m", ha="center", fontsize=6)
        for sp in ins.spines.values(): sp.set_alpha(0.3)
        fig.canvas.draw()
        mini_px = [(*ins.transData.transform((lons[0], lats[0])), "flag", "#2980B9"), (*ins.transData.transform((lons[-1], lats[-1])), "mountain", C["chart_point"])]

    fig.savefig(out); h_px = fig.get_size_inches()[1] * fig.dpi; plt.close(fig)

    im = Image.open(out).convert("RGBA")
    if "markers" in L:
        sz = 26
        for px, py, ic, _ in px_marks:
            fg = C["chart_point"] if ic == "mountain" else ("#2980B9" if ic == "flag" else C["chart_line"])
            b = badge(ic, sz, fg); im.paste(b, (int(px - sz / 2), int(h_px - py - sz / 2)), b)
    if "minimap" in L and mini_px:
        for (px, py, ic, fg) in mini_px:
            pn = pin(ic, 30, fg); im.paste(pn, (int(px - pn.width / 2), int(h_px - py - pn.height)), pn)   # 꼭짓점이 위치
    im.convert("RGB").save(out)

    gain = float(np.sum(np.clip(np.diff(y), 0, None))); loss = gain if "roundtrip" in L else float(abs(np.sum(np.clip(np.diff(y), None, 0))))
    add_title_band(out, [("icon", "mountain"), course.mountain, "·", ("icon", "trending_up"), "고도 프로파일"])
    if "stats" in L:
        total_min = int(tmin[-1] + (30 + sum((s.down_min or int(s.up_min * 0.7)) for s in course.segments) if "roundtrip" in L else 0))
        _stats_strip(out, [("icon", "ruler"), f"{(xr[-1] if 'roundtrip' in L else x[-1]):.1f} km", "·", ("icon", "trending_up"), f"상승 {gain:.0f} m · 하강 {loss:.0f} m",
                           "·", ("icon", "mountain"), f"최고 {y.max():.0f} m", "·", ("icon", "timer"), f"{total_min // 60}시간 {total_min % 60}분"])
    return out

def _stats_strip(png: Path, parts: list, size_px: int = 22) -> Path:
    from PIL import Image
    T = tokens(); band = int(size_px * 2.0)
    chart = Image.open(png).convert("RGB")
    out = Image.new("RGB", (chart.width, chart.height + band), T["color"]["panel"]); out.paste(chart, (0, 0))
    tmp = Image.new("RGB", (chart.width, band), T["color"]["panel"]); w = draw_row(tmp, (0, int(size_px * 0.45)), parts, size_px, T["color"]["text"], gap=int(size_px * 0.35))
    out.paste(tmp.crop((0, 0, max(w, 1), band)), ((chart.width - w) // 2, chart.height)); out.save(png); return png
