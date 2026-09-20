"""클립용 세로 애니메이션 (1080×1920). 위: 경로 지도가 그려지고, 아래: 고도 프로파일이 같은 지점까지 채워진다.
GIF 는 항상, MP4 는 ffmpeg 가 있으면 생성."""
from __future__ import annotations
import math, shutil, subprocess, tempfile
from pathlib import Path
from src.media.design import tokens, pin, font, draw_row
from src.media.profile import grade_color
from src.media.area_map import waypoints

def render(course, out_gif: Path, seconds: float = 8.0, fps: int = 15, size=(1080, 1920), mp4: bool = True) -> dict:
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    from PIL import Image
    from src.media.course_viz import cumulative_km, _font
    _font(); T = tokens(); C = T["color"]
    pts = [q for s in course.segments for q in s.coords]; elev = [e for s in course.segments for e in s.elev]
    x = np.array(cumulative_km(pts)); y = np.array(elev, float); lons = [p[0] for p in pts]; lats = [p[1] for p in pts]
    wps = waypoints(course); wp_idx = [0] + [sum(len(s.coords) for s in course.segments[:k + 1]) - 1 for k in range(len(course.segments))]
    n_frames = int(seconds * fps); frames = []
    W, H = size; dpi = 150
    for f in range(n_frames + fps):                      # 마지막 1초 정지
        k = min(len(pts) - 1, int(len(pts) * min(f, n_frames) / n_frames))
        fig = plt.figure(figsize=(W / dpi, H / dpi), dpi=dpi); fig.patch.set_facecolor(C["bg"])
        axm = fig.add_axes([0.06, 0.50, 0.88, 0.40]); axp = fig.add_axes([0.10, 0.10, 0.84, 0.30])
        for a in (axm, axp): a.set_facecolor("#F4F7F2")
        # 지도
        for other in getattr(course, "context_lines", []) or []:
            axm.plot([q[0] for q in other], [q[1] for q in other], color="#B7C6BA", lw=1.2)
        axm.plot(lons, lats, color="#D5DED6", lw=3)
        for i in range(k):
            dxm = (x[i + 1] - x[i]) * 1000; g = abs(y[i + 1] - y[i]) / dxm * 100 if dxm > 0 else 0
            axm.plot([lons[i], lons[i + 1]], [lats[i], lats[i + 1]], color=grade_color(g), lw=5, solid_capstyle="round")
        axm.plot(lons[k], lats[k], "o", color=C["chart_point"], ms=9, zorder=5)
        axm.set_aspect(1 / math.cos(math.radians(sum(lats) / len(lats)))); axm.margins(0.15); axm.set_xticks([]); axm.set_yticks([])
        # 프로파일
        axp.plot(x, y, color="#D5DED6", lw=2); axp.fill_between(x[:k + 1], y[:k + 1], y.min() - 30, color=C["chart_fill"], alpha=0.5); axp.plot(x[:k + 1], y[:k + 1], color=C["chart_line"], lw=2.5)
        axp.plot(x[k], y[k], "o", color=C["chart_point"], ms=8, zorder=5); axp.set_ylim(y.min() - 30, y.max() + (y.max() - y.min()) * 0.25)
        axp.set_xlabel("거리 (km)"); axp.set_ylabel("고도 (m)"); axp.grid(alpha=0.3)
        for a in (axm, axp):
            for sp in a.spines.values(): sp.set_alpha(0.2)
        # 도달한 지점 라벨
        for j, (label, (lo, la), ic) in enumerate(wps):
            if wp_idx[j] <= k:
                axp.annotate(label, (x[wp_idx[j]], y[wp_idx[j]]), textcoords="offset points", xytext=(0, 10), ha="center", fontsize=9, fontweight="bold")
        tmp = Path(tempfile.mkdtemp()) / f"f{f:04d}.png"; fig.savefig(tmp, dpi=dpi, facecolor=C["bg"]); plt.close(fig)
        im = Image.open(tmp).convert("RGB")
        draw_row(im, (60, 80), [("icon", "mountain"), course.mountain], 64, C["text"])
        draw_row(im, (60, 170), [("icon", "ruler"), f"{x[k]:.1f} km", "·", ("icon", "trending_up"), f"{y[k]:.0f} m"], 40, C["muted"])
        frames.append(im)
    out_gif.parent.mkdir(parents=True, exist_ok=True)
    small = [fr.resize((W // 2, H // 2)) for fr in frames]
    small[0].save(out_gif, save_all=True, append_images=small[1:], duration=int(1000 / fps), loop=0)
    res = {"gif": out_gif}
    if mp4 and shutil.which("ffmpeg"):
        d = Path(tempfile.mkdtemp())
        for i, fr in enumerate(frames): fr.save(d / f"{i:04d}.png")
        out_mp4 = out_gif.with_suffix(".mp4")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps), "-i", str(d / "%04d.png"), "-c:v", "libx264", "-pix_fmt", "yuv420p", str(out_mp4)], check=False)
        if out_mp4.exists(): res["mp4"] = out_mp4
    return res
