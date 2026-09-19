from datetime import date
from src.research import conditions as c

def test_grid_seoul_city_hall():
    assert c.latlon_to_grid(37.5665, 126.9780) == (60, 127)

def test_grid_monotonic():
    nx0, ny0 = c.latlon_to_grid(37.5665, 126.9780)
    nx1, ny1 = c.latlon_to_grid(37.5665, 127.5)   # 동쪽
    nx2, ny2 = c.latlon_to_grid(38.0, 126.9780)   # 북쪽
    assert nx1 > nx0 and ny2 > ny0

def test_foliage_phases():
    assert "아직" in c.foliage_status("설악산", date(2026, 9, 20))
    assert "절정 시기" in c.foliage_status("설악산", date(2026, 10, 19))
    assert "지남" in c.foliage_status("북한산", date(2026, 11, 20))
    assert c.foliage_status("없는산", date(2026, 10, 1)) is None

def test_block_dry_run_has_all_lines():
    b = c.conditions_block("북한산 우이동", "북한산", date(2026, 10, 24), dry_run=True)
    assert "날씨" in b and "단풍" in b and "통제" in b
