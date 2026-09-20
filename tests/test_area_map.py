from pathlib import Path
from src.media import area_map as am, course_viz as cv

def test_area_map_and_gpx(tmp_path):
    c = cv.sample_course(); cv.ensure_elevation(c, dry_run=True)
    p = am.render(c, tmp_path / "a.png", c.stops, c.restaurants, c.parking); assert Path(p).stat().st_size > 5000
    g = am.to_gpx(c, tmp_path / "a.gpx"); t = g.read_text(encoding="utf-8")
    assert "<trkpt" in t and "<wpt" in t and "①" in t

def test_numbering_consistent():
    c = cv.sample_course(); wps = am.waypoints(c)
    assert wps[0][0].startswith("① ") and wps[-1][0].startswith("④ ") and wps[-1][2] == "mountain"
    assert "① 우이동" in cv.timeline_table(c) and "④ 백운대" in cv.timeline_table(c)
