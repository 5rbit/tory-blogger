from datetime import date
from pathlib import Path
from src.media import profile as pf
from src.media import course_viz as cv

def test_sunset_seoul_autumn():
    ss = pf.sunset_time(37.57, 126.98, date(2026, 10, 24))
    assert 17 <= ss.hour <= 18          # 10월 말 서울 일몰 17:30 전후

def test_sunrise_before_sunset_and_winter_later():
    d = date(2026, 12, 21); sr = pf.sunrise_time(37.57, 126.98, d); ss = pf.sunset_time(37.57, 126.98, d)
    assert sr.hour == 7 and ss.hour == 17 and sr < ss   # 동지 서울 일출 07:4x, 일몰 17:1x
    assert pf.sunrise_time(37.57, 126.98, date(2026, 6, 21)).hour == 5

def test_dawn_start_renders(tmp_path):
    c = cv.sample_course(); cv.ensure_elevation(c, dry_run=True); lon, lat = c.segments[0].coords[0]
    p = pf.render(c, tmp_path / "dawn.png", None, "season", "04:30", date(2026, 10, 24), lat, lon)
    assert Path(p).exists()

def test_foliage_threshold_descends():
    a = pf.foliage_threshold("북한산", date(2026, 11, 1)); b = pf.foliage_threshold("북한산", date(2026, 11, 6))
    assert a and b and b[0] < a[0]

def test_all_presets_render(tmp_path):
    c = cv.sample_course(); cv.ensure_elevation(c, dry_run=True); lon, lat = c.segments[0].coords[0]
    for name in pf.PRESETS:
        p = pf.render(c, tmp_path / f"{name}.png", None, name, "09:00", date(2026, 10, 24), lat, lon)
        assert Path(p).stat().st_size > 5000

def test_grade_color_bands():
    assert pf.grade_color(3) == "#7AA874" and pf.grade_color(25) == "#C0392B"
