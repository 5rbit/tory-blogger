from PIL import Image
from src.media import emoji_text as et
from src.emoji import difficulty_emoji, DIFFICULTY_LABEL

def test_alignment_within_tolerance():
    for text in ["🥾 보통", "📈 고도 프로파일", "💪 난이도", "🍁 단풍 절정", "⏱️ 소요", "⛰️ 북한산", "🗺️ 지도"]:
        r = et.check_alignment(text, 40)
        if r.get("note"):
            return   # 이모지 폰트 없는 환경
        assert r["center_diff_px"] <= 1.0, (text, r)
        assert 0.85 <= r["height_ratio"] <= 1.05, (text, r)

def test_draw_mixed_width_and_no_crash():
    img = Image.new("RGB", (600, 80), "white")
    w = et.draw_mixed(img, (10, 10), "🥾🥾🥾 땀 좀 나요 · 📏 7.6 km", 32, "black")
    assert 200 < w < 600

def test_difficulty_names_and_label_icon():
    assert difficulty_emoji("어려움") == "🥾🥾🥾🥾 빡센 편" and difficulty_emoji(1) == "🥾 산책 수준"
    assert DIFFICULTY_LABEL.startswith("💪")
