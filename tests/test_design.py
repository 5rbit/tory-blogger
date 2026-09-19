from PIL import Image
from src.media import design as ds

def test_all_icons_render_nonempty():
    for name in ds.ICONS:
        im = ds.icon(name, 48, "#000000")
        assert im.size == (48, 48) and im.getbbox() is not None, name
        bb = im.getbbox(); assert bb[0] >= 0 and bb[2] <= 48   # 격자 밖으로 안 나감

def test_alignment_follows_tokens():
    r = ds.check_alignment(40)
    assert r["center_diff_px"] <= 0.5 and 0.9 <= r["height_ratio"] <= 1.1

def test_draw_row_and_levels():
    img = Image.new("RGB", (800, 100), "white")
    w = ds.draw_row(img, (10, 10), [("icon", "mountain"), "북한산", "·", ("icon", "ruler"), "7.6 km"], 36, "#000")
    assert 200 < w < 800
    w2 = ds.level_icons(img, (10, 60), 3, 36, "#E8B04B", "#BFD3C1")
    assert w2 > 0

def test_tokens_loaded():
    t = ds.tokens(); assert t["color"]["bg"].startswith("#") and t["font"]["title"] > t["font"]["caption"]

def test_badge_and_pin_shapes():
    b = ds.badge("pin", 26, "#000"); assert b.size == (26, 26) and b.getbbox()
    p = ds.pin("mountain", 30, "#C0392B"); assert p.height == 30 and p.width < p.height and p.getbbox()
