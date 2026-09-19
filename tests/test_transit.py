from unittest.mock import MagicMock
from src.research import transit as tr

def _resp(items):
    r = MagicMock(status_code=200); r.json.return_value = {"response": {"body": {"items": {"item": items}}}}; return r

def test_routes_near_chain(monkeypatch, tmp_path):
    monkeypatch.setenv("DATA_GO_KR_KEY", "k"); monkeypatch.setattr(tr, "_CACHE", tmp_path / "c.json"); monkeypatch.setattr(tr.time, "sleep", lambda *_: None)
    sess = MagicMock()
    sess.get.side_effect = [_resp([{"nodeid": "N1", "nodenm": "우이동", "nodeno": "10", "citycode": "31"}]),
                            _resp([{"routeid": "R1", "routeno": "120", "routetp": "일반"}, {"routeid": "R1", "routeno": "120"}]),
                            _resp({"routeno": "120", "routetp": "일반", "startvehicletime": "0430", "endvehicletime": "2300", "intervaltime": "8", "intervalsattime": "10", "startnodenm": "우이", "endnodenm": "시청"})]
    rows = tr.routes_near(37.66, 127.01, session=sess)
    assert len(rows) == 1 and rows[0].route_no == "120" and rows[0].hhmm(rows[0].first) == "04:30"
    assert tr.routes_near(37.66, 127.01, session=sess)[0].last == "2300"   # 캐시
    assert sess.get.call_count == 3

def test_markdown_dry_run_and_manual(monkeypatch, tmp_path):
    (tmp_path / "trailheads.yaml").write_text('테스트 들머리: {lat: 37.6, lon: 127.0, transit_manual: [{type: 지하철, stop: 우이신설선 북한산우이역, route: 우이신설, first: "05:30", last: "23:50", interval: 6, note: 2번 출구}]}\n', encoding="utf-8")
    monkeypatch.setattr(tr, "CONFIG", tmp_path)
    md = tr.to_markdown("테스트 들머리", "테스트 들머리", dry_run=True)
    assert "진입로" in md and "북한산우이역" in md and "05:30" in md and "(예시)" in md and "진출로" not in md
