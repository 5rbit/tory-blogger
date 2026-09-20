from pathlib import Path
from src.media import area_map as am, course_viz as cv, clip
from src.research.transit import RouteInfo, stops_as_pois

def test_places_order_matches_map():
    c = cv.sample_course(); pl = am.places_for_editor(c, c.stops, c.restaurants, c.parking)
    assert [p["query"] for p in pl[:4]] == ["우이동", "도선사", "백운봉암문", "백운대"] and pl[4]["kind"] == "정류장"
    assert "1. [코스] 우이동" in am.places_block(pl)

def test_stops_as_pois_dedup():
    rows = [RouteInfo("A", "1", "120", "일반", "0430", "2300", "8", lat=37.6, lon=127.0), RouteInfo("A", "1", "130", "일반", "0500", "2200", "9", lat=37.6, lon=127.0), RouteInfo("B", "2", "1", "지하철", "0530", "2350", "6")]
    assert [p["name"] for p in stops_as_pois(rows)] == ["A"]

def test_clip_gif(tmp_path):
    c = cv.sample_course(); cv.ensure_elevation(c, dry_run=True)
    r = clip.render(c, tmp_path / "c.gif", seconds=0.4, fps=5, mp4=False)
    assert Path(r["gif"]).stat().st_size > 10000
