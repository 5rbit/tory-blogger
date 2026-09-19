import base64, hashlib, hmac
from unittest.mock import MagicMock
import pytest
from src.research import naver_ad_api as api

def test_signature_matches_spec():
    sig = api._signature("1700000000000", "GET", "/keywordstool", "secret")
    expected = base64.b64encode(hmac.new(b"secret", b"1700000000000.GET./keywordstool", hashlib.sha256).digest()).decode()
    assert sig == expected

def test_headers_require_env(monkeypatch):
    monkeypatch.delenv("NAVER_AD_API_KEY", raising=False)
    with pytest.raises(RuntimeError):
        api._headers("GET", api.URI)

def test_headers_fields(monkeypatch):
    monkeypatch.setenv("NAVER_AD_API_KEY", "k"); monkeypatch.setenv("NAVER_AD_SECRET", "s"); monkeypatch.setenv("NAVER_AD_CUSTOMER_ID", "c")
    h = api._headers("GET", api.URI)
    assert {"X-Timestamp", "X-API-KEY", "X-Customer", "X-Signature"} <= h.keys()
    assert h["X-Customer"] == "c"

def test_parse_handles_lt10_and_comp():
    items = [{"relKeyword": "북한산 단풍", "monthlyPcQcCnt": 1200, "monthlyMobileQcCnt": "< 10", "compIdx": "낮음",
              "monthlyAvePcClkCnt": 3.5, "monthlyAveMobileClkCnt": 1},
             {"relKeyword": "x", "monthlyPcQcCnt": "< 10", "monthlyMobileQcCnt": "< 10", "compIdx": "높음"}]
    c = api.parse_keyword_list(items)
    assert c[0].volume == 1200 and c[0].competition == 0.3 and c[0].extra["mobile"] == 0
    assert c[1].volume == 0 and c[1].competition == 0.9

def test_query_chunks_hints_by_five(monkeypatch):
    monkeypatch.setenv("NAVER_AD_API_KEY", "k"); monkeypatch.setenv("NAVER_AD_SECRET", "s"); monkeypatch.setenv("NAVER_AD_CUSTOMER_ID", "c")
    monkeypatch.setattr(api.time, "sleep", lambda *_: None)
    sess = MagicMock()
    resp = MagicMock(status_code=200); resp.json.return_value = {"keywordList": [{"relKeyword": "a", "monthlyPcQcCnt": 1, "monthlyMobileQcCnt": 1}]}
    sess.get.return_value = resp
    out = api.query_keywordstool([f"k{i} 공백" for i in range(7)], session=sess)
    assert sess.get.call_count == 2 and len(out) == 2
    assert sess.get.call_args_list[0].kwargs["params"]["hintKeywords"] == "k0공백,k1공백,k2공백,k3공백,k4공백"

def test_fetch_uses_cache_and_filters(monkeypatch, tmp_path):
    monkeypatch.setenv("NAVER_AD_API_KEY", "k"); monkeypatch.setenv("NAVER_AD_SECRET", "s"); monkeypatch.setenv("NAVER_AD_CUSTOMER_ID", "c")
    monkeypatch.setattr(api, "cache_dir", lambda: tmp_path)
    calls = []
    monkeypatch.setattr(api, "query_keywordstool", lambda seeds: calls.append(1) or [
        {"relKeyword": "big", "monthlyPcQcCnt": 5000, "monthlyMobileQcCnt": 5000, "compIdx": "중간"},
        {"relKeyword": "big", "monthlyPcQcCnt": 5000, "monthlyMobileQcCnt": 5000, "compIdx": "중간"},
        {"relKeyword": "tiny", "monthlyPcQcCnt": 10, "monthlyMobileQcCnt": 10, "compIdx": "낮음"}])
    first = api.fetch_keyword_stats(["seed"])
    second = api.fetch_keyword_stats(["seed"])
    assert len(calls) == 1                       # 두 번째는 캐시
    assert [c.keyword for c in first] == ["big"] and [c.keyword for c in second] == ["big"]
