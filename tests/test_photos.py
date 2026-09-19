from unittest.mock import MagicMock
from src.media import photos as ph

ITEMS = [{"galContentId": 1, "galTitle": "북한산 단풍", "galWebImageUrl": "http://x/1.jpg", "galPhotographer": "홍길동", "galPhotographyMonth": "202310"},
         {"galContentId": 2, "galTitle": "북한산 설경", "galWebImageUrl": "http://x/2.jpg", "galPhotographer": "", "galPhotographyMonth": "202201"},
         {"galContentId": 3, "galTitle": "없는 URL"}]

def test_parse_skips_missing_url():
    assert [p.id for p in ph.parse_items(ITEMS)] == ["1", "2"]

def test_search_sorts_by_month(monkeypatch):
    monkeypatch.setenv("DATA_GO_KR_KEY", "k")
    sess = MagicMock(); resp = MagicMock(status_code=200)
    resp.json.return_value = {"response": {"body": {"items": {"item": ITEMS}}}}
    sess.get.return_value = resp
    got = ph.search("북한산", month=12, session=sess)
    assert got[0].id == "2"          # 1월이 12월에 더 가깝다

def test_fill_slots_and_attribution():
    md = "# 제목\n\n[사진: 정상]\n\n본문\n\n[사진: 하산]\n\n[사진: 남는 슬롯]\n"
    out, n = ph.fill_slots(md, ph.parse_items(ITEMS))
    assert n == 2 and "![정상](http://x/1.jpg)" in out and "공공누리 1유형" in out and "[사진: 남는 슬롯]" in out
    assert "촬영자 미상" in out
