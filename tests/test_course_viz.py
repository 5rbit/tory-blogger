from pathlib import Path
from src.media import course_viz as cv

def test_haversine_seoul_busan():
    assert 320 < cv.haversine_km((126.978, 37.5665), (129.0756, 35.1796)) < 330

def test_sample_course_lengths_and_timeline():
    c = cv.sample_course()
    assert abs(c.length_km - 3.8) < 0.01 and c.up_min == 120
    t = cv.timeline_table(c, "09:00", lunch_min=30)
    assert "| 09:00 |" in t and "| 11:00 | ④ 백운대 ⛰️" in t and "(하산" in t and "🥾" in t

def test_scores_in_range():
    sc = cv.difficulty_scores(cv.sample_course(), access=5, view=2)
    assert set(sc) == set(cv.AXES) and len(cv.AXES) == 6 and all(1 <= v <= 5 for v in sc.values()) and sc["접근성"] == 5
    assert sc["기술"] == 4   # 샘플 코스 마지막 구간 '어려움' → 4

def test_build_all_creates_files(tmp_path):
    res = cv.build_all(cv.sample_course(), tmp_path, dry_run=True)
    for k in ["profile", "radar", "card"]:
        assert Path(res[k]).exists() and Path(res[k]).stat().st_size > 1000
    assert (tmp_path / "timeline.md").exists()

def test_load_geojson_field_mapping(tmp_path):
    gj = {"type": "FeatureCollection", "features": [{"type": "Feature", "geometry": {"type": "LineString", "coordinates": [[127.0, 37.6], [127.01, 37.61]]},
          "properties": {"PMNTN_NM": "북한산", "PMNTN_MTRQ": "우이동→도선사", "PMNTN_LT": "1.8", "PMNTN_UPPL": "35", "PMNTN_GODN": "25", "PMNTN_DFFL": "쉬움"}}]}
    p = tmp_path / "t.geojson"; p.write_text(__import__("json").dumps(gj), encoding="utf-8")
    c = cv.find_course("북한산", trails_dir=tmp_path)
    assert c and c.segments[0].up_min == 35 and c.segments[0].difficulty == "쉬움"
    assert cv.find_course("없는산", trails_dir=tmp_path) is None
