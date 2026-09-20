"""클립용 세로 애니메이션 (1080×1920). 위: 주변 지도(경사 색 경로·핀), 아래: 고도 프로파일(경사 색 채움·배지 마커).
정적 이미지와 같은 디자인 토큰·아이콘·색 규칙을 쓴다. GIF 는 항상, MP4 는 ffmpeg 가 있으면 생성."""
from __future__ import annotations
import math, shutil, subprocess, tempfile
from pathlib import Path
from src.media.design import tokens, pin, badge, draw_row, font
from src.media.profile import grade_color
from src.media.area_map import waypoints

def _frame(course, k, x, y, lons, lats, wps, wp_idx, size, dpi, C, hold_last: bool):
    import matplotlib.pyplot as plt
    import numpy as np
    from PIL import Image
    W, H = size
    fig = plt.figure(figsize=(W / dpi, H / dpi), dpi=dpi); fig.patch.set_facecolor(C["bg"])
    axm = fig.add_axes([0.06, 0.45, 0.88, 0.37]); axp = fig.add_axes([0.10, 0.10, 0.84, 0.29])
    for a in (axm, axp):
        a.set_facecolor("#F4F7F2")
        for sp in a.spines.values(): sp.set_alpha(0.2)
    # ---- 지도: 주변 등산로(흐림) + 아직 안 간 경로(연함) + 간 경로(경사 색)
    for other in getattr(course, "context_lines", []) or []:
        axm.plot([q[0] for q in other], [q[1] for q in other], color="#B7C6BA", lw=1.2)
    axm.plot(lons, lats, color="#D5DED6", lw=3.5, solid_capstyle="round")
    for i in range(k):
        dxm = (x[i + 1] - x[i]) * 1000; g = abs(y[i + 1] - y[i]) / dxm * 100 if dxm > 0 else 0
        axm.plot([lons[i], lons[i + 1]], [lats[i], lats[i + 1]], color=grade_color(g), lw=5.5, solid_capstyle="round")
    axm.set_aspect(1 / math.cos(math.radians(sum(lats) / len(lats)))); axm.margins(0.22); axm.set_xticks([]); axm.set_yticks([])
    # ---- 프로파일: 전체 윤곽(연함) + 진행 구간 경사 색 채움 + 선
    base = y.min() - 30
    axp.plot(x, y, color="#D5DED6", lw=2)
    for i in range(k):
        dxm = (x[i + 1] - x[i]) * 1000; g = abs(y[i + 1] - y[i]) / dxm * 100 if dxm > 0 else 0
        axp.fill_between(x[i:i + 2], y[i:i + 2], base, color=grade_color(g), alpha=0.45, linewidth=0)
    axp.plot(x[:k + 1], y[:k + 1], color=C["chart_line"], lw=2.5)
    axp.set_ylim(base, y.max() + (y.max() - y.min()) * 0.30); axp.set_xlabel("거리 (km)"); axp.set_ylabel("고도 (m)"); axp.grid(alpha=0.3)
    for j, (label, _, _) in enumerate(wps):
        if wp_idx[j] <= k:
            axp.annotate(label, (x[wp_idx[j]], y[wp_idx[j]]), textcoords="offset points", xytext=(0, 16), ha="center", fontsize=9, fontweight="bold")
    fig.canvas.draw()
    # 픽셀 좌표 (핀·배지는 PIL 로)
    map_px = [(*axm.transData.transform((lons[wp_idx[j]], lats[wp_idx[j]])), ic) for j, (_, _, ic) in enumerate(wps) if wp_idx[j] <= k]
    prof_px = [(*axp.transData.transform((x[wp_idx[j]], y[wp_idx[j]])), ic) for j, (_, _, ic) in enumerate(wps) if wp_idx[j] <= k]
    cur_map = axm.transData.transform((lons[k], lats[k])); cur_prof = axp.transData.transform((x[k], y[k]))
    tmp = Path(tempfile.mkdtemp()) / "f.png"; fig.savefig(tmp, dpi=dpi, facecolor=C["bg"]); plt.close(fig)
    im = Image.open(tmp).convert("RGBA"); h_px = H
    def color_for(ic): return "#2980B9" if ic == "flag" else (C["chart_point"] if ic == "mountain" else C["accent"])
    for px, py, ic in map_px:
        pn = pin(ic, 44, color_for(ic)); im.paste(pn, (int(px - pn.width / 2), int(h_px - py - pn.height)), pn)
    for px, py, ic in prof_px:
        b = badge(ic, 30, color_for(ic)); im.paste(b, (int(px - 15), int(h_px - py - 15)), b)
    # 현재 위치 점 (지도·프로파일)
    from PIL import ImageDraw
    d = ImageDraw.Draw(im)
    for (px, py) in (cur_map, cur_prof):
        cx, cy = px, h_px - py
        d.ellipse([cx - 13, cy - 13, cx + 13, cy + 13], fill=C["chart_point"], outline="white", width=3)
    # 헤더 (토큰 폰트·아이콘)
    draw_row(im, (60, 80), [("icon", "mountain"), course.mountain], 64, C["text"])
    draw_row(im, (60, 170), [("icon", "ruler"), f"{x[k]:.1f} km", "·", ("icon", "trending_up"), f"{y[k]:.0f} m"], 40, C["muted"])
    if hold_last:
        draw_row(im, (60, H - 70), [("icon", "flag"), "전체 코스와 시간표는 본문에서"], 30, C["accent"])
    return im.convert("RGB")

def render(course, out_gif: Path, seconds: float = 8.0, fps: int = 15, size=(1080, 1920), mp4: bool = True) -> dict:
    import matplotlib; matplotlib.use("Agg")
    import numpy as np
    from src.media.course_viz import cumulative_km, _font
    _font(); C = tokens()["color"]
    pts = [q for s in course.segments for q in s.coords]; elev = [e for s in course.segments for e in s.elev]
    x = np.array(cumulative_km(pts)); y = np.array(elev, float); lons = [p[0] for p in pts]; lats = [p[1] for p in pts]
    wps = waypoints(course); wp_idx = [0] + [sum(len(s.coords) for s in course.segments[:k + 1]) - 1 for k in range(len(course.segments))]
    n_frames = int(seconds * fps); frames = []
    for f in range(n_frames + fps):                      # 마지막 1초 정지
        k = min(len(pts) - 1, int(len(pts) * min(f, n_frames) / n_frames))
        frames.append(_frame(course, k, x, y, lons, lats, wps, wp_idx, size, 150, C, hold_last=f >= n_frames))
    out_gif.parent.mkdir(parents=True, exist_ok=True)
    small = [fr.resize((size[0] // 2, size[1] // 2)) for fr in frames]
    small[0].save(out_gif, save_all=True, append_images=small[1:], duration=int(1000 / fps), loop=0)
    res = {"gif": out_gif}
    if mp4 and shutil.which("ffmpeg"):
        d = Path(tempfile.mkdtemp())
        for i, fr in enumerate(frames): fr.save(d / f"{i:04d}.png")
        out_mp4 = out_gif.with_suffix(".mp4")
        p = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps), "-i", str(d / "%04d.png"), "-c:v", "libx264", "-pix_fmt", "yuv420p", str(out_mp4)], capture_output=True)
        if p.returncode == 0 and out_mp4.exists(): res["mp4"] = out_mp4
    return res
