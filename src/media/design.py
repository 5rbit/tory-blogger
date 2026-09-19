"""디자인 토큰 로더 + 자체 라인 아이콘 세트 (24×24 격자 벡터, PIL 로 직접 그림 → 폰트·OS 무관).
아이콘 이름: mountain, ruler, timer, trending_up, flame, boot, leaf, bus, train, pin, flag, sun, cloud, alert, map, bag, food
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from src.common import CONFIG, load_yaml

@lru_cache
def tokens() -> dict:
    return load_yaml(CONFIG / "design.yaml")

def font(kind_or_px: str | int):
    px = tokens()["font"][kind_or_px] if isinstance(kind_or_px, str) else kind_or_px
    for p in tokens()["font"]["family"]:
        if Path(p).exists():
            return ImageFont.truetype(p, px)
    return ImageFont.load_default()

# 24×24 격자. "L"=폴리라인(열린), "P"=폴리곤(닫힘, 테두리), "F"=채운 폴리곤, "C"=원(cx,cy,r), "D"=채운 원
ICONS: dict[str, list[tuple]] = {
    "mountain":   [("L", [(2, 20), (9, 7), (13, 13), (15, 10), (22, 20), (2, 20)])],
    "ruler":      [("P", [(3, 17), (17, 3), (21, 7), (7, 21)]), ("L", [(7, 13), (9, 15)]), ("L", [(10, 10), (12, 12)]), ("L", [(13, 7), (15, 9)])],
    "timer":      [("C", (12, 13, 8)), ("L", [(12, 9), (12, 13), (15, 15)]), ("L", [(10, 2), (14, 2)]), ("L", [(12, 2), (12, 5)])],
    "trending_up":[("L", [(3, 17), (9, 11), (13, 15), (21, 7)]), ("L", [(15, 7), (21, 7), (21, 13)])],
    "boot":       [("F", [(4, 3), (11, 3), (11, 11), (13, 13), (19, 14), (21, 16), (21, 20), (3, 20), (3, 17), (4, 14)]), ("L", [(3, 17), (21, 17)])],
    "boot_off":   [("P", [(4, 3), (11, 3), (11, 11), (13, 13), (19, 14), (21, 16), (21, 20), (3, 20), (3, 17), (4, 14)])],
    "flame":      [("P", [(12, 2), (8, 8), (6, 13), (7, 18), (12, 22), (17, 18), (18, 13), (16, 8), (14, 10), (13, 5)]), ("L", [(12, 12), (10, 16), (12, 19), (14, 16), (12, 12)])],
    "flame_fill": [("F", [(12, 2), (8, 8), (6, 13), (7, 18), (12, 22), (17, 18), (18, 13), (16, 8), (14, 10), (13, 5)])],
    "gauge":      [("L", [(4, 16), (5, 11), (8, 7), (12, 6), (16, 7), (19, 11), (20, 16)]), ("L", [(12, 16), (16, 10)]), ("D", (12, 16, 1.5))],
    "leaf":       [("L", [(4, 20), (8, 12), (14, 6), (21, 3), (20, 10), (15, 17), (8, 19), (4, 20)]), ("L", [(4, 20), (14, 10)])],
    "bus":        [("P", [(4, 4), (20, 4), (20, 17), (4, 17)]), ("L", [(4, 11), (20, 11)]), ("D", (8, 14, 1.3)), ("D", (16, 14, 1.3)), ("L", [(6, 17), (6, 20)]), ("L", [(18, 17), (18, 20)])],
    "train":      [("P", [(5, 3), (19, 3), (19, 16), (5, 16)]), ("L", [(5, 10), (19, 10)]), ("D", (9, 13, 1.3)), ("D", (15, 13, 1.3)), ("L", [(8, 16), (5, 21)]), ("L", [(16, 16), (19, 21)])],
    "pin":        [("L", [(12, 21), (6, 13), (6, 9), (12, 3), (18, 9), (18, 13), (12, 21)]), ("C", (12, 10, 2.5))],
    "flag":       [("L", [(5, 21), (5, 3)]), ("L", [(5, 3), (19, 3), (16, 8), (19, 13), (5, 13)])],
    "sun":        [("C", (12, 12, 4)), ("L", [(12, 2), (12, 5)]), ("L", [(12, 19), (12, 22)]), ("L", [(2, 12), (5, 12)]), ("L", [(19, 12), (22, 12)]), ("L", [(5, 5), (7, 7)]), ("L", [(17, 17), (19, 19)]), ("L", [(5, 19), (7, 17)]), ("L", [(17, 7), (19, 5)])],
    "cloud":      [("L", [(6, 18), (18, 18), (20, 16), (20, 13), (17, 11), (16, 8), (12, 6), (8, 8), (7, 11), (4, 13), (4, 16), (6, 18)])],
    "alert":      [("P", [(12, 3), (22, 20), (2, 20)]), ("L", [(12, 9), (12, 14)]), ("D", (12, 17, 1.2))],
    "map":        [("P", [(3, 6), (9, 3), (15, 6), (21, 3), (21, 18), (15, 21), (9, 18), (3, 21)]), ("L", [(9, 3), (9, 18)]), ("L", [(15, 6), (15, 21)])],
    "bag":        [("P", [(6, 8), (18, 8), (19, 21), (5, 21)]), ("L", [(9, 8), (9, 5), (15, 5), (15, 8)]), ("L", [(8, 12), (16, 12)])],
    "food":       [("L", [(3, 12), (21, 12), (19, 19), (5, 19), (3, 12)]), ("L", [(6, 12), (8, 6)]), ("L", [(18, 12), (16, 6)]), ("L", [(12, 12), (12, 5)])],
}

def icon(name: str, size: int, color: str, stroke: int | None = None) -> Image.Image:
    """아이콘을 size×size RGBA 로 렌더 (4배 슈퍼샘플링 후 축소)."""
    ss = 4; S = size * ss; sc = S / 24; w = stroke * ss if stroke else max(2, int(S * tokens()["icon"]["stroke_ratio"]))
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    def P(pt): return (pt[0] * sc, pt[1] * sc)
    for kind, data in ICONS[name]:
        if kind == "L":
            pts = [P(p) for p in data]; d.line(pts, fill=color, width=w, joint="curve")
            for p in (pts[0], pts[-1]): d.ellipse([p[0] - w / 2, p[1] - w / 2, p[0] + w / 2, p[1] + w / 2], fill=color)
        elif kind == "P":
            pts = [P(p) for p in data] + [P(data[0])]; d.line(pts, fill=color, width=w, joint="curve")
        elif kind == "F":
            d.polygon([P(p) for p in data], fill=color)
        elif kind in ("C", "D"):
            cx, cy, r = data; box = [(cx - r) * sc, (cy - r) * sc, (cx + r) * sc, (cy + r) * sc]
            d.ellipse(box, outline=None if kind == "D" else color, fill=color if kind == "D" else None, width=w)
    return img.resize((size, size), Image.LANCZOS)

def cap_height(f) -> tuple[int, int]:
    """(글자 상단 오프셋, 캡 높이) — '가' 기준."""
    l, t, r, b = f.getbbox("가"); return t, b - t

def draw_row(img: Image.Image, xy: tuple[int, int], parts: list, size_px: int, color: str, gap: int | None = None, align: str = "left") -> int:
    """parts: 문자열 또는 ("icon", name) 혼합. 아이콘 높이는 캡 높이×ratio, 세로 중심을 글자 중심에 맞춘다. 폭 반환.
    align='right' 이면 xy 를 오른쪽 끝으로 본다."""
    f = font(size_px); t, cap = cap_height(f); ih = max(8, int(cap * tokens()["icon"]["ratio"]))
    gap = tokens()["space"]["icon_gap"] if gap is None else gap
    d = ImageDraw.Draw(img)
    # 폭 계산
    widths = [ih if isinstance(p, tuple) else int(d.textlength(p, font=f)) for p in parts]
    total = sum(widths) + gap * (len(parts) - 1)
    x, y = (xy[0] - total, xy[1]) if align == "right" else xy
    cy = y + t + cap / 2
    for p, w in zip(parts, widths):
        if isinstance(p, tuple):
            ic = icon(p[1], ih, color); img.paste(ic, (x, int(round(cy - ih / 2))), ic)
        else:
            d.text((x, y), p, font=f, fill=color)
        x += w + gap
    return total

def level_icons(img: Image.Image, xy: tuple[int, int], level: int, size_px: int, on: str, off: str, align: str = "left") -> int:
    """난이도 등급: 채운 불꽃 level 개 + 테두리 불꽃 (max-level) 개."""
    f = font(size_px); t, cap = cap_height(f); ih = int(cap * 1.15); gap = 6
    n = tokens()["icon"]["level_max"]; total = n * ih + (n - 1) * gap
    x = xy[0] - total if align == "right" else xy[0]; cy = xy[1] + t + cap / 2
    for i in range(n):
        ic = icon("flame_fill" if i < level else "flame", ih, on if i < level else off); img.paste(ic, (x, int(round(cy - ih / 2))), ic); x += ih + gap
    return total

def check_alignment(size_px: int = 40) -> dict:
    """아이콘·글자 세로 중심 차이(px)와 높이 비율 — 토큰 규칙이 지켜지는지 검사."""
    f = font(size_px); t, cap = cap_height(f); ih = int(cap * tokens()["icon"]["ratio"])
    cy = t + cap / 2; iy = int(round(cy - ih / 2))
    return {"center_diff_px": abs((iy + ih / 2) - cy), "height_ratio": ih / cap}

def add_title_band(png: Path, parts: list, size_px: int | None = None) -> Path:
    """차트 PNG 위에 아이콘+글자 제목 띠를 붙인다 (제자리 덮어쓰기)."""
    T = tokens(); size_px = size_px or T["font"]["chart_title"]; band = int(size_px * 2.2)
    chart = Image.open(png).convert("RGB")
    out = Image.new("RGB", (chart.width, chart.height + band), T["color"]["chart_bg"]); out.paste(chart, (0, band))
    tmp = Image.new("RGB", (chart.width, band), T["color"]["chart_bg"])
    w = draw_row(tmp, (0, int(size_px * 0.35)), parts, size_px, T["color"]["chart_text"], gap=int(size_px * 0.3))
    out.paste(tmp.crop((0, 0, max(w, 1), band)), ((chart.width - w) // 2, 0)); out.save(png); return png
