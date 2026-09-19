"""PIL 로 한글+컬러 이모지 혼합 텍스트를 그린다. matplotlib 그래프에 이모지 제목 띠를 얹을 때 사용."""
from __future__ import annotations
import re
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

EMOJI_RE = re.compile(
    "[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\u2300-\u23FF\u2190-\u21FF\u25A0-\u25FF\u2900-\u297F\u3030\u303D\u3297\u3299\u00A9\u00AE]"
    "[\uFE0F\u200D\U0001F3FB-\U0001F3FF]*(?:\u200D[\U0001F000-\U0001FAFF\u2600-\u27BF][\uFE0F]?)*")
_KR = ["/System/Library/Fonts/AppleSDGothicNeo.ttc", "/System/Library/Fonts/Supplemental/AppleGothic.ttf", "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf"]
_EMOJI = [("/System/Library/Fonts/Apple Color Emoji.ttc", 160), ("/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf", 109)]

def kr_font(size: int):
    for p in _KR:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()

def emoji_image(text: str, height: int) -> Image.Image | None:
    for p, native in _EMOJI:
        if Path(p).exists():
            try:
                f = ImageFont.truetype(p, native)
                tmp = Image.new("RGBA", (native * 2 * max(1, len(text)), native * 2), (0, 0, 0, 0))
                ImageDraw.Draw(tmp).text((0, 0), text, font=f, embedded_color=True)
                bb = tmp.getbbox()
                if bb:
                    tmp = tmp.crop(bb); r = height / tmp.height
                    return tmp.resize((max(1, int(tmp.width * r)), height), Image.LANCZOS)
            except Exception:
                continue
    return None

def text_center_y(font, y: int) -> float:
    """한글 글자의 시각적 세로 중심 (폰트 메트릭 기준). '가' 의 bbox 로 측정."""
    l, t, r, b = font.getbbox("가")
    return y + (t + b) / 2

def draw_mixed(img: Image.Image, xy: tuple[int, int], text: str, size: int, fill="white", emoji_scale: float = 0.95) -> int:
    """이모지는 이미지로, 나머지는 폰트로. 이모지 세로 중심을 글자 중심에 맞춘다. 그린 폭(px) 반환."""
    d = ImageDraw.Draw(img); f = kr_font(size); x, y = xy; pos = 0
    l, t, r, b = f.getbbox("가"); glyph_h = b - t
    eh = max(8, int(glyph_h * emoji_scale)); cy = text_center_y(f, y)
    for m in EMOJI_RE.finditer(text):
        seg = text[pos:m.start()]
        if seg:
            d.text((x, y), seg, font=f, fill=fill); x += int(d.textlength(seg, font=f))
        e = emoji_image(m.group(0), eh)
        if e:
            img.paste(e, (x + 2, int(round(cy - e.height / 2))), e); x += e.width + int(size * 0.2)
        else:
            d.text((x, y), m.group(0), font=f, fill=fill); x += int(d.textlength(m.group(0), font=f))
        pos = m.end()
    if text[pos:]:
        d.text((x, y), text[pos:], font=f, fill=fill); x += int(d.textlength(text[pos:], font=f))
    return x - xy[0]

def check_alignment(text: str, size: int = 40) -> dict:
    """이모지와 글자의 세로 중심·높이 차이를 측정 (테스트·품질 검사용). 값이 작을수록 잘 맞는다."""
    f = kr_font(size); l, t, r, b = f.getbbox("가"); glyph_h = b - t
    y = 10; cy = text_center_y(f, y)
    m = EMOJI_RE.search(text)
    if not m:
        return {"center_diff_px": 0.0, "height_ratio": 1.0}
    e = emoji_image(m.group(0), max(8, int(glyph_h * 0.95)))
    if e is None:
        return {"center_diff_px": 0.0, "height_ratio": 1.0, "note": "emoji font missing"}
    ey = int(round(cy - e.height / 2)); ecy = ey + e.height / 2
    return {"center_diff_px": abs(ecy - cy), "height_ratio": e.height / glyph_h}

def add_title_band(png: Path, title: str, size: int = 30, band: int | None = None, bg="white", fg="#1f3d2b") -> Path:
    """저장된 차트 PNG 위에 이모지 제목 띠를 붙인다 (제자리 덮어쓰기)."""
    chart = Image.open(png).convert("RGB"); band = band or int(size * 2.2)
    out = Image.new("RGB", (chart.width, chart.height + band), bg); out.paste(chart, (0, band))
    tmp = Image.new("RGB", (chart.width, band), bg); w = draw_mixed(tmp, (0, int(size * 0.35)), title, size, fg)
    out.paste(tmp.crop((0, 0, max(w, 1), band)), ((chart.width - w) // 2, 0))
    out.save(png); return png
