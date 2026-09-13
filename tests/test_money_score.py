from src.common import KeywordCandidate as K
def test_competition_and_intent_raise_score():
    base = K(keyword="모니터", volume=1000, competition=0.3, personal_ratio=0.5)
    comp = K(keyword="모니터", volume=1000, competition=0.9, personal_ratio=0.5)
    intent = K(keyword="모니터 추천", volume=1000, competition=0.3, personal_ratio=0.5)
    w = ["추천"]
    assert comp.money_score(intent_words=w) > base.money_score(intent_words=w)
    assert intent.money_score(intent_words=w) > base.money_score(intent_words=w)
