from unittest.mock import MagicMock
from src.research import seoul_bus as sb, transit as tr

def _r(items, code="0"):
    r = MagicMock(status_code=200); r.json.return_value = {"msgHeader": {"headerCd": code, "headerMsg": ""}, "msgBody": {"itemList": items}}; return r

def test_in_seoul():
    assert sb.in_seoul(37.6625, 127.0129) and not sb.in_seoul(38.17, 128.49)

def test_routes_near_chain(monkeypatch):
    monkeypatch.setenv("DATA_GO_KR_KEY", "k"); monkeypatch.setattr(sb.time, "sleep", lambda *_: None)
    sess = MagicMock()
    sess.get.side_effect = [_r([{"stationNm": "우이동", "arsId": "09123", "dist": "120"}, {"stationNm": "먼곳", "arsId": "0", "dist": "400"}]),
                            _r([{"busRouteId": "100100", "busRouteNm": "120", "busRouteType": "3"}]),
                            _r([{"busRouteNm": "120", "routeType": "3", "firstBusTm": "20260919043000", "lastBusTm": "20260919230000", "term": "8", "stStationNm": "우이동", "edStationNm": "시청"}])]
    rows = sb.routes_near(37.66, 127.01, session=sess)
    assert len(rows) == 1 and rows[0].route_type == "간선" and rows[0].hhmm(rows[0].first) == "04:30" and rows[0].last == "2300"

def test_transit_for_uses_seoul_and_caches(monkeypatch, tmp_path):
    monkeypatch.setenv("DATA_GO_KR_KEY", "k"); monkeypatch.setattr(tr, "_CACHE", tmp_path / "c.json")
    (tmp_path / "trailheads.yaml").write_text("서울들머리: {lat: 37.66, lon: 127.01}\n지방들머리: {lat: 38.17, lon: 128.49}\n", encoding="utf-8")
    monkeypatch.setattr(tr, "CONFIG", tmp_path)
    calls = {"seoul": 0, "tago": 0}
    monkeypatch.setattr(sb, "routes_near", lambda lat, lon, **k: calls.__setitem__("seoul", calls["seoul"] + 1) or [tr.RouteInfo("s", "1", "120", "간선", "0430", "2300", "8", source="서울버스")])
    monkeypatch.setattr(tr, "routes_near", lambda lat, lon, **k: calls.__setitem__("tago", calls["tago"] + 1) or [])
    assert tr.transit_for("서울들머리")[0].source == "서울버스"
    tr.transit_for("서울들머리"); tr.transit_for("지방들머리")
    assert calls == {"seoul": 1, "tago": 1}
