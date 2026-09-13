from unittest.mock import MagicMock
import pytest
from src.common import KeywordCandidate
from src.research import naver_search_api as api

def test_is_personal():
    assert api.is_personal({"bloggerlink": "https://blog.naver.com/tory123"})
    assert not api.is_personal({"bloggerlink": "https://blog.naver.com/samsung_official"})
    assert not api.is_personal({"bloggerlink": "https://foo.tistory.com"})
    assert not api.is_personal({"link": "https://company.com/post"})

def test_analyze():
    items = [{"bloggerlink": "https://blog.naver.com/a", "title": "<b>AI</b> 도구", "description": "x" * 50, "postdate": "20990101"},
             {"bloggerlink": "https://blog.naver.com/brand_store", "title": "t", "description": "", "postdate": "20100101"},
             {"link": "https://b.tistory.com/1", "title": "t", "description": "yy", "postdate": "20990101"}]
    a = api.analyze(items)
    assert a["personal_ratio"] == pytest.approx(1 / 3)
    assert a["naver_ratio"] == pytest.approx(2 / 3)
    assert a["top_titles"][0] == "AI 도구"
    assert a["avg_desc_len"] == 17

def test_headers_require_env(monkeypatch):
    for k in ["NAVER_CLIENT_ID", "NAVER_CLIENT_SECRET", "NAVER_NCP_KEY_ID", "NAVER_NCP_KEY"]:
        monkeypatch.delenv(k, raising=False)
    with pytest.raises(RuntimeError):
        api._headers()

def test_hub_preferred_over_legacy(monkeypatch):
    monkeypatch.setenv("NAVER_CLIENT_ID", "i"); monkeypatch.setenv("NAVER_CLIENT_SECRET", "s")
    monkeypatch.setenv("NAVER_NCP_KEY_ID", "hid"); monkeypatch.setenv("NAVER_NCP_KEY", "hkey")
    url, h = api._endpoint()
    assert url == api.HUB_URL and h["X-NCP-APIGW-API-KEY-ID"] == "hid"
    monkeypatch.delenv("NAVER_NCP_KEY_ID"); monkeypatch.delenv("NAVER_NCP_KEY")
    url, h = api._endpoint()
    assert url == api.LEGACY_URL and h["X-Naver-Client-Id"] == "i"

def test_enrich_uses_cache(monkeypatch, tmp_path):
    monkeypatch.setenv("NAVER_NCP_KEY_ID", "i"); monkeypatch.setenv("NAVER_NCP_KEY", "s")
    monkeypatch.setattr(api, "cache_dir", lambda: tmp_path)
    monkeypatch.setattr(api.time, "sleep", lambda *_: None)
    calls = []
    monkeypatch.setattr(api, "search_blog", lambda q, session=None: calls.append(q) or [{"bloggerlink": "https://blog.naver.com/p"}])
    c = [KeywordCandidate(keyword="k1"), KeywordCandidate(keyword="k2")]
    api.enrich_with_serp(c); api.enrich_with_serp([KeywordCandidate(keyword="k1")])
    assert calls == ["k1", "k2"]
    assert c[0].personal_ratio == 1.0 and "serp" in c[0].extra

def test_search_blog_error(monkeypatch):
    monkeypatch.setenv("NAVER_NCP_KEY_ID", "i"); monkeypatch.setenv("NAVER_NCP_KEY", "s")
    sess = MagicMock(); sess.get.return_value = MagicMock(status_code=401, text="bad")
    with pytest.raises(RuntimeError):
        api.search_blog("q", session=sess)
